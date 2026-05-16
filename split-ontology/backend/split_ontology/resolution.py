from __future__ import annotations

from hashlib import sha1
from itertools import count

from shapely.ops import unary_union

from split_ontology.domain import (
    CADASTRE_SOURCE,
    CanonicalBuilding,
    ObservationLink,
    SourceObservation,
)


def resolve_buildings(
    observations: list[SourceObservation],
    *,
    iou_threshold: float = 0.5,
    smaller_overlap_threshold: float = 0.65,
    centroid_threshold_m: float = 10.0,
    size_mismatch_ratio: float = 1.3,
) -> list[CanonicalBuilding]:
    cadastre = [obs for obs in observations if obs.source == CADASTRE_SOURCE]
    live = [obs for obs in observations if obs.is_live_footprint_source]
    unmatched_live = set(range(len(live)))
    buildings: list[CanonicalBuilding] = []

    for cadastre_obs in cadastre:
        match_indexes = _find_live_matches(
            cadastre_obs,
            live,
            unmatched_live,
            iou_threshold=iou_threshold,
            smaller_overlap_threshold=smaller_overlap_threshold,
            centroid_threshold_m=centroid_threshold_m,
        )
        for index in match_indexes:
            unmatched_live.discard(index)

        matched_live = [live[index] for index in match_indexes]
        buildings.append(
            _build_registered(
                cadastre_obs,
                matched_live,
                size_mismatch_ratio=size_mismatch_ratio,
            )
        )

    for index in sorted(unmatched_live):
        buildings.append(_build_unregistered(live[index]))

    return sorted(buildings, key=lambda building: building.building_id)


def _find_live_matches(
    cadastre_obs: SourceObservation,
    live: list[SourceObservation],
    unmatched_live: set[int],
    *,
    iou_threshold: float,
    smaller_overlap_threshold: float,
    centroid_threshold_m: float,
) -> list[int]:
    matches = []
    for index in sorted(unmatched_live):
        candidate = live[index]
        iou = _intersection_over_union(cadastre_obs.geometry, candidate.geometry)
        overlap = _intersection_over_smaller(cadastre_obs.geometry, candidate.geometry)
        centroid_distance = cadastre_obs.geometry.centroid.distance(candidate.geometry.centroid)
        if iou >= iou_threshold or (
            overlap >= smaller_overlap_threshold and centroid_distance <= centroid_threshold_m
        ):
            matches.append(index)
    return matches


def _build_registered(
    cadastre_obs: SourceObservation,
    matched_live: list[SourceObservation],
    *,
    size_mismatch_ratio: float,
) -> CanonicalBuilding:
    if not matched_live:
        return CanonicalBuilding(
            building_id=_stable_id([cadastre_obs]),
            geometry=cadastre_obs.geometry,
            is_registered=True,
            discrepancy_type="demolished_but_registered",
            confidence=min(0.75, cadastre_obs.confidence),
            observation_links=(
                ObservationLink(cadastre_obs, match_score=1.0, match_method="seed_cadastre"),
            ),
            first_seen=_first_seen([cadastre_obs]),
        )

    live_union = unary_union([obs.geometry for obs in matched_live])
    area_delta_ratio = _area_delta_ratio(cadastre_obs.geometry.area, live_union.area)
    discrepancy_type = (
        "size_mismatch" if area_delta_ratio > size_mismatch_ratio else "registered_match"
    )
    match_score = max(
        _intersection_over_union(cadastre_obs.geometry, live_union),
        _intersection_over_smaller(cadastre_obs.geometry, live_union),
    )
    links = [ObservationLink(cadastre_obs, match_score=1.0, match_method="seed_cadastre")]
    links.extend(
        ObservationLink(obs, match_score=match_score, match_method="spatial_overlap")
        for obs in matched_live
    )
    confidence = _clamp(
        (cadastre_obs.confidence + _average(obs.confidence for obs in matched_live) + match_score)
        / 3.0
    )
    return CanonicalBuilding(
        building_id=_stable_id([cadastre_obs, *matched_live]),
        geometry=cadastre_obs.geometry,
        is_registered=True,
        discrepancy_type=discrepancy_type,
        confidence=confidence,
        observation_links=tuple(links),
        first_seen=_first_seen([cadastre_obs, *matched_live]),
        area_delta_ratio=area_delta_ratio,
    )


def _build_unregistered(observation: SourceObservation) -> CanonicalBuilding:
    return CanonicalBuilding(
        building_id=_stable_id([observation]),
        geometry=observation.geometry,
        is_registered=False,
        discrepancy_type="unregistered",
        confidence=observation.confidence,
        observation_links=(
            ObservationLink(observation, match_score=1.0, match_method="single_live_source"),
        ),
        first_seen=_first_seen([observation]),
    )


def _intersection_over_union(left, right) -> float:
    union_area = left.union(right).area
    if union_area == 0:
        return 0.0
    return float(left.intersection(right).area / union_area)


def _intersection_over_smaller(left, right) -> float:
    smaller_area = min(left.area, right.area)
    if smaller_area == 0:
        return 0.0
    return float(left.intersection(right).area / smaller_area)


def _area_delta_ratio(registered_area: float, live_area: float) -> float:
    if registered_area == 0 or live_area == 0:
        return float("inf")
    return float(max(registered_area, live_area) / min(registered_area, live_area))


def _stable_id(observations: list[SourceObservation]) -> str:
    seed = "|".join(
        f"{obs.source}:{obs.source_feature_id}" for obs in sorted(observations, key=_obs_sort_key)
    )
    return f"bldg_{sha1(seed.encode('utf-8')).hexdigest()[:12]}"


def _obs_sort_key(observation: SourceObservation) -> tuple[str, str]:
    return observation.source, observation.source_feature_id


def _first_seen(observations: list[SourceObservation]) -> str | None:
    dated = [
        obs.properties.get("observed_at") or obs.properties.get("snapshot_date")
        for obs in observations
    ]
    values = [value for value in dated if isinstance(value, str) and value]
    return min(values) if values else None


def _average(values) -> float:
    items = list(values)
    if not items:
        return 0.0
    return float(sum(items) / len(items))


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, float(value)))
