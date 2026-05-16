# Parcel Enforcement Queue Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first city-facing dashboard slice: a ranked parcel queue showing likely enforcement priorities from the existing v3 building, parcel, and land-use evidence.

**Architecture:** Add a backend parcel analytics module that does deterministic centroid-in-parcel assignment at load time and produces compact queue rows. Expose the rows through FastAPI, then render a dense dashboard panel in the existing Cesium app that can select a parcel, filter the map to its flagged buildings, and show a case-file style summary.

**Tech Stack:** Python/FastAPI, GeoJSON, vanilla JavaScript, CesiumJS, pytest, browser QA.

---

### Task 1: Backend Parcel Queue

**Files:**
- Create: `backend/split_ontology/parcel_queue.py`
- Modify: `backend/split_ontology/data_loader.py`
- Modify: `backend/split_ontology/api.py`
- Test: `backend/tests/test_parcel_queue.py`

- [ ] **Step 1: Write failing tests**

```python
from split_ontology.data_loader import load_dataset
from split_ontology.parcel_queue import build_parcel_queue


def test_parcel_queue_ranks_flagged_parcels_by_score():
    queue = build_parcel_queue(load_dataset())

    assert [row["parcel_id"] for row in queue[:2]] == ["Split/1240", "Split/1241"]
    assert queue[0]["priority_building_count"] == 2
    assert queue[0]["total_flagged_area_m2"] == 179
    assert queue[0]["impact_score"] > queue[1]["impact_score"]
    assert queue[0]["risk_level"] == "high"
    assert queue[0]["recommended_next_step"] == "Field inspection and zoning review"


def test_parcel_queue_keeps_empty_context_parcels_at_bottom():
    queue = build_parcel_queue(load_dataset())

    assert queue[-1]["priority_building_count"] == 0
    assert queue[-1]["impact_score"] == 0
    assert queue[-1]["recommended_next_step"] == "No action"
```

Run: `.venv/bin/python -m pytest backend/tests/test_parcel_queue.py -v`
Expected: fail because `split_ontology.parcel_queue` does not exist.

- [ ] **Step 2: Implement queue builder**

Create `parcel_queue.py` with:
- `build_parcel_queue(dataset) -> list[dict]`
- `point_in_polygon(point, ring) -> bool`
- simple centroid helpers using the largest outer ring
- scoring: flagged area plus bonuses for agricultural/protected parcels and high confidence

- [ ] **Step 3: Add dataset field and API endpoint**

Modify `LocalGeoJsonDataset` to include `parcel_queue`.
Add `GET /api/parcels/queue` returning `{"items": dataset.parcel_queue}`.

- [ ] **Step 4: Run backend tests**

Run: `.venv/bin/python -m pytest backend/tests/test_parcel_queue.py backend/tests/test_api.py -v`
Expected: pass.

### Task 2: Dashboard Panel

**Files:**
- Modify: `frontend/index.html`
- Modify: `frontend/app.js`
- Modify: `frontend/styles.css`
- Test: `backend/tests/test_frontend_cesium_rendering.py`

- [ ] **Step 1: Write failing static frontend test**

Assert the HTML contains `#caseQueue`, app script fetches `/api/parcels/queue`, and app script has `selectParcelCase`.

- [ ] **Step 2: Implement panel markup and styles**

Add a compact “Parcel Queue” section under metrics with queue rows, risk badges, score, flagged count, and action labels.

- [ ] **Step 3: Implement frontend behavior**

Fetch `/api/parcels/queue` during initialization. Render rows sorted by backend order. Clicking a row filters the active map layer to `unregistered,protected_land`, opens a case-file inspector summary, and flies the camera to the parcel bbox.

- [ ] **Step 4: Run static tests and JS check**

Run: `.venv/bin/python -m pytest backend/tests/test_frontend_cesium_rendering.py -v`
Run: `node --check frontend/app.js`
Expected: pass.

### Task 3: Browser QA

**Files:**
- No source changes unless QA finds defects.

- [ ] **Step 1: Restart LAN server**

Run: `screen -S split-ontology-server -X quit; screen -dmS split-ontology-server bash -lc 'cd /Users/matejban/firma/split-ontology && .venv/bin/python -m uvicorn split_ontology.api:app --host 0.0.0.0 --port 8000'`

- [ ] **Step 2: Validate in browser**

Open `http://10.10.0.186:8000/`.
Check:
- page loads v3 metrics
- parcel queue renders two high-value flagged cases above no-action parcels
- click `Split/1240` opens case-file summary
- map remains usable and toolbar remains accessible
- no fresh console errors

- [ ] **Step 3: Final verification**

Run: `.venv/bin/python -m pytest`
Run: `node --check frontend/app.js && node --check frontend/ion-token.local.js`
Run: `curl -s http://10.10.0.186:8000/api/parcels/queue`

Expected: all tests pass, JS syntax passes, queue API returns seven parcel rows.
