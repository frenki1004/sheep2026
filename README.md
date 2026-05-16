# Vantir Technologies

Automated detection of unregistered and illegal construction in Split, Croatia.  
Cross-references satellite ML building footprints with official katastar records.

## Architecture

Two independent frontends, one shared data pipeline:

| Component | Port | Description |
|-----------|------|-------------|
| `app/` (2D Viewer) | 3000 | MapLibre-based 2D/3D map with terrain, land use zones, parcel boundaries |
| `vantir/` (3D Viewer) | 8000 | Cesium + FastAPI backend with Google Photorealistic 3D Tiles |

---

## Quick Start — 2D Viewer (`app/`)

```bash
cd app
npm install
npx vite --host
```

Opens on http://localhost:3000 (exposed on LAN with `--host`).

No backend needed — all data is static GeoJSON in `app/public/data/`.

---

## Quick Start — 3D Viewer (`vantir/`)

Requires Python 3.12+.

```bash
cd vantir
pip install -e .
uvicorn backend.split_ontology.api:app --host 0.0.0.0 --port 8000
```

Then open http://localhost:8000 — the FastAPI backend serves the frontend from `vantir/frontend/`.

---

## Data Pipeline (regenerating buildings.geojson)

If you need to re-run the classification:

```bash
cd app/scripts
node spatial-join.js
```

This reads `buildings_ms.geojson` + `buildings_oss.geojson` + `landuse.geojson` from `app/public/data/` and outputs the classified `buildings.geojson`.

---

## Data Sources

- **Microsoft Global ML Building Footprints** — satellite-detected polygons
- **OSS uredjenazemlja.hr** — live Croatian katastar (2026)
- **DGU INSPIRE WFS** — land use zones
- **OSS WMS** — cadastral parcel boundary overlay (live tiles)

---

## Team

Built at SheepAI Hackathon 2026, Split.
