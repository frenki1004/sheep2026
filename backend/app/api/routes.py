"""REST query API over the ontology.

GeoJSON-flavored responses for direct map consumption.
"""
from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from shapely.geometry import box, mapping
from shapely.geometry.base import BaseGeometry
from shapely.wkt import loads as wkt_loads
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.llm.ask import ask as nl_ask
from app.llm.explain import explain as nl_explain
from app.ontology.models import (
    Building,
    BuildingStatus,
    EntityType,
    Link,
    LinkType,
    ObservedBuilding,
    Parcel,
    RegisteredBuilding,
    ReviewCase,
)

router = APIRouter()


def _parse_bbox(bbox: str | None) -> tuple[float, float, float, float] | None:
    if not bbox:
        return None
    parts = [p.strip() for p in bbox.split(",")]
    if len(parts) != 4:
        raise HTTPException(400, "bbox must be 'minLon,minLat,maxLon,maxLat'")
    try:
        return tuple(float(p) for p in parts)  # type: ignore[return-value]
    except ValueError:
        raise HTTPException(400, "bbox values must be floats")


def _feature(geom: BaseGeometry, properties: dict[str, Any], id_: str) -> dict[str, Any]:
    return {
        "type": "Feature",
        "id": id_,
        "geometry": mapping(geom),
        "properties": properties,
    }


@router.get("/buildings")
def list_buildings(
    bbox: str | None = Query(None, description="minLon,minLat,maxLon,maxLat"),
    status: BuildingStatus | None = Query(None),
    parcel_id: str | None = Query(None),
    min_area_m2: float | None = Query(None, ge=0),
    min_confidence: float | None = Query(None, ge=0, le=1),
    limit: int = Query(5000, ge=1, le=20000),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """GeoJSON FeatureCollection of buildings."""
    stmt = select(Building)
    if status:
        stmt = stmt.where(Building.status == status)
    if parcel_id:
        stmt = stmt.where(Building.parcel_id == parcel_id)
    if min_area_m2 is not None:
        stmt = stmt.where(Building.area_m2 >= min_area_m2)
    if min_confidence is not None:
        stmt = stmt.where(Building.confidence >= min_confidence)
    stmt = stmt.limit(limit)

    bbox_poly = box(*_parse_bbox(bbox)) if bbox else None
    features: list[dict[str, Any]] = []
    for b in db.scalars(stmt):
        geom = wkt_loads(b.geometry_wkt)
        if bbox_poly is not None and not bbox_poly.intersects(geom):
            continue
        features.append(_feature(
            geom,
            {
                "status": b.status.value,
                "confidence": round(b.confidence, 2),
                "area_m2": round(b.area_m2, 1) if b.area_m2 is not None else None,
                "parcel_id": b.parcel_id,
            },
            b.id,
        ))
    return {"type": "FeatureCollection", "features": features, "count": len(features)}


@router.get("/buildings/stats")
def building_stats(db: Session = Depends(get_db)) -> dict[str, Any]:
    """Counts by status — for the dashboard summary header."""
    rows = db.execute(
        select(Building.status, func.count(Building.id)).group_by(Building.status)
    ).all()
    return {row[0].value: row[1] for row in rows}


@router.get("/buildings/{building_id}/evidence")
def building_evidence(building_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    b = db.scalar(select(Building).where(Building.id == building_id))
    if not b:
        raise HTTPException(404, "Building not found")

    # Observed evidence.
    obs_link_dsts = [
        l.dst_id for l in db.scalars(
            select(Link).where(
                Link.src_id == b.id,
                Link.link_type == LinkType.BUILDING_OBSERVED_AS,
            )
        )
    ]
    observed = []
    for o in db.scalars(select(ObservedBuilding).where(ObservedBuilding.id.in_(obs_link_dsts))):
        observed.append({
            "id": o.id,
            "source": o.source,
            "source_id": o.source_id,
            "height_m": o.height_m,
            "raw_attributes": json.loads(o.raw_attributes) if o.raw_attributes else None,
        })

    # Registered evidence.
    reg_link_dsts = [
        l.dst_id for l in db.scalars(
            select(Link).where(
                Link.src_id == b.id,
                Link.link_type == LinkType.BUILDING_REGISTERED_AS,
            )
        )
    ]
    registered = []
    for r in db.scalars(select(RegisteredBuilding).where(RegisteredBuilding.id.in_(reg_link_dsts))):
        registered.append({
            "id": r.id,
            "source": r.source,
            "source_id": r.source_id,
            "permit_ref": r.permit_ref,
            "year_built": r.year_built,
        })

    # Parcel context.
    parcel_info = None
    if b.parcel_id:
        p = db.scalar(select(Parcel).where(Parcel.id == b.parcel_id))
        if p:
            parcel_info = {
                "id": p.id,
                "source": p.source,
                "ko_id": p.ko_id,
                "ko_naziv": p.ko_naziv,
                "broj_cestice": p.broj_cestice,
                "area_m2": p.area_m2,
                "land_use": p.land_use,
            }

    return {
        "id": b.id,
        "status": b.status.value,
        "confidence": b.confidence,
        "area_m2": b.area_m2,
        "geometry": mapping(wkt_loads(b.geometry_wkt)),
        "parcel": parcel_info,
        "observed": observed,
        "registered": registered,
        "review_open": db.scalar(
            select(func.count(ReviewCase.id)).where(ReviewCase.building_id == b.id)
        ) > 0,
    }


@router.get("/parcels")
def list_parcels(
    bbox: str | None = Query(None),
    source: str | None = Query(None),
    limit: int = Query(2000, ge=1, le=10000),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    stmt = select(Parcel)
    if source:
        stmt = stmt.where(Parcel.source == source)
    stmt = stmt.limit(limit)

    bbox_poly = box(*_parse_bbox(bbox)) if bbox else None
    features = []
    for p in db.scalars(stmt):
        geom = wkt_loads(p.geometry_wkt)
        if bbox_poly is not None and not bbox_poly.intersects(geom):
            continue
        features.append(_feature(
            geom,
            {
                "source": p.source,
                "ko_id": p.ko_id,
                "broj_cestice": p.broj_cestice,
                "land_use": p.land_use,
                "area_m2": p.area_m2,
            },
            p.id,
        ))
    return {"type": "FeatureCollection", "features": features, "count": len(features)}


class AskRequest(BaseModel):
    question: str = Field(min_length=2, max_length=500)


@router.post("/ask")
def ask_endpoint(req: AskRequest) -> dict[str, Any]:
    """Natural-language → ontology query → answer + highlighted buildings."""
    try:
        return nl_ask(req.question)
    except RuntimeError as err:
        raise HTTPException(503, str(err))


@router.get("/buildings/{building_id}/explain")
def building_explain(building_id: str) -> dict[str, Any]:
    """Claude-generated analyst note explaining the building's classification."""
    try:
        return nl_explain(building_id)
    except KeyError:
        raise HTTPException(404, "Building not found")
    except RuntimeError as err:
        raise HTTPException(503, str(err))


@router.get("/review-cases")
def list_review_cases(
    status: str | None = Query(None),
    limit: int = Query(200, ge=1, le=2000),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    stmt = select(ReviewCase)
    if status:
        stmt = stmt.where(ReviewCase.status == status)
    stmt = stmt.order_by(ReviewCase.opened_at.desc()).limit(limit)
    cases = [
        {
            "id": rc.id,
            "building_id": rc.building_id,
            "parcel_id": rc.parcel_id,
            "status": rc.status.value,
            "reason": rc.reason,
            "opened_at": rc.opened_at.isoformat() if rc.opened_at else None,
        }
        for rc in db.scalars(stmt)
    ]
    return {"cases": cases, "count": len(cases)}
