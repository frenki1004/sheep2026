from __future__ import annotations

from typing import Any

from split_ontology.parcel_queue import PRIORITY_TYPES, _building_centroid, _point_in_geometry


LARGE_FOOTPRINT_M2 = 250


def build_priority_case_payload(
    dataset: Any,
    *,
    limit: int = 100,
    offset: int = 0,
) -> dict[str, Any]:
    parcel_id_by_building_id = _parcel_assignments(dataset)
    cases = sorted(
        (
            _priority_case(feature, parcel_id_by_building_id.get(feature["id"]))
            for feature in dataset.buildings["features"]
            if feature["properties"]["discrepancy_type"] in PRIORITY_TYPES
        ),
        key=lambda item: (
            -item["impact_score"],
            -item["area_m2"],
            -item["confidence"],
            item["id"],
        ),
    )
    parcel_ids_with_priority = {
        parcel_id for parcel_id in parcel_id_by_building_id.values() if parcel_id is not None
    }
    return {
        "type": "PriorityCaseList",
        "total": len(cases),
        "limit": limit,
        "offset": offset,
        "parcel_sample": {
            "loaded_parcels": len(dataset.parcels["features"]),
            "flagged_parcels": len(parcel_ids_with_priority),
            "priority_buildings_in_loaded_parcels": len(parcel_id_by_building_id),
        },
        "items": cases[offset : offset + limit],
    }


def _parcel_assignments(dataset: Any) -> dict[str, str]:
    assignments = {}
    priority_features = [
        feature
        for feature in dataset.buildings["features"]
        if feature["properties"]["discrepancy_type"] in PRIORITY_TYPES
    ]
    for parcel in dataset.parcels["features"]:
        parcel_id = parcel.get("properties", {}).get("parcel_id", "unknown")
        parcel_geometry = parcel.get("geometry") or {}
        for feature in priority_features:
            if feature["id"] in assignments:
                continue
            if _point_in_geometry(_building_centroid(feature), parcel_geometry):
                assignments[feature["id"]] = parcel_id
    return assignments


def _priority_case(feature: dict[str, Any], parcel_id: str | None) -> dict[str, Any]:
    properties = feature["properties"]
    area_m2 = round(float(properties.get("area_m2") or 0))
    confidence = float(properties.get("confidence") or 0)
    discrepancy_type = properties["discrepancy_type"]
    impact_score = _impact_score(
        area_m2=area_m2,
        confidence=confidence,
        discrepancy_type=discrepancy_type,
    )
    return {
        "id": feature["id"],
        "discrepancy_type": discrepancy_type,
        "area_m2": area_m2,
        "confidence": confidence,
        "land_zone": properties.get("land_zone") or "unknown",
        "parcel_id": parcel_id,
        "impact_score": impact_score,
        "risk_level": _risk_level(impact_score),
        "reasons": _reasons(discrepancy_type, area_m2),
        "bbox": list(_bbox_for_geometry(feature.get("geometry") or {})),
    }


def _impact_score(*, area_m2: int, confidence: float, discrepancy_type: str) -> int:
    score = (area_m2 * confidence) + 25
    if discrepancy_type == "protected_land":
        score += 50
    return round(score)


def _risk_level(impact_score: int) -> str:
    if impact_score >= 200:
        return "high"
    if impact_score > 0:
        return "elevated"
    return "none"


def _reasons(discrepancy_type: str, area_m2: int) -> list[str]:
    reasons = [discrepancy_type]
    if area_m2 >= LARGE_FOOTPRINT_M2:
        reasons.append("large_footprint")
    return reasons


def _bbox_for_geometry(geometry: dict[str, Any]) -> tuple[float, float, float, float]:
    points = list(_iter_positions(geometry))
    return (
        min(point[0] for point in points),
        min(point[1] for point in points),
        max(point[0] for point in points),
        max(point[1] for point in points),
    )


def _iter_positions(geometry: dict[str, Any]):
    coordinates = geometry.get("coordinates", [])
    if geometry.get("type") == "Polygon":
        polygons = [coordinates]
    elif geometry.get("type") == "MultiPolygon":
        polygons = coordinates
    else:
        return
    for polygon in polygons:
        for ring in polygon:
            for position in ring:
                if len(position) >= 2:
                    yield float(position[0]), float(position[1])
