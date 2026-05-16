# Sheep AI 2026 — Split Illegal Construction Detector

An AI-assisted platform that helps the **City of Split** and its citizens detect, report, and resolve illegal construction by combining satellite imagery, computer vision, and the Croatian cadastre (*katastar*).

## The problem

Split — like much of the Croatian coast — has a long-standing problem with unpermitted construction: rooftop additions, extensions, pools, and entire structures built without a valid building permit. Today, enforcement is mostly reactive and complaint-driven; legalization (*legalizacija*) is paperwork-heavy and opaque to citizens.

We want to flip both sides of that:

1. **Proactive detection** — automatically surface discrepancies between what exists on the ground and what the cadastre/permit records say should be there.
2. **Friendlier compliance** — give citizens a clear, guided path to check what they're allowed to build *before* they build, and to legalize existing structures where possible.

## How it works (high level)

```
        ┌────────────────────┐        ┌────────────────────┐
        │  Satellite / aerial │        │  Katastar + DGU    │
        │  imagery (Google    │        │  parcel & building │
        │  Earth, Sentinel,   │        │  footprints,       │
        │  city orthophoto)   │        │  permits, zoning   │
        └─────────┬──────────┘        └─────────┬──────────┘
                  │                              │
                  ▼                              ▼
        ┌──────────────────────────────────────────────┐
        │  Computer vision: building footprint &        │
        │  change detection (segmentation + diff over   │
        │  time, georeferenced to parcels)              │
        └─────────────────────┬─────────────────────────┘
                              ▼
        ┌──────────────────────────────────────────────┐
        │  Discrepancy engine: footprint Δ vs records,  │
        │  confidence score, parcel/owner lookup,       │
        │  human review queue                           │
        └──────────────────────────────────────────────┘
                              │
            ┌─────────────────┴─────────────────┐
            ▼                                   ▼
   ┌─────────────────┐                 ┌─────────────────┐
   │ City dashboard  │                 │ Citizen portal  │
   │ (planners,      │                 │ (build-check &  │
   │ inspectors)     │                 │ legalization)   │
   └─────────────────┘                 └─────────────────┘
```

## Two products, one pipeline

### 1. City-facing dashboard
For urban planners, inspectors, and the *Konzervatorski odjel*:

- Map of Split with **flagged parcels** ranked by confidence and impact (footprint area, protected zone, coastal setback violations, etc.).
- **Change-detection time-lapse** per parcel so an inspector can see *when* a structure appeared.
- One-click case file: parcel ID, owner (from katastar), permit history, image evidence, suggested next step.
- **Heatmaps** of unpermitted activity by district — useful input for zoning and enforcement strategy.

### 2. Citizen-facing portal — "Can I build this?"
Most owners don't *want* to build illegally; the system is just hard to navigate. We make it easy:

- **Address / parcel lookup** → returns the zoning rules that apply (max height, coverage ratio, distance from coast, conservation status).
- **"Build wizard"**: pick what you want to add (extra floor, pool, terrace, ADU) → tool tells you *upfront* whether it's likely permitted, conditionally permitted, or forbidden, and what documents you'd need.
- **Legalization assistant**: if our CV pipeline detects an undeclared structure on your parcel, the owner is notified *before* enforcement and offered a guided legalization flow — auto-filled forms, list of required attachments, fee estimate, and a clear "this is or isn't legalizable" verdict based on current law.
- **Pre-permit chatbot** grounded in Split's GUP/PPU planning documents so citizens can ask plain-language questions ("can I close my balcony?") and get cited answers.

The shared belief: enforcement alone doesn't fix the problem. Pairing detection with a *good* legalization on-ramp is what actually improves compliance, and it's what makes this ethically defensible — we're not just snitching, we're helping people get right with the city.

## Why this is ethically sound

- **Public-interest data**: cadastre and orthophoto data are public records; we're not surveilling individuals, we're comparing official records to official imagery.
- **Human-in-the-loop**: the system flags, it does not punish. Every flag goes to a city reviewer before any action.
- **Owner-first notification**: where possible, owners are informed and offered legalization *before* an inspector is dispatched.
- **Bias-aware**: we surface confidence scores and known failure modes (shadows, tree canopy, recent legal permits not yet in the dataset) rather than presenting CV output as ground truth.

## Data sources we're targeting

- **Imagery**: Google Earth / Google Earth Engine, Sentinel-2, and the City of Split / DGU orthophoto layers where available.
- **Cadastre & buildings**: [katastar.hr](https://katastar.hr/) (DGU) parcel and building footprint data, ARKOD where relevant.
- **Planning & zoning**: Split GUP/PPU documents and conservation overlays.
- **Permits**: City of Split building-permit registry (scope/availability TBD for the hackathon).

## Hackathon scope

Realistic slice for the timebox:

- One pilot neighborhood in Split (e.g. a coastal section with known issues).
- Building footprint segmentation + diff against katastar footprints on a fixed set of parcels.
- Minimal citizen portal: parcel lookup + zoning summary + "is this legalizable?" stub.
- Demo dashboard: map of flagged parcels with evidence panel.

Stretch:
- Time-series change detection across multiple orthophoto vintages.
- LLM-grounded chatbot over Split's planning documents.
- Auto-drafted legalization paperwork.

## Stack

Agreed during planning — see `CLAUDE.md` for the full rationale and conventions.

| Layer | Choice | Why |
|---|---|---|
| Imagery | Google Earth Engine (`earthengine-api`) | Multi-source, historical, change-detection done server-side |
| CV / footprints | Microsoft Global ML Building Footprints + GeoPandas/Shapely diff | Croatia is already covered — no training needed |
| Backend | Python 3.11+ + FastAPI | Plays well with GEE and the geospatial Python stack |
| Storage | SQLite + SpatiaLite (hackathon); Postgres/PostGIS later | Zero-ops for the demo |
| Frontend | Next.js (App Router) + TypeScript + MapLibre + Tailwind | Two product surfaces (`/city`, `/citizen`) want a real frontend |
| LLM (stretch) | Claude API (Sonnet 4.6 / Haiku 4.5) with prompt caching | "Can I build this?" chatbot + auto-drafted legalization summaries |

## Getting started (team)

```bash
git clone https://github.com/frenki1004/sheep2026.git
cd sheep2026
```

The repo is currently docs-only. Code lands in `backend/` and `frontend/` as we scaffold — see `CLAUDE.md` for the target layout and conventions.

**Before you start coding:**

1. Read `CLAUDE.md` end-to-end. The ethics framing and the "human-in-the-loop / both audiences" rules are product requirements, not style preferences.
2. Pick a slice from "Hackathon scope" above and open a short PR rather than a long-running branch.
3. If you change the stack or the scope, update `CLAUDE.md` and the relevant README section in the same commit.

**Prerequisites you'll need locally (once code lands):**

- Python 3.11+ and [`uv`](https://github.com/astral-sh/uv) (or pip) — backend.
- Node 20+ and `pnpm` — frontend.
- A Google account with access to a Google Earth Engine project. Run `earthengine authenticate` once.
- (Optional, stretch) an Anthropic API key for the chatbot work.

Real `uv run` / `pnpm dev` commands will be filled in once the first scaffold lands.

## Project structure

```
sheep2026/
├── README.md
├── CLAUDE.md
└── .gitignore
```

Heading toward `backend/` + `frontend/` + `docs/` — see `CLAUDE.md` for the planned layout.

## Team

Built during the Sheep AI 2026 Hackathon.

## License

TBD — to be set before submission.
