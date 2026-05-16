from fastapi.testclient import TestClient

from split_ontology.api import create_app


def client():
    return TestClient(create_app())


def test_search_returns_building_id_result_with_bbox():
    response = client().get("/api/search?q=building-14853")

    assert response.status_code == 200
    payload = response.json()
    assert payload["type"] == "SearchResults"
    assert payload["query"] == "building-14853"
    assert payload["total"] >= 1
    first = payload["items"][0]
    assert first["type"] == "building"
    assert first["id"] == "building-14853"
    assert first["building_id"] == "building-14853"
    assert "Unregistered" in first["subtitle"]
    assert len(first["bbox"]) == 4


def test_search_returns_loaded_parcel_result():
    response = client().get("/api/search?q=Split/1240")

    assert response.status_code == 200
    payload = response.json()
    assert payload["items"][0]["type"] == "parcel"
    assert payload["items"][0]["id"] == "Split/1240"
    assert payload["items"][0]["parcel_id"] == "Split/1240"
    assert payload["items"][0]["label"] == "Split/1240"


def test_search_park_returns_local_landuse_results_only():
    response = client().get("/api/search?q=park")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] >= 1
    assert {item["type"] for item in payload["items"]} == {"landuse_zone"}
    assert all("Park" in item["label"] or "Park" in item["subtitle"] for item in payload["items"])


def test_search_rejects_outside_city_terms():
    response = client().get("/api/search?q=zagreb")

    assert response.status_code == 200
    assert response.json()["items"] == []
    assert response.json()["total"] == 0


def test_search_respects_limit():
    response = client().get("/api/search?q=park&limit=3")

    assert response.status_code == 200
    payload = response.json()
    assert payload["limit"] == 3
    assert len(payload["items"]) == 3
