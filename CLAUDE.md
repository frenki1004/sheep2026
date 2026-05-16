# CLAUDE.md

Guidance for Claude Code (and human teammates) working in this repo.

## What this project is

Sheep AI 2026 hackathon entry: an AI platform that detects likely illegal construction in the City of Split by comparing satellite imagery to the Croatian cadastre (*katastar*), and that pairs detection with a citizen-friendly portal for build-pre-checks and guided legalization. See `README.md` for the full pitch and the ethics framing — both are load-bearing for this project and any feature work should keep them in mind.

Two product surfaces ship in the demo, equal weight:

1. **City dashboard** — flagged-parcel map, evidence panel, time-lapse change detection.
2. **Citizen portal** — parcel/address lookup, "can I build this?" wizard, legalization assistant.

## Stack (agreed)

Pick these unless there's a strong reason to deviate, and update this file if you do.

**Backend — Python 3.11+, FastAPI**
- `earthengine-api` — imagery + change detection done server-side on GEE (don't pull big rasters locally).
- Building footprints: Microsoft Global ML Building Footprints (covers Croatia) as the CV shortcut — we *diff* existing footprints against katastar polygons rather than training a segmenter from scratch. `segment-geospatial` is the fallback if we need on-the-fly segmentation.
- `geopandas` + `shapely` for the footprint-diff and parcel-intersection logic.
- SQLite + SpatiaLite for the flagged-parcel store during the hackathon (swap to Postgres/PostGIS only if needed).
- Mocked katastar data: a hand-built `data/parcels.geojson` for the pilot neighborhood. The live katastar.hr / DGU integration is documented but not wired up — see README "Hackathon scope".

**Frontend — Next.js (App Router) + TypeScript**
- One app, two routes: `/city` and `/citizen`.
- MapLibre GL for the map; GEE thumbnails / pre-rendered tiles for imagery overlays.
- Tailwind for styling. Keep it minimal — judges look at the demo, not the design system.

**LLM (stretch)**
- Claude API (Sonnet 4.6 default, Haiku 4.5 for cheap calls) for the "can I build this?" chatbot and auto-drafted legalization summaries. RAG over Split's GUP/PPU PDFs. Use prompt caching on the planning-doc context.

**Why not Streamlit:** two product surfaces with map-heavy UX outgrow it fast. We accept the extra glue code.

## Repository layout (target)

This is where we're heading — directories will appear as code lands. Don't create empty scaffolding ahead of need.

```
sheep2026/
├── backend/                 FastAPI app
│   ├── app/
│   │   ├── main.py
│   │   ├── gee/             Earth Engine wrappers (auth, change detection, thumbnails)
│   │   ├── cv/              footprint diff, confidence scoring
│   │   ├── katastar/        mocked-data loaders + live-API spike
│   │   └── api/             routes for dashboard + citizen portal
│   ├── data/
│   │   └── parcels.geojson  mocked katastar for the pilot neighborhood
│   └── pyproject.toml
├── frontend/                Next.js app
│   ├── app/
│   │   ├── city/            planner dashboard
│   │   └── citizen/         build-check + legalization wizard
│   ├── components/
│   └── package.json
├── docs/                    pitch deck, demo script, data-source notes
├── CLAUDE.md
└── README.md
```

## Build / run (placeholders — fill these in as the toolchain lands)

Nothing is wired up yet. Update this section with real commands as soon as the first `pyproject.toml` / `package.json` is committed. Don't invent commands that don't exist.

```bash
# backend (planned)
cd backend
uv sync                       # or: pip install -e .
uv run uvicorn app.main:app --reload

# frontend (planned)
cd frontend
pnpm install
pnpm dev
```

GEE access requires `earthengine authenticate` once per machine, against a Google account that has been added to a GEE project. Document the project ID in `backend/.env.example` when it exists.

## Conventions

- **Don't train models.** Use Microsoft's pre-extracted building footprints + GEE-side ops. Training is out of scope for the timebox.
- **GEE-side first.** If a computation can run in Earth Engine, it should — local raster work is a time sink.
- **Mocked katastar is real-shaped.** When adding mocked parcels, mirror the field names from the actual DGU katastar schema so the live-integration switch is mechanical.
- **Human-in-the-loop is a product requirement, not a nice-to-have.** Anything that surfaces a flagged parcel must show a confidence score and route to a review queue — never an automated notification to an owner without a city reviewer in between.
- **Both audiences, every PR.** When adding a feature, briefly note in the PR description how it affects the city dashboard *and* the citizen portal (even if "n/a" for one of them).
- **Keep PRs small and the demo runnable.** `main` should always boot.

## Pilot scope (so we don't sprawl)

- One neighborhood in Split (Žnjan / Stobreč / Bačvice are good candidates — coastal, visually compelling, known activity).
- ~20–50 mocked parcels with mixed compliance states (clean, minor extension, undeclared structure, recent legal permit).
- 3–5 "ground truth" cases drawn from public reporting where possible — the demo lands harder with real addresses.

## Out of scope for the hackathon

- Training any segmentation model from scratch.
- Live writes to katastar or any city system.
- Authentication / multi-tenant. Single demo user per surface is fine.
- Mobile app. Responsive web is enough.

## When updating this file

- Replace placeholder build commands with real ones the moment they exist.
- If you change the stack, update both this file and the README's "Stack" section in the same commit.
- Don't document aspirational structure. Reflect what is in the repo *now*.
