"""Live DGU katastar adapter via the INSPIRE Cadastral Parcels WFS.

Endpoint discovered 2026-05-16:
    https://api.uredjenazemlja.hr/services/inspire/cp/wfs

Feature types (from GetCapabilities):
    cp:CadastralParcel   parcels (default CRS EPSG:3765 / HTRS96/TM)
    cp:CadastralZoning   cadastral municipalities

Known flakiness: the upstream Oracle backend sometimes raises
`ORA-01000: maximum open cursors exceeded` on bbox GetFeature requests
(SDO_INDEX exhaustion). The adapter retries with backoff and, on persistent
failure, exits cleanly so the mocked adapter remains the source of truth
for demo runs. Re-run when the server recovers.

Run:
    uv run python -m app.ingest.dgu_wfs
"""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from shapely.geometry import shape
from sqlalchemy import select

from app.config import get_settings
from app.db import SessionLocal
from app.ontology.models import Parcel

log = logging.getLogger(__name__)

SOURCE = "dgu_wfs"
ENDPOINT = "https://api.uredjenazemlja.hr/services/inspire/cp/wfs"
TYPE_NAME = "cp:CadastralParcel"
USER_AGENT = "Sheep-AI/0.1 (hackathon; +https://github.com/frenki1004/sheep2026)"

# Map DGU INSPIRE CP properties to our schema. Properties seen in the GML schema:
#   gml:id                  unique id
#   cp:nationalCadastralReference  e.g. "338320 8523/1" — our broj_cestice + ko_id
#   cp:areaValue            povrsina (m²)
#   cp:beginLifespanVersion timestamp
# The INSPIRE schema is opinionated; we tolerate missing fields.


def _http_get(url: str, timeout: float = 30.0) -> bytes:
    req = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
    with urlopen(req, timeout=timeout) as resp:  # noqa: S310 — trusted endpoint
        return resp.read()


def get_capabilities() -> bytes:
    url = f"{ENDPOINT}?{urlencode({'service': 'WFS', 'request': 'GetCapabilities', 'version': '2.0.0'})}"
    return _http_get(url)


def _fetch_page(
    bbox_4326: tuple[float, float, float, float],
    start_index: int,
    page_size: int,
    *,
    max_retries: int = 5,
    backoff_s: float = 4.0,
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
            body = _http_get(url, timeout=60.0)
            try:
                data = json.loads(body)
            except json.JSONDecodeError:
                snippet = body[:400].decode("utf-8", errors="replace")
                raise RuntimeError(f"WFS returned non-JSON: {snippet}")
            return data.get("features", [])
        except Exception as err:
            last_err = err
            log.warning("DGU CP page@%d attempt %d/%d failed: %s", start_index, attempt, max_retries, err)
            if attempt < max_retries:
                time.sleep(backoff_s + attempt * 2)
    assert last_err is not None
    raise RuntimeError(f"DGU CP WFS page@{start_index} unavailable after {max_retries} attempts: {last_err}")


def fetch_parcels(
    bbox_4326: tuple[float, float, float, float],
    *,
    page_size: int = 500,
    max_pages: int = 20,
) -> list[dict[str, Any]]:
    """Fetch parcels by paginating WFS startIndex. Returns whatever was fetched if a later page is unrecoverable."""
    all_feats: list[dict[str, Any]] = []
    for page in range(max_pages):
        start = page * page_size
        try:
            feats = _fetch_page(bbox_4326, start, page_size)
        except RuntimeError as err:
            log.error("DGU CP pagination stopped at page %d: %s. Keeping %d parcels fetched so far.", page, err, len(all_feats))
            break
        all_feats.extend(feats)
        log.info("DGU CP page %d: +%d (total %d)", page, len(feats), len(all_feats))
        if len(feats) < page_size:
            break
    return all_feats


def _unpack_measure(val: Any) -> float | None:
    """INSPIRE Measure types come through as {'value': N, '@uom': 'm2'}. Tolerate scalars too."""
    if val is None:
        return None
    if isinstance(val, dict):
        v = val.get("value")
        try:
            return float(v) if v is not None else None
        except (TypeError, ValueError):
            return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _map_feature(feat: dict[str, Any]) -> dict[str, Any] | None:
    """Pull DGU INSPIRE fields into our schema. Returns None if essential fields are missing."""
    props = feat.get("properties") or {}
    geom = feat.get("geometry")
    if not geom:
        return None

    # DGU's nationalCadastralReference is "{ko_id}-{parcel_num}", e.g. "329835-2567/1".
    nat_ref: str = props.get("nationalCadastralReference") or ""
    ko_id: str | None = None
    broj_cestice: str | None = None
    if "-" in nat_ref:
        ko_id, broj_cestice = nat_ref.split("-", 1)
    elif " " in nat_ref:  # fallback for INSPIRE-canonical space separator
        ko_id, broj_cestice = nat_ref.split(" ", 1)
    elif nat_ref:
        broj_cestice = nat_ref

    return {
        "source_id": feat.get("id") or nat_ref or "unknown",
        "ko_id": ko_id,
        "ko_naziv": props.get("cadastralZoningName"),
        "broj_cestice": broj_cestice,
        "geometry": geom,
        "area_m2": _unpack_measure(props.get("areaValue")),
        "land_use": props.get("landUse") or props.get("nacin_uporabe"),
    }


def ingest(bbox_4326: tuple[float, float, float, float] | None = None) -> int:
    """Pull parcels for the pilot bbox and upsert into the Parcel table."""
    settings = get_settings()
    if bbox_4326 is None:
        bbox_4326 = settings.pilot_bbox

    log.info("Fetching DGU parcels for bbox %s ...", bbox_4326)
    features = fetch_parcels(bbox_4326)
    log.info("DGU WFS returned %d features", len(features))

    n = 0
    with SessionLocal() as db:
        for feat in features:
            row = _map_feature(feat)
            if row is None:
                continue
            geom = shape(row["geometry"])
            parcel_id = f"{SOURCE}:{row['source_id']}"
            existing = db.scalar(select(Parcel).where(Parcel.id == parcel_id))
            if existing:
                existing.geometry_wkt = geom.wkt
                existing.ko_id = row["ko_id"]
                existing.ko_naziv = row["ko_naziv"]
                existing.broj_cestice = row["broj_cestice"]
                existing.area_m2 = row["area_m2"]
                existing.land_use = row["land_use"]
            else:
                db.add(
                    Parcel(
                        id=parcel_id,
                        source=SOURCE,
                        source_id=row["source_id"],
                        ko_id=row["ko_id"],
                        ko_naziv=row["ko_naziv"],
                        broj_cestice=row["broj_cestice"],
                        geometry_wkt=geom.wkt,
                        area_m2=row["area_m2"],
                        land_use=row["land_use"],
                    )
                )
            n += 1
        db.commit()
    log.info("Ingested %d DGU parcels", n)
    return n


def probe() -> dict[str, Any]:
    """Cheap health check. Returns capabilities-size and reachability status."""
    try:
        caps = get_capabilities()
        return {"ok": True, "capabilities_bytes": len(caps), "endpoint": ENDPOINT}
    except Exception as err:
        return {"ok": False, "error": str(err), "endpoint": ENDPOINT}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    print("Probing DGU WFS ...")
    print(json.dumps(probe(), indent=2))
    print()
    try:
        n = ingest()
        print(f"DGU WFS: {n} parcels ingested.")
    except RuntimeError as err:
        print(f"DGU WFS ingest failed: {err}")
        print("Mocked katastar remains the source of truth for this run.")
        raise SystemExit(2)
