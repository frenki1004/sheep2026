from fastapi.testclient import TestClient

from split_ontology.api import create_app


def client():
    return TestClient(create_app())


def test_health_reports_sample_mode_and_aoi():
    response = client().get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "mode": "local_geojson",
        "aoi": "Split dataset v3",
    }


def test_buildings_geojson_uses_provided_merged_file():
    response = client().get("/api/buildings.geojson")

    assert response.status_code == 200
    payload = response.json()
    assert payload["type"] == "FeatureCollection"
    assert len(payload["features"]) == 25991
    discrepancy_types = {
        feature["properties"]["discrepancy_type"] for feature in payload["features"]
    }
    assert discrepancy_types == {
        "registered_match",
        "unregistered",
        "protected_land",
        "katastar_only",
    }


def test_buildings_geojson_can_filter_priority_flags():
    response = client().get(
        "/api/buildings.geojson?discrepancy_type=unregistered,protected_land"
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["features"]) == 4085
    assert {
        feature["properties"]["discrepancy_type"] for feature in payload["features"]
    } == {"unregistered", "protected_land"}


def test_building_detail_returns_linked_source_observations():
    listing = client().get("/api/buildings.geojson?discrepancy_type=protected_land").json()
    feature = next(
        item
        for item in listing["features"]
        if item["properties"]["discrepancy_type"] == "protected_land"
    )

    response = client().get(f"/api/buildings/{feature['id']}")

    assert response.status_code == 200
    detail = response.json()
    assert detail["id"] == feature["id"]
    assert detail["is_registered"] is False
    assert detail["land_zone"]
    assert {obs["source"] for obs in detail["source_observations"]} == {
        "merged_buildings",
        "microsoft_ml_footprints",
        "landuse_zones",
    }
    assert detail["match_summary"]["linked_observation_count"] == 3


def test_summary_reports_file_counts_and_status_counts():
    response = client().get("/api/summary")

    assert response.status_code == 200
    assert response.json()["source_counts"]["buildings_ms.geojson"] == 23431
    assert response.json()["source_counts"]["parcels.geojson"] == 7
    assert response.json()["status_counts"]["protected_land"] == 258


def test_parcels_geojson_uses_v3_parcels_file():
    response = client().get("/api/parcels.geojson")

    assert response.status_code == 200
    payload = response.json()
    assert payload["type"] == "FeatureCollection"
    assert len(payload["features"]) == 7


def test_parcel_queue_returns_ranked_enforcement_cases():
    response = client().get("/api/parcels/queue")

    assert response.status_code == 200
    payload = response.json()
    assert payload["type"] == "ParcelQueue"
    assert len(payload["items"]) == 7
    assert payload["items"][0]["parcel_id"] == "Split/1240"
    assert payload["items"][0]["risk_level"] == "high"
    assert payload["items"][0]["priority_building_count"] == 2
