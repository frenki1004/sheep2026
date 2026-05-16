import "maplibre-gl/dist/maplibre-gl.css";
import { Map, Popup } from "maplibre-gl";
import { init3D, destroy3D } from "./view3d.js";

const map = new Map({
  container: "map",
  style: {
    version: 8,
    sources: {
      "esri-satellite": {
        type: "raster",
        tiles: ["https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"],
        tileSize: 256,
        maxzoom: 19,
        attribution: "Esri, Maxar, Earthstar Geographics",
      },
      terrain: {
        type: "raster-dem",
        tiles: ["https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"],
        encoding: "terrarium",
        tileSize: 256,
      },
    },
    terrain: { source: "terrain", exaggeration: 1.3 },
    layers: [{ id: "satellite", type: "raster", source: "esri-satellite" }],
  },
  center: [16.44, 43.508],
  zoom: 14.5,
  maxZoom: 20,
  pitch: 55,
  bearing: -20,
  antialias: true,
});

const OSS_TOKEN = "7effb6395af73ee111123d3d1317471357a1f012d4df977d3ab05ebdc184a46e";

map.on("load", async () => {
  // Cadastral parcel boundaries from oss.uredjenazemlja.hr
  map.addSource("parcels-wms", {
    type: "raster",
    tiles: [
      `https://wms1-gs-oss.uredjenazemlja.hr/ows2-m/wms?token=${OSS_TOKEN}&service=WMS&version=1.3.0&request=GetMap&LAYERS=oss:BZP_CESTICE&STYLES=jis_cestice_kathr&CRS=EPSG:3857&BBOX={bbox-epsg-3857}&WIDTH=256&HEIGHT=256&FORMAT=image/png&TRANSPARENT=true`,
    ],
    tileSize: 256,
  });
  map.addLayer({
    id: "parcels",
    type: "raster",
    source: "parcels-wms",
    paint: { "raster-opacity": 0.7 },
  });
  const [buildings, landuse] = await Promise.all([
    fetch("/data/buildings.geojson").then((r) => r.json()),
    fetch("/data/landuse.geojson").then((r) => r.json()),
  ]);

  const features = buildings.features || [];
  const total = features.length;
  const matched = features.filter((f) => f.properties.status === "matched").length;
  const unregistered = features.filter((f) => f.properties.status === "unregistered").length;
  const katastarOnly = features.filter((f) => f.properties.status === "katastarOnly").length;

  const onProtected = features.filter((f) => f.properties.status === "illegal_protected").length;

  document.getElementById("stat-total").textContent = total.toLocaleString();
  document.getElementById("stat-matched").textContent = matched.toLocaleString();
  document.getElementById("stat-unregistered").textContent = unregistered.toLocaleString();
  document.getElementById("stat-protected").textContent = onProtected.toLocaleString();
  document.getElementById("stat-katastar").textContent = katastarOnly.toLocaleString();

  // Land use zones (below buildings)
  map.addSource("landuse", { type: "geojson", data: landuse });
  map.addLayer({
    id: "landuse-fill",
    type: "fill",
    source: "landuse",
    filter: ["!", ["in", ["get", "land_type"], ["literal", ["Dvoriste", "PovrsineTrajnijegKaraktera", "PovrsinaCeste", "Parkiraliste", "GospodarskePovrsine"]]]],
    paint: {
      "fill-color": [
        "match", ["get", "land_type"],
        "Vinograd", "rgba(128, 0, 128, 0.4)",
        "Maslinik", "rgba(107, 142, 35, 0.4)",
        "Oranica", "rgba(210, 180, 60, 0.35)",
        "Vrt", "rgba(144, 238, 144, 0.3)",
        "Park", "rgba(34, 139, 34, 0.4)",
        "Crnogorica", "rgba(0, 100, 0, 0.4)",
        "TravnatePovrsine", "rgba(124, 252, 0, 0.25)",
        "SportskoIgraliste", "rgba(0, 191, 255, 0.3)",
        "Kamenjar", "rgba(160, 160, 160, 0.3)",
        "Rasadnik", "rgba(50, 205, 50, 0.35)",
        "rgba(0, 0, 0, 0)",
      ],
      "fill-opacity": 0.6,
    },
  });
  map.addLayer({
    id: "landuse-outline",
    type: "line",
    source: "landuse",
    filter: ["!", ["in", ["get", "land_type"], ["literal", ["Dvoriste", "PovrsineTrajnijegKaraktera", "PovrsinaCeste", "Parkiraliste", "GospodarskePovrsine"]]]],
    paint: {
      "line-color": "rgba(255, 255, 255, 0.85)",
      "line-width": 1.5,
    },
  });
  map.addLayer({
    id: "landuse-labels",
    type: "symbol",
    source: "landuse",
    filter: ["!", ["in", ["get", "land_type"], ["literal", ["Dvoriste", "PovrsineTrajnijegKaraktera", "PovrsinaCeste", "Parkiraliste", "GospodarskePovrsine", "Raskrizje"]]]],
    layout: {
      "text-field": ["get", "land_type"],
      "text-size": 11,
      "text-allow-overlap": false,
    },
    paint: {
      "text-color": "#fff",
      "text-halo-color": "rgba(0,0,0,0.7)",
      "text-halo-width": 1.2,
    },
  });

  map.addSource("buildings", { type: "geojson", data: buildings });

  map.addLayer({
    id: "buildings-3d",
    type: "fill-extrusion",
    source: "buildings",
    paint: {
      "fill-extrusion-color": [
        "match", ["get", "status"],
        "matched", "#64c864",
        "unregistered", "#dc3232",
        "illegal_protected", "#8b0000",
        "katastarOnly", "#ffa500",
        "#999999",
      ],
      "fill-extrusion-height": ["coalesce", ["get", "height"], 8],
      "fill-extrusion-base": 0,
      "fill-extrusion-opacity": 0.85,
    },
  });

  map.on("click", "buildings-3d", (e) => {
    e.preventDefault();
    const p = e.features[0].properties;
    const lon = p.centroid_lon || e.lngLat.lng;
    const lat = p.centroid_lat || e.lngLat.lat;
    let html = `
      <b>Status:</b> ${p.status}<br/>
      <b>Area:</b> ${p.area_m2 ? Math.round(p.area_m2) + " m²" : "unknown"}<br/>
      <b>Height:</b> ${p.height > 0 ? p.height + "m" : "est. 8m"}<br/>
    `;
    if (p.building_type) html += `<b>Type:</b> ${p.building_type}<br/>`;
    if (p.building_id) html += `<b>Zgrada ID:</b> ${p.building_id}<br/>`;
    if (p.land_zone && p.land_zone !== "unknown") html += `<b>Land zone:</b> ${p.land_zone}<br/>`;
    html += `<div style="margin-top:4px; font-size:11px;">`;
    html += `<a href="https://www.google.com/maps/place/${lat},${lon}/@${lat},${lon},20z" target="_blank" style="color:#4da6ff; text-decoration:underline;">View on Google Maps</a>`;
    html += `</div>`;
    new Popup({ offset: 15 })
      .setLngLat(e.lngLat)
      .setHTML(html)
      .addTo(map);
  });

  map.on("click", "landuse-fill", (e) => {
    if (e.defaultPrevented) return;
    const p = e.features[0].properties;
    const skip = ["Dvoriste", "PovrsineTrajnijegKaraktera", "PovrsinaCeste", "Parkiraliste", "GospodarskePovrsine"];
    if (skip.includes(p.land_type)) return;
    const html = `<b>Land use:</b> ${p.land_type}<br/><b>Observed:</b> ${p.observation_date || "N/A"}`;
    new Popup({ offset: 15 }).setLngLat(e.lngLat).setHTML(html).addTo(map);
  });

  map.on("mouseenter", "buildings-3d", () => { map.getCanvas().style.cursor = "pointer"; });
  map.on("mouseleave", "buildings-3d", () => { map.getCanvas().style.cursor = ""; });
});

// Address search (Nominatim)
const searchInput = document.getElementById("search-input");
const searchResults = document.getElementById("search-results");
let searchTimeout = null;

searchInput.addEventListener("input", () => {
  clearTimeout(searchTimeout);
  const q = searchInput.value.trim();
  if (q.length < 3) { searchResults.classList.remove("visible"); return; }
  searchTimeout = setTimeout(async () => {
    const res = await fetch(`https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(q + ", Split, Croatia")}&format=json&limit=5`);
    const data = await res.json();
    if (data.length === 0) { searchResults.classList.remove("visible"); return; }
    searchResults.innerHTML = data.map(r =>
      `<div class="result" data-lon="${r.lon}" data-lat="${r.lat}">${r.display_name.split(",").slice(0, 3).join(",")}</div>`
    ).join("");
    searchResults.classList.add("visible");
  }, 400);
});

searchResults.addEventListener("click", (e) => {
  const el = e.target.closest(".result");
  if (!el) return;
  const lon = parseFloat(el.dataset.lon);
  const lat = parseFloat(el.dataset.lat);
  map.flyTo({ center: [lon, lat], zoom: 17, pitch: 55 });
  searchResults.classList.remove("visible");
  searchInput.value = el.textContent;
});

searchInput.addEventListener("keydown", (e) => {
  if (e.key === "Escape") { searchResults.classList.remove("visible"); searchInput.blur(); }
});

document.addEventListener("click", (e) => {
  if (!e.target.closest(".search-bar")) searchResults.classList.remove("visible");
});

// View toggle
let cesiumLoaded = false;
const btn2d = document.getElementById("btn-2d");
const btn3d = document.getElementById("btn-3d");
const mapEl = document.getElementById("map");
const cesiumEl = document.getElementById("cesium-container");

const searchBar = document.getElementById("search-bar");
const statsPanel = document.querySelector(".stats-panel");

btn3d.addEventListener("click", async () => {
  btn3d.classList.add("active");
  btn2d.classList.remove("active");
  mapEl.style.display = "none";
  cesiumEl.style.display = "block";
  searchBar.style.display = "none";
  statsPanel.style.display = "none";
  if (!cesiumLoaded) {
    await init3D("cesium-container");
    cesiumLoaded = true;
  }
  const canvas = cesiumEl.querySelector("canvas");
  if (canvas) canvas.focus();
});

btn2d.addEventListener("click", () => {
  btn2d.classList.add("active");
  btn3d.classList.remove("active");
  cesiumEl.style.display = "none";
  mapEl.style.display = "block";
  searchBar.style.display = "block";
  statsPanel.style.display = "block";
  map.resize();
});
