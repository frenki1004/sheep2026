from split_ontology.data_loader import load_dataset
from split_ontology.parcel_queue import build_parcel_queue


def test_parcel_queue_ranks_flagged_parcels_by_score():
    queue = build_parcel_queue(load_dataset())

    assert [row["parcel_id"] for row in queue[:2]] == ["Split/1240", "Split/1241"]
    assert queue[0]["priority_building_count"] == 2
    assert queue[0]["total_flagged_area_m2"] == 179
    assert queue[0]["impact_score"] > queue[1]["impact_score"]
    assert queue[0]["risk_level"] == "high"
    assert queue[0]["recommended_next_step"] == "Field inspection and zoning review"


def test_parcel_queue_keeps_empty_context_parcels_at_bottom():
    queue = build_parcel_queue(load_dataset())

    assert len(queue) == 7
    assert queue[-1]["priority_building_count"] == 0
    assert queue[-1]["impact_score"] == 0
    assert queue[-1]["recommended_next_step"] == "No action"


def test_parcel_queue_api_returns_case_file_fields():
    queue = build_parcel_queue(load_dataset())
    first = queue[0]

    assert first["case_file"]["parcel_id"] == first["parcel_id"]
    assert first["case_file"]["suggested_next_step"] == first["recommended_next_step"]
    assert first["case_file"]["evidence_summary"]
    assert first["bbox"]
    assert {building["discrepancy_type"] for building in first["flagged_buildings"]} == {
        "unregistered"
    }
