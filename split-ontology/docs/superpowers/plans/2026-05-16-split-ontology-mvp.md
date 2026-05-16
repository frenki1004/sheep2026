# Split Ontology MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the smallest end-to-end Split building ontology MVP for the Mejasí pilot area: official DGU cadastre observations, one live footprint source, canonical building resolution, discrepancy API, and Cesium overlay/inspector.

**Architecture:** The MVP is a self-contained project with a Python geospatial backend and a static Cesium frontend. The backend keeps source observations as immutable evidence, computes canonical building records through spatial matching, and exposes GeoJSON plus inspector endpoints. The frontend loads Google Photorealistic 3D Tiles using the requested Cesium bootstrap and overlays discrepancy-colored building polygons.

**Tech Stack:** Python 3.12, FastAPI, Shapely, Pytest, optional DuckDB/Pyogrio ingestion adapters, static HTML/CSS/ES modules, CesiumJS via import map/CDN.

---

## File Structure

- `pyproject.toml`: Python package metadata, dependencies, test configuration.
- `README.md`: local setup, data-source notes, Cesium token notes, and MVP commands.
- `backend/split_ontology/domain.py`: dataclasses and enum-like constants for source observations, canonical buildings, and links.
- `backend/split_ontology/resolution.py`: spatial matching, canonical building creation, discrepancy classification.
- `backend/split_ontology/sample_data.py`: deterministic Mejasí-sized fixture observations for local development and tests.
- `backend/split_ontology/api.py`: FastAPI app exposing health, sources, buildings GeoJSON, building inspector detail.
- `backend/split_ontology/ingest/dgu.py`: DGU WFS URL construction and parsing boundary for cadastre buildings/parcels.
- `backend/split_ontology/ingest/overture.py`: Overture release query boundary and documented DuckDB SQL.
- `backend/tests/test_resolution.py`: TDD coverage for matching and discrepancy classification.
- `backend/tests/test_api.py`: API contract tests.
- `frontend/index.html`: static app shell with Cesium container and inspector.
- `frontend/styles.css`: dense planning-tool UI styling.
- `frontend/app.js`: Cesium bootstrap, overlay loading, color mapping, click inspector.

## Task 1: Project Skeleton and Domain Tests

**Files:**
- Create: `split-ontology/pyproject.toml`
- Create: `split-ontology/backend/split_ontology/domain.py`
- Create: `split-ontology/backend/tests/test_resolution.py`

- [ ] Write failing tests for canonical records and discrepancy categories.
- [ ] Run `python -m pytest backend/tests/test_resolution.py -q`; expect import failures before implementation.
- [ ] Implement domain dataclasses and constants.
- [ ] Re-run tests until the domain imports cleanly.

## Task 2: Spatial Resolution

**Files:**
- Create: `split-ontology/backend/split_ontology/resolution.py`
- Modify: `split-ontology/backend/tests/test_resolution.py`

- [ ] Add failing tests for IoU matching, unregistered footprints, demolished registered buildings, and size mismatch.
- [ ] Implement matching with Shapely geometry operations.
- [ ] Re-run resolution tests.

## Task 3: API Contract

**Files:**
- Create: `split-ontology/backend/split_ontology/sample_data.py`
- Create: `split-ontology/backend/split_ontology/api.py`
- Create: `split-ontology/backend/tests/test_api.py`

- [ ] Write failing tests for `/health`, `/api/buildings.geojson`, and `/api/buildings/{id}`.
- [ ] Implement the FastAPI app using sample observations.
- [ ] Re-run API tests.

## Task 4: Ingestion Boundaries

**Files:**
- Create: `split-ontology/backend/split_ontology/ingest/dgu.py`
- Create: `split-ontology/backend/split_ontology/ingest/overture.py`

- [ ] Add functions that build DGU WFS and Overture query inputs for the configured AOI.
- [ ] Keep live downloading optional so tests do not depend on external services.
- [ ] Document source URLs, releases, and command stubs in `README.md`.

## Task 5: Cesium Frontend

**Files:**
- Create: `split-ontology/frontend/index.html`
- Create: `split-ontology/frontend/styles.css`
- Create: `split-ontology/frontend/app.js`

- [ ] Implement the requested Cesium bootstrap exactly in `app.js`.
- [ ] Load `/api/buildings.geojson`.
- [ ] Render discrepancy-colored polygons/extrusions.
- [ ] Open an inspector with linked source observations on click.

## Task 6: Verification

**Files:**
- Modify: `split-ontology/README.md`

- [ ] Install Python dependencies in a local `.venv`.
- [ ] Run `python -m pytest`.
- [ ] Start the API/static server.
- [ ] Open the frontend in a browser and verify the app loads, the sample overlay appears, and clicking a building opens the inspector.
- [ ] Record any blocker, especially Cesium/Google credentials if Photorealistic 3D Tiles cannot load locally.

## Self-Review

- Spec coverage: covers MVP sources, schema concepts, entity resolution, Cesium overlay, inspector, and source boundaries.
- Scope check: Phase 2/3 features are intentionally deferred; the MVP has a local sample-data mode and source adapter boundaries.
- Placeholder scan: no implementation placeholder is required for runtime behavior; source downloads are intentionally optional because public services and credentials are external.
