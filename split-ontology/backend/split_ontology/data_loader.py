from __future__ import annotations

import json
from collections import Counter
from copy import deepcopy
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from split_ontology.parcel_queue import build_parcel_queue


AOI_NAME = "Split dataset v3"
DATA_DIR = Path(__file__).resolve().parents[2] / "data"

SOURCE_FILES = {
    "merged_buildings": "buildings.geojson",
    "microsoft_ml_footprints": "buildings_ms.geojson",
    "oss_katastar_current": "buildings_oss.geojson",
    "oss_katastar_raw": "buildings_oss_raw.geojson",
    "dgu_inspire_2016": "buildings_dgu.geojson",
    "landuse_zones": "landuse.geojson",
    "parcels": "parcels.geojson",
}

STATUS_TO_DISCREPANCY = {
    "matched": "registered_match",
    "unregistered": "unregistered",
    "illegal_protected": "protected_land",
    "katastarOnly": "katastar_only",
}

REGISTERED_DISCREPANCIES = {"registered_match", "katastar_only"}


@dataclass(frozen=True)
class LocalGeoJsonDataset:
    buildings: dict[str, Any]
    landuse: dict[str, Any]
    parcels: dict[str, Any]
    parcel_queue: list[dict[str, Any]]
    source_counts: dict[str, int]
    source_file_counts: dict[str, int]
    status_counts: dict[str, int]
    priority_flag_count: int
    bbox: tuple[float, float, float, float]
    buildings_by_id: dict[str, dict[str, Any]]


@lru_cache(maxsize=1)
def load_dataset(data_dir: Path | None = None) -> LocalGeoJsonDataset:
    root = data_dir or DATA_DIR
    raw_buildings = _read_geojson(root / "buildings.geojson")
    landuse = _read_geojson(root / "landuse.geojson")
    parcels = _read_geojson(root / "parcels.geojson")

    buildings = _normalize_buildings(raw_buildings)
    source_counts = {
        source_id: len(_read_geojson(root / filename).get("features", []))
        for source_id, filename in SOURCE_FILES.items()
    }
    source_file_counts = {
        filename: count for filename, count in zip(SOURCE_FILES.values(), source_counts.values())
    }
    status_counter = Counter(
        feature["properties"]["discrepancy_type"] for feature in buildings["features"]
    )
    status_counts = {
        "katastar_only": status_counter["katastar_only"],
        "registered_match": status_counter["registered_match"],
        "unregistered": status_counter["unregistered"],
        "protected_land": status_counter["protected_land"],
    }
    buildings_by_id = {feature["id"]: feature for feature in buildings["features"]}
    dataset = LocalGeoJsonDataset(
        buildings=buildings,
        landuse=landuse,
        parcels=parcels,
        parcel_queue=[],
        source_counts=source_counts,
        source_file_counts=source_file_counts,
        status_counts=status_counts,
        priority_flag_count=status_counts["unregistered"] + status_counts["protected_land"],
        bbox=_bbox(buildings["features"]),
        buildings_by_id=buildings_by_id,
    )
    return LocalGeoJsonDataset(
        buildings=dataset.buildings,
        landuse=dataset.landuse,
        parcels=dataset.parcels,
        parcel_queue=build_parcel_queue(dataset),
        source_counts=dataset.source_counts,
        source_file_counts=dataset.source_file_counts,
        status_counts=dataset.status_counts,
        priority_flag_count=dataset.priority_flag_count,
        bbox=dataset.bbox,
        buildings_by_id=dataset.buildings_by_id,
    )


def filter_buildings(
    dataset: LocalGeoJsonDataset,
    *,
    discrepancy_types: set[str] | None = None,
    priority_only: bool = False,
    limit: int | None = None,
) -> dict[str, Any]:
    if priority_only:
        discrepancy_types = {"unregistered", "protected_land"}

    features = dataset.buildings["features"]
    if discrepancy_types:
        features = [
            feature
            for feature in features
            if feature["properties"]["discrepancy_type"] in discrepancy_types
        ]
    if limit is not None:
        features = features[:limit]

    return {
        "type": "FeatureCollection",
        "name": "split_buildings_v3",
        "bbox": list(_bbox(features) if features else dataset.bbox),
        "features": features,
    }


def _read_geojson(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _normalize_buildings(raw: dict[str, Any]) -> dict[str, Any]:
    normalized = {
        "type": "FeatureCollection",
        "name": "split_buildings_v3",
        "features": [],
    }
    for index, feature in enumerate(raw.get("features", []), start=1):
        item = deepcopy(feature)
        building_id = item.get("id") or f"building-{index:05d}"
        properties = dict(item.get("properties") or {})
        status = properties.get("status")
        discrepancy_type = STATUS_TO_DISCREPANCY.get(status, "unknown")
        properties.update(
            {
                "id": building_id,
                "source_file": "buildings.geojson",
                "discrepancy_type": discrepancy_type,
                "is_registered": discrepancy_type in REGISTERED_DISCREPANCIES,
                "area": properties.get("area_m2"),
                "source_count": _source_count(discrepancy_type),
            }
        )
        item["id"] = building_id
        item["properties"] = properties
        normalized["features"].append(item)
    normalized["bbox"] = list(_bbox(normalized["features"]))
    return normalized


def _source_count(discrepancy_type: str) -> int:
    if discrepancy_type == "registered_match":
        return 3
    if discrepancy_type == "protected_land":
        return 3
    return 2


def _bbox(features: list[dict[str, Any]]) -> tuple[float, float, float, float]:
    min_x = min_y = float("inf")
    max_x = max_y = float("-inf")
    for feature in features:
        for x, y in _iter_positions(feature.get("geometry")):
            min_x = min(min_x, x)
            min_y = min(min_y, y)
            max_x = max(max_x, x)
            max_y = max(max_y, y)
    if min_x == float("inf"):
        return (0.0, 0.0, 0.0, 0.0)
    return (min_x, min_y, max_x, max_y)


def _iter_positions(geometry: dict[str, Any] | None):
    if not geometry:
        return
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
