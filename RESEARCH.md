# "Make Split Better" — Hackathon Research

## Table of Contents
1. [Split's Biggest Problems](#1-splits-biggest-problems)
2. [What Similar Cities Have Done](#2-what-similar-cities-have-done)
3. [EU & Croatian Laws You Can Leverage](#3-eu--croatian-laws-you-can-leverage)
4. [Funding & Alignment Opportunities](#4-funding--alignment-opportunities)
5. [Technologies & Tools](#5-technologies--tools)
6. [Winning Hackathon Projects (Patterns)](#6-winning-hackathon-projects)
7. [Top Project Ideas (Ranked by Feasibility + Impact)](#7-top-project-ideas)
8. [Pitch Strategy](#8-pitch-strategy)

---

## 1. Split's Biggest Problems

### Traffic & Parking
- Medieval streets + modern traffic = severe congestion (triples in summer)
- Smart Parking App exists but demand far exceeds supply
- City deploying video surveillance for illegal parking since Feb 2026

### Overtourism (THE BIG ONE)
- **20.9 million overnight stays** in Split-Dalmatia County vs. **~160,000 residents**
- Diocletian's Palace receives **thousands over its daily recommended limit**
- NO entry limits, NO capacity management (unlike Dubrovnik which caps at 8,000)
- ~3,000 people still live inside the Palace complex
- Split is **2nd in Europe** for short-term rentals per capita

### Housing Crisis
- Property prices: EUR 4,500-5,500/m²
- Massive "apartmentization" — residential → tourist rentals
- Young Croatians leave home at 31.3 years (highest in EU)
- Croatia lost ~20% of population in 3 decades

### Noise & Anti-Social Behavior
- Historic center = "pub crawl" zone
- 2025 ordinance: alcohol sales banned 8PM-6AM, fines +25%
- Swimwear banned outside beaches since May 2025

### Waste
- **606 kg/person/year** (vs national avg 486 kg) due to tourism
- Streets too narrow for recycling bins
- Croatia at risk of **missing 2025 EU 55% recycling target**

### Water Infrastructure
- **42% of drinking water LOST** in the supply system
- Some untreated sewage discharged directly into the sea
- Adriatic: 25% increase in microplastics since 2019

### Heat & Environment
- Croatia warming **20% faster** than global average
- Urban heat islands in dense zones (Split 3 especially)
- Marjan Forest = only green lung (western city); east has nothing
- "Very high" wildfire risk (2017 Split wildfire precedent)

### Public Transport
- Promet Split: delays up to 40 min, overcrowding, no reliable real-time tracking
- **No tram/light rail** (only Zagreb and Osijek have trams)
- NextBike: 41 stations, 242 bikes — usage jumped 200%
- Split = **largest passenger port on the Adriatic** (ferries + cruise ships)

### What Split Has NOT Done (That Dubrovnik Has)
- ❌ No real-time crowd monitoring
- ❌ No visitor capacity management
- ❌ No AI-powered visitor forecasting
- ❌ No digital signage for tourist redistribution
- ❌ No noise monitoring sensors
- ❌ No comprehensive city data dashboard
- ❌ No dedicated open data portal

---

## 2. What Similar Cities Have Done

### Dubrovnik (Croatia) — 2026 European Green Pioneer of Smart Tourism
- "Respect the City" programme (since 2017)
- Real-time crowd monitoring with sensors at Old Town gates
- AI-powered visitor forecasting
- 8,000-person cap with live counting
- Noise meters with automated fines
- **Result: historic core vulnerability index halved (2017-2022)**

### Barcelona — Superblocks
- Groups ~9 blocks, reroutes traffic to perimeter, pedestrianizes interior
- Traffic -40%, noise -30%, air pollutants -18%, temp -0.4°C
- **250+ cities worldwide** have adopted the model

### Athens — Anti-Tourism Overload
- Acropolis: 20,000/day cap with timed entry slots
- 1-year freeze on new short-term rental registrations
- EUR 20,000 fines for violations
- Tourist tax: EUR 1.50 → EUR 8/day (peak season)

---

## 3. EU & Croatian Laws You Can Leverage

### Key EU Regulations (Opportunities)

| Regulation | What It Means for Your Project |
|---|---|
| **EU Reg 2024/1028** (Short-Term Rentals) | Effective **May 2026** — platforms must share rental data with cities. Build tools to USE this data! |
| **Open Data Directive 2019/1024** | Government data must be open by default. High-value datasets (geo, mobility, stats) must be free + machine-readable via APIs |
| **Data Act 2023/2854** (effective Sep 2025) | IoT data must be shareable. Cities gain rights to access sensor/device data. Enables smart city projects |
| **GDPR** | Use open/aggregated data freely. Individual tracking needs legal basis + DPIA. Privacy by design required |
| **Nature Restoration Reg 2024/1991** | Binding obligations on urban green space — justify green intervention projects |
| **EU Urban Mobility Framework** | Cities >100K need SUMPs. Split (170K, swells to 400K+) is in scope |

### Key Croatian Laws

| Law | Relevance |
|---|---|
| **2025 Hospitality Act** | 80% co-owner consent needed for STR in apartments. Existing operators get 5-year grace period |
| **2025 Property Tax Reform** | STRs taxed at 10% (vs 8% long-term). Economic incentive to convert tourist → residential |
| **2025 Spatial Planning Act** | Introduces **ePlanovi** — all spatial plans digital, publicly accessible. Open data opportunity! |
| **Access to Information Act** | Public authorities must publish in machine-readable form. Portal: data.gov.hr |
| **Tourist Tax** | Split = Category B. EUR 13M went unpaid in 2025. Revenue earmarked for local infrastructure |

### GDPR Practical Rules
- ✅ **Can use freely**: data.gov.hr, EU open data, aggregated stats, environmental sensors, OpenStreetMap
- ⚠️ **Use with care**: anonymized mobility data, tourist flow statistics
- ❌ **Cannot use**: individual location tracking, personal tourist data, camera feeds without DPIA

---

## 4. Funding & Alignment Opportunities

If you want to pitch "this could get EU funding" to judges:

| Programme | Budget | Deadline | Fit |
|---|---|---|---|
| **EUI 4th Call** (European Urban Initiative) | EUR 60M | June 2026 | Innovative urban actions |
| **Horizon Europe Cities Mission** | EUR 85.5M | Oct 2026 | Climate-neutral city solutions |
| **Digital Europe 2026** | Part of EUR 7.5B | Oct 2026 | AI, data spaces, digital public services |
| **New European Bauhaus** | ~EUR 120M/yr | Rolling | Heritage + sustainability + inclusivity |
| **Interreg Euro-MED** | Varies | Rolling | Mediterranean green transition |
| **Croatian NPOO** (RRF) | EUR 1.55B digital | 2026 | Digitalization of public services |

**Key narrative**: Split is NOT in the EU Mission Cities (103 cities are). A hackathon project could be the foundation for Split's application.

---

## 5. Technologies & Tools

### Immediately Usable APIs & Data

| Resource | What | Cost |
|---|---|---|
| **OpenStreetMap + Overpass API** | Buildings, roads, POIs for Split | Free |
| **PVGIS** (EU) | Solar radiation for any location | Free API |
| **Copernicus/Sentinel** | Satellite imagery (heat, vegetation) | Free |
| **OpenWeatherMap** | Weather data | 1000 calls/day free |
| **OpenRouteService** | Routing, isochrones | Free & open source |
| **data.gov.hr** | 3,000+ Croatian datasets | Free |
| **Open Charge Map** | EV charger locations | Free |
| **MarineTraffic** | Ship/ferry AIS tracking | Limited free |
| **Google Maps Platform** | Everything maps | $200/mo free credit |
| **Mapbox** | Custom maps, navigation | 50K loads/mo free |

### Best Tech for a 24-48h Hackathon

**Frontend**: React/Next.js + Leaflet.js or deck.gl for maps
**Backend**: FastAPI (Python) or Express (Node)
**AI/ML**: Prophet (time series), YOLOv8 (computer vision), scikit-learn
**IoT demo**: ESP32 + sensors (HC-SR04 ultrasonic, MQ-135 air)
**3D/AR**: CesiumJS (3D city), AR.js (web AR, no app install needed)
**Data viz**: Grafana, D3.js, deck.gl
**Routing/Optimization**: Google OR-Tools, OpenTripPlanner

### Key Open Source Projects

| Tool | Use Case |
|---|---|
| **OpenTripPlanner** | Multimodal transit routing engine |
| **SUMO** | Traffic simulation |
| **pvlib-python** | Solar energy modeling |
| **FixMyStreet** | Citizen issue reporting (fork-ready) |
| **Decidim** | Participatory budgeting platform |
| **AR.js + A-Frame** | Web-based AR (no app needed) |
| **sensor.community** | Citizen science air quality |
| **CesiumJS** | 3D geospatial visualization |
| **OR-Tools** | Route optimization |

---

## 6. Winning Hackathon Projects

### European Winners with Similar Themes

| Hackathon | Winner | What It Does | Why It Won |
|---|---|---|---|
| **Brussels Smart City 2023** | bAIcycle | Citizens classify cycle path conditions via smartphone → trains AI | Citizen science + ML + immediately useful |
| **Brussels Smart City 2024** | BrusAir | Predictive air quality model (wind + AI) | Novel data combination, clear health impact |
| **EIT ChallengeMyCity 2022** | CrowdFree | Avoid crowds in public transport, suggest alternatives + incentives | Gamification + real mobility data |
| **EU Sparks for Climate 2024** | The Nettuniani | Urban flooding prediction with AI + IoT | Real problem, working sensors, clear ROI |
| **CASSINI 2024 (Croatia!)** | WasteNoTime | Satellite imagery + citizen reports → detect illegal landfills | Space data + crowdsourcing |
| **HackZurich 2022** | GridGuard | Orchestrate smart devices to prevent grid blackouts | Timely (energy crisis), immediately deployable |
| **Junction 2023** | ReMaskit | Instagram filter identifies materials + how to recycle | Gamified sustainability on existing platform |
| **NEB Hackathon 2022** | URBAN TREE | Sustainable drainage + plants growing from stored rainwater | Beautiful + functional + sustainable |
| **Climathon Bratislava 2022** | Team Acropolis | Optimize city response to extreme weather | Practical, data-driven, scalable |
| **Split Smart City 2022** | SmartNest | Smart housing solution | Local context, working prototype |

### Previous Split Hackathons
- **Hack4Split 2022**: 52 participants, 10 teams. Winner: Pitaj studenta (student info forum)
- **Smart City Challenge 2022**: SmartNest, Green Team 2, FlexGRID. Notable: Evala (tourist storytelling guide)
- **INNOVATE NOW CROATIA 2023**: Blue Growth focus in Split

### Patterns — What Wins

**Solution types that win most often:**
1. 🏆 AI/ML-powered analytics (predictive models, classification)
2. 🏆 Citizen engagement/crowdsourcing (phones as sensors)
3. 🏆 Real-time monitoring + visualization
4. 🏆 Gamification of sustainability
5. 🏆 Novel data combination (satellite + citizen + open data)
6. 🏆 Mobility/transport optimization

**What judges reward:**
- **Specific user, specific problem** — not vague "smart city" but "cyclists in Brussels don't know which paths are broken"
- **Working demo > slides** — ALWAYS
- **Clear impact narrative** — "saves X lives / reduces Y tons / saves Z hours"
- **Feasibility** — can this actually be deployed? Is the data real?
- **Novel combination** — existing tech combined in a new way
- **Scalability** — works for Split but could work for any coastal city

---

## 7. Top Project Ideas (Ranked)

### Tier 1: High Impact + High Feasibility (24-48h buildable)

#### 1. 🏛️ Split Crowd Pulse — Palace Capacity Management
**Problem**: Diocletian's Palace has no visitor management (Dubrovnik proved this works)
**Solution**: Estimate crowd density at key locations, show live green/yellow/red zones on a map, predict surges, suggest alternative times/routes
**Tech**: Python + Prophet (time series prediction) + Leaflet.js map + FastAPI
**Data**: Simulate with historical tourist data + event calendars + cruise ship schedules
**Why it wins**: Dubrovnik's system is proven, Split desperately needs it, aligns with EU tourism regulation, judges love "city X did it, we bring it to city Y"
**EU alignment**: EU Tourism Transition Pathway, Smart Tourism Capital criteria

#### 2. 🚌 Split MaaS — Unified Mobility App
**Problem**: Buses (Promet), ferries (Jadrolinija), bikes (NextBike), walking — all separate, no integration
**Solution**: Multimodal journey planner showing best combo of transport modes with real-time info
**Tech**: OpenTripPlanner + GTFS data + React frontend + ferry schedule integration
**Data**: Promet timetables, Jadrolinija schedules, NextBike stations, OSM
**Why it wins**: Practical, immediately useful for residents AND tourists, aligns with EU Urban Mobility Framework

#### 3. 🏠 ApartmentWatch — Housing Market Transparency
**Problem**: 2nd in Europe for STR per capita, no transparency on impact
**Solution**: Dashboard showing STR density per neighborhood, price trends, residential displacement index, impact on housing availability. Leverages new EU Reg 2024/1028 (effective May 2026!)
**Tech**: Web scraping (Airbnb/Booking listings) + GIS visualization + deck.gl 3D map
**Data**: Listing data, property registry (open), Croatian census, data.gov.hr
**Why it wins**: Politically hot topic, aligns with brand new EU regulation, data-driven policy tool

#### 4. 🌡️ Split Heat Map — Urban Heat Island Intervention Planner
**Problem**: City warming 20% faster than global avg, heat islands in eastern districts, no equivalent to Marjan Forest
**Solution**: Map surface temperatures using satellite data, identify hotspots, recommend green interventions (trees, green roofs) with cooling impact predictions
**Tech**: Python + Sentinel-2 satellite data + NDVI analysis + Leaflet choropleth + cost-benefit model
**Data**: Copernicus (free), OSM buildings, PVGIS solar data
**Why it wins**: Climate urgency, beautiful visualization, actionable recommendations, EU Nature Restoration Reg alignment

### Tier 2: High Impact + Medium Feasibility

#### 5. 🏛️ Diocletian AR — See the Palace in 305 AD
**Problem**: Tourists see ruins without understanding original splendor
**Solution**: Web-based AR experience showing the Palace reconstructed in Roman times. Point phone at ruins → see columns, statues, original colors
**Tech**: AR.js + A-Frame (no app install!) + Blender 3D models + GPS triggers
**Why it wins**: WOW factor for demo, heritage preservation angle, aligns with New European Bauhaus, tourism tech

#### 6. 🗑️ Smart Waste Split — Tourist Season Optimization
**Problem**: 606 kg/person/year waste, narrow streets, overflowing bins in summer
**Solution**: Simulated IoT bin monitoring + optimized collection routes for narrow streets
**Tech**: ESP32 + ultrasonic sensor demo + Google OR-Tools optimization + OpenRouteService
**Why it wins**: IoT + optimization is proven winner pattern, measurable impact (60% fewer unnecessary pickups), hardware demo impresses judges

#### 7. 🚢 Port Flow — Cruise Impact Predictor
**Problem**: Cruise ships dump thousands of tourists simultaneously, overwhelming the city
**Solution**: Predict impact of incoming cruise ships (which areas will be overwhelmed, when), alert residents, suggest tourist redistribution
**Tech**: Cruise schedule data + MarineTraffic API + walking-time analysis + notification system
**Data**: Cruise calendars (public), AIS ship data, historical crowd patterns
**Why it wins**: Unique angle, combines maritime + urban data, directly addresses overtourism

### Tier 3: Cool but Harder

#### 8. ☀️ Solar Split — Every Rooftop's Potential
Map solar potential of every building using OSM + PVGIS. Tech: pvlib + deck.gl 3D.

#### 9. 🔊 Noise Network — Old Town Sound Monitoring
Low-cost sensor concept for night noise enforcement. Tech: ESP32 + microphone + time-series DB.

#### 10. 💧 Leak Detective — Water Loss AI
Tackle the 42% water loss rate with anomaly detection. Tech: simulated network data + scikit-learn.

---

## 8. Pitch Strategy

### Structure (3-5 min pitch)
1. **Problem** (30 sec) — one statistic that shocks ("Split has NO crowd management while getting 20.9M overnight stays")
2. **Solution** (60 sec) — show don't tell, live demo
3. **How it works** (60 sec) — quick tech explanation, data sources
4. **Impact** (30 sec) — "If deployed, this would reduce X by Y%"
5. **Feasibility** (30 sec) — "Data is available today, EU regulation enables this, Dubrovnik proved the concept"
6. **Ask** (15 sec) — what's next (pilot with city, EU funding application, etc.)

### Tips from Winners
- **Start pitch prep on Day 1** — allocate 20% of time to presentation from the start
- **"One User, One Problem"** — don't build a platform that does everything
- **Record a backup demo** — screen-capture your working prototype
- **Build MVP with 2-3 features** — polished demo of 1 feature beats buggy attempt at 10
- **Ship in 12 hours, polish for 36** — teams that finish early and iterate win
- **Storytelling sells** — "Maria lives in the Palace. Every morning at 7am, 3 cruise ships arrive..."
- **Align explicitly with judging criteria** — read the rubric, build to match it

### Killer Phrases for Judges
- "Dubrovnik halved their vulnerability index with this approach — Split has nothing"
- "EU Regulation 2024/1028 becomes effective this month — we're the tool that uses that data"
- "This works for Split but scales to any Mediterranean coastal city"
- "The data is free, the tech is open source, deployment cost is near zero"

---

## Sources & Links

### Croatian Data
- [data.gov.hr](https://data.gov.hr/) — National open data
- [NIPP Geoportal](https://geoportal.nipp.hr/) — Spatial/GIS data
- [Code for Croatia](https://data.codeforcroatia.org/) — Civic open data
- [Promet Split](https://www.promet-split.hr/) — Bus schedules
- [DHMZ](https://meteo.hr/) — Weather data

### EU Resources
- [data.europa.eu](https://data.europa.eu/) — EU open data portal
- [NetZeroCities](https://netzerocities.eu/) — Cities Mission platform
- [PVGIS](https://re.jrc.ec.europa.eu/pvg_tools/) — Solar radiation
- [Copernicus](https://scihub.copernicus.eu/) — Satellite imagery
- [Smart Tourism Capital](https://smart-tourism-capital.ec.europa.eu/) — EU smart tourism best practices

### Tech Tools
- [OpenTripPlanner](https://www.opentripplanner.org/) — Transit routing
- [OR-Tools](https://developers.google.com/optimization) — Optimization
- [AR.js](https://ar-js-org.github.io/AR.js-Docs/) — Web AR
- [CesiumJS](https://cesium.com/cesiumjs/) — 3D geo
- [sensor.community](https://sensor.community/) — DIY air quality
- [pvlib](https://pvlib-python.readthedocs.io/) — Solar modeling
- [OSM Croatia](https://download.geofabrik.de/europe/croatia.html) — Map data
