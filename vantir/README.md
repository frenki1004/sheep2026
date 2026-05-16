# Vantir Technologies

Small end-to-end prototype for fusing official and live building evidence in Split, Croatia. The app now runs from the local `katastar-eye-data-v3` GeoJSON export, copied into `data/`.

## What Is Included

- Canonical building records from `data/buildings.geojson`.
- Discrepancy classes: `registered_match`, `unregistered`, `protected_land`, `katastar_only`.
- FastAPI endpoints for GeoJSON overlays and building inspector details.
- Cesium viewer using Google Photorealistic 3D Tiles bootstrap and discrepancy-colored ground-clamped Cesium layers.
- Local source files:
  - `buildings_ms.geojson`: 23,431 Microsoft ML footprints
  - `buildings_oss.geojson`: 39,279 current OSS katastar buildings
  - `buildings_oss_raw.geojson`: 39,279 raw OSS katastar buildings
  - `buildings_dgu.geojson`: 11,317 DGU INSPIRE 2016 buildings
  - `buildings.geojson`: 25,991 merged building results
  - `landuse.geojson`: 1,254 land use zones
  - `parcels.geojson`: 7 parcel context features
  - `reproject-oss.js`, `spatial-join.js`: v3 processing/provenance scripts

The merged result contains 19,346 matched buildings, 3,827 plain unregistered buildings, 258 protected-land flags, and 2,560 katastar-only buildings. The 3,827 plain unregistered plus 258 protected-land flags make 4,085 priority flags.

## Local Setup

```bash
cd /Users/matejban/firma/split-ontology
.venv/bin/python -m pytest
.venv/bin/python -m uvicorn split_ontology.api:app --reload --port 8000
```

Open `http://127.0.0.1:8000`.

For LAN access, run Uvicorn on all interfaces and open the machine's local-network IP:

```bash
.venv/bin/python -m uvicorn split_ontology.api:app --host 0.0.0.0 --port 8000
```

The app loads the Cesium ion token from `frontend/ion-token.local.js`. That file is gitignored because browser-visible tokens are local deployment config.

## API

- `GET /api/summary`
- `GET /api/sources`
- `GET /api/buildings.geojson`
- `GET /api/buildings.geojson?view=priority`
- `GET /api/buildings.geojson?discrepancy_type=protected_land`
- `GET /api/buildings/{id}`
- `GET /api/landuse.geojson`
- `GET /api/parcels.geojson`
- `GET /api/parcels/queue`
