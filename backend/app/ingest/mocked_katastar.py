"""Mocked katastar adapter — placeholder until the live DGU WFS spike (task #4) lands.

Field names mirror the real DGU schema so the live switch is mechanical:
    ko_id / ko_naziv      cadastral municipality (Split = 338320)
    broj_cestice          parcel number, e.g. "8523/1"
    povrsina              area in m²
    nacin_uporabe         land-use category

The data file lives at `backend/data/parcels.geojson`. If absent, this module
generates a deterministic ~36-parcel mock for the Žnjan pilot bbox.

Run:
    uv run python -m app.ingest.mocked_katastar
"""
from __future__ import annotations

import json
import logging
import math
from pathlib import Path
from random import Random
from typing import Any

from shapely.geometry import Polygon, mapping, shape
from sqlalchemy import select

from app.db import SessionLocal
from app.ontology.models import Parcel

log = logging.getLogger(__name__)

SOURCE = "mocked_katastar"
KO_ID = "338320"
KO_NAZIV = "Split"

DATA_FILE = Path(__file__).resolve().parent.parent.parent / "data" / "parcels.geojson"

# Žnjan cluster center; rows N-S, cols E-W.
_CENTER_LON = 16.4900
_CENTER_LAT = 43.5100
_ROWS = 6
_COLS = 6
_PARCEL_W_M = 35.0  # ~residential lot width
_PARCEL_H_M = 45.0
_FIRST_CESTICA = 8500

# Land-use distribution (realistic mix for a coastal Split neighborhood).
_USE_WEIGHTS: list[tuple[str, float]] = [
    ("stambeno zemljište", 0.50),
    ("gradilište", 0.18),
    ("poslovno zemljište", 0.10),
    ("zelena površina", 0.14),
    ("poljoprivredno zemljište", 0.05),
    ("neuporabljivo", 0.03),
]


def _meters_to_degrees(dx_m: float, dy_m: float, lat_deg: float) -> tuple[float, float]:
    dlat = dy_m / 111_320.0
    dlon = dx_m / (111_320.0 * math.cos(math.radians(lat_deg)))
    return dlon, dlat


def _weighted_pick(rng: Random) -> str:
    r = rng.random()
    acc = 0.0
    for label, w in _USE_WEIGHTS:
        acc += w
        if r <= acc:
            return label
    return _USE_WEIGHTS[-1][0]


def generate_parcels_geojson() -> dict[str, Any]:
    """Return a deterministic GeoJSON FeatureCollection of mocked Žnjan parcels."""
    rng = Random(20260516)
    features: list[dict[str, Any]] = []
    dlon, dlat = _meters_to_degrees(_PARCEL_W_M, _PARCEL_H_M, _CENTER_LAT)

    origin_lon = _CENTER_LON - dlon * _COLS / 2
    origin_lat = _CENTER_LAT - dlat * _ROWS / 2

    for r in range(_ROWS):
        for c in range(_COLS):
            # Tiny jitter so the grid doesn't look CAD-perfect.
            jx = rng.uniform(-0.15, 0.15) * dlon
            jy = rng.uniform(-0.15, 0.15) * dlat
            x0 = origin_lon + c * dlon + jx
            y0 = origin_lat + r * dlat + jy
            x1, y1 = x0 + dlon, y0 + dlat

            poly = Polygon([(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)])
            cestica_num = _FIRST_CESTICA + r * _COLS + c
            sub = rng.choice([1, 1, 1, 2, 3])  # most parcels are /1, some subdivided

            features.append(
                {
                    "type": "Feature",
                    "id": f"{KO_ID}-{cestica_num}/{sub}",
                    "geometry": mapping(poly),
                    "properties": {
                        "ko_id": KO_ID,
                        "ko_naziv": KO_NAZIV,
                        "broj_cestice": f"{cestica_num}/{sub}",
                        "nacin_uporabe": _weighted_pick(rng),
                        # Area is computed against a local equirectangular approximation
                        # so the value is plausible m² — exact area happens in code.
                        "povrsina": round(_PARCEL_W_M * _PARCEL_H_M, 1),
                        "source": SOURCE,
                    },
                }
            )

    return {
        "type": "FeatureCollection",
        "name": "znjan_mocked_parcels",
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
        "features": features,
    }


def ensure_data_file(path: Path = DATA_FILE) -> Path:
    if path.exists():
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = generate_parcels_geojson()
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    log.info("Generated %d mocked parcels at %s", len(payload["features"]), path)
    return path


def ingest(path: Path = DATA_FILE) -> int:
    """Read parcels.geojson and upsert into the Parcel table. Returns row count."""
    path = ensure_data_file(path)
    raw = json.loads(path.read_text())
    n = 0
    with SessionLocal() as db:
        for feat in raw["features"]:
            props = feat["properties"]
            geom = shape(feat["geometry"])
            source_id = feat.get("id") or f"{props.get('ko_id')}-{props.get('broj_cestice')}"
            parcel_id = f"{SOURCE}:{source_id}"

            existing = db.scalar(select(Parcel).where(Parcel.id == parcel_id))
            if existing:
                existing.geometry_wkt = geom.wkt
                existing.ko_id = props.get("ko_id")
                existing.ko_naziv = props.get("ko_naziv")
                existing.broj_cestice = props.get("broj_cestice")
                existing.land_use = props.get("nacin_uporabe")
                existing.area_m2 = props.get("povrsina")
            else:
                db.add(
                    Parcel(
                        id=parcel_id,
                        source=SOURCE,
                        source_id=source_id,
                        ko_id=props.get("ko_id"),
                        ko_naziv=props.get("ko_naziv"),
                        broj_cestice=props.get("broj_cestice"),
                        geometry_wkt=geom.wkt,
                        area_m2=props.get("povrsina"),
                        land_use=props.get("nacin_uporabe"),
                    )
                )
            n += 1
        db.commit()
    log.info("Ingested %d parcels from %s", n, path)
    return n


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    n = ingest()
    print(f"Mocked katastar: {n} parcels ingested.")
