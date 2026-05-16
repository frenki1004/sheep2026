"""OSM buildings adapter via Overpass API.

Pulls `building=*` ways inside the pilot bbox, writes one ObservedBuilding row per
polygon with source='osm'. OSM tags (building category, addr:*, start_date, height)
are stashed in raw_attributes as JSON for downstream classification.

Multipolygon relations (rare in residential Split) are skipped — handle in a follow-up
if the resolve layer needs them.

Run:
    uv run python -m app.ingest.osm
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from shapely.geometry import Polygon
from sqlalchemy import select

from app.config import get_settings
from app.db import SessionLocal
from app.ontology.models import ObservedBuilding

log = logging.getLogger(__name__)

SOURCE = "osm"
USER_AGENT = "Sheep-AI/0.1 (hackathon; contact via repo)"
OVERPASS_ENDPOINTS = (
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
)


def _build_query(bbox_4326: tuple[float, float, float, float]) -> str:
    minx, miny, maxx, maxy = bbox_4326
    # Overpass bbox order is south,west,north,east (lat,lon).
    bbox = f"{miny},{minx},{maxy},{maxx}"
    return f"""
        [out:json][timeout:90];
        (
          way["building"]({bbox});
        );
        out tags geom;
    """.strip()


def _fetch(query: str) -> dict[str, Any]:
    last_err: Exception | None = None
    for endpoint in OVERPASS_ENDPOINTS:
        try:
            data = urlencode({"data": query}).encode("utf-8")
            req = Request(
                endpoint,
                data=data,
                headers={"User-Agent": USER_AGENT, "Content-Type": "application/x-www-form-urlencoded"},
            )
            log.info("Querying %s ...", endpoint)
            with urlopen(req, timeout=120) as resp:  # noqa: S310 — trusted endpoint
                return json.loads(resp.read())
        except Exception as err:
            log.warning("Overpass endpoint %s failed: %s", endpoint, err)
            last_err = err
    raise RuntimeError(f"All Overpass endpoints failed: {last_err}")


def _stable_id(osm_id: int) -> str:
    h = hashlib.sha1(f"way:{osm_id}".encode()).hexdigest()[:24]
    return f"{SOURCE}:{h}"


def ingest(bbox_4326: tuple[float, float, float, float] | None = None) -> int:
    settings = get_settings()
    if bbox_4326 is None:
        bbox_4326 = settings.pilot_bbox

    query = _build_query(bbox_4326)
    payload = _fetch(query)
    elements = payload.get("elements", [])
    log.info("Overpass returned %d elements", len(elements))

    now = datetime.now(timezone.utc)
    inserted = 0

    with SessionLocal() as db:
        for el in elements:
            if el.get("type") != "way":
                continue
            geom_pts = el.get("geometry") or []
            if len(geom_pts) < 4:  # need a closed ring
                continue
            # OSM may not auto-close; Polygon requires the first/last match.
            coords = [(pt["lon"], pt["lat"]) for pt in geom_pts]
            if coords[0] != coords[-1]:
                coords.append(coords[0])
            try:
                poly = Polygon(coords)
                if not poly.is_valid:
                    poly = poly.buffer(0)
                if poly.is_empty:
                    continue
            except Exception as err:
                log.debug("Skipping malformed way %s: %s", el.get("id"), err)
                continue

            tags = el.get("tags") or {}
            osm_id = el.get("id")
            bid = _stable_id(osm_id)
            geom_wkt = poly.wkt

            # Crude start_date → datetime parse (OSM is heterogeneous: "2015", "2015-06", etc.)
            first_seen: datetime | None = None
            sd = tags.get("start_date")
            if sd and len(sd) >= 4 and sd[:4].isdigit():
                try:
                    first_seen = datetime(int(sd[:4]), 1, 1, tzinfo=timezone.utc)
                except ValueError:
                    pass

            height_m: float | None = None
            h = tags.get("height")
            if h:
                try:
                    height_m = float(h.split()[0])  # strip units like "12 m"
                except ValueError:
                    pass

            existing = db.scalar(select(ObservedBuilding).where(ObservedBuilding.id == bid))
            raw_attrs = json.dumps(
                {k: tags[k] for k in tags if k in {
                    "building", "building:levels", "addr:street", "addr:housenumber",
                    "addr:city", "name", "amenity", "start_date", "height",
                }},
                ensure_ascii=False,
            )
            if existing:
                existing.geometry_wkt = geom_wkt
                existing.height_m = height_m
                existing.first_seen = first_seen or existing.first_seen
                existing.last_seen = now
                existing.raw_attributes = raw_attrs
            else:
                db.add(
                    ObservedBuilding(
                        id=bid,
                        source=SOURCE,
                        source_id=f"way:{osm_id}",
                        geometry_wkt=geom_wkt,
                        height_m=height_m,
                        first_seen=first_seen,
                        last_seen=now,
                        raw_attributes=raw_attrs,
                    )
                )
                inserted += 1
        db.commit()

    log.info("Ingested %d new OSM buildings", inserted)
    return inserted


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    n = ingest()
    print(f"OSM: {n} buildings ingested.")
