from split_ontology.data_loader import load_dataset


def test_loader_reads_provided_geojson_counts():
    dataset = load_dataset()

    assert dataset.source_counts == {
        "merged_buildings": 25991,
        "microsoft_ml_footprints": 23431,
        "oss_katastar_current": 39279,
        "oss_katastar_raw": 39279,
        "dgu_inspire_2016": 11317,
        "landuse_zones": 1254,
        "parcels": 7,
    }
    assert dataset.status_counts == {
        "katastar_only": 2560,
        "registered_match": 19346,
        "unregistered": 3827,
        "protected_land": 258,
    }
    assert dataset.priority_flag_count == 4085


def test_loader_normalizes_merged_building_features():
    dataset = load_dataset()
    protected = next(
        feature
        for feature in dataset.buildings["features"]
        if feature["properties"]["discrepancy_type"] == "protected_land"
    )

    assert protected["id"].startswith("building-")
    assert protected["properties"]["id"] == protected["id"]
    assert protected["properties"]["source_file"] == "buildings.geojson"
    assert protected["properties"]["status"] == "illegal_protected"
    assert protected["properties"]["is_registered"] is False
    assert protected["properties"]["land_zone"]
