"""Ontology layer: typed entities + links over Split building/parcel data.

Entities are append-only with `valid_from` / `valid_to` so we can answer
\"what did we believe at point T?\" without losing history.

Geometries are stored as WKT text (EPSG:4326). Spatial ops happen in Python
via shapely — pilot scale doesn't need a spatial index. If we outgrow this,
swap to GeoAlchemy2 + SpatiaLite without touching the entity types.
"""
from app.ontology.models import (
    Base,
    Building,
    BuildingStatus,
    ChangeEvent,
    Link,
    LinkType,
    ObservedBuilding,
    Parcel,
    Permit,
    RegisteredBuilding,
    ReviewCase,
    ReviewStatus,
)

__all__ = [
    "Base",
    "Building",
    "BuildingStatus",
    "ChangeEvent",
    "Link",
    "LinkType",
    "ObservedBuilding",
    "Parcel",
    "Permit",
    "RegisteredBuilding",
    "ReviewCase",
    "ReviewStatus",
]
