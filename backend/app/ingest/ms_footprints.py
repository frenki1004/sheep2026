"""Microsoft Global ML Building Footprints adapter.

Pulls per-country quadkey tiles (geojsonl.gz on Azure Blob), filters to the
pilot bbox, and writes one ObservedBuilding row per polygon with source='ms_footprints'.

Dataset index: https://minedbuildings.z5.web.core.windows.net/global-buildings/dataset-links.csv

Run:
    uv run python -m app.ingest.ms_footprints
"""
from __future__ import annotations

import csv
import gzip
import hashlib
import json
import logging
import math
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

from shapely.geometry import box, shape
from shapely.prepared import prep
from sqlalchemy import select

from app.config import get_settings
from app.db import SessionLocal
from app.ontology.models import ObservedBuilding

log = logging.getLogger(__name__)

SOURCE = "ms_footprints"
USER_AGENT = "Sheep-AI/0.1 (hackathon)"
INDEX_URL = "https://minedbuildings.z5.web.core.windows.net/global-buildings/dataset-links.csv"
CACHE_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "cache" / "ms_footprints"
QUADKEY_ZOOM = 9
# Microsoft's index includes a generic "Europe" duplicate-region for the same tiles —
# prefer the country-specific region to avoid double-pulling.
DEFAULT_COUNTRIES = ("Croatia",)


def _lonlat_to_quadkey(lon: float, lat: float, zoom: int = QUADKEY_ZOOM) -> str:
    lat_rad = math.radians(lat)
    n = 2.0**zoom
    xtile = int((lon + 180.0) / 360.0 * n)
    ytile = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    qk = []
    for i in range(zoom, 0, -1):
        digit = 0
        mask = 1 << (i - 1)
        if xtile & mask:
            digit += 1
        if ytile & mask:
            digit += 2
        qk.append(str(digit))
    return "".join(qk)


def bbox_quadkeys(bbox_4326: tuple[float, float, float, float], zoom: int = QUADKEY_ZOOM) -> set[str]:
    """Return all quadkeys that intersect the bbox at the given zoom."""
    minx, miny, maxx, maxy = bbox_4326
    keys: set[str] = set()
    # Sample a 5x5 lattice — bbox is small enough that this catches all tiles.
    for i in range(6):
        for j in range(6):
            lon = minx + (maxx - minx) * i / 5
            lat = miny + (maxy - miny) * j / 5
            keys.add(_lonlat_to_quadkey(lon, lat, zoom))
    return keys


def _download(url: str, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = Request(url, headers={"User-Agent": USER_AGENT})
    log.info("Downloading %s ...", url)
    with urlopen(req, timeout=120) as resp:  # noqa: S310 — trusted endpoint
        dest.write_bytes(resp.read())
    log.info("  → %s (%.1f MB)", dest, dest.stat().st_size / 1_048_576)
    return dest


def fetch_index() -> list[dict[str, str]]:
    cache = CACHE_DIR / "dataset-links.csv"
    if not cache.exists():
        _download(INDEX_URL, cache)
    with cache.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def select_tiles(
    bbox_4326: tuple[float, float, float, float],
    countries: tuple[str, ...] = DEFAULT_COUNTRIES,
) -> list[dict[str, str]]:
    target_keys = bbox_quadkeys(bbox_4326)
    rows = fetch_index()
    return [r for r in rows if r["QuadKey"] in target_keys and r["Location"] in countries]


def _bbox_polygon(bbox_4326: tuple[float, float, float, float]):
    minx, miny, maxx, maxy = bbox_4326
    return prep(box(minx, miny, maxx, maxy))


def _stable_id(geom_wkt: str, source_id_seed: str) -> str:
    h = hashlib.sha1(f"{source_id_seed}:{geom_wkt}".encode()).hexdigest()[:24]
    return f"{SOURCE}:{h}"


def ingest(bbox_4326: tuple[float, float, float, float] | None = None) -> int:
    settings = get_settings()
    if bbox_4326 is None:
        bbox_4326 = settings.pilot_bbox
    bbox_prep = _bbox_polygon(bbox_4326)

    tiles = select_tiles(bbox_4326)
    if not tiles:
        log.warning("No MS Footprints tiles selected for bbox %s", bbox_4326)
        return 0
    log.info("Selected %d tile(s) for bbox %s", len(tiles), bbox_4326)

    now = datetime.now(timezone.utc)
    inserted = 0
    seen_in_bbox = 0

    with SessionLocal() as db:
        for tile in tiles:
            qk = tile["QuadKey"]
            country = tile["Location"]
            url = tile["Url"]
            cache = CACHE_DIR / country / f"{qk}.csv.gz"
            if not cache.exists():
                _download(url, cache)
            else:
                log.info("Using cached tile %s", cache)

            with gzip.open(cache, "rb") as gz:
                for line_no, raw in enumerate(gz, 1):
                    if not raw.strip():
                        continue
                    feat = json.loads(raw)
                    geom = shape(feat["geometry"])
                    if not bbox_prep.intersects(geom):
                        continue
                    seen_in_bbox += 1
                    geom_wkt = geom.wkt
                    src_id = f"{country}/{qk}/{line_no}"
                    bid = _stable_id(geom_wkt, src_id)

                    existing = db.scalar(select(ObservedBuilding).where(ObservedBuilding.id == bid))
                    props = feat.get("properties") or {}
                    height = props.get("height")
                    confidence = props.get("confidence")
                    if existing:
                        existing.geometry_wkt = geom_wkt
                        existing.height_m = height if height and height > 0 else None
                        existing.raw_attributes = json.dumps({"confidence": confidence, "tile": qk})
                    else:
                        db.add(
                            ObservedBuilding(
                                id=bid,
                                source=SOURCE,
                                source_id=src_id,
                                geometry_wkt=geom_wkt,
                                height_m=height if height and height > 0 else None,
                                last_seen=now,
                                raw_attributes=json.dumps({"confidence": confidence, "tile": qk}),
                            )
                        )
                        inserted += 1
            db.commit()
            log.info("Tile %s: %d in-bbox features so far, %d new", qk, seen_in_bbox, inserted)

    log.info("Ingested %d new MS footprints (%d total in bbox).", inserted, seen_in_bbox)
    return inserted


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    n = ingest()
    print(f"MS Footprints: {n} buildings ingested.")
