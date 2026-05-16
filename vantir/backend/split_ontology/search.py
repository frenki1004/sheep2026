from __future__ import annotations

from typing import Any

from split_ontology.parcel_queue import PRIORITY_TYPES


def build_search_payload(dataset: Any, *, query: str, limit: int = 8) -> dict[str, Any]:
    normalized_query = _normalize(query)
    if not normalized_query:
        return _payload(query=query, limit=limit, items=[])

    candidates = []
    candidates.extend(_building_results(dataset, normalized_query))
    candidates.extend(_parcel_results(dataset, normalized_query))
    candidates.extend(_landuse_results(dataset, normalized_query))
    candidates.sort(key=lambda item: item["_rank"])

    items = [_strip_rank(item) for item in candidates]
    return _payload(query=query, limit=limit, items=items[:limit], total=len(items))


def _payload(
    *,
    query: str,
    limit: int,
    items: list[dict[str, Any]],
    total: int | None = None,
) -> dict[str, Any]:
    return {
        "type": "SearchResults",
        "query": query,
        "total": len(items) if total is None else total,
        "limit": limit,
        "items": items,
    }


def _building_results(dataset: Any, query: str) -> list[dict[str, Any]]:
    results = []
    for feature in dataset.buildings["features"]:
        properties = feature["properties"]
        discrepancy_type = properties["discrepancy_type"]
        building_id = feature["id"]
        searchable = [building_id]
        if discrepancy_type in PRIORITY_TYPES:
            searchable.append(discrepancy_type)
        match_rank = _best_match_rank(query, searchable)
        if match_rank is None:
            continue
        area_m2 = round(float(properties.get("area_m2") or 0))
        confidence = float(properties.get("confidence") or 0)
        is_priority = discrepancy_type in PRIORITY_TYPES
        results.append(
            {
                "_rank": (
                    match_rank,
                    0 if is_priority else 1,
                    -area_m2,
                    building_id,
                ),
                "type": "building",
                "id": building_id,
                "label": building_id,
                "subtitle": (
                    f"{_readable(discrepancy_type)} · {area_m2:,} m2 · "
                    f"{round(confidence * 100)}% · {properties.get('land_zone') or 'unknown'}"
                ),
                "bbox": list(_bbox_for_geometry(feature.get("geometry") or {})),
                "building_id": building_id,
            }
        )
    return results


def _parcel_results(dataset: Any, query: str) -> list[dict[str, Any]]:
    results = []
    parcel_cases = {item["parcel_id"]: item for item in dataset.parcel_queue}
    for feature in dataset.parcels["features"]:
        properties = feature.get("properties") or {}
        parcel_id = properties.get("parcel_id", "unknown")
        short_id = parcel_id.split("/")[-1]
        match_rank = _best_match_rank(query, [parcel_id, short_id])
        if match_rank is None:
            continue
        parcel_case = parcel_cases.get(parcel_id)
        subtitle = properties.get("land_use", "unknown")
        if parcel_case and parcel_case["priority_building_count"]:
            subtitle = (
                f"{subtitle} · {parcel_case['priority_building_count']} priority buildings · "
                f"{parcel_case['total_flagged_area_m2']:,} m2 flagged"
            )
        results.append(
            {
                "_rank": (match_rank, 0, parcel_id),
                "type": "parcel",
                "id": parcel_id,
                "label": parcel_id,
                "subtitle": subtitle,
                "bbox": list(_bbox_for_geometry(feature.get("geometry") or {})),
                "parcel_id": parcel_id,
            }
        )
    return results


def _landuse_results(dataset: Any, query: str) -> list[dict[str, Any]]:
    results = []
    for feature in dataset.landuse["features"]:
        properties = feature.get("properties") or {}
        land_type = properties.get("land_type") or "unknown"
        local_id = properties.get("local_id") or "unknown"
        match_rank = _best_match_rank(query, [land_type, local_id])
        if match_rank is None:
            continue
        results.append(
            {
                "_rank": (match_rank, land_type, local_id),
                "type": "landuse_zone",
                "id": local_id,
                "label": land_type,
                "subtitle": f"{local_id} · local land-use zone",
                "bbox": list(_bbox_for_geometry(feature.get("geometry") or {})),
            }
        )
    return results


def _best_match_rank(query: str, values: list[str]) -> int | None:
    normalized_values = [_normalize(value) for value in values if value]
    if query in normalized_values:
        return 0
    if any(value.startswith(query) for value in normalized_values):
        return 1
    if any(query in value for value in normalized_values):
        return 2
    return None


def _strip_rank(item: dict[str, Any]) -> dict[str, Any]:
    result = dict(item)
    result.pop("_rank", None)
    return result


def _readable(value: str) -> str:
    return " ".join(part.capitalize() for part in value.split("_"))


def _normalize(value: str) -> str:
    return str(value).strip().casefold()


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
