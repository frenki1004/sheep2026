import "maplibre-gl/dist/maplibre-gl.css";
import { Map, Popup } from "maplibre-gl";

const map = new Map({
  container: "map",
  style: {
    version: 8,
    sources: {
      "esri-satellite": {
        type: "raster",
        tiles: ["https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"],
        tileSize: 256,
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
    const html = `
      <b>Status:</b> ${p.status}<br/>
      <b>Area:</b> ${p.area_m2 ? Math.round(p.area_m2) + " m²" : "unknown"}<br/>
      <b>Height:</b> ${p.height > 0 ? p.height + "m" : "est. 8m"}<br/>
      <b>Confidence:</b> ${p.confidence ? (p.confidence * 100).toFixed(0) + "%" : "N/A"}<br/>
      <b>Source:</b> ${p.source || "N/A"}
    `;
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
