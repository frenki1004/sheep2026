import * as Cesium from "cesium";

const colorByDiscrepancy = {
  registered_match: Cesium.Color.fromCssColorString("#76d191").withAlpha(0.58),
  unregistered: Cesium.Color.fromCssColorString("#ff5d5d").withAlpha(0.68),
  protected_land: Cesium.Color.fromCssColorString("#f5bb4f").withAlpha(0.68),
  katastar_only: Cesium.Color.fromCssColorString("#8ab2ff").withAlpha(0.62),
};

const outlineByDiscrepancy = {
  registered_match: Cesium.Color.fromCssColorString("#c8ffd5"),
  unregistered: Cesium.Color.fromCssColorString("#ffd0d0"),
  protected_land: Cesium.Color.fromCssColorString("#ffe3a2"),
  katastar_only: Cesium.Color.fromCssColorString("#d2e0ff"),
};

const PRIORITY_CASE_PAGE_SIZE = 100;
const DEFAULT_SPLIT_SEARCH_BBOX = [
  16.409954564750034, 43.489921808732305, 16.550139806444825, 43.5502367895936,
];
const SEARCH_RESULT_LIMIT = 12;
const LOCAL_SEARCH_LIMIT = 8;
const GOOGLE_SEARCH_LIMIT = 6;

Cesium.Ion.defaultAccessToken = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJqdGkiOiI4MzBmYzI3My1hYjY4LTQ2M2EtOGJlMC05NmVjY2M5MzMxNWMiLCJpZCI6NDMyMzc5LCJzdWIiOiJNYXJ0aW5WcmJvdmNhbiIsImlzcyI6Imh0dHBzOi8vaW9uLmNlc2l1bS5jb20iLCJhdWQiOiJTaGVlcEFJIiwiaWF0IjoxNzc4OTUwOTg2fQ.UvKEfn5zoMIagOAxBu1SefvAt6iHwoRTi-nBgFK8qMY";

const viewer = new Cesium.Viewer("cesiumContainer", {
  timeline: false,
  animation: false,
  sceneModePicker: false,
  baseLayerPicker: false,
  geocoder: false,
  homeButton: false,
  selectionIndicator: false,
  infoBox: false,
  globe: false,
});

viewer.scene.requestRenderMode = true;
viewer.scene.maximumRenderTimeChange = 1;
viewer.scene.skyAtmosphere.show = true;
improveCesiumToolbarAccessibility();

try {
  const tileset = await Cesium.createGooglePhotorealistic3DTileset({
    onlyUsingWithGoogleGeocoder: true,
  });
  tileset.maximumScreenSpaceError = 12;
  tileset.dynamicScreenSpaceError = true;
  viewer.scene.primitives.add(tileset);
} catch (error) {
  console.log(`Error loading Photorealistic 3D Tiles tileset. ${error}`);
  viewer.scene.globe = new Cesium.Globe(Cesium.Ellipsoid.WGS84);
  viewer.scene.globe.baseColor = Cesium.Color.fromCssColorString("#111817");
  viewer.scene.globe.show = true;
}

const appState = {
  activeDataSource: null,
  addressCache: new Map(),
  addressLookupSequence: 0,
  dataSources: new Map(),
  filter: "priority",
  googleGeocoder: null,
  loadSequence: 0,
  parcelQueue: [],
  priorityCases: null,
  searchResults: [],
  selectedSearchIndex: -1,
  summary: null,
};

window.__splitOntologyViewer = viewer;
window.__splitOntologyState = appState;

await initialize();

async function initialize() {
  bindLocalSearch();
  bindInspectorClose();
  const [summary, sourcePayload, priorityCasePayload, parcelQueuePayload] = await Promise.all([
    fetchJson("/api/summary"),
    fetchJson("/api/sources"),
    fetchJson("/api/priority-cases"),
    fetchJson("/api/parcels/queue"),
  ]);
  appState.summary = summary;
  appState.priorityCases = priorityCasePayload;
  appState.parcelQueue = parcelQueuePayload.items;
  renderSources(sourcePayload.sources);
  renderMetrics(summary);
  renderPriorityCases(priorityCasePayload);
  focusPilotArea(summary.aoi.bbox);
  await loadBuildings("priority");
  bindLegend();
  bindPicking();
}

function renderPriorityCases(payload) {
  const queue = document.querySelector("#caseQueue");
  const count = document.querySelector("#caseQueueCount");
  const context = document.querySelector("#caseSampleContext");
  count.textContent = `${formatCount(payload.total)} building flags`;
  context.textContent = `Parcel sample: ${formatCount(
    payload.parcel_sample.flagged_parcels,
  )} flagged parcels / ${formatCount(payload.parcel_sample.loaded_parcels)} loaded parcels`;
  queue.replaceChildren(...payload.items.map(priorityCaseRow));
  if (payload.items.length < payload.total) {
    const loadMore = document.createElement("button");
    loadMore.className = "load-more-row";
    loadMore.type = "button";
    loadMore.innerHTML = `
      <span>Showing ${formatCount(payload.items.length)} of ${formatCount(payload.total)}</span>
      <strong>Load more</strong>
    `;
    loadMore.addEventListener("click", loadMorePriorityCases);
    queue.appendChild(loadMore);
  }
}

function priorityCaseRow(item) {
  const row = document.createElement("button");
  const parcelLabel = item.parcel_id
    ? `Loaded parcel ${item.parcel_id}`
    : "Outside loaded parcel sample";
  row.className = `case-row priority-case-row ${item.risk_level}`;
  row.type = "button";
  row.dataset.buildingId = item.id;
  row.setAttribute("aria-pressed", "false");
  row.innerHTML = `
    <span class="case-row-main">
      <strong>${escapeHtml(item.id)}</strong>
      <span>${escapeHtml(readableDiscrepancy(item.discrepancy_type))} · ${formatCount(
        item.area_m2,
      )} m2 · ${Math.round(item.confidence * 100)}% confidence</span>
      <span>${escapeHtml(item.land_zone)} · ${escapeHtml(parcelLabel)}</span>
    </span>
    <span class="case-score">
      <span>Impact</span>
      <strong>${formatCount(item.impact_score)}</strong>
    </span>
  `;
  row.addEventListener("click", () => selectPriorityCase(item));
  return row;
}

async function loadMorePriorityCases() {
  const nextOffset = appState.priorityCases.items.length;
  const payload = await fetchJson(
    `/api/priority-cases?limit=${PRIORITY_CASE_PAGE_SIZE}&offset=${nextOffset}`,
  );
  appState.priorityCases = {
    ...payload,
    offset: 0,
    items: [...appState.priorityCases.items, ...payload.items],
  };
  renderPriorityCases(appState.priorityCases);
}

function bindLocalSearch() {
  const form = document.querySelector("#localSearch");
  const input = document.querySelector("#localSearchInput");
  const results = document.querySelector("#localSearchResults");
  let debounceId = null;
  input.disabled = false;

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    if (appState.selectedSearchIndex >= 0) {
      selectSearchResult(appState.searchResults[appState.selectedSearchIndex]);
      return;
    }
    searchSplitDataset(input.value);
  });

  input.addEventListener("input", () => {
    window.clearTimeout(debounceId);
    const query = input.value.trim();
    if (!shouldSearch(query)) {
      appState.searchResults = [];
      appState.selectedSearchIndex = -1;
      hideSearchResults();
      return;
    }
    renderSearchMessage("Searching Split and Google Maps...");
    debounceId = window.setTimeout(() => searchSplitDataset(query), 160);
  });

  input.addEventListener("keydown", (event) => {
    if (results.hidden) return;
    if (event.key === "ArrowDown") {
      event.preventDefault();
      moveSearchSelection(1);
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      moveSearchSelection(-1);
    } else if (event.key === "Enter" && appState.selectedSearchIndex >= 0) {
      event.preventDefault();
      selectSearchResult(appState.searchResults[appState.selectedSearchIndex]);
    } else if (event.key === "Escape") {
      event.preventDefault();
      hideSearchResults();
    }
  });

  document.addEventListener("click", (event) => {
    if (!form.contains(event.target)) {
      hideSearchResults();
    }
  });
}

function shouldSearch(query) {
  return query.length >= 2 || /^b$/i.test(query) || /^\d{3,}$/.test(query);
}

async function searchSplitDataset(query) {
  const input = document.querySelector("#localSearchInput");
  const currentQuery = query.trim();
  if (!shouldSearch(currentQuery)) return;
  renderSearchMessage("Searching Split and Google Maps...");
  const [payload, googleItems] = await Promise.all([
    fetchJson(`/api/search?q=${encodeURIComponent(currentQuery)}&limit=${LOCAL_SEARCH_LIMIT}`),
    searchGoogleMapsInSplit(currentQuery),
  ]);
  if (input.value.trim() !== currentQuery) return;
  const items = mergeSearchResults(payload.items, googleItems);
  appState.searchResults = items;
  appState.selectedSearchIndex = items.length ? 0 : -1;
  renderSearchResults(items);
}

async function searchGoogleMapsInSplit(query) {
  const geocoder = getGoogleGeocoder();
  if (!geocoder) return [];
  try {
    const results = await geocoder.geocode(googleMapsSplitQuery(query), Cesium.GeocodeType.SEARCH);
    return results
      .map((result, index) => googleResultToSearchItem(result, index, query))
      .filter(Boolean)
      .slice(0, GOOGLE_SEARCH_LIMIT);
  } catch (error) {
    console.log(`Google Maps search unavailable. ${error}`);
    return [];
  }
}

function getGoogleGeocoder() {
  if (appState.googleGeocoder) return appState.googleGeocoder;
  if (!Cesium.Ion.defaultAccessToken || !Cesium.IonGeocoderService) return null;
  const geocodeProviderType = Cesium.IonGeocodeProviderType?.GOOGLE;
  if (!geocodeProviderType) return null;
  appState.googleGeocoder = new Cesium.IonGeocoderService({
    scene: viewer.scene,
    geocodeProviderType,
  });
  return appState.googleGeocoder;
}

function googleMapsSplitQuery(query) {
  return /\b(split|croatia|hrvatska|hr)\b/i.test(query) ? query : `${query}, Split, Croatia`;
}

function googleResultToSearchItem(result, index, query) {
  const bbox = bboxFromCesiumDestination(result.destination);
  if (!bbox || !bboxCenterInSplit(bbox)) return null;
  const label = String(result.displayName || "Google Maps result").replace(/\s+/g, " ").trim();
  if (!googleResultMatchesQuery(label, query)) return null;
  return {
    type: "google_maps",
    id: `google-maps-${index}-${label}`,
    label,
    subtitle: "Google Maps place, address, or monument in Split",
    bbox,
    source: "Google Maps",
  };
}

function googleResultMatchesQuery(label, query) {
  const normalizedLabel = normalizeSearchText(label);
  const tokens = normalizeSearchText(query)
    .split(" ")
    .filter(
      (token) =>
        token.length >= 3 &&
        !["split", "croatia", "hrvatska", "grad", "ulica", "street"].includes(token),
    );
  return !tokens.length || tokens.some((token) => normalizedLabel.includes(token));
}

function normalizeSearchText(value) {
  return String(value)
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
}

function mergeSearchResults(localItems, googleItems) {
  const seen = new Set();
  const merged = [];
  for (const item of [...localItems, ...googleItems]) {
    const bbox = item.bbox || [];
    const key = `${item.type}:${String(item.label).toLowerCase()}:${bbox
      .map((value) => Number(value).toFixed(4))
      .join(",")}`;
    if (seen.has(key)) continue;
    seen.add(key);
    merged.push(item);
  }
  return merged.slice(0, SEARCH_RESULT_LIMIT);
}

function renderSearchResults(items) {
  const results = document.querySelector("#localSearchResults");
  const input = document.querySelector("#localSearchInput");
  if (!items.length) {
    renderSearchMessage("No Split dataset or Google Maps results");
    return;
  }
  results.replaceChildren(
    ...items.map((item, index) => {
      const row = document.createElement("button");
      row.type = "button";
      row.className = "search-result-row";
      row.id = `search-result-${index}`;
      row.dataset.index = String(index);
      row.setAttribute("role", "option");
      row.setAttribute("aria-selected", String(index === appState.selectedSearchIndex));
      row.innerHTML = `
        <span class="search-result-type">${escapeHtml(readableSearchType(item.type))}</span>
        <span class="search-result-main">
          <strong>${escapeHtml(item.label)}</strong>
          <span>${escapeHtml(item.subtitle)}</span>
        </span>
      `;
      row.addEventListener("mouseenter", () => {
        appState.selectedSearchIndex = index;
        syncSearchSelection();
      });
      row.addEventListener("click", () => selectSearchResult(item));
      return row;
    }),
  );
  results.hidden = false;
  input.setAttribute("aria-expanded", "true");
}

function renderSearchMessage(message) {
  const results = document.querySelector("#localSearchResults");
  const input = document.querySelector("#localSearchInput");
  const row = document.createElement("div");
  row.className = "search-message";
  row.textContent = message;
  results.replaceChildren(row);
  results.hidden = false;
  input.setAttribute("aria-expanded", "true");
}

function hideSearchResults() {
  const results = document.querySelector("#localSearchResults");
  const input = document.querySelector("#localSearchInput");
  results.hidden = true;
  input.setAttribute("aria-expanded", "false");
  appState.selectedSearchIndex = -1;
}

function moveSearchSelection(direction) {
  if (!appState.searchResults.length) return;
  appState.selectedSearchIndex =
    (appState.selectedSearchIndex + direction + appState.searchResults.length) %
    appState.searchResults.length;
  syncSearchSelection();
}

function syncSearchSelection() {
  for (const row of document.querySelectorAll(".search-result-row")) {
    row.setAttribute(
      "aria-selected",
      String(Number(row.dataset.index) === appState.selectedSearchIndex),
    );
  }
}

async function selectSearchResult(result) {
  if (!result) return;
  const input = document.querySelector("#localSearchInput");
  input.value = result.label;
  hideSearchResults();
  if (result.type === "building") {
    focusBbox(result.bbox, 900);
    const detail = await fetchJson(`/api/buildings/${result.building_id}`);
    renderInspector(detail);
  } else if (result.type === "parcel") {
    await selectParcelCase(result.parcel_id);
  } else if (result.type === "landuse_zone") {
    focusBbox(result.bbox, 1800);
  } else if (result.type === "google_maps") {
    focusBbox(result.bbox, 1200);
    renderGoogleMapsInspector(result);
  }
}

async function selectPriorityCase(priorityCase) {
  for (const row of document.querySelectorAll(".case-row")) {
    row.setAttribute("aria-pressed", String(row.dataset.buildingId === priorityCase.id));
  }
  await loadBuildings("priority");
  focusBbox(priorityCase.bbox, 900);
  const detail = await fetchJson(`/api/buildings/${priorityCase.id}`);
  renderInspector(detail);
}

async function selectParcelCase(parcelId) {
  const selected = appState.parcelQueue.find((item) => item.parcel_id === parcelId);
  if (!selected) return;
  for (const row of document.querySelectorAll(".case-row")) {
    row.setAttribute("aria-pressed", String(row.dataset.parcelId === parcelId));
  }
  await loadBuildings("priority");
  focusBbox(selected.bbox, 1800);
  renderParcelCase(selected);
}

async function loadBuildings(filter) {
  appState.filter = filter;
  const loadId = (appState.loadSequence += 1);
  resetInspector();
  setLayerLoading(true);
  try {
    const dataSource = await getOrCreateBuildingDataSource(filter);
    if (loadId !== appState.loadSequence) {
      dataSource.show = false;
      return;
    }
    if (appState.activeDataSource) {
      appState.activeDataSource.show = false;
    }
    dataSource.show = true;
    appState.activeDataSource = dataSource;
    viewer.scene.requestRender();
  } finally {
    if (loadId === appState.loadSequence) {
      setLayerLoading(false);
    }
  }
}

async function getOrCreateBuildingDataSource(filter) {
  const cached = appState.dataSources.get(filter);
  if (cached) {
    return cached;
  }

  const url =
    filter === "priority"
      ? "/api/buildings.geojson?view=priority"
      : `/api/buildings.geojson?discrepancy_type=${encodeURIComponent(filter)}`;
  const geojson = await fetchJson(url);
  const dataSource = buildBuildingDataSource(filter, geojson.features);
  dataSource.show = false;
  await viewer.dataSources.add(dataSource);
  appState.dataSources.set(filter, dataSource);
  return dataSource;
}

async function fetchJson(url) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Request failed: ${url}`);
  }
  return response.json();
}

function buildBuildingDataSource(filter, features) {
  const dataSource = new Cesium.CustomDataSource(`buildings-${filter}`);
  dataSource.entities.suspendEvents();
  try {
    for (const feature of features) {
      const discrepancyType = feature.properties.discrepancy_type;
      const polygons = polygonCoordinateSets(feature.geometry);
      polygons.forEach((coordinates, polygonIndex) => {
        const hierarchy = polygonHierarchy(coordinates);
        if (!hierarchy) return;
        const outlinePositions = positionsFromRing(coordinates[0]);
        dataSource.entities.add({
          id: `${feature.id}:${polygonIndex}`,
          name: readableDiscrepancy(discrepancyType),
          polygon: {
            hierarchy,
            material: colorByDiscrepancy[discrepancyType],
            classificationType: Cesium.ClassificationType.BOTH,
          },
          polyline: {
            positions: outlinePositions,
            clampToGround: true,
            width: 2,
            material: outlineByDiscrepancy[discrepancyType],
          },
          properties: {
            ...feature.properties,
            canonicalId: feature.id,
          },
        });
      });
    }
  } finally {
    dataSource.entities.resumeEvents();
  }
  return dataSource;
}

function focusPilotArea(bbox) {
  focusBbox(bbox, 12500);
}

function focusBbox(bbox, height) {
  const [minLon, minLat, maxLon, maxLat] = bbox;
  viewer.camera.setView({
    destination: Cesium.Cartesian3.fromDegrees(
      (minLon + maxLon) / 2,
      (minLat + maxLat) / 2,
      height,
    ),
    orientation: {
      heading: Cesium.Math.toRadians(8),
      pitch: Cesium.Math.toRadians(-84),
      roll: 0,
    },
  });
}

function bboxFromCesiumDestination(destination) {
  if (!destination) return null;
  if (
    Number.isFinite(destination.west) &&
    Number.isFinite(destination.south) &&
    Number.isFinite(destination.east) &&
    Number.isFinite(destination.north)
  ) {
    return [
      Cesium.Math.toDegrees(destination.west),
      Cesium.Math.toDegrees(destination.south),
      Cesium.Math.toDegrees(destination.east),
      Cesium.Math.toDegrees(destination.north),
    ];
  }
  if (
    Number.isFinite(destination.x) &&
    Number.isFinite(destination.y) &&
    Number.isFinite(destination.z)
  ) {
    const cartographic = Cesium.Cartographic.fromCartesian(destination);
    const longitude = Cesium.Math.toDegrees(cartographic.longitude);
    const latitude = Cesium.Math.toDegrees(cartographic.latitude);
    const pad = 0.0012;
    return [longitude - pad, latitude - pad, longitude + pad, latitude + pad];
  }
  return null;
}

function bboxCenterInSplit(bbox) {
  const [minLon, minLat, maxLon, maxLat] = bbox;
  const [splitMinLon, splitMinLat, splitMaxLon, splitMaxLat] =
    appState.summary?.aoi?.bbox || DEFAULT_SPLIT_SEARCH_BBOX;
  const longitude = (minLon + maxLon) / 2;
  const latitude = (minLat + maxLat) / 2;
  return (
    longitude >= splitMinLon &&
    longitude <= splitMaxLon &&
    latitude >= splitMinLat &&
    latitude <= splitMaxLat
  );
}

function improveCesiumToolbarAccessibility() {
  const applyLabels = () => {
    const toolbar = document.querySelector(".cesium-viewer-toolbar");
    toolbar?.setAttribute("aria-label", "Map controls");
    setControlLabel(".cesium-navigation-help-button", "Map controls help");
  };
  applyLabels();
  window.setTimeout(applyLabels, 250);
}

function setControlLabel(selector, label) {
  const element = document.querySelector(selector);
  if (!element) return;
  element.setAttribute("aria-label", label);
  element.setAttribute("title", label);
}

function polygonCoordinateSets(geometry) {
  if (!geometry) return [];
  if (geometry.type === "Polygon") {
    return [geometry.coordinates];
  }
  if (geometry.type === "MultiPolygon") {
    return geometry.coordinates;
  }
  return [];
}

function polygonHierarchy(coordinates) {
  const [outer, ...holes] = coordinates;
  const outerPositions = positionsFromRing(outer);
  if (outerPositions.length < 3) {
    return null;
  }
  return new Cesium.PolygonHierarchy(
    outerPositions,
    holes
      .map((ring) => positionsFromRing(ring))
      .filter((positions) => positions.length >= 3)
      .map((positions) => new Cesium.PolygonHierarchy(positions)),
  );
}

function positionsFromRing(ring) {
  const cleaned = closedRingRemoved(ring).filter(
    ([longitude, latitude]) => Number.isFinite(longitude) && Number.isFinite(latitude),
  );
  return Cesium.Cartesian3.fromDegreesArray(
    cleaned.flatMap(([longitude, latitude]) => [longitude, latitude]),
  );
}

function closedRingRemoved(ring) {
  if (!ring || ring.length === 0) {
    return [];
  }
  const first = ring[0];
  const last = ring[ring.length - 1];
  if (first[0] === last[0] && first[1] === last[1]) {
    return ring.slice(0, -1);
  }
  return ring;
}

function renderMetrics(summary) {
  const values = document.querySelectorAll("#metrics .metric-value");
  values[0].textContent = formatCount(summary.total_buildings);
  values[1].textContent = formatCount(summary.priority_flag_count);
}

function renderSources(sources) {
  const list = document.querySelector("#sourceList");
  list.replaceChildren(
    ...sources.map((source) => {
      const item = document.createElement("li");
      item.innerHTML = `
        <strong>${escapeHtml(source.id)}</strong>
        <span>${formatCount(source.observation_count)} observations · ${source.file}</span>
      `;
      return item;
    }),
  );
}

function bindLegend() {
  for (const button of document.querySelectorAll(".legend-row")) {
    button.addEventListener("click", async () => {
      for (const row of document.querySelectorAll(".legend-row")) {
        row.setAttribute("aria-pressed", String(row === button));
      }
      await loadBuildings(button.dataset.filter);
    });
  }
}

function bindPicking() {
  const handler = new Cesium.ScreenSpaceEventHandler(viewer.scene.canvas);
  handler.setInputAction(async (movement) => {
    const picked = viewer.scene.pick(movement.position);
    const buildingId = pickedBuildingId(picked?.id);
    if (!buildingId) {
      return;
    }
    const detail = await fetchJson(`/api/buildings/${buildingId}`);
    renderInspector(detail);
  }, Cesium.ScreenSpaceEventType.LEFT_CLICK);
}

function pickedBuildingId(pickedId) {
  if (!Cesium.defined(pickedId)) {
    return null;
  }
  const canonicalId = pickedId.properties?.canonicalId?.getValue(Cesium.JulianDate.now());
  if (canonicalId) {
    return canonicalId;
  }
  if (typeof pickedId.id === "string") {
    return pickedId.id.split(":")[0];
  }
  return null;
}

function setLayerLoading(isLoading) {
  document.body.classList.toggle("is-loading-layer", isLoading);
  viewer.scene.canvas.style.cursor = isLoading ? "progress" : "";
}

function resetInspector() {
  const inspector = document.querySelector("#inspector");
  inspector.innerHTML = `
    <div class="empty-state">
      <h2>Select a building</h2>
      <p>Click a colored footprint to inspect linked source observations and match evidence.</p>
    </div>
  `;
  closeInspector();
}

function renderParcelCase(parcelCase) {
  const lookupSequence = nextAddressLookupSequence();
  const inspector = document.querySelector("#inspector");
  inspector.innerHTML = `
    <div class="inspector-header">
      ${inspectorCloseButton()}
      <div class="status-line">
        <span>${escapeHtml(readableRisk(parcelCase.risk_level))} parcel case</span>
        <span class="confidence">score ${formatCount(parcelCase.impact_score)}</span>
      </div>
      <h2>${escapeHtml(parcelCase.parcel_id)}</h2>
    </div>
    <div class="inspector-content">
      <div class="detail-grid">
        ${detailRow("Suggested next step", parcelCase.recommended_next_step)}
        ${detailRow("Land use", parcelCase.land_use)}
        ${detailRow("Priority buildings", String(parcelCase.priority_building_count))}
        ${detailRow("Flagged footprint", `${formatCount(parcelCase.total_flagged_area_m2)} m2`)}
        ${detailRow("Average confidence", `${Math.round(parcelCase.average_confidence * 100)}%`)}
        ${detailRow("Flags", parcelCase.flags.map(readableRisk).join(", ") || "None")}
      </div>
      <div class="observation-list">
        <h2>Case Evidence</h2>
        <div class="observation-row">
          <strong>Evidence summary</strong>
          <span>${escapeHtml(parcelCase.case_file.evidence_summary)}</span>
        </div>
        ${parcelCase.flagged_buildings.map(caseBuildingRow).join("")}
      </div>
    </div>
  `;
  openInspector();
  hydrateParcelCaseAddresses(parcelCase, lookupSequence);
}

function caseBuildingRow(building) {
  return `
    <div class="observation-row">
      <strong data-building-address-target="${escapeHtml(building.id)}">Looking up address...</strong>
      <span>${escapeHtml(readableDiscrepancy(building.discrepancy_type))} · ${formatCount(
        Math.round(building.area_m2 || 0),
      )} m2 · confidence ${Math.round((building.confidence || 0) * 100)}%</span>
      <span class="internal-id">Internal ID: ${escapeHtml(building.id)}</span>
      <span>${building.land_zone ? escapeHtml(building.land_zone) : "No land-zone label"}</span>
    </div>
  `;
}

function renderInspector(detail) {
  const lookupSequence = nextAddressLookupSequence();
  const inspector = document.querySelector("#inspector");
  inspector.innerHTML = `
    <div class="inspector-header">
      ${inspectorCloseButton()}
      <div class="status-line">
        <span>${escapeHtml(readableDiscrepancy(detail.discrepancy_type))}</span>
        <span class="confidence">${Math.round(detail.confidence * 100)}% confidence</span>
      </div>
      <h2 data-building-address-target="${escapeHtml(detail.id)}">Looking up address...</h2>
    </div>
    <div class="inspector-content">
      <div class="detail-grid">
        <div class="detail-row" data-building-address-row="${escapeHtml(detail.id)}">
          <strong>Address</strong>
          <span>Looking up nearest address...</span>
        </div>
        ${detailRow("Internal ID", detail.id)}
        ${detailRow("Registered", detail.is_registered ? "Yes" : "No")}
        ${detailRow("Area", detail.area ? `${formatCount(Math.round(detail.area))} m2` : "Unknown")}
        ${detail.land_zone ? detailRow("Land zone", detail.land_zone) : ""}
        ${detail.height ? detailRow("Height", `${detail.height} m`) : ""}
        ${detailRow("Linked observations", String(detail.match_summary.linked_observation_count))}
      </div>
      <div class="observation-list">
        <h2>Source Observations</h2>
        ${detail.source_observations.map(observationRow).join("")}
      </div>
    </div>
  `;
  openInspector();
  hydrateBuildingInspectorAddress(detail, lookupSequence);
}

async function hydrateParcelCaseAddresses(parcelCase, lookupSequence) {
  for (const building of parcelCase.flagged_buildings) {
    const address = await lookupBuildingAddress(building);
    if (lookupSequence !== appState.addressLookupSequence) return;
    updateBuildingAddressTargets(building.id, address?.label || "Address unavailable");
  }
}

async function hydrateBuildingInspectorAddress(detail, lookupSequence) {
  const address = await lookupBuildingAddress(detail);
  if (lookupSequence !== appState.addressLookupSequence) return;
  const label = address?.label || "Address unavailable";
  updateBuildingAddressTargets(detail.id, label);
  updateBuildingAddressRows(detail.id, label, address?.source);
}

function nextAddressLookupSequence() {
  appState.addressLookupSequence += 1;
  return appState.addressLookupSequence;
}

async function lookupBuildingAddress(building) {
  if (!Array.isArray(building.centroid) || building.centroid.length < 2) {
    return null;
  }
  const [lon, lat] = building.centroid;
  if (!Number.isFinite(lon) || !Number.isFinite(lat)) {
    return null;
  }
  const cacheKey = `${lat.toFixed(5)},${lon.toFixed(5)}`;
  if (appState.addressCache.has(cacheKey)) {
    return appState.addressCache.get(cacheKey);
  }
  try {
    const address = await fetchJson(
      `/api/addresses/reverse?lat=${encodeURIComponent(lat)}&lon=${encodeURIComponent(lon)}`,
    );
    appState.addressCache.set(cacheKey, address);
    return address;
  } catch (error) {
    console.log(`Address lookup unavailable for ${building.id}. ${error}`);
    appState.addressCache.set(cacheKey, null);
    return null;
  }
}

function updateBuildingAddressTargets(buildingId, label) {
  for (const element of document.querySelectorAll("[data-building-address-target]")) {
    if (element.dataset.buildingAddressTarget === buildingId) {
      element.textContent = label;
    }
  }
}

function updateBuildingAddressRows(buildingId, label, source) {
  for (const row of document.querySelectorAll("[data-building-address-row]")) {
    if (row.dataset.buildingAddressRow !== buildingId) continue;
    const value = source ? `${label} · ${source}` : label;
    row.querySelector("span").textContent = value;
  }
}

function renderGoogleMapsInspector(result) {
  const inspector = document.querySelector("#inspector");
  inspector.innerHTML = `
    <div class="inspector-header">
      ${inspectorCloseButton()}
      <div class="status-line">
        <span>Google Maps result</span>
        <span class="confidence">Split-bounded</span>
      </div>
      <h2>${escapeHtml(result.label)}</h2>
    </div>
    <div class="inspector-content">
      <div class="detail-grid">
        ${detailRow("Source", "Google Maps via Cesium ion geocoder")}
        ${detailRow("Result type", "Place, address, or monument")}
        ${detailRow("Search boundary", "Current Split dataset bounds")}
      </div>
    </div>
  `;
  openInspector();
}

function bindInspectorClose() {
  const inspector = document.querySelector("#inspector");
  inspector.addEventListener("click", (event) => {
    if (event.target.closest("[data-inspector-close]")) {
      closeInspector();
    }
  });
}

function openInspector() {
  const inspector = document.querySelector("#inspector");
  document.body.classList.add("inspector-open");
  inspector.setAttribute("aria-hidden", "false");
  viewer.scene.requestRender();
}

function closeInspector() {
  const inspector = document.querySelector("#inspector");
  document.body.classList.remove("inspector-open");
  inspector.setAttribute("aria-hidden", "true");
  nextAddressLookupSequence();
  viewer.scene.requestRender();
}

function inspectorCloseButton() {
  return `
    <button class="inspector-close" type="button" data-inspector-close aria-label="Close inspector" title="Close inspector">
      X
    </button>
  `;
}

function detailRow(label, value) {
  return `
    <div class="detail-row">
      <strong>${escapeHtml(label)}</strong>
      <span>${escapeHtml(value)}</span>
    </div>
  `;
}

function observationRow(observation) {
  const parcel = observation.properties.parcel_id
    ? ` · parcel ${observation.properties.parcel_id}`
    : "";
  return `
    <div class="observation-row">
      <strong>${escapeHtml(observation.source)}</strong>
      <span>${escapeHtml(observation.source_feature_id)} · ${escapeHtml(observation.snapshot_id)}</span>
      <span>match ${Math.round(observation.match_score * 100)}% · confidence ${Math.round(
        observation.confidence * 100,
      )}%${escapeHtml(parcel)}</span>
    </div>
  `;
}

function readableDiscrepancy(value) {
  return value
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function readableSearchType(value) {
  return {
    building: "Bldg",
    parcel: "Parcel",
    landuse_zone: "Zone",
    google_maps: "Google",
  }[value] || "Result";
}

function readableRisk(value) {
  return String(value)
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function formatRatio(value) {
  if (value === null || value === undefined) return "Not applicable";
  return `${value.toFixed(2)}x`;
}

function formatCount(value) {
  return new Intl.NumberFormat("en-US").format(value);
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
