"""Resolve observed + registered footprints into canonical Building entities.

Run:
    uv run python -m app.resolve.resolver
"""
from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from typing import Iterable

import math

from shapely.geometry import shape
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union
from shapely.strtree import STRtree
from shapely.wkt import loads as wkt_loads
from sqlalchemy import delete, select

from app.db import SessionLocal
from app.ontology.models import (
    Building,
    BuildingStatus,
    EntityType,
    Link,
    LinkType,
    ObservedBuilding,
    Parcel,
    RegisteredBuilding,
)

log = logging.getLogger(__name__)

# IoU threshold for deciding two footprints describe the same building.
# 0.20 — DGU geometries can drift 2–5m from imagery (different base maps).
# We pair IoU with a centroid-distance fallback (CENTROID_DIST_M) so close
# but non-overlapping pairs still merge — common for small auxiliary structures.
IOU_THRESHOLD = 0.20
CENTROID_DIST_M = 8.0
# Approximate metres per degree latitude at Split's latitude (~43.5°N).
_M_PER_DEG_LAT = 111_320.0
_M_PER_DEG_LON_AT_43_5 = _M_PER_DEG_LAT * math.cos(math.radians(43.5))


def _centroid_dist_m(a: BaseGeometry, b: BaseGeometry) -> float:
    ca, cb = a.centroid, b.centroid
    dlon_m = (ca.x - cb.x) * _M_PER_DEG_LON_AT_43_5
    dlat_m = (ca.y - cb.y) * _M_PER_DEG_LAT
    return math.hypot(dlon_m, dlat_m)


@dataclass
class _Node:
    """One footprint in the resolution graph."""
    key: str          # composite "obs:<id>" or "reg:<id>"
    kind: str         # "obs" | "reg"
    entity_id: str    # the underlying ObservedBuilding.id or RegisteredBuilding.id
    source: str
    geom: BaseGeometry


class _UnionFind:
    def __init__(self) -> None:
        self.parent: dict[str, str] = {}

    def add(self, k: str) -> None:
        self.parent.setdefault(k, k)

    def find(self, k: str) -> str:
        # Iterative path compression.
        root = k
        while self.parent[root] != root:
            root = self.parent[root]
        cur = k
        while self.parent[cur] != root:
            nxt = self.parent[cur]
            self.parent[cur] = root
            cur = nxt
        return root

    def union(self, a: str, b: str) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[ra] = rb

    def groups(self) -> dict[str, list[str]]:
        out: dict[str, list[str]] = {}
        for k in self.parent:
            r = self.find(k)
            out.setdefault(r, []).append(k)
        return out


def _iou(a: BaseGeometry, b: BaseGeometry) -> float:
    if not a.intersects(b):
        return 0.0
    inter = a.intersection(b).area
    if inter == 0.0:
        return 0.0
    union = a.area + b.area - inter
    return inter / union if union > 0 else 0.0


def _stable_building_id(member_keys: Iterable[str]) -> str:
    h = hashlib.sha1("|".join(sorted(member_keys)).encode()).hexdigest()[:24]
    return f"building:{h}"


def _load_nodes(db) -> list[_Node]:
    nodes: list[_Node] = []
    for ob in db.scalars(select(ObservedBuilding)).all():
        try:
            geom = wkt_loads(ob.geometry_wkt)
        except Exception:
            continue
        if geom.is_empty:
            continue
        nodes.append(_Node(key=f"obs:{ob.id}", kind="obs", entity_id=ob.id, source=ob.source, geom=geom))
    for rb in db.scalars(select(RegisteredBuilding)).all():
        if not rb.geometry_wkt:
            continue
        try:
            geom = wkt_loads(rb.geometry_wkt)
        except Exception:
            continue
        if geom.is_empty:
            continue
        nodes.append(_Node(key=f"reg:{rb.id}", kind="reg", entity_id=rb.id, source=rb.source, geom=geom))
    return nodes


def _find_parcel_for_centroid(centroid, parcels: list[tuple[str, BaseGeometry]]) -> str | None:
    # Pilot is ~500 parcels — linear scan is fine; if it grows, prebuild an STRtree of parcels.
    for pid, poly in parcels:
        if poly.contains(centroid):
            return pid
    return None


def resolve_all() -> dict[str, int]:
    """Idempotently re-resolve all observed + registered into Buildings + Links.

    Returns counts of (buildings, links) written.
    """
    stats = {"buildings": 0, "links": 0, "components": 0}

    with SessionLocal() as db:
        # Wipe prior resolution. Idempotent.
        db.execute(delete(Link).where(Link.link_type.in_([
            LinkType.BUILDING_OBSERVED_AS,
            LinkType.BUILDING_REGISTERED_AS,
            LinkType.PARCEL_CONTAINS_BUILDING,
        ])))
        db.execute(delete(Building))
        db.commit()

        nodes = _load_nodes(db)
        log.info("Loaded %d footprint nodes (%d observed, %d registered)",
                 len(nodes),
                 sum(1 for n in nodes if n.kind == "obs"),
                 sum(1 for n in nodes if n.kind == "reg"))

        if not nodes:
            return stats

        # STRtree for candidate-pair generation.
        geoms = [n.geom for n in nodes]
        tree = STRtree(geoms)

        uf = _UnionFind()
        for n in nodes:
            uf.add(n.key)

        # For each node, query candidates and union if IoU >= threshold OR centroids are close.
        for i, n in enumerate(nodes):
            cand_idxs = tree.query(n.geom)
            for j in cand_idxs:
                if int(j) <= i:
                    continue
                m = nodes[int(j)]
                if _iou(n.geom, m.geom) >= IOU_THRESHOLD:
                    uf.union(n.key, m.key)
                elif _centroid_dist_m(n.geom, m.geom) <= CENTROID_DIST_M:
                    # Sanity: only merge by centroid if both footprints are roughly comparable size.
                    a_area, b_area = n.geom.area, m.geom.area
                    if a_area > 0 and b_area > 0:
                        ratio = max(a_area, b_area) / min(a_area, b_area)
                        if ratio <= 4.0:
                            uf.union(n.key, m.key)

        groups = uf.groups()
        stats["components"] = len(groups)
        log.info("Formed %d connected components", len(groups))

        # Preload parcels for centroid-in-parcel lookup.
        parcels = [
            (p.id, wkt_loads(p.geometry_wkt))
            for p in db.scalars(select(Parcel)).all()
            if p.geometry_wkt
        ]
        log.info("Loaded %d parcels for containment lookup", len(parcels))

        by_key = {n.key: n for n in nodes}
        for _root, members in groups.items():
            obs_members = [by_key[k] for k in members if by_key[k].kind == "obs"]
            reg_members = [by_key[k] for k in members if by_key[k].kind == "reg"]

            # Geometry: prefer the union of observed footprints; fall back to registered.
            source_geoms = [n.geom for n in obs_members] if obs_members else [n.geom for n in reg_members]
            merged = unary_union(source_geoms)
            if merged.is_empty:
                continue
            # If union produced a MultiPolygon, take the largest part as the canonical footprint.
            if merged.geom_type == "MultiPolygon":
                merged = max(merged.geoms, key=lambda g: g.area)

            bid = _stable_building_id(members)
            parcel_id = _find_parcel_for_centroid(merged.centroid, parcels)

            db.add(
                Building(
                    id=bid,
                    parcel_id=parcel_id,
                    geometry_wkt=merged.wkt,
                    area_m2=None,  # filled in by the classify pass
                    status=BuildingStatus.UNKNOWN,
                    confidence=0.0,
                )
            )
            stats["buildings"] += 1

            for n in obs_members:
                db.add(Link(
                    src_type=EntityType.BUILDING, src_id=bid,
                    link_type=LinkType.BUILDING_OBSERVED_AS,
                    dst_type=EntityType.OBSERVED_BUILDING, dst_id=n.entity_id,
                ))
                stats["links"] += 1
            for n in reg_members:
                db.add(Link(
                    src_type=EntityType.BUILDING, src_id=bid,
                    link_type=LinkType.BUILDING_REGISTERED_AS,
                    dst_type=EntityType.REGISTERED_BUILDING, dst_id=n.entity_id,
                ))
                stats["links"] += 1
            if parcel_id:
                db.add(Link(
                    src_type=EntityType.PARCEL, src_id=parcel_id,
                    link_type=LinkType.PARCEL_CONTAINS_BUILDING,
                    dst_type=EntityType.BUILDING, dst_id=bid,
                ))
                stats["links"] += 1

        db.commit()
    log.info("Resolve: %s", stats)
    return stats


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    stats = resolve_all()
    print(f"Resolve done: {stats}")
