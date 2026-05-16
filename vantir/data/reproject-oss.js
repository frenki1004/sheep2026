import { readFileSync, writeFileSync } from "fs";

// EPSG:3765 (HTRS96/TM) → EPSG:4326 (WGS84)
// Transverse Mercator inverse projection
const a = 6378137.0; // GRS80 semi-major axis
const f = 1 / 298.257222101;
const b = a * (1 - f);
const e2 = 2 * f - f * f;
const e = Math.sqrt(e2);
const e_prime2 = e2 / (1 - e2);
const lon0 = 16.5 * Math.PI / 180; // central meridian
const k0 = 0.9999;
const E0 = 500000; // false easting
const N0 = 0;

function tmInverse(easting, northing) {
  const x = easting - E0;
  const y = northing - N0;

  const M = y / k0;
  const mu = M / (a * (1 - e2/4 - 3*e2*e2/64 - 5*e2*e2*e2/256));

  const e1 = (1 - Math.sqrt(1 - e2)) / (1 + Math.sqrt(1 - e2));
  const phi1 = mu
    + (3*e1/2 - 27*e1*e1*e1/32) * Math.sin(2*mu)
    + (21*e1*e1/16 - 55*e1*e1*e1*e1/32) * Math.sin(4*mu)
    + (151*e1*e1*e1/96) * Math.sin(6*mu)
    + (1097*e1*e1*e1*e1/512) * Math.sin(8*mu);

  const sinPhi = Math.sin(phi1);
  const cosPhi = Math.cos(phi1);
  const tanPhi = Math.tan(phi1);
  const N1 = a / Math.sqrt(1 - e2 * sinPhi * sinPhi);
  const T1 = tanPhi * tanPhi;
  const C1 = e_prime2 * cosPhi * cosPhi;
  const R1 = a * (1 - e2) / Math.pow(1 - e2 * sinPhi * sinPhi, 1.5);
  const D = x / (N1 * k0);

  const lat = phi1
    - (N1 * tanPhi / R1) * (
      D*D/2
      - (5 + 3*T1 + 10*C1 - 4*C1*C1 - 9*e_prime2) * D*D*D*D/24
      + (61 + 90*T1 + 298*C1 + 45*T1*T1 - 252*e_prime2 - 3*C1*C1) * D*D*D*D*D*D/720
    );

  const lon = lon0 + (
    D
    - (1 + 2*T1 + C1) * D*D*D/6
    + (5 - 2*C1 + 28*T1 - 3*C1*C1 + 8*e_prime2 + 24*T1*T1) * D*D*D*D*D/120
  ) / cosPhi;

  return [lon * 180 / Math.PI, lat * 180 / Math.PI];
}

// Load and reproject
const raw = JSON.parse(readFileSync("../public/data/buildings_oss_raw.geojson", "utf-8"));
console.log(`Loaded ${raw.features.length} OSS buildings`);

function reprojectRing(ring) {
  return ring.map(coord => tmInverse(coord[0], coord[1]));
}

function reprojectGeometry(geom) {
  if (geom.type === "Polygon") {
    return { type: "Polygon", coordinates: geom.coordinates.map(reprojectRing) };
  }
  if (geom.type === "MultiPolygon") {
    return { type: "MultiPolygon", coordinates: geom.coordinates.map(poly => poly.map(reprojectRing)) };
  }
  return geom;
}

const reprojected = {
  type: "FeatureCollection",
  features: raw.features.map(f => ({
    type: "Feature",
    properties: {
      building_id: f.properties.ZGRADA_ID,
      building_type: f.properties.NAZIV_VRSTE_ZGRADE,
      building_type_code: f.properties.SIFRA_VRSTE_ZGRADE,
      municipality_id: f.properties.MATICNI_BROJ_KO,
      number: f.properties.BROJ,
    },
    geometry: reprojectGeometry(f.geometry),
  })),
};

// Verify coordinates look right (should be around lon 16.4, lat 43.5)
const sample = reprojected.features[0];
const coords = sample.geometry.type === "MultiPolygon"
  ? sample.geometry.coordinates[0][0][0]
  : sample.geometry.coordinates[0][0];
console.log(`Sample reprojected coord: [${coords[0].toFixed(5)}, ${coords[1].toFixed(5)}]`);

writeFileSync("../public/data/buildings_oss.geojson", JSON.stringify(reprojected));
console.log(`Saved ${reprojected.features.length} buildings to buildings_oss.geojson`);
