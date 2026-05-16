"""SQLAlchemy entity definitions for the Sheep AI ontology.

Conventions:
- Every entity has a stable string `id` (UUID or deterministic hash, set by ingester).
- Geometry columns are WKT text, EPSG:4326 (lon/lat). Project to EPSG:3765 in code when measuring.
- `valid_from` / `valid_to` are nullable timestamps; NULL `valid_to` means \"current\".
- `source` / `source_id` carry provenance back to the original record.
"""
from __future__ import annotations

import enum
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


# --- enums ----------------------------------------------------------------


class BuildingStatus(str, enum.Enum):
    REGISTERED_AND_OBSERVED = "registered_and_observed"
    OBSERVED_ONLY = "observed_only"  # the illegal-construction signal
    REGISTERED_ONLY = "registered_only"  # demolished or never built?
    UNDER_CONSTRUCTION = "under_construction"
    UNKNOWN = "unknown"


class ReviewStatus(str, enum.Enum):
    OPEN = "open"
    REVIEWING = "reviewing"
    RESOLVED_LEGAL = "resolved_legal"
    RESOLVED_ILLEGAL = "resolved_illegal"
    DISMISSED = "dismissed"


class LinkType(str, enum.Enum):
    PARCEL_CONTAINS_BUILDING = "parcel_contains_building"
    BUILDING_REGISTERED_AS = "building_registered_as"
    BUILDING_OBSERVED_AS = "building_observed_as"
    BUILDING_PERMITTED_BY = "building_permitted_by"
    CHANGE_AFFECTS_BUILDING = "change_affects_building"
    REVIEW_ABOUT_BUILDING = "review_about_building"
    REVIEW_ABOUT_PARCEL = "review_about_parcel"


class EntityType(str, enum.Enum):
    PARCEL = "parcel"
    REGISTERED_BUILDING = "registered_building"
    OBSERVED_BUILDING = "observed_building"
    BUILDING = "building"
    PERMIT = "permit"
    CHANGE_EVENT = "change_event"
    REVIEW_CASE = "review_case"


# --- mixins ---------------------------------------------------------------


class _Provenance:
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    source_id: Mapped[str] = mapped_column(String(256), nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)


class _Temporal:
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


# --- entities -------------------------------------------------------------


class Parcel(Base, _Provenance, _Temporal):
    __tablename__ = "parcels"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)

    # DGU katastar field names — keep these stable so the live-API switch is mechanical.
    ko_id: Mapped[str | None] = mapped_column(String(32), index=True)  # cadastral municipality code
    ko_naziv: Mapped[str | None] = mapped_column(String(128))  # municipality name
    broj_cestice: Mapped[str | None] = mapped_column(String(64), index=True)  # parcel number

    geometry_wkt: Mapped[str] = mapped_column(Text, nullable=False)
    area_m2: Mapped[float | None] = mapped_column(Float)
    land_use: Mapped[str | None] = mapped_column(String(64))  # gradevinsko / poljoprivredno / sumsko / ...
    owner_ref: Mapped[str | None] = mapped_column(String(256))  # opaque ref, never PII

    __table_args__ = (
        UniqueConstraint("source", "source_id", name="uq_parcels_source"),
        Index("ix_parcels_ko_cestica", "ko_id", "broj_cestice"),
    )


class RegisteredBuilding(Base, _Provenance, _Temporal):
    """A building the state says exists. From DGU HOK / building registry."""
    __tablename__ = "registered_buildings"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    parcel_id: Mapped[str | None] = mapped_column(ForeignKey("parcels.id"), index=True)

    geometry_wkt: Mapped[str | None] = mapped_column(Text)  # nullable: some registries are point-only
    declared_use: Mapped[str | None] = mapped_column(String(64))  # residential / commercial / aux
    year_built: Mapped[int | None] = mapped_column(Integer)
    permit_ref: Mapped[str | None] = mapped_column(String(256))

    __table_args__ = (UniqueConstraint("source", "source_id", name="uq_registered_source"),)


class ObservedBuilding(Base, _Provenance, _Temporal):
    """A building footprint observed in imagery / OSM. One row per (source, footprint)."""
    __tablename__ = "observed_buildings"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    geometry_wkt: Mapped[str] = mapped_column(Text, nullable=False)
    area_m2: Mapped[float | None] = mapped_column(Float)
    height_m: Mapped[float | None] = mapped_column(Float)  # google open buildings 2.5d if available
    first_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    raw_attributes: Mapped[str | None] = mapped_column(Text)  # JSON blob for source-specific tags

    __table_args__ = (
        UniqueConstraint("source", "source_id", name="uq_observed_source"),
        Index("ix_observed_source", "source"),
    )


class Building(Base, _Temporal):
    """Reconciled building entity — the thing the UI talks about.

    Links out to 0..N RegisteredBuilding rows and 0..N ObservedBuilding rows via the `links` table.
    """
    __tablename__ = "buildings"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    parcel_id: Mapped[str | None] = mapped_column(ForeignKey("parcels.id"), index=True)
    geometry_wkt: Mapped[str] = mapped_column(Text, nullable=False)
    area_m2: Mapped[float | None] = mapped_column(Float)
    status: Mapped[BuildingStatus] = mapped_column(
        Enum(BuildingStatus, name="building_status"),
        default=BuildingStatus.UNKNOWN,
        nullable=False,
        index=True,
    )
    confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    classified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Permit(Base, _Provenance, _Temporal):
    __tablename__ = "permits"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    parcel_id: Mapped[str | None] = mapped_column(ForeignKey("parcels.id"), index=True)
    building_id: Mapped[str | None] = mapped_column(ForeignKey("buildings.id"), index=True)
    permit_type: Mapped[str | None] = mapped_column(String(64))  # gradevinska / uporabna / legalizacija
    issued_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    document_ref: Mapped[str | None] = mapped_column(String(256))

    __table_args__ = (UniqueConstraint("source", "source_id", name="uq_permits_source"),)


class ChangeEvent(Base, _Temporal):
    """Derived: imagery indicates the footprint at this location changed."""
    __tablename__ = "change_events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    building_id: Mapped[str | None] = mapped_column(ForeignKey("buildings.id"), index=True)
    parcel_id: Mapped[str | None] = mapped_column(ForeignKey("parcels.id"), index=True)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)  # appeared / grew / shrunk / disappeared
    area_delta_m2: Mapped[float | None] = mapped_column(Float)
    geometry_wkt: Mapped[str | None] = mapped_column(Text)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    detector: Mapped[str] = mapped_column(String(64), nullable=False)  # e.g. "sentinel2_ndbi_v1"


class ReviewCase(Base, _Temporal):
    """Human-in-the-loop queue. Every flagged Building gets one before the city notifies anyone."""
    __tablename__ = "review_cases"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    building_id: Mapped[str | None] = mapped_column(ForeignKey("buildings.id"), index=True)
    parcel_id: Mapped[str | None] = mapped_column(ForeignKey("parcels.id"), index=True)
    status: Mapped[ReviewStatus] = mapped_column(
        Enum(ReviewStatus, name="review_status"),
        default=ReviewStatus.OPEN,
        nullable=False,
        index=True,
    )
    reason: Mapped[str | None] = mapped_column(Text)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reviewer_note: Mapped[str | None] = mapped_column(Text)


class Link(Base):
    """Typed edges between entities. Lets us answer graph-ish questions in plain SQL."""
    __tablename__ = "links"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    src_type: Mapped[EntityType] = mapped_column(Enum(EntityType, name="entity_type_src"), nullable=False)
    src_id: Mapped[str] = mapped_column(String(64), nullable=False)
    link_type: Mapped[LinkType] = mapped_column(Enum(LinkType, name="link_type"), nullable=False)
    dst_type: Mapped[EntityType] = mapped_column(Enum(EntityType, name="entity_type_dst"), nullable=False)
    dst_id: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    weight: Mapped[float | None] = mapped_column(Float)  # e.g. IoU score for observed/registered links

    __table_args__ = (
        UniqueConstraint("src_type", "src_id", "link_type", "dst_type", "dst_id", name="uq_link"),
        Index("ix_links_src", "src_type", "src_id"),
        Index("ix_links_dst", "dst_type", "dst_id"),
    )
