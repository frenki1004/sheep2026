"""Live DGU INSPIRE Buildings registry adapter.

Endpoint: https://api.uredjenazemlja.hr/services/inspire/bu/wfs
Feature type: bu:Building

Quirks of this WFS (observed 2026-05-16):
- The same Oracle backend powers the parcels and buildings WFS and is flaky
  (ORA-01000 max open cursors). Aggressive retry / backoff is essential.
- Geometry is nested at `properties.geometry2D.geometry`, NOT at the top-level
  GeoJSON `geometry` field (which is always null in this WFS's output).
- Coordinates come back in INSPIRE axis order (lat, lon) for EPSG:4326, not the
  GeoJSON-canonical (lon, lat). We swap.

This source feeds RegisteredBuilding — the official state record of buildings.
Buildings observed in imagery (MS / OSM) but absent here = the illegal-construction signal.

Run:
    uv run python -m app.ingest.dgu_buildings
"""
from __future__ import annotations

import json
import logging
import time
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from shapely.geometry import Polygon
from sqlalchemy import select

from app.config import get_settings
from app.db import SessionLocal
from app.ontology.models import RegisteredBuilding

log = logging.getLogger(__name__)

SOURCE = "dgu_bu"
ENDPOINT = "https://api.uredjenazemlja.hr/services/inspire/bu/wfs"
TYPE_NAME = "bu:Building"
USER_AGENT = "Sheep-AI/0.1 (hackathon)"


def _http_get(url: str, timeout: float = 60.0) -> bytes:
    req = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json,*/*"})
    with urlopen(req, timeout=timeout) as resp:  # noqa: S310 — trusted endpoint
        return resp.read()


def _fetch_page(
    bbox_4326: tuple[float, float, float, float],
    start_index: int,
    page_size: int,
    *,
    max_retries: int = 6,
    backoff_s: float = 5.0,
) -> list[dict[str, Any]]:
    minx, miny, maxx, maxy = bbox_4326
    bbox_axis_swapped = f"{miny},{minx},{maxy},{maxx},urn:ogc:def:crs:EPSG::4326"
    params = {
        "service": "WFS",
        "request": "GetFeature",
        "version": "2.0.0",
        "typeNames": TYPE_NAME,
        "srsName": "urn:ogc:def:crs:EPSG::4326",
        "bbox": bbox_axis_swapped,
        "count": str(page_size),
        "startIndex": str(start_index),
        "outputFormat": "application/json",
    }
    url = f"{ENDPOINT}?{urlencode(params)}"
    last_err: Exception | None = None
    for attempt in range(1, max_retries + 1):
        try:
            body = _http_get(url, timeout=90.0)
            try:
                data = json.loads(body)
            except json.JSONDecodeError:
                snippet = body[:400].decode("utf-8", errors="replace")
                raise RuntimeError(f"WFS returned non-JSON: {snippet}")
            return data.get("features", [])
        except Exception as err:
            last_err = err
            log.warning("DGU BU page@%d attempt %d/%d failed: %s", start_index, attempt, max_retries, err)
            if attempt < max_retries:
                time.sleep(backoff_s + attempt * 2)
    assert last_err is not None
    raise RuntimeError(f"DGU BU WFS page@{start_index} unavailable after {max_retries} attempts: {last_err}")


def fetch_buildings(
    bbox_4326: tuple[float, float, float, float],
    *,
    page_size: int = 1000,
    max_pages: int = 20,
) -> list[dict[str, Any]]:
    """Fetch buildings by paginating WFS startIndex. Returns whatever was fetched if a later page is unrecoverable."""
    all_feats: list[dict[str, Any]] = []
    for page in range(max_pages):
        start = page * page_size
        try:
            feats = _fetch_page(bbox_4326, start, page_size)
        except RuntimeError as err:
            log.error("DGU BU pagination stopped at page %d: %s. Keeping %d buildings fetched so far.", page, err, len(all_feats))
            break
        all_feats.extend(feats)
        log.info("DGU BU page %d: +%d (total %d)", page, len(feats), len(all_feats))
        if len(feats) < page_size:
            break
    return all_feats


def _extract_polygon(geom2d: dict[str, Any] | None) -> Polygon | None:
    """Pull the polygon out of INSPIRE BuildingGeometry2D and swap axis to (lon, lat)."""
    if not geom2d:
        return None
    geom = geom2d.get("geometry") or {}
    if geom.get("type") != "Polygon":
        return None
    rings = geom.get("coordinates") or []
    if not rings:
        return None
    # INSPIRE EPSG:4326 axis order is (lat, lon) — swap to GeoJSON (lon, lat).
    swapped_rings = [[(pt[1], pt[0]) for pt in ring] for ring in rings]
    if len(swapped_rings[0]) < 4:
        return None
    try:
        poly = Polygon(swapped_rings[0], holes=swapped_rings[1:] or None)
        if not poly.is_valid:
            poly = poly.buffer(0)
        return poly if not poly.is_empty else None
    except Exception:
        return None


def _safe_height(props: dict[str, Any]) -> float | None:
    h = (props.get("heightAboveGround") or {}).get("HeightAboveGround") or {}
    v = (h.get("value") or {}).get("value")
    try:
        if v is None:
            return None
        f = float(v)
        return f if f > 0 else None
    except (TypeError, ValueError):
        return None


def _safe_name(props: dict[str, Any]) -> str | None:
    name = (props.get("name") or {}).get("GeographicalName") or {}
    spelling = name.get("spelling") or {}
    txt = spelling.get("text")
    return txt if isinstance(txt, str) else None


def ingest(bbox_4326: tuple[float, float, float, float] | None = None) -> int:
    settings = get_settings()
    if bbox_4326 is None:
        bbox_4326 = settings.pilot_bbox

    log.info("Fetching DGU registered buildings for bbox %s ...", bbox_4326)
    features = fetch_buildings(bbox_4326)
    log.info("DGU BU WFS returned %d features", len(features))

    inserted = 0
    skipped_no_geom = 0
    with SessionLocal() as db:
        for feat in features:
            props = feat.get("properties") or {}
            poly = _extract_polygon(props.get("geometry2D"))
            if poly is None:
                skipped_no_geom += 1
                continue

            inspire_id = (props.get("inspireId") or {}).get("localId") or feat.get("id") or "unknown"
            rid = f"{SOURCE}:{inspire_id}"
            existing = db.scalar(select(RegisteredBuilding).where(RegisteredBuilding.id == rid))
            permit_ref = _safe_name(props)  # the "spelling.text" is usually a building number
            height_m = _safe_height(props)

            if existing:
                existing.geometry_wkt = poly.wkt
                existing.permit_ref = permit_ref
            else:
                db.add(
                    RegisteredBuilding(
                        id=rid,
                        source=SOURCE,
                        source_id=inspire_id,
                        geometry_wkt=poly.wkt,
                        permit_ref=permit_ref,
                        year_built=None,  # not in this WFS; comes from a different DGU dataset
                    )
                )
                inserted += 1
        db.commit()
    log.info("Ingested %d registered buildings (%d skipped: no geom)", inserted, skipped_no_geom)
    return inserted


def probe() -> dict[str, Any]:
    try:
        caps_url = f"{ENDPOINT}?{urlencode({'service': 'WFS', 'request': 'GetCapabilities', 'version': '2.0.0'})}"
        body = _http_get(caps_url, timeout=15.0)
        return {"ok": True, "capabilities_bytes": len(body), "endpoint": ENDPOINT}
    except Exception as err:
        return {"ok": False, "error": str(err), "endpoint": ENDPOINT}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    print("Probing DGU Buildings WFS ...")
    print(json.dumps(probe(), indent=2))
    print()
    try:
        n = ingest()
        print(f"DGU Buildings: {n} registered buildings ingested.")
    except RuntimeError as err:
        print(f"DGU Buildings ingest failed: {err}")
        raise SystemExit(2)
