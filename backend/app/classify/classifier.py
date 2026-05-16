"""Classify each Building: status + confidence + area.

Run after the resolver. Reads Building + its Links; writes back status, confidence, area_m2.

    uv run python -m app.classify.classifier
"""
from __future__ import annotations

import logging
import math
from datetime import datetime, timezone

from shapely.wkt import loads as wkt_loads
from sqlalchemy import select

from app.config import get_settings
from app.db import SessionLocal
from app.ontology.models import (
    Building,
    BuildingStatus,
    EntityType,
    Link,
    LinkType,
    ObservedBuilding,
    ReviewCase,
    ReviewStatus,
)

log = logging.getLogger(__name__)

# Minimum confidence to auto-open a ReviewCase for an observed_only building.
REVIEW_OPEN_CONF = 0.60
# Minimum observed area to be considered a serious illegal-construction signal.
# Smaller structures (sheds, carports) often legitimately aren't in DGU and aren't worth a review case.
MIN_AREA_M2 = 25.0
REVIEW_MIN_AREA_M2 = 25.0


def _approx_area_m2(geom_wkt: str, lat: float) -> float:
    g = wkt_loads(geom_wkt)
    deg2m_lat = 111_320.0
    deg2m_lon = 111_320.0 * math.cos(math.radians(lat))
    return float(g.area) * deg2m_lat * deg2m_lon


def _confidence(n_observed: int, n_registered: int, distinct_obs_sources: int) -> float:
    """Heuristic. Anchored at 0.5 for a single-source observed building."""
    score = 0.0
    if n_registered > 0 and n_observed > 0:
        score = 0.95  # both sides agree — high trust
    elif n_observed >= 2:
        score = 0.75 + 0.1 * (distinct_obs_sources - 1)  # multiple independent observers
    elif n_observed == 1:
        score = 0.50
    elif n_registered > 0:
        score = 0.40  # registered but unseen — could be demolished, could be small/occluded
    return max(0.0, min(1.0, score))


def classify_all() -> dict[str, int]:
    settings = get_settings()
    pilot_lat = (settings.pilot_bbox_miny + settings.pilot_bbox_maxy) / 2

    stats = {b.value: 0 for b in BuildingStatus}
    stats["reviews_opened"] = 0
    now = datetime.now(timezone.utc)

    with SessionLocal() as db:
        # Index observed sources per building.
        obs_links = db.execute(
            select(Link.src_id, Link.dst_id)
            .where(Link.src_type == EntityType.BUILDING, Link.link_type == LinkType.BUILDING_OBSERVED_AS)
        ).all()
        reg_links = db.execute(
            select(Link.src_id, Link.dst_id)
            .where(Link.src_type == EntityType.BUILDING, Link.link_type == LinkType.BUILDING_REGISTERED_AS)
        ).all()

        obs_by_building: dict[str, list[str]] = {}
        for bid, dst in obs_links:
            obs_by_building.setdefault(bid, []).append(dst)
        reg_by_building: dict[str, list[str]] = {}
        for bid, dst in reg_links:
            reg_by_building.setdefault(bid, []).append(dst)

        # Source name lookup for distinctness.
        obs_source_by_id = {
            o.id: o.source
            for o in db.scalars(select(ObservedBuilding)).all()
        }

        for b in db.scalars(select(Building)).all():
            obs_ids = obs_by_building.get(b.id, [])
            reg_ids = reg_by_building.get(b.id, [])
            distinct_obs_sources = len({obs_source_by_id.get(oid, "?") for oid in obs_ids})

            # Status.
            if obs_ids and reg_ids:
                status = BuildingStatus.REGISTERED_AND_OBSERVED
            elif obs_ids and not reg_ids:
                status = BuildingStatus.OBSERVED_ONLY
            elif reg_ids and not obs_ids:
                status = BuildingStatus.REGISTERED_ONLY
            else:
                status = BuildingStatus.UNKNOWN

            area = _approx_area_m2(b.geometry_wkt, pilot_lat)
            conf = _confidence(len(obs_ids), len(reg_ids), distinct_obs_sources)

            # Tiny footprints are noise unless multi-source confirmed.
            if area < MIN_AREA_M2 and distinct_obs_sources < 2:
                conf *= 0.5

            b.area_m2 = area
            b.status = status
            b.confidence = conf
            b.classified_at = now
            stats[status.value] += 1

            # Auto-open a ReviewCase for high-confidence, non-trivial observed_only buildings.
            # Human-in-the-loop rule: never notify the owner directly.
            if (
                status == BuildingStatus.OBSERVED_ONLY
                and conf >= REVIEW_OPEN_CONF
                and area >= REVIEW_MIN_AREA_M2
            ):
                existing = db.scalar(select(ReviewCase).where(ReviewCase.building_id == b.id))
                if existing is None:
                    db.add(
                        ReviewCase(
                            id=f"rc:{b.id[len('building:'):]}",
                            building_id=b.id,
                            parcel_id=b.parcel_id,
                            status=ReviewStatus.OPEN,
                            reason=(
                                f"Observed in {distinct_obs_sources} imagery source(s) "
                                f"but absent from DGU registry. Area ≈ {area:.0f} m²."
                            ),
                            opened_at=now,
                        )
                    )
                    stats["reviews_opened"] += 1

        db.commit()
    log.info("Classify: %s", stats)
    return stats


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    stats = classify_all()
    print(f"Classify done: {stats}")
