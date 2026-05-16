from fastapi.testclient import TestClient

from split_ontology.api import create_app


def client():
    return TestClient(create_app())


def test_priority_cases_api_reports_full_building_case_count_and_parcel_sample_context():
    response = client().get("/api/priority-cases")

    assert response.status_code == 200
    payload = response.json()
    assert payload["type"] == "PriorityCaseList"
    assert payload["total"] == 4085
    assert payload["limit"] == 100
    assert payload["offset"] == 0
    assert payload["parcel_sample"] == {
        "loaded_parcels": 7,
        "flagged_parcels": 2,
        "priority_buildings_in_loaded_parcels": 4,
    }
    assert len(payload["items"]) == 100

    first = payload["items"][0]
    assert first["id"] == "building-14853"
    assert first["discrepancy_type"] == "unregistered"
    assert first["area_m2"] == 8441
    assert first["confidence"] == 0.9
    assert first["land_zone"] == "GospodarskePovrsine"
    assert first["parcel_id"] is None
    assert first["impact_score"] == 7622
    assert first["risk_level"] == "high"
    assert first["reasons"] == ["unregistered", "large_footprint"]
    assert len(first["bbox"]) == 4


def test_priority_cases_api_respects_limit_and_offset():
    response = client().get("/api/priority-cases?limit=2&offset=2")

    assert response.status_code == 200
    payload = response.json()
    assert payload["limit"] == 2
    assert payload["offset"] == 2
    assert [item["id"] for item in payload["items"]] == ["building-08958", "building-00734"]


def test_priority_cases_keep_known_sample_parcel_assignments():
    response = client().get("/api/priority-cases?limit=5000")

    assert response.status_code == 200
    payload = response.json()
    by_parcel = {}
    for item in payload["items"]:
        if item["parcel_id"]:
            by_parcel.setdefault(item["parcel_id"], []).append(item["id"])

    assert by_parcel["Split/1240"] == ["building-18705", "building-18959"]
    assert by_parcel["Split/1241"] == ["building-00147", "building-18583"]
