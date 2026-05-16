from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from shapely.geometry.base import BaseGeometry


CADASTRE_SOURCE = "dgu_buildings"
LIVE_FOOTPRINT_SOURCES = {"overture_buildings", "microsoft_buildings", "osm_buildings"}


@dataclass(frozen=True)
class SourceObservation:
    source: str
    source_feature_id: str
    snapshot_id: str
    geometry: BaseGeometry
    confidence: float = 1.0
    properties: dict[str, Any] = field(default_factory=dict)

    @property
    def area_m2(self) -> float:
        return float(self.geometry.area)

    @property
    def is_registered_source(self) -> bool:
        return self.source == CADASTRE_SOURCE

    @property
    def is_live_footprint_source(self) -> bool:
        return self.source in LIVE_FOOTPRINT_SOURCES


@dataclass(frozen=True)
class ObservationLink:
    observation: SourceObservation
    match_score: float
    match_method: str


@dataclass(frozen=True)
class CanonicalBuilding:
    building_id: str
    geometry: BaseGeometry
    is_registered: bool
    discrepancy_type: str
    confidence: float
    observation_links: tuple[ObservationLink, ...]
    first_seen: str | None = None
    area_delta_ratio: float | None = None

    @property
    def area_m2(self) -> float:
        return float(self.geometry.area)
