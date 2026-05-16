from __future__ import annotations

from typing import Any


PRIORITY_TYPES = {"unregistered", "protected_land"}


def build_parcel_queue(dataset: Any) -> list[dict[str, Any]]:
    rows = [_parcel_row(parcel, dataset.buildings["features"]) for parcel in dataset.parcels["features"]]
    return sorted(
        rows,
        key=lambda row: (
            row["impact_score"],
            row["priority_building_count"],
            row["total_flagged_area_m2"],
            row["parcel_id"],
        ),
        reverse=True,
    )


def _parcel_row(parcel: dict[str, Any], buildings: list[dict[str, Any]]) -> dict[str, Any]:
    parcel_id = parcel.get("properties", {}).get("parcel_id", "unknown")
    land_use = parcel.get("properties", {}).get("land_use", "unknown")
    parcel_geometry = parcel.get("geometry") or {}
    parcel_bbox = _bbox_for_geometry(parcel_geometry)
    inside_buildings = [
        building
        for building in buildings
        if _point_in_geometry(_building_centroid(building), parcel_geometry)
    ]
    flagged = [
        building
        for building in inside_buildings
        if building["properties"]["discrepancy_type"] in PRIORITY_TYPES
    ]
    total_area = round(sum(float(building["properties"].get("area_m2") or 0) for building in flagged))
    average_confidence = _average(
        float(building["properties"].get("confidence") or 0) for building in flagged
    )
    unregistered_count = _count_type(flagged, "unregistered")
    protected_count = _count_type(flagged, "protected_land")
    flags = _parcel_flags(land_use, parcel_bbox, protected_count)
    impact_score = _impact_score(
        total_area=total_area,
        average_confidence=average_confidence,
        priority_count=len(flagged),
        protected_count=protected_count,
        flags=flags,
    )
    risk_level = _risk_level(impact_score)
    recommended_next_step = _recommended_next_step(impact_score)
    flagged_buildings = [_building_summary(building) for building in flagged]
    return {
        "parcel_id": parcel_id,
        "land_use": land_use,
        "bbox": list(parcel_bbox),
        "building_count": len(inside_buildings),
        "priority_building_count": len(flagged),
        "unregistered_count": unregistered_count,
        "protected_land_count": protected_count,
        "coastal_setback_review_count": len(flagged) if "coastal_setback_review" in flags else 0,
        "total_flagged_area_m2": total_area,
        "average_confidence": round(average_confidence, 3),
        "impact_score": impact_score,
        "risk_level": risk_level,
        "flags": flags,
        "recommended_next_step": recommended_next_step,
        "flagged_buildings": flagged_buildings,
        "case_file": _case_file(
            parcel_id=parcel_id,
            land_use=land_use,
            risk_level=risk_level,
            recommended_next_step=recommended_next_step,
            flagged_buildings=flagged_buildings,
            flags=flags,
            total_area=total_area,
        ),
    }


def _impact_score(
    *,
    total_area: int,
    average_confidence: float,
    priority_count: int,
    protected_count: int,
    flags: list[str],
) -> int:
    if priority_count == 0:
        return 0
    score = (total_area * average_confidence) + (priority_count * 25) + (protected_count * 50)
    if "non_buildable_land_use" in flags:
        score += 40
    if "coastal_setback_review" in flags:
        score += 20
    return round(score)


def _risk_level(impact_score: int) -> str:
    if impact_score >= 200:
        return "high"
    if impact_score > 0:
        return "elevated"
    return "none"


def _recommended_next_step(impact_score: int) -> str:
    if impact_score >= 200:
        return "Field inspection and zoning review"
    if impact_score > 0:
        return "Desk review"
    return "No action"


def _parcel_flags(land_use: str, bbox: tuple[float, float, float, float], protected_count: int) -> list[str]:
    flags = []
    if land_use != "građevinsko":
        flags.append("non_buildable_land_use")
    if protected_count:
        flags.append("protected_land")
    if bbox[1] < 43.508:
        flags.append("coastal_setback_review")
    return flags


def _case_file(
    *,
    parcel_id: str,
    land_use: str,
    risk_level: str,
    recommended_next_step: str,
    flagged_buildings: list[dict[str, Any]],
    flags: list[str],
    total_area: int,
) -> dict[str, Any]:
    if flagged_buildings:
        evidence_summary = (
            f"{len(flagged_buildings)} priority structure(s), "
            f"{total_area} m2 flagged footprint, flags: {', '.join(flags) or 'none'}."
        )
    else:
        evidence_summary = "No priority structures intersect this parcel in the current dataset."
    return {
        "parcel_id": parcel_id,
        "land_use": land_use,
        "risk_level": risk_level,
        "suggested_next_step": recommended_next_step,
        "evidence_summary": evidence_summary,
        "building_ids": [building["id"] for building in flagged_buildings],
    }


def _building_summary(building: dict[str, Any]) -> dict[str, Any]:
    properties = building["properties"]
    return {
        "id": building["id"],
        "discrepancy_type": properties["discrepancy_type"],
        "area_m2": properties.get("area_m2"),
        "confidence": properties.get("confidence"),
        "height": properties.get("height"),
        "land_zone": properties.get("land_zone"),
    }


def _count_type(buildings: list[dict[str, Any]], discrepancy_type: str) -> int:
    return sum(1 for building in buildings if building["properties"]["discrepancy_type"] == discrepancy_type)


def _average(values: Any) -> float:
    items = list(values)
    if not items:
        return 0.0
    return sum(items) / len(items)


def _building_centroid(building: dict[str, Any]) -> tuple[float, float]:
    ring = _largest_outer_ring(building.get("geometry") or {})
    points = _open_ring(ring)
    longitude = sum(point[0] for point in points) / len(points)
    latitude = sum(point[1] for point in points) / len(points)
    return longitude, latitude


def _point_in_geometry(point: tuple[float, float], geometry: dict[str, Any]) -> bool:
    if geometry.get("type") == "Polygon":
        return _point_in_polygon(point, geometry["coordinates"][0])
    if geometry.get("type") == "MultiPolygon":
        return any(_point_in_polygon(point, polygon[0]) for polygon in geometry["coordinates"])
    return False


def _point_in_polygon(point: tuple[float, float], ring: list[list[float]]) -> bool:
    longitude, latitude = point
    inside = False
    previous = len(ring) - 1
    for current in range(len(ring)):
        current_lon, current_lat = ring[current][0], ring[current][1]
        previous_lon, previous_lat = ring[previous][0], ring[previous][1]
        intersects = (current_lat > latitude) != (previous_lat > latitude) and longitude < (
            (previous_lon - current_lon) * (latitude - current_lat) / (previous_lat - current_lat)
            + current_lon
        )
        if intersects:
            inside = not inside
        previous = current
    return inside


def _bbox_for_geometry(geometry: dict[str, Any]) -> tuple[float, float, float, float]:
    points = list(_iter_positions(geometry))
    return (
        min(point[0] for point in points),
        min(point[1] for point in points),
        max(point[0] for point in points),
        max(point[1] for point in points),
    )


def _largest_outer_ring(geometry: dict[str, Any]) -> list[list[float]]:
    if geometry.get("type") == "Polygon":
        return geometry["coordinates"][0]
    if geometry.get("type") == "MultiPolygon":
        return max((polygon[0] for polygon in geometry["coordinates"]), key=_ring_area)
    raise ValueError("Building geometry must be Polygon or MultiPolygon")


def _ring_area(ring: list[list[float]]) -> float:
    area = 0.0
    for index in range(len(ring) - 1):
        x1, y1 = ring[index][0], ring[index][1]
        x2, y2 = ring[index + 1][0], ring[index + 1][1]
        area += x1 * y2 - x2 * y1
    return abs(area / 2)


def _open_ring(ring: list[list[float]]) -> list[list[float]]:
    if ring[0] == ring[-1]:
        return ring[:-1]
    return ring


def _iter_positions(geometry: dict[str, Any]):
    if geometry.get("type") == "Polygon":
        polygons = [geometry["coordinates"]]
    elif geometry.get("type") == "MultiPolygon":
        polygons = geometry["coordinates"]
    else:
        return
    for polygon in polygons:
        for ring in polygon:
            for position in ring:
                yield float(position[0]), float(position[1])
