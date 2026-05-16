"""Natural-language query over the ontology, powered by Claude.

POST /ask { "question": "..." } →
    { "answer": "...", "filter": {...}, "buildings": GeoJSON FeatureCollection, "count": N }

Two-call pattern:
1. Claude (Sonnet 4.6) chooses whether to call the `filter_buildings` tool.
2. We execute the filter against SQLite and feed the result back as tool_result.
3. Claude produces the final natural-language answer.

The system prompt + tool spec is cached via the Anthropic prompt-cache API so repeat
calls only re-bill the user's question + the filter result.
"""
from __future__ import annotations

import json
import logging
from typing import Any

import anthropic
from shapely.geometry import box, mapping
from shapely.wkt import loads as wkt_loads
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import SessionLocal
from app.ontology.models import (
    Building,
    BuildingStatus,
    EntityType,
    Link,
    LinkType,
    ObservedBuilding,
    Parcel,
)

log = logging.getLogger(__name__)

MODEL = "claude-sonnet-4-6"

SYSTEM_PROMPT = """You are the query assistant for the Sheep AI ontology over Split, Croatia.

The ontology covers:
- Parcels (cadastre, from the live DGU INSPIRE WFS — ko_id 329835 is Split-Sjever covering Žnjan)
- Registered buildings (DGU state registry)
- Observed buildings (Microsoft Global ML Building Footprints, OpenStreetMap)
- Reconciled Building entities, each classified into one of:
    • registered_and_observed — building is in DGU AND visible in imagery (legal)
    • observed_only — visible in imagery but absent from DGU registry (likely illegal construction)
    • registered_only — in DGU registry but not visible in imagery (possibly demolished)
    • under_construction — change-detected (not yet active in MVP)

When a question needs data, call the `filter_buildings` tool with the right structured filters.
After receiving the tool result, write a tight one- or two-sentence answer summarising what was found.
Mention concrete numbers (count, total area, examples of broj_cestice when interesting) — be specific, not hedgy.

If the question is conceptual ("what does observed_only mean?"), answer directly without a tool call.

Languages: reply in the same language the user wrote in (English or Croatian/hrvatski)."""

TOOL_FILTER_BUILDINGS = {
    "name": "filter_buildings",
    "description": (
        "Filter the canonical Building entities by structured criteria. "
        "Returns a count, total footprint area, status breakdown, and a sample of building IDs + parcel refs."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "status": {
                "type": "string",
                "enum": [
                    "registered_and_observed",
                    "observed_only",
                    "registered_only",
                    "under_construction",
                ],
                "description": "Filter to buildings of this legality status.",
            },
            "min_area_m2": {"type": "number", "description": "Minimum footprint area in m²."},
            "max_area_m2": {"type": "number"},
            "min_confidence": {"type": "number", "description": "0–1 score; defaults to 0 if omitted."},
            "ko_id": {"type": "string", "description": "Cadastral municipality code, e.g. '329835'."},
            "broj_cestice": {"type": "string", "description": "Parcel number, e.g. '2567/1'."},
            "observed_in_source": {
                "type": "string",
                "enum": ["ms_footprints", "osm"],
                "description": "Restrict to buildings observed in this specific imagery source.",
            },
            "land_use": {
                "type": "string",
                "description": "Parcel land-use category (e.g. 'stambeno zemljište').",
            },
            "limit": {"type": "integer", "default": 200, "description": "Max buildings to return."},
        },
        "required": [],
    },
}

_TOOLS = [TOOL_FILTER_BUILDINGS]


def _build_query(db: Session, args: dict[str, Any]):
    stmt = select(Building)
    if "status" in args and args["status"]:
        stmt = stmt.where(Building.status == BuildingStatus(args["status"]))
    if args.get("min_area_m2") is not None:
        stmt = stmt.where(Building.area_m2 >= args["min_area_m2"])
    if args.get("max_area_m2") is not None:
        stmt = stmt.where(Building.area_m2 <= args["max_area_m2"])
    if args.get("min_confidence") is not None:
        stmt = stmt.where(Building.confidence >= args["min_confidence"])

    # Parcel-related filters require a join via parcel_id.
    if args.get("ko_id") or args.get("broj_cestice") or args.get("land_use"):
        stmt = stmt.join(Parcel, Building.parcel_id == Parcel.id)
        if args.get("ko_id"):
            stmt = stmt.where(Parcel.ko_id == args["ko_id"])
        if args.get("broj_cestice"):
            stmt = stmt.where(Parcel.broj_cestice == args["broj_cestice"])
        if args.get("land_use"):
            stmt = stmt.where(Parcel.land_use == args["land_use"])

    # Observed-source filter requires the link table.
    if args.get("observed_in_source"):
        # Find Building.ids that link to an ObservedBuilding of this source.
        ob_ids_subq = (
            select(Link.src_id)
            .join(ObservedBuilding, ObservedBuilding.id == Link.dst_id)
            .where(
                Link.src_type == EntityType.BUILDING,
                Link.link_type == LinkType.BUILDING_OBSERVED_AS,
                ObservedBuilding.source == args["observed_in_source"],
            )
        )
        stmt = stmt.where(Building.id.in_(ob_ids_subq))

    return stmt


def _execute_filter(args: dict[str, Any]) -> dict[str, Any]:
    """Run the filter; return aggregate stats + a sample for Claude + full id list for the UI."""
    limit = int(args.get("limit") or 200)
    with SessionLocal() as db:
        stmt = _build_query(db, args)
        rows = db.scalars(stmt.limit(limit)).all()

        # Get the count without the limit.
        count_stmt = select(func.count()).select_from(_build_query(db, args).subquery())
        total = db.scalar(count_stmt) or 0
        total_area = db.scalar(
            select(func.sum(Building.area_m2)).select_from(_build_query(db, args).subquery())
        )

        sample_for_llm = []
        building_ids: list[str] = []
        features: list[dict[str, Any]] = []
        for b in rows:
            building_ids.append(b.id)
            parcel_broj: str | None = None
            if b.parcel_id:
                p = db.scalar(select(Parcel).where(Parcel.id == b.parcel_id))
                parcel_broj = p.broj_cestice if p else None
            if len(sample_for_llm) < 6:
                sample_for_llm.append({
                    "id": b.id,
                    "status": b.status.value,
                    "area_m2": round(b.area_m2, 0) if b.area_m2 else None,
                    "confidence": round(b.confidence, 2),
                    "broj_cestice": parcel_broj,
                })
            geom = wkt_loads(b.geometry_wkt)
            features.append({
                "type": "Feature",
                "id": b.id,
                "geometry": mapping(geom),
                "properties": {
                    "status": b.status.value,
                    "area_m2": round(b.area_m2, 1) if b.area_m2 else None,
                    "confidence": round(b.confidence, 2),
                    "parcel_id": b.parcel_id,
                    "broj_cestice": parcel_broj,
                },
            })

    return {
        "count": int(total),
        "returned": len(rows),
        "total_area_m2": round(total_area or 0, 0),
        "sample": sample_for_llm,
        "_building_ids": building_ids,
        "_features": features,
    }


def _client() -> anthropic.Anthropic:
    api_key = get_settings().anthropic_api_key
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set in backend/.env")
    return anthropic.Anthropic(api_key=api_key)


def ask(question: str) -> dict[str, Any]:
    """Run the two-call NL → filter → answer loop. Returns the demo payload."""
    client = _client()

    messages: list[dict[str, Any]] = [{"role": "user", "content": question}]
    filter_args: dict[str, Any] | None = None
    filter_result: dict[str, Any] | None = None

    # Cap at 3 turns so a misbehaving model can't run wild on tool calls.
    for _turn in range(3):
        resp = client.messages.create(
            model=MODEL,
            max_tokens=512,
            system=[{
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }],
            tools=_TOOLS,
            messages=messages,
        )

        if resp.stop_reason != "tool_use":
            answer_text = "".join(
                block.text for block in resp.content if block.type == "text"
            ).strip()
            return {
                "answer": answer_text or "(no answer)",
                "filter": filter_args,
                "buildings": (
                    {"type": "FeatureCollection", "features": filter_result["_features"]}
                    if filter_result
                    else {"type": "FeatureCollection", "features": []}
                ),
                "building_ids": filter_result["_building_ids"] if filter_result else [],
                "count": filter_result["count"] if filter_result else 0,
                "total_area_m2": filter_result["total_area_m2"] if filter_result else 0,
            }

        # Append the assistant message exactly as returned.
        messages.append({"role": "assistant", "content": resp.content})

        # Execute any tool_use blocks and produce tool_result content.
        tool_results = []
        for block in resp.content:
            if block.type != "tool_use":
                continue
            if block.name == "filter_buildings":
                filter_args = dict(block.input)
                filter_result = _execute_filter(filter_args)
                # Strip the internal-only fields before sending back to Claude.
                public = {k: v for k, v in filter_result.items() if not k.startswith("_")}
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(public, ensure_ascii=False),
                })
            else:
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps({"error": f"unknown tool {block.name}"}),
                })
        messages.append({"role": "user", "content": tool_results})

    return {
        "answer": "Claude exceeded the tool-call cap without producing a final answer.",
        "filter": filter_args,
        "buildings": {"type": "FeatureCollection", "features": []},
        "building_ids": [],
        "count": 0,
        "total_area_m2": 0,
    }
