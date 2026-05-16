"""Per-building natural-language explanation of classification status.

Given a Building's evidence (parcel, observed sources, registered registry,
area, confidence), Claude writes a 2–3 sentence analyst note explaining why
the classifier landed where it did.

The user clicks a polygon → the evidence panel renders a template explanation
instantly, then calls this endpoint and replaces the text with Claude's note.
"""
from __future__ import annotations

import json
import logging
from typing import Any

import anthropic
from shapely.wkt import loads as wkt_loads
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import SessionLocal
from app.ontology.models import (
    Building,
    EntityType,
    Link,
    LinkType,
    ObservedBuilding,
    Parcel,
    RegisteredBuilding,
    ReviewCase,
)

log = logging.getLogger(__name__)

MODEL = "claude-sonnet-4-6"

SYSTEM_PROMPT = """You are an analyst note generator for the Sheep AI ontology over Split, Croatia.

The ontology compares:
- The DGU INSPIRE state buildings registry (what the state says exists).
- Microsoft Global ML Building Footprints + OpenStreetMap (what's visible in imagery).
- DGU cadastral parcels (land plots, with land-use classification).

Each canonical Building is classified into one of:
- registered_and_observed: appears in BOTH the DGU registry AND imagery → legal.
- observed_only: appears in imagery but NOT in the DGU registry → likely illegal construction.
- registered_only: in DGU registry but no imagery footprint matched → possibly demolished, very small, or geolocation drift.
- under_construction: detected via Sentinel-2 change (not active yet).

You will receive a JSON blob describing one specific Building. Write a tight 2–3 sentence
analyst note explaining WHY this Building has its current status, citing the actual evidence
(which sources, how many of them, parcel context, area). Be specific, not generic.

Important rules:
- Do not use hedging phrases like "it appears" or "potentially" unless the data warrants it.
- Mention concrete sources by name (Microsoft Footprints, OpenStreetMap, DGU registry).
- If the building is observed_only on a residential parcel and >100m², flag that as a strong
  illegal-construction signal worth a city review. Otherwise be more cautious in tone.
- Language: respond in English by default. If the question or any parcel field contains
  Croatian characters (č, ž, š, đ), reply in Croatian.

Output: just the analyst note. No preamble, no markdown headers, no list — plain prose."""


def _evidence_blob(building_id: str) -> dict[str, Any]:
    with SessionLocal() as db:
        b: Building | None = db.scalar(select(Building).where(Building.id == building_id))
        if not b:
            raise KeyError(building_id)

        obs_ids = [
            l.dst_id for l in db.scalars(
                select(Link).where(
                    Link.src_id == b.id,
                    Link.link_type == LinkType.BUILDING_OBSERVED_AS,
                )
            )
        ]
        observed = [
            {"source": o.source, "source_id": o.source_id, "height_m": o.height_m}
            for o in db.scalars(select(ObservedBuilding).where(ObservedBuilding.id.in_(obs_ids)))
        ]

        reg_ids = [
            l.dst_id for l in db.scalars(
                select(Link).where(
                    Link.src_id == b.id,
                    Link.link_type == LinkType.BUILDING_REGISTERED_AS,
                )
            )
        ]
        registered = [
            {"source": r.source, "source_id": r.source_id, "permit_ref": r.permit_ref}
            for r in db.scalars(select(RegisteredBuilding).where(RegisteredBuilding.id.in_(reg_ids)))
        ]

        parcel = None
        if b.parcel_id:
            p = db.scalar(select(Parcel).where(Parcel.id == b.parcel_id))
            if p:
                parcel = {
                    "broj_cestice": p.broj_cestice,
                    "ko_id": p.ko_id,
                    "land_use": p.land_use,
                    "area_m2": p.area_m2,
                }

        has_review = db.scalar(
            select(ReviewCase.id).where(ReviewCase.building_id == b.id)
        ) is not None

        return {
            "status": b.status.value,
            "confidence": round(b.confidence, 2),
            "area_m2": round(b.area_m2, 0) if b.area_m2 else None,
            "parcel": parcel,
            "observed_in": observed,
            "registered_as": registered,
            "review_open": has_review,
        }


def _client() -> anthropic.Anthropic:
    api_key = get_settings().anthropic_api_key
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set in backend/.env")
    return anthropic.Anthropic(api_key=api_key)


def explain(building_id: str) -> dict[str, Any]:
    """Return {"explanation": "...", "evidence": {...}}."""
    evidence = _evidence_blob(building_id)
    client = _client()

    resp = client.messages.create(
        model=MODEL,
        max_tokens=300,
        system=[{
            "type": "text",
            "text": SYSTEM_PROMPT,
            "cache_control": {"type": "ephemeral"},
        }],
        messages=[{
            "role": "user",
            "content": f"Explain this Building's status:\n```json\n{json.dumps(evidence, ensure_ascii=False)}\n```",
        }],
    )

    text = "".join(block.text for block in resp.content if block.type == "text").strip()
    return {"explanation": text, "evidence": evidence}
