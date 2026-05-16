# "Make Split Better" — Technology-First Ideation

> Approach: Start with exciting tech, then find the city problem it solves.

---

## TOP 5 PICKS (Summary)

| # | Project | Tech | Wow | Feasibility | Utility |
|---|---------|------|-----|-------------|---------|
| 1 | **SplitMediator** — AI agents debate city policy | Multi-Agent LLMs | 5/5 | 4/5 | 5/5 |
| 2 | **PalaceReborn** — Gaussian Splatting time travel | 3DGS + WebGL | 5/5 | 3/5 | 4/5 |
| 3 | **SplitStory** — AI crowd-aware personalized routes | LLM + RAG | 4/5 | 5/5 | 5/5 |
| 4 | **MarjanWatch** — AI fire detection for the forest | Computer Vision | 4/5 | 4/5 | 5/5 |
| 5 | **HeatGuard** — Shade-aware routing | Wearables + Geo | 4/5 | 4/5 | 5/5 |

---

## 1. Large Language Models / Generative AI

### Ideas
- **"SplitGPT"** — Natural language interface to city open data ("How much did we spend on road repairs in Bacvice?")
- **"BureaucracyBreaker"** — AI agent navigating Croatian municipal bureaucracy (permits, residency, registration)
- **"SplitStory"** — AI-generated personalized heritage walks that dynamically avoid crowds

### Best: "SplitStory" — AI Crowd-Aware Personalized Heritage Routes

**Concept:** Tourist describes interests in natural language. LLM (via RAG over Split heritage knowledge base) generates a UNIQUE walking tour. Key innovation: integrates real-time crowd density to route people AWAY from overcrowded areas, actively distributing tourist flow.

**Input:** "I love Roman history and hidden gardens, I have 2 hours, I hate crowds"
**Output:** A unique narrative route through less-visited Palace areas with AI storytelling at each stop

**Tech Stack:**
- Next.js/React frontend
- Claude/OpenAI API + RAG (ChromaDB/Pinecone)
- Google Popular Times or BestTime API for crowd estimates
- Mapbox/Leaflet for map display

**What makes it novel:** Most tour apps give everyone the SAME routes. This creates unique routes AND actively reduces overtourism. It's a crowd management tool disguised as a tourist app.

**Wow: 4/5 | Feasibility: 5/5**

---

## 2. Computer Vision (Real-Time)

### Ideas
- **"PalaceGuard"** — Phone-based structural damage detection for the Palace walls (cracks, water damage, graffiti)
- **"SplitAccess"** — Video-based wheelchair accessibility mapping (detect stairs, narrow passages, curbs)
- **"MarjanWatch"** — Fire/smoke detection for Marjan Forest

### Best: "MarjanWatch" — AI Early Fire Detection for Marjan Forest

**Concept:** Cameras at vantage points around Marjan run fine-tuned YOLOv8 to detect smoke/flame in real-time. Instant alerts with GPS-estimated location to fire services. Marjan burns nearly every summer — this is a REAL, emotionally resonant problem.

**Tech Stack:**
- YOLOv8 (Ultralytics)
- Pre-trained fire/smoke models (D-Fire, FiSmo datasets — open source)
- NVIDIA Jetson Nano or RPi 5 for edge inference
- Twilio/SMS for alerts
- Simple web dashboard with camera feeds

**What makes it novel:** Every Split resident has watched Marjan burn. The emotional "why don't we have this already?" factor is enormous.

**Demo:** Show recorded video of smoke rising, model detects in <3 seconds, triggers alert.

**Wow: 4/5 | Feasibility: 4/5**

---

## 3. Voice / Audio AI

### Ideas
- **"NoiseSplit"** — Real-time sound classification + noise map (distinguish nightlife vs. construction vs. traffic)
- **"SplitVoice"** — NFC-triggered AI audio guides in 20+ languages via voice synthesis
- **"SirenSense"** — Emergency vehicle detection for narrow streets → visual warnings for pedestrians

### Best: "NoiseSplit" — AI-Powered Noise Classification Map

**Concept:** Network of sound sensors (or phone app) that classifies urban sounds in real-time using a CNN. Distinguishes: nightlife music, construction, traffic, boat horns, quiet. Visualizes on live map. City uses it to enforce noise ordinances objectively.

**Key innovation:** Goes beyond simple dB measurement to CLASSIFY sources — "this is construction" vs. "this is illegal nightlife noise at 3 AM."

**Tech Stack:**
- RPi Zero + USB microphone (or smartphone app)
- TensorFlow Lite model trained on UrbanSound8K + Split recordings
- MFCCs for feature extraction
- InfluxDB + Grafana + Leaflet.js map

**Wow: 3/5 | Feasibility: 4/5**

---

## 4. Spatial Computing / AR / 3D Reconstruction

### Ideas
- **"PalaceReborn"** — Gaussian Splatting 3D reconstruction with "time slider" (present ↔ 305 AD)
- **"SplitShadow"** — AR overlay showing how proposed buildings would cast shadows
- **"NavPalace"** — AR wayfinding in underground Palace passages (no GPS underground)

### Best: "PalaceReborn" — Gaussian Splatting Heritage Time Travel

**Concept:** Use 3D Gaussian Splatting (THE hot tech of 2024-2025) to create a photorealistic, real-time explorable 3D model of Diocletian's Palace from phone video. Then create a "historical twin" showing the palace in 305 AD. Users "slide" between present and past in a web browser.

**Tech Stack:**
- Nerfstudio or gsplat for 3DGS training
- 100-200 photos or 5-10 min video of one courtyard (Peristyle)
- Three.js or custom WebGL viewer
- Blender for historical overlays
- WebXR for optional AR mode

**What makes it novel:** 3DGS for heritage is cutting edge — papers published in Nature, SIGGRAPH 2024, Frontiers in 2025. Combining with historical "time slider" and LLM narration would be a world-first prototype.

**Scope for demo:** Just the Peristyle courtyard. Train splat from phone video (1-2 hrs on GPU).

**Wow: 5/5 | Feasibility: 3/5**

---

## 5. Edge AI / TinyML

### Ideas
- **"BinBrain"** — Smart bins with fill-level + waste-type classification
- **"VibeCheck"** — Structural health monitoring for 1700-year-old Palace walls (vibration anomaly detection)
- **"AirSplit"** — Cruise ship pollution detection along the Riva waterfront

### Best: "AirSplit" — Cruise Ship Pollution Alert System

**Concept:** ESP32-based air quality monitors along Split's waterfront detect pollution spikes correlated with cruise ship arrivals. When a ship docks and PM2.5/NO2 spikes, citizens get alerts and the city gets hard data to negotiate emission controls. Politically powerful — gives residents objective evidence about cruise ship pollution.

**Tech Stack:**
- ESP32-S3 + BME680 (gas) + PMS5003 (particulate)
- Edge Impulse for anomaly detection
- MQTT → InfluxDB → Grafana dashboard
- AIS ship tracking correlation (MarineTraffic API)

**Key innovation:** Not just "air quality monitor" but "WHO is polluting and WHEN" — causal attribution via ship-tracking correlation.

**Wow: 4/5 | Feasibility: 3/5**

---

## 6. Blockchain / Web3

### Ideas
- **"SplitVote"** — DAO participatory budgeting for neighborhood projects
- **"GreenCoin"** — Token incentives for sustainable tourist behavior
- **"HeritageLedger"** — Immutable conservation records for UNESCO reporting

### Best: "GreenCoin" — Blockchain Rewards for Sustainable Tourism

**Concept:** Tourists earn tokens for verified sustainable actions: visiting off-peak (NFC tap verification), using electric buses (transit API), recycling (QR scan). Tokens redeemable at partner shops. Blockchain ensures transparency.

**Tech Stack:**
- Polygon/Base L2 (low gas fees)
- Solidity smart contracts
- React Native app
- NFC/QR verification layer

**What makes it novel:** Gamified overtourism management with real economic incentives. Unlike loyalty programs, blockchain ensures transparency and composability.

**Wow: 3/5 | Feasibility: 3/5**

---

## 7. Digital Twins / Simulation

### Ideas
- **"SplitFlow"** — Agent-based tourist crowd simulation for the Palace
- **"ShadowSplit"** — Solar shadow analysis for proposed buildings
- **"FloodRiva"** — Sea level rise / storm surge simulation for the waterfront

### Best: "SplitFlow" — Real-Time Tourist Crowd Simulation

**Concept:** Agent-based simulation of tourist movement through the Palace. Agents have profiles (cruise day-trippers vs. hotel guests vs. backpackers). Input: "3000-passenger ship arrives at 9 AM" → Output: predicted congestion peaks at 11 AM. City pre-positions staff, opens alternate routes.

**Tech Stack:**
- Mesa (Python ABM framework)
- OSM street network data
- CesiumJS or Deck.gl for visualization
- Streamlit dashboard

**What makes it novel:** Agent-based tourism simulation for a medieval old town with narrow streets is unique. The "what-if" scenario planning is something Split's tourism board would actually want.

**Wow: 4/5 | Feasibility: 3/5**

---

## 8. Agentic AI / Multi-Agent Systems

### Ideas
- **"SplitMediator"** — Multi-agent stakeholder debate simulator
- **"PermitBot"** — Chain of AI agents processing building permits
- **"EventOrchestrator"** — Multi-agent coordination for city events (Ultra Festival, etc.)

### Best: "SplitMediator" — AI Stakeholder Negotiation Simulator ⭐ TOP PICK

**Concept:** Multi-agent LLM system where each agent represents a stakeholder group (Old Town Residents, Tourism Board, Heritage Conservators, Restaurant Owners, Port Authority). Input a policy proposal → agents debate → Mediator Agent synthesizes compromise. Decision-support tool for city council.

**Demo example:** Input "Should Split limit cruise ships to 2 per day?" → Watch agents debate live → See trade-offs revealed → Mediator proposes: "Cap at 3, but stagger arrivals by 2 hours, revenue-neutral via increased per-ship fee"

**Tech Stack:**
- Claude/GPT-4 API (one call per agent)
- Custom system prompts encoding stakeholder priorities
- RAG over Split city data for factual grounding
- Streamlit frontend showing debate in real-time
- Structured output for compromise proposals

**What makes it novel:** Multi-agent debate for urban policy published in academic papers only in 2025 (MDPI "LLM Agents for Smart City Management"). Visually compelling, intellectually impressive. Judges can input their OWN policy questions live.

**Why it's the #1 pick:**
1. Most demo-friendly (live AI debate is theater)
2. NO hardware or complex data pipelines needed
3. Directly addresses hackathon theme
4. Cutting-edge AI research made tangible
5. Extensible during demo — judges ask their own questions

**Wow: 5/5 | Feasibility: 4/5**

---

## 9. Satellite / Remote Sensing

### Ideas
- **"GreenWatch"** — 10-year NDVI time-lapse of Split's green space loss
- **"CoastAlert"** — Beach erosion monitoring + illegal construction detection
- **"CruiseWatch"** — Ship NO2 plume detection from Sentinel-5P

### Best: "GreenWatch" — Satellite Urban Greening Tracker

**Concept:** Dashboard showing 10 years of vegetation change in Split using Sentinel-2 NDVI. Click any neighborhood to see: vegetation trend, correlation with building permits, comparison with other Med cities. Includes "what-if": "If we plant 1000 trees here, estimated cooling = X°C."

**Tech Stack:**
- Google Earth Engine or Copernicus API
- Python (rasterio, geopandas)
- Deck.gl or Leaflet for web viz
- Simple thermal model for cooling estimates

**What makes it novel:** 10-year time-lapse of greening/de-greening is emotionally powerful. Satellite data made accessible and actionable for citizens.

**Wow: 3/5 | Feasibility: 5/5**

---

## 10. Wearables / Personal IoT

### Ideas
- **"HeatGuard"** — Personal heat stress warning with shade-aware routing
- **"PalaceQuest"** — NFC heritage gamification (collect stories, spread crowds)
- **"AccessSplit"** — BLE beacon accessibility navigation (underground Palace has no GPS)

### Best: "HeatGuard" — AI Heat Stress Prevention with Shade Routing

**Concept:** Mobile/smartwatch app preventing heat illness. Combines personal health data (activity level from watch), hyperlocal weather (temp, humidity, UV), and city knowledge (shade map, water fountains, AC museums). When risk is high, reroutes tourist through shade.

**Killer feature:** Two routes between A and B:
- Standard: 15 min, 80% sun exposure
- HeatGuard: 18 min, 30% sun exposure

**Tech Stack:**
- React Native / Flutter
- Apple HealthKit / Google Fit
- OpenWeather API
- Shade map from OSM building footprints + SunCalc.js sun position
- Mapbox routing with custom "prefer shade" weights

**What makes it novel:** "Shade-aware routing" does not exist in any navigation app. The shade map alone is a useful city asset. Humanitarian angle (preventing hospitalizations).

**Wow: 4/5 | Feasibility: 4/5**

---

## Recent Breakthrough Inspirations (2024-2026)

| Project | Tech | Adapt for Split? |
|---------|------|-----------------|
| Kaohsiung City — physical AI detects damaged streetlights | CV + Edge | Palace damage detection |
| Dublin VivaCity — multimodal traffic sensors on Jetson | CV + Edge | Pedestrian counting in narrow streets |
| Heritage-3DGS (2025 paper) — LLM-narrated Gaussian Splatting | 3DGS + LLM | Palace reconstruction with AI narration |
| Memphis "Byte the Blight" — AI urban decay detection | CV + Data | Old town building deterioration |
| Copernicus Urban Heat Monitoring (2025) | Remote Sensing | Heat island mapping |
| MDPI LLM Agents for Smart City (2025) | Multi-Agent | Policy negotiation tool |
| Dubrovnik Smart Tourism (2026 EU award) | Smart City | Split should replicate + improve |

---

## Strategic Decision Matrix

| If your team is strong in... | Build this | Why |
|------------------------------|-----------|-----|
| **Backend / AI / Prompt engineering** | SplitMediator | No hardware, pure AI, highest wow |
| **Frontend / 3D / Visual** | PalaceReborn | Most visually stunning demo |
| **Full-stack / Product** | SplitStory | Safest bet, guaranteed working demo |
| **Hardware / IoT** | MarjanWatch or AirSplit | Physical demo impresses judges differently |
| **Data science / GIS** | HeatGuard or GreenWatch | Novel analysis, clear utility |

---

## The Meta-Strategy

**Safest path to winning:** SplitStory (LLM + RAG personalized tours)
- Guaranteed working demo, clear utility, directly addresses #1 problem

**Highest ceiling:** SplitMediator (multi-agent debate)
- If executed well, it's unforgettable. Judges can interact with it live.

**Most visual impact:** PalaceReborn (Gaussian Splatting)
- If you can pull it off in 48h, nothing else comes close visually

**Most emotionally resonant:** MarjanWatch (fire detection)
- Every local judge thinks "why don't we have this?" — that's powerful
