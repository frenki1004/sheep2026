import { readFileSync, writeFileSync } from "fs";

const MS_PATH = "../public/data/buildings_ms.geojson";
const DGU_PATH = "../public/data/buildings_oss.geojson"; // Live OSS katastar (2026)
const OUT_PATH = "../public/data/buildings.geojson";

const BBOX = { minLon: 16.41, maxLon: 16.55, minLat: 43.49, maxLat: 43.55 };

// --- Geometry utilities ---

function centroid(ring) {
  let cx = 0, cy = 0, n = ring.length;
  for (const [x, y] of ring) { cx += x; cy += y; }
  return [cx / n, cy / n];
}

function getCentroid(geometry) {
  if (geometry.type === "Polygon") return centroid(geometry.coordinates[0]);
  if (geometry.type === "MultiPolygon") return centroid(geometry.coordinates[0][0]);
  return null;
}

function getBbox(geometry) {
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
  const rings = geometry.type === "MultiPolygon" ? geometry.coordinates[0][0] : geometry.coordinates[0];
  for (const [x, y] of rings) {
    if (x < minX) minX = x; if (x > maxX) maxX = x;
    if (y < minY) minY = y; if (y > maxY) maxY = y;
  }
  return { minX, minY, maxX, maxY };
}

function bboxArea(bb) { return (bb.maxX - bb.minX) * (bb.maxY - bb.minY); }

function bboxIntersects(a, b) {
  return a.minX <= b.maxX && a.maxX >= b.minX && a.minY <= b.maxY && a.maxY >= b.minY;
}

function bboxBuffer(bb, buf) {
  return { minX: bb.minX - buf, minY: bb.minY - buf, maxX: bb.maxX + buf, maxY: bb.maxY + buf };
}

// Ray casting point-in-polygon
function pointInRing(pt, ring) {
  let inside = false;
  const [px, py] = pt;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [xi, yi] = ring[i], [xj, yj] = ring[j];
    if ((yi > py) !== (yj > py) && px < (xj - xi) * (py - yi) / (yj - yi) + xi) {
      inside = !inside;
    }
  }
  return inside;
}

function pointInPolygon(pt, geometry) {
  if (geometry.type === "Polygon") {
    return pointInRing(pt, geometry.coordinates[0]);
  }
  if (geometry.type === "MultiPolygon") {
    for (const poly of geometry.coordinates) {
      if (pointInRing(pt, poly[0])) return true;
    }
  }
  return false;
}

// Approximate polygon area in m²
function ringAreaDeg(ring) {
  let area = 0;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    area += (ring[j][0] + ring[i][0]) * (ring[j][1] - ring[i][1]);
  }
  return Math.abs(area / 2);
}

function areaM2(geometry, lat) {
  const mLon = 111320 * Math.cos(lat * Math.PI / 180);
  const mLat = 110540;
  if (geometry.type === "Polygon") return ringAreaDeg(geometry.coordinates[0]) * mLon * mLat;
  if (geometry.type === "MultiPolygon") {
    let total = 0;
    for (const poly of geometry.coordinates) total += ringAreaDeg(poly[0]);
    return total * mLon * mLat;
  }
  return 0;
}

function inBbox(pt) {
  return pt[0] >= BBOX.minLon && pt[0] <= BBOX.maxLon && pt[1] >= BBOX.minLat && pt[1] <= BBOX.maxLat;
}

function distM(a, b) {
  const R = 6371000;
  const dLat = (b[1] - a[1]) * Math.PI / 180;
  const dLon = (b[0] - a[0]) * Math.PI / 180;
  const lat1 = a[1] * Math.PI / 180;
  const lat2 = b[1] * Math.PI / 180;
  const s = Math.sin(dLat / 2) ** 2 + Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLon / 2) ** 2;
  return R * 2 * Math.asin(Math.sqrt(s));
}

// --- Spatial index (grid of bounding boxes) ---

function buildBboxGrid(items, cellSize) {
  const grid = {};
  for (let i = 0; i < items.length; i++) {
    const bb = items[i].bbox;
    const x0 = Math.floor(bb.minX / cellSize), x1 = Math.floor(bb.maxX / cellSize);
    const y0 = Math.floor(bb.minY / cellSize), y1 = Math.floor(bb.maxY / cellSize);
    for (let x = x0; x <= x1; x++) {
      for (let y = y0; y <= y1; y++) {
        const key = `${x},${y}`;
        if (!grid[key]) grid[key] = [];
        grid[key].push(i);
      }
    }
  }
  return grid;
}

function queryCandidates(pt, grid, cellSize) {
  const key = `${Math.floor(pt[0] / cellSize)},${Math.floor(pt[1] / cellSize)}`;
  return grid[key] || [];
}

// --- Main ---

console.log("Loading data...");
const ms = JSON.parse(readFileSync(MS_PATH, "utf-8"));
const dgu = JSON.parse(readFileSync(DGU_PATH, "utf-8"));

// Prepare and filter
const msData = [], dguData = [];
for (const f of ms.features) {
  const c = getCentroid(f.geometry);
  if (c && inBbox(c)) msData.push({ feature: f, centroid: c, bbox: getBbox(f.geometry), area: areaM2(f.geometry, c[1]) });
}
for (const f of dgu.features) {
  const c = getCentroid(f.geometry);
  if (c && inBbox(c)) dguData.push({ feature: f, centroid: c, bbox: getBbox(f.geometry), area: areaM2(f.geometry, c[1]) });
}
console.log(`In bbox — MS: ${msData.length}, DGU: ${dguData.length}`);

// Compute systematic offset (median of centroid differences for close pairs)
console.log("Computing offset...");
const CELL = 0.0008;
const dguCentroidGrid = {};
for (let i = 0; i < dguData.length; i++) {
  const [lon, lat] = dguData[i].centroid;
  const key = `${Math.floor(lon / CELL)},${Math.floor(lat / CELL)}`;
  if (!dguCentroidGrid[key]) dguCentroidGrid[key] = [];
  dguCentroidGrid[key].push(i);
}

const offsets = [];
for (const d of msData) {
  const [lon, lat] = d.centroid;
  const cx = Math.floor(lon / CELL), cy = Math.floor(lat / CELL);
  let bestDist = 20, bestIdx = -1;
  for (let dx = -1; dx <= 1; dx++) for (let dy = -1; dy <= 1; dy++) {
    const bucket = dguCentroidGrid[`${cx+dx},${cy+dy}`];
    if (!bucket) continue;
    for (const idx of bucket) {
      const dist = distM(d.centroid, dguData[idx].centroid);
      if (dist < bestDist) { bestDist = dist; bestIdx = idx; }
    }
  }
  if (bestIdx >= 0) {
    offsets.push({ dLon: dguData[bestIdx].centroid[0] - d.centroid[0], dLat: dguData[bestIdx].centroid[1] - d.centroid[1] });
  }
}
offsets.sort((a, b) => a.dLon - b.dLon);
const medLon = offsets[Math.floor(offsets.length / 2)].dLon;
offsets.sort((a, b) => a.dLat - b.dLat);
const medLat = offsets[Math.floor(offsets.length / 2)].dLat;
console.log(`  Offset: dLon=${(medLon * 111000).toFixed(2)}m, dLat=${(medLat * 111000).toFixed(2)}m`);

// Apply offset to MS data
function shiftCoords(coords, dLon, dLat) {
  return coords.map(ring => ring.map(([x, y]) => [x + dLon, y + dLat]));
}
function shiftGeometry(geom, dLon, dLat) {
  if (geom.type === "Polygon") return { type: "Polygon", coordinates: shiftCoords(geom.coordinates, dLon, dLat) };
  if (geom.type === "MultiPolygon") return { type: "MultiPolygon", coordinates: geom.coordinates.map(p => shiftCoords(p, dLon, dLat)) };
  return geom;
}

for (const d of msData) {
  d.feature = { ...d.feature, geometry: shiftGeometry(d.feature.geometry, medLon, medLat) };
  d.centroid = [d.centroid[0] + medLon, d.centroid[1] + medLat];
  d.bbox = getBbox(d.feature.geometry);
}

// --- Smart matching: mutual containment + proximity ---
// Strategy:
// 1. MS centroid inside DGU polygon → match
// 2. DGU centroid inside MS polygon → match
// 3. Centroid distance < 12m AND area ratio > 0.3 → match (fallback for small offsets)
// This handles rotation, shape differences, and partial overlaps

console.log("Matching (mutual containment + proximity)...");

const BUFFER_DEG = 0.00005; // ~5m buffer for bbox pre-filter
const dguBboxGrid = buildBboxGrid(dguData.map(d => ({ bbox: bboxBuffer(d.bbox, BUFFER_DEG) })), CELL);
const msBboxGrid = buildBboxGrid(msData.map(d => ({ bbox: bboxBuffer(d.bbox, BUFFER_DEG) })), CELL);

const msMatchedTo = new Array(msData.length).fill(-1);  // which DGU index
const dguMatchedBy = new Array(dguData.length).fill(-1); // first MS that matched

// Pass 1: MS centroid inside DGU polygon
let pass1 = 0;
for (let i = 0; i < msData.length; i++) {
  const pt = msData[i].centroid;
  const candidates = queryCandidates(pt, dguBboxGrid, CELL);
  for (const j of candidates) {
    const bb = bboxBuffer(dguData[j].bbox, BUFFER_DEG);
    if (pt[0] < bb.minX || pt[0] > bb.maxX || pt[1] < bb.minY || pt[1] > bb.maxY) continue;
    if (pointInPolygon(pt, dguData[j].feature.geometry)) {
      msMatchedTo[i] = j;
      dguMatchedBy[j] = i;
      pass1++;
      break;
    }
  }
}
console.log(`  Pass 1 (MS centroid in DGU poly): ${pass1}`);

// Pass 2: DGU centroid inside MS polygon (catches reverse direction)
let pass2 = 0;
for (let j = 0; j < dguData.length; j++) {
  const pt = dguData[j].centroid;
  const candidates = queryCandidates(pt, msBboxGrid, CELL);
  for (const i of candidates) {
    if (msMatchedTo[i] >= 0) continue; // already matched
    const bb = bboxBuffer(msData[i].bbox, BUFFER_DEG);
    if (pt[0] < bb.minX || pt[0] > bb.maxX || pt[1] < bb.minY || pt[1] > bb.maxY) continue;
    if (pointInPolygon(pt, msData[i].feature.geometry)) {
      msMatchedTo[i] = j;
      dguMatchedBy[j] = i;
      pass2++;
      break;
    }
  }
}
console.log(`  Pass 2 (DGU centroid in MS poly): ${pass2}`);

// Pass 3: proximity fallback — require reasonable area similarity to avoid matching to wrong neighbor
let pass3 = 0;
for (let i = 0; i < msData.length; i++) {
  if (msMatchedTo[i] >= 0) continue;
  const pt = msData[i].centroid;
  const msArea = msData[i].area;
  const cx = Math.floor(pt[0] / CELL), cy = Math.floor(pt[1] / CELL);
  let bestScore = 0, bestJ = -1;
  for (let dx = -1; dx <= 1; dx++) for (let dy = -1; dy <= 1; dy++) {
    const bucket = dguCentroidGrid[`${cx+dx},${cy+dy}`];
    if (!bucket) continue;
    for (const j of bucket) {
      const dist = distM(pt, dguData[j].centroid);
      if (dist > 20) continue;
      const areaRatio = Math.min(msArea, dguData[j].area) / Math.max(msArea, dguData[j].area);
      if (areaRatio < 0.2) continue; // skip if areas differ >5x
      const score = (1 - dist/20) * 0.6 + areaRatio * 0.4;
      if (score > bestScore) { bestScore = score; bestJ = j; }
    }
  }
  if (bestJ >= 0 && bestScore > 0.3) {
    msMatchedTo[i] = bestJ;
    dguMatchedBy[bestJ] = i;
    pass3++;
  }
}
console.log(`  Pass 3 (proximity+area): ${pass3}`);

// Pass 4: Check MS polygon VERTICES inside OSS polygons (catches edge cases where centroid is outside)
let pass4 = 0;
function getVertices(geometry) {
  const ring = geometry.type === "MultiPolygon" ? geometry.coordinates[0][0] : geometry.coordinates[0];
  return ring;
}
for (let i = 0; i < msData.length; i++) {
  if (msMatchedTo[i] >= 0) continue;
  const verts = getVertices(msData[i].feature.geometry);
  let matched = false;
  for (const v of verts) {
    if (matched) break;
    const candidates = queryCandidates(v, dguBboxGrid, CELL);
    for (const j of candidates) {
      const bb = dguData[j].bbox;
      if (v[0] < bb.minX || v[0] > bb.maxX || v[1] < bb.minY || v[1] > bb.maxY) continue;
      if (pointInPolygon(v, dguData[j].feature.geometry)) {
        msMatchedTo[i] = j;
        dguMatchedBy[j] = i;
        pass4++;
        matched = true;
        break;
      }
    }
  }
}
console.log(`  Pass 4 (MS vertex in OSS poly): ${pass4}`);

// Pass 5: Check if any OSS vertex falls inside MS polygon
let pass5 = 0;
for (let i = 0; i < msData.length; i++) {
  if (msMatchedTo[i] >= 0) continue;
  const msBb = bboxBuffer(msData[i].bbox, BUFFER_DEG);
  const candidates = queryCandidates(msData[i].centroid, dguBboxGrid, CELL);
  for (const j of candidates) {
    const verts = getVertices(dguData[j].feature.geometry);
    let found = false;
    for (const v of verts) {
      if (v[0] < msBb.minX || v[0] > msBb.maxX || v[1] < msBb.minY || v[1] > msBb.maxY) continue;
      if (pointInPolygon(v, msData[i].feature.geometry)) {
        msMatchedTo[i] = j;
        dguMatchedBy[j] = i;
        pass5++;
        found = true;
        break;
      }
    }
    if (found) break;
  }
}
console.log(`  Pass 5 (OSS vertex in MS poly): ${pass5}`);

// Pass 6: bbox overlap >20% of smaller
let pass6 = 0;
for (let i = 0; i < msData.length; i++) {
  if (msMatchedTo[i] >= 0) continue;
  const msBb = msData[i].bbox;
  const candidates = queryCandidates(msData[i].centroid, dguBboxGrid, CELL);
  for (const j of candidates) {
    if (!bboxIntersects(msBb, dguData[j].bbox)) continue;
    const ix = Math.max(0, Math.min(msBb.maxX, dguData[j].bbox.maxX) - Math.max(msBb.minX, dguData[j].bbox.minX));
    const iy = Math.max(0, Math.min(msBb.maxY, dguData[j].bbox.maxY) - Math.max(msBb.minY, dguData[j].bbox.minY));
    const overlap = ix * iy;
    const smaller = Math.min(bboxArea(msBb), bboxArea(dguData[j].bbox));
    if (smaller > 0 && overlap / smaller > 0.2) {
      msMatchedTo[i] = j;
      dguMatchedBy[j] = i;
      pass6++;
      break;
    }
  }
}
console.log(`  Pass 6 (bbox overlap >20%): ${pass6}`);

// --- Land use cross-reference ---
console.log("\nCross-referencing with land use...");
const landuse = JSON.parse(readFileSync("../public/data/landuse.geojson", "utf-8"));
const luData = [];
for (const f of landuse.features) {
  const bb = getBbox(f.geometry);
  const landType = f.properties.land_type || f.properties.specific_land_use?.split("/").pop() || "unknown";
  luData.push({ feature: f, bbox: bb, landType });
}
const luGrid = buildBboxGrid(luData.map(d => ({ bbox: d.bbox })), CELL);

const PROTECTED_ZONES = new Set(["Vinograd", "Maslinik", "Oranica", "Crnogorica", "Park"]);
const LEGITIMATE_ZONES = new Set(["SportskoIgraliste", "PovrsineCeste", "Parkiraliste"]);

function getLandUse(pt) {
  const candidates = queryCandidates(pt, luGrid, CELL);
  for (const idx of candidates) {
    const lu = luData[idx];
    if (pt[0] < lu.bbox.minX || pt[0] > lu.bbox.maxX || pt[1] < lu.bbox.minY || pt[1] > lu.bbox.maxY) continue;
    if (pointInPolygon(pt, lu.feature.geometry)) return lu.landType;
  }
  return null;
}

// --- Build output ---
const outputFeatures = [];

let onProtected = 0;
for (let i = 0; i < msData.length; i++) {
  const d = msData[i];
  let status;
  if (msMatchedTo[i] >= 0) status = "matched";
  else status = "unregistered";

  const landZone = getLandUse(d.centroid);
  const onProtectedLand = status === "unregistered" && landZone && PROTECTED_ZONES.has(landZone);
  const onLegitimateLand = status === "unregistered" && landZone && LEGITIMATE_ZONES.has(landZone);
  if (onProtectedLand) onProtected++;
  // Buildings on sports fields, economic zones, parking, courtyards → likely legitimate
  if (onLegitimateLand) status = "matched";

  const matchedOss = msMatchedTo[i] >= 0 ? dguData[msMatchedTo[i]] : null;
  outputFeatures.push({
    type: "Feature",
    properties: {
      status: onProtectedLand ? "illegal_protected" : status,
      height: d.feature.properties.height > 0 ? d.feature.properties.height : 8,
      area_m2: Math.round(d.area),
      confidence: d.feature.properties.confidence || 0.9,
      source: "microsoft",
      land_zone: landZone || "unknown",
      centroid_lon: d.centroid[0],
      centroid_lat: d.centroid[1],
      building_id: matchedOss ? matchedOss.feature.properties.building_id : null,
      building_type: matchedOss ? matchedOss.feature.properties.building_type : null,
      municipality_id: matchedOss ? matchedOss.feature.properties.municipality_id : null,
    },
    geometry: d.feature.geometry,
  });
}

// For "katastar only" — check if the OSS building is actually inside an MS blob
// (MS merges adjacent buildings into one polygon)
const MIN_KATASTAR_AREA = 50;
let coveredByMs = 0;
for (let j = 0; j < dguData.length; j++) {
  if (dguMatchedBy[j] >= 0) continue;
  const d = dguData[j];
  if (d.area < MIN_KATASTAR_AREA) continue;

  // Check if this OSS building's centroid is inside any MS polygon
  const pt = d.centroid;
  const candidates = queryCandidates(pt, msBboxGrid, CELL);
  let insideMs = false;
  for (const i of candidates) {
    const bb = bboxBuffer(msData[i].bbox, BUFFER_DEG);
    if (pt[0] < bb.minX || pt[0] > bb.maxX || pt[1] < bb.minY || pt[1] > bb.maxY) continue;
    if (pointInPolygon(pt, msData[i].feature.geometry)) {
      insideMs = true;
      coveredByMs++;
      break;
    }
  }
  if (insideMs) continue; // It's covered by an MS blob, not truly "katastar only"

  outputFeatures.push({
    type: "Feature",
    properties: {
      status: "katastarOnly",
      height: 8,
      area_m2: Math.round(d.area),
      confidence: 0,
      source: "oss",
      building_type: d.feature.properties.building_type || null,
      building_id: d.feature.properties.building_id || null,
      municipality_id: d.feature.properties.municipality_id || null,
      centroid_lon: d.centroid[0],
      centroid_lat: d.centroid[1],
    },
    geometry: d.feature.geometry,
  });
}
console.log(`  OSS buildings covered by MS blobs (not truly katastar-only): ${coveredByMs}`);

const output = { type: "FeatureCollection", features: outputFeatures };
const counts = { matched: 0, unregistered: 0, illegal_protected: 0, katastarOnly: 0 };
for (const f of outputFeatures) counts[f.properties.status] = (counts[f.properties.status] || 0) + 1;

console.log("\nResults:");
console.log(`  Total: ${outputFeatures.length}`);
console.log(`  Matched: ${counts.matched} (${(counts.matched / msData.length * 100).toFixed(1)}% of MS)`);
console.log(`  Unregistered (all sizes): ${counts.unregistered}`);
console.log(`  On protected land: ${counts.illegal_protected} ← HIGH PRIORITY`);
console.log(`  Katastar only: ${counts.katastarOnly}`);

writeFileSync(OUT_PATH, JSON.stringify(output));
console.log(`\nSaved (${(Buffer.byteLength(JSON.stringify(output)) / 1024 / 1024).toFixed(1)} MB)`);
