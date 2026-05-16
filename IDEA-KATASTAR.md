# KatastarEye — Satellite + Cadastre Discrepancy Detection

## The Pitch (30 seconds)

> "Croatia has 300,000+ illegal buildings. The inspectorate has 200 inspectors. We cross-reference the official cadastre with satellite-detected buildings and flag every discrepancy automatically. Point at the map, ask a question in Croatian, get an answer."

---

## Why This Wins

1. **Real problem** — 300K+ illegal buildings, enforcement is manual and failing
2. **Data exists** — katastar is on WFS, Microsoft has building footprints, Sentinel is free
3. **No one is doing this** — Croatia has NO systematic satellite monitoring for construction
4. **Politically hot** — tourism construction pressure, legalization scandals, Split is ground zero
5. **EU alignment** — INSPIRE, Copernicus, ePlanovi digitalization, CASSINI-style project
6. **Technically impressive** — ontology + satellite + NL queries = cutting-edge
7. **Proven winner pattern** — WasteNoTime (CASSINI Croatia 2024) won with satellite + citizen data

---

## What It Does

### Questions It Can Answer:
- "Što je izgrađeno na ovoj parceli bez dozvole?" (What's built here without a permit?)
- "Koje građevine ne odgovaraju katastru?" (Which buildings don't match the cadastre?)
- "Pokaži novu gradnju u zadnjih 6 mjeseci" (Show new construction in last 6 months)
- "Koji objekti su na poljoprivrednom zemljištu?" (Which buildings are on agricultural land?)
- "Koliko se građevni fond promijenio od 2019?" (How has building stock changed since 2019?)

### Three Core Layers:

```
┌────────────────────────────────────────────┐
│  LAYER 1: OFFICIAL (What should exist)     │
│  - Cadastral parcels (DGU WFS)             │
│  - Registered buildings                     │
│  - Zoning (ePlanovi)                       │
│  - Land use categories                      │
├────────────────────────────────────────────┤
│  LAYER 2: REALITY (What actually exists)   │
│  - Microsoft Building Footprints (ML)       │
│  - Sentinel-2 change detection             │
│  - OpenStreetMap buildings                  │
├────────────────────────────────────────────┤
│  LAYER 3: DISCREPANCY (The delta)          │
│  - Unregistered buildings                   │
│  - Size mismatches                          │
│  - Zone violations                          │
│  - New construction (temporal)              │
└────────────────────────────────────────────┘
```

---

## Data Sources (All Free & Accessible)

| Source | What | Access | Format |
|--------|------|--------|--------|
| **DGU Geoportal** | Cadastral parcels (DKP) | WMS/WFS | GML vectors |
| **DGU** | Digital Orthophoto (DOF) | WMS | Raster tiles |
| **Microsoft Building Footprints** | ML-detected buildings globally | GitHub download | GeoJSON |
| **Sentinel-2** | 10m optical imagery (every 5 days) | Copernicus Data Space / GEE | GeoTIFF |
| **Sentinel-1** | SAR for change detection | GEE | GeoTIFF |
| **ePlanovi/ISPU** | Zoning data (what's allowed where) | https://ispu.mgipu.hr/ | WMS |
| **ARKOD** | Agricultural land parcels | https://arkod.gis.hr/ | WMS/WFS |
| **Urban Atlas** | 2.5m land use for Split metro | Copernicus Land Monitoring | Vector |
| **OpenStreetMap** | Community-mapped buildings | Overpass API / Geofabrik | GeoJSON |

### Key URLs:
- DGU Geoportal: https://geoportal.dgu.hr/
- Katastar viewer: https://oss.uredjenazemlja.hr/public/cadServices.jsp
- Microsoft Buildings: https://github.com/microsoft/GlobalMLBuildingFootprints
- Copernicus Data Space: https://dataspace.copernicus.eu/
- Google Earth Engine: https://earthengine.google.com/
- ISPU (spatial plans): https://ispu.mgipu.hr/
- ARKOD: https://arkod.gis.hr/

---

## Ontology / Knowledge Graph

```
Parcel (katastarska čestica)
├── parcel_id (kat. općina + broj čestice)
├── geometry (polygon)
├── area_m2
├── land_use_category (oranica, šuma, izgrađeno, etc.)
├── registered_buildings[] → Building
├── zoning → ZoningZone
└── ownership_status

Building (zgrada)
├── geometry (footprint polygon)
├── source (katastar | satellite | osm)
├── area_m2, height, floors
├── legal_status (legal | illegal | legalized | unknown)
├── permits[] → Permit
└── parcel → Parcel

Permit (građevinska dozvola)
├── permit_id, issue_date
├── permitted_footprint, permitted_height
├── usage_permit_issued (bool)
└── parcel → Parcel

SatelliteObservation
├── datetime, source, resolution
├── detected_structures[] (polygons)
├── change_type (new | expanded | demolished)
└── confidence_score

Discrepancy (nesklad)
├── type: UNREGISTERED | SIZE_MISMATCH | ZONE_VIOLATION | NO_PERMIT | LAND_USE_VIOLATION
├── detected_building → SatelliteObservation
├── parcel → Parcel
├── severity_score (1-5)
└── evidence (satellite image, measurements)

ZoningZone (from ePlanovi)
├── allowed_use (stambena, gospodarska, poljoprivredna, zaštićena...)
├── max_height, max_coverage_ratio
└── geometry
```

### Discrepancy Detection Rules:

| Rule | Logic | Severity |
|------|-------|----------|
| **Unregistered building** | Satellite detects building + No registered building on parcel | HIGH |
| **Size mismatch** | Detected footprint > 120% of registered footprint | MEDIUM |
| **Zone violation** | Building on agricultural/protected/forest zone | CRITICAL |
| **New construction** | Change detection shows new structure + no recent permit | HIGH |
| **Land use change** | Parcel marked "oranica" but satellite shows impervious surface | MEDIUM |

---

## Tech Stack (48h Feasible)

### Option A: Full-Stack MVP (Recommended)

```
Frontend:      Next.js + MapLibre GL / Deck.gl (split-screen map)
Backend:       Python FastAPI
Data:          PostGIS (spatial queries) + Neo4j or just PostGIS with JSONB
AI/NL:         Claude API (natural language → spatial query translation)
Satellite:     Google Earth Engine (Python API) for change detection
Processing:    GeoPandas + Shapely for spatial operations
```

### Option B: Lighter (if time-constrained)

```
Frontend:      Streamlit + Folium/Leaflet
Backend:       Python (no separate backend)
Data:          GeoDataFrames in memory (GeoPandas)
AI/NL:         Claude API
Satellite:     Pre-downloaded Microsoft footprints + Sentinel composites
```

### Key Libraries:
- `geopandas` — spatial dataframes
- `shapely` — geometric operations
- `rasterio` — satellite imagery
- `sentinelsat` or `planetary_computer` — Sentinel data access
- `osmnx` — OpenStreetMap data
- `anthropic` — Claude API for NL interface
- `maplibre-gl` or `deck.gl` — web map visualization

---

## 48-Hour Implementation Plan

### Hours 0-6: Data Pipeline
- [ ] Download Microsoft Building Footprints for Split area
- [ ] Fetch cadastral parcels from DGU WFS for Split
- [ ] Download ePlanovi/ISPU zoning for Split
- [ ] Get recent Sentinel-2 composite for Split (GEE or Copernicus)
- [ ] Harmonize CRS (everything to EPSG:4326 or EPSG:3765)

### Hours 6-12: Discrepancy Engine
- [ ] Spatial join: Microsoft buildings ↔ cadastral parcels
- [ ] For each detected building: check if parcel has registered building
- [ ] Size comparison: detected vs. registered footprint area
- [ ] Zone check: is building in non-buildable zone?
- [ ] Generate discrepancy table with severity scores

### Hours 12-18: Change Detection
- [ ] Sentinel-2 NDBI (Normalized Difference Built-up Index) 2019 vs 2025
- [ ] Identify areas where vegetation → built-up
- [ ] Cross-reference new built-up areas with permits database
- [ ] Flag temporal discrepancies

### Hours 18-30: NL Interface + Ontology
- [ ] Define ontology schema in PostGIS / JSON
- [ ] Build Claude-powered query interface
- [ ] System prompt: translate Croatian NL questions → spatial SQL / filter logic
- [ ] Return results with map highlights + statistics

### Hours 30-42: Frontend + Visualization
- [ ] Split-screen map: Official (katastar) vs Reality (satellite)
- [ ] Red/yellow/green flagging of parcels
- [ ] Click parcel → see discrepancy details + satellite image
- [ ] Chat interface for NL queries
- [ ] Summary statistics dashboard (total discrepancies by type, by area)

### Hours 42-48: Polish + Demo Prep
- [ ] Demo script with compelling examples
- [ ] Key stats ("We found X unregistered buildings in Y area")
- [ ] Screen recording backup
- [ ] Pitch deck (5 slides max)

---

## Demo Script (What to Show Judges)

1. **Open map of Split** — show cadastral overlay vs. satellite
2. **Zoom to area with obvious discrepancies** — red highlighted parcels
3. **Click one** — "This parcel is registered as agricultural land (oranica). Satellite shows a 200m² building. No permit found. Confidence: 94%"
4. **Ask in Croatian:** "Koliko nelegalno izgrađenih objekata ima u Mravincima?" → system returns count + highlights on map
5. **Show change detection:** "Here's Split coast in 2019 vs 2025. These 47 structures appeared without any corresponding permits."
6. **The big number:** "In this 5km² area alone, we detected X potential discrepancies. Croatia's inspectorate would need Y years to check these manually."

---

## Killer Phrases for Judges

- "Croatia spent 10 years processing 800,000 legalization applications. We flag discrepancies in seconds."
- "The inspectorate has 200 people for all of Croatia. This system never sleeps."
- "Sentinel gives us new imagery every 5 days. Every building that goes up, we see it."
- "The data is free. Copernicus is free. The cadastre is open. We just connected the dots."
- "This isn't theoretical — we're running it on real Split data right now."
- "WasteNoTime won CASSINI 2024 with satellite + citizen data. We take it further with cadastral ontology + NL queries."

---

## Potential Expansions (Mention But Don't Build)

- **3D analysis** — use building heights (from LiDAR/stereo) to detect height violations
- **Temporal monitoring** — automated alerts when new construction detected in non-permitted zones
- **Tax implications** — unregistered buildings = untaxed property (massive revenue potential)
- **Insurance risk** — illegal buildings may not meet safety codes (earthquake, fire)
- **Climate risk** — buildings in flood zones or coastal erosion areas without permits
- **Citizen reporting** — add a "report" button like WasteNoTime did
- **Integration with eDozvola** — check permit database directly via API

---

## Legal & Ethical Notes

- All data sources are open/public (no GDPR issue — parcels, not persons)
- Don't show ownership names in the demo (even if accessible)
- Frame it as a **tool for the inspectorate**, not a vigilante system
- Mention: "This supports the rule of law and spatial planning integrity"
- Position as enabling Croatia's EU obligations (INSPIRE compliance)

---

## Similar Winners That Validate This Approach

| Project | Event | Similarity |
|---------|-------|-----------|
| **WasteNoTime** | CASSINI Croatia 2024 | Satellite + citizen input for environmental violations |
| **Galacticum** | CASSINI Lithuania 2022 | Satellite detection of roof types (asbestos) per building |
| **TerraMetallum** | CASSINI Czech 2024 | Satellite spectral analysis for soil/land analysis |
| **ECOTEN** | Climathon Vienna 2018 | Satellite-derived urban vulnerability mapping |
| **withthegrid** | Amsterdam Smart City | AI image recognition for infrastructure monitoring |
| **Gentrification Index** | Barcelona 2019 | Open data quantifying urban transformation |
