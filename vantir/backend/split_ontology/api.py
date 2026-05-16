from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from split_ontology.address_lookup import lookup_reverse_address
from split_ontology.data_loader import (
    AOI_NAME,
    SOURCE_FILES,
    filter_buildings,
    load_dataset,
)
from split_ontology.priority_cases import build_priority_case_payload
from split_ontology.search import build_search_payload


def create_app() -> FastAPI:
    app = FastAPI(title="Vantir Technologies")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    dataset = load_dataset()

    @app.get("/health")
    def health():
        return {"ok": True, "mode": "local_geojson", "aoi": AOI_NAME}

    @app.get("/api/summary")
    def summary():
        return {
            "aoi": {"name": AOI_NAME, "bbox": list(dataset.bbox)},
            "source_counts": dataset.source_file_counts,
            "status_counts": dataset.status_counts,
            "priority_flag_count": dataset.priority_flag_count,
            "total_buildings": len(dataset.buildings["features"]),
        }

    @app.get("/api/sources")
    def sources():
        return {
            "aoi": {"name": AOI_NAME, "bbox": list(dataset.bbox)},
            "sources": [
                {
                    "id": source_id,
                    "file": filename,
                    "observation_count": dataset.source_counts[source_id],
                    "snapshots": [_snapshot_for(source_id)],
                }
                for source_id, filename in SOURCE_FILES.items()
            ],
        }

    @app.get("/api/buildings.geojson")
    def buildings_geojson(
        discrepancy_type: str | None = None,
        view: str | None = None,
        limit: int | None = Query(default=None, ge=1, le=50000),
    ):
        discrepancy_types = (
            {item.strip() for item in discrepancy_type.split(",") if item.strip()}
            if discrepancy_type
            else None
        )
        return filter_buildings(
            dataset,
            discrepancy_types=discrepancy_types,
            priority_only=view == "priority",
            limit=limit,
        )

    @app.get("/api/landuse.geojson")
    def landuse_geojson():
        return dataset.landuse

    @app.get("/api/parcels.geojson")
    def parcels_geojson():
        return dataset.parcels

    @app.get("/api/parcels/queue")
    def parcel_queue():
        return {"type": "ParcelQueue", "items": dataset.parcel_queue}

    @app.get("/api/priority-cases")
    def priority_cases(
        limit: int = Query(default=100, ge=1, le=5000),
        offset: int = Query(default=0, ge=0),
    ):
        return build_priority_case_payload(dataset, limit=limit, offset=offset)

    @app.get("/api/search")
    def search(q: str = Query(..., min_length=1), limit: int = Query(default=8, ge=1, le=25)):
        return build_search_payload(dataset, query=q, limit=limit)

    @app.get("/api/addresses/reverse")
    def reverse_address(
        lat: float = Query(..., ge=-90, le=90),
        lon: float = Query(..., ge=-180, le=180),
    ):
        return lookup_reverse_address(lat=lat, lon=lon)

    @app.get("/api/buildings/{building_id}")
    def building_detail(building_id: str):
        feature = dataset.buildings_by_id.get(building_id)
        if feature is None:
            raise HTTPException(status_code=404, detail="Building not found")
        return _building_detail(feature)

    frontend_dir = Path(__file__).resolve().parents[2] / "frontend"
    if frontend_dir.exists():
        app.mount("/assets", StaticFiles(directory=frontend_dir), name="frontend-assets")

        @app.get("/")
        def index():
            return FileResponse(frontend_dir / "index.html")

    return app


app = create_app()


def _building_detail(feature: dict) -> dict:
    properties = feature["properties"]
    observations = _source_observations(feature)
    return {
        "id": feature["id"],
        "is_registered": properties["is_registered"],
        "discrepancy_type": properties["discrepancy_type"],
        "confidence": properties.get("confidence"),
        "area": properties.get("area_m2"),
        "height": properties.get("height"),
        "land_zone": properties.get("land_zone"),
        "centroid": list(_building_centroid(feature)),
        "first_seen": None,
        "geometry": feature["geometry"],
        "properties": properties,
        "match_summary": {
            "linked_observation_count": len(observations),
            "best_match_score": 1.0,
        },
        "source_observations": observations,
    }


def _building_centroid(feature: dict) -> tuple[float, float]:
    points = list(_iter_positions(feature.get("geometry") or {}))
    if not points:
        return (0.0, 0.0)
    return (
        sum(point[0] for point in points) / len(points),
        sum(point[1] for point in points) / len(points),
    )


def _iter_positions(geometry: dict):
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


def _source_observations(feature: dict) -> list[dict]:
    properties = feature["properties"]
    discrepancy_type = properties["discrepancy_type"]
    observations = [
        _observation("merged_buildings", "buildings.geojson", feature, "provided_merged_result")
    ]
    if properties.get("source") == "microsoft" or discrepancy_type in {
        "registered_match",
        "unregistered",
        "protected_land",
    }:
        observations.append(
            _observation(
                "microsoft_ml_footprints",
                "buildings_ms.geojson",
                feature,
                "provided_source_membership",
            )
        )
    if discrepancy_type == "registered_match":
        observations.append(
            _observation(
                "oss_katastar_current",
                "buildings_oss.geojson",
                feature,
                "provided_match_status",
            )
        )
    if discrepancy_type == "katastar_only":
        observations.append(
            _observation(
                "dgu_inspire_2016",
                "buildings_dgu.geojson",
                feature,
                "provided_katastar_only_status",
            )
        )
    if discrepancy_type == "protected_land":
        observations.append(
            _observation(
                "landuse_zones",
                "landuse.geojson",
                feature,
                "provided_land_zone_overlap",
            )
        )
    return observations


def _observation(source: str, filename: str, feature: dict, match_method: str) -> dict:
    properties = feature["properties"]
    return {
        "source": source,
        "source_feature_id": feature["id"],
        "snapshot_id": _snapshot_for(source),
        "source_file": filename,
        "confidence": properties.get("confidence"),
        "area": properties.get("area_m2"),
        "match_score": 1.0,
        "match_method": match_method,
        "properties": properties,
    }


def _snapshot_for(source: str) -> str:
    return {
        "merged_buildings": "data-sources-v3:merged",
        "microsoft_ml_footprints": "2026-02",
        "oss_katastar_current": "2026-current",
        "oss_katastar_raw": "2026-current-raw",
        "dgu_inspire_2016": "2016-inspire",
        "landuse_zones": "landuse-zones",
        "parcels": "parcel-context-v3",
    }[source]
