from shapely.geometry import Polygon

from split_ontology.domain import SourceObservation
from split_ontology.resolution import resolve_buildings


def square(x, y, size):
    return Polygon(
        [
            (x, y),
            (x + size, y),
            (x + size, y + size),
            (x, y + size),
            (x, y),
        ]
    )


def observation(source, feature_id, geometry, *, confidence=1.0):
    return SourceObservation(
        source=source,
        source_feature_id=feature_id,
        snapshot_id=f"{source}:snapshot",
        geometry=geometry,
        confidence=confidence,
        properties={"label": feature_id},
    )


def test_matching_cadastre_and_footprint_creates_registered_building():
    cadastre = observation("dgu_buildings", "DGU-1", square(0, 0, 10))
    footprint = observation("overture_buildings", "OVT-1", square(1, 1, 10))

    buildings = resolve_buildings([cadastre, footprint])

    assert len(buildings) == 1
    building = buildings[0]
    assert building.is_registered is True
    assert building.discrepancy_type == "registered_match"
    assert {link.observation.source_feature_id for link in building.observation_links} == {
        "DGU-1",
        "OVT-1",
    }
    assert building.confidence > 0.8


def test_live_footprint_without_cadastre_is_unregistered_candidate():
    footprint = observation("overture_buildings", "OVT-2", square(50, 50, 8), confidence=0.92)

    buildings = resolve_buildings([footprint])

    assert len(buildings) == 1
    assert buildings[0].is_registered is False
    assert buildings[0].discrepancy_type == "unregistered"
    assert buildings[0].confidence == 0.92


def test_cadastre_without_live_footprint_is_demolished_or_stale_candidate():
    cadastre = observation("dgu_buildings", "DGU-2", square(100, 100, 12))

    buildings = resolve_buildings([cadastre])

    assert len(buildings) == 1
    assert buildings[0].is_registered is True
    assert buildings[0].discrepancy_type == "demolished_but_registered"


def test_matched_building_with_large_area_delta_is_size_mismatch():
    cadastre = observation("dgu_buildings", "DGU-3", square(200, 200, 10))
    footprint = observation("overture_buildings", "OVT-3", square(199, 199, 15))

    buildings = resolve_buildings([cadastre, footprint])

    assert len(buildings) == 1
    assert buildings[0].discrepancy_type == "size_mismatch"
    assert buildings[0].area_delta_ratio > 1.3
