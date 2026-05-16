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

const searchParams = new URLSearchParams(window.location.search);
const hashParams = new URLSearchParams(window.location.hash.slice(1));
Cesium.Ion.defaultAccessToken =
  searchParams.get("ionToken") || hashParams.get("ionToken") || window.CESIUM_ION_TOKEN || "";

const viewer = new Cesium.Viewer("cesiumContainer", {
  timeline: false,
  animation: false,
  sceneModePicker: false,
  baseLayerPicker: false,
  geocoder: Cesium.IonGeocodeProviderType.GOOGLE,
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
  dataSources: new Map(),
  filter: "priority",
  loadSequence: 0,
  parcelQueue: [],
  summary: null,
};

window.__splitOntologyViewer = viewer;
window.__splitOntologyState = appState;

await initialize();

async function initialize() {
  const [summary, sourcePayload, parcelQueuePayload] = await Promise.all([
    fetchJson("/api/summary"),
    fetchJson("/api/sources"),
    fetchJson("/api/parcels/queue"),
  ]);
  appState.summary = summary;
  appState.parcelQueue = parcelQueuePayload.items;
  renderSources(sourcePayload.sources);
  renderMetrics(summary);
  renderParcelQueue(parcelQueuePayload.items);
  focusPilotArea(summary.aoi.bbox);
  bindHomeButtonToPilotArea(summary.aoi.bbox);
  await loadBuildings("priority");
  bindLegend();
  bindPicking();
}

function renderParcelQueue(items) {
  const queue = document.querySelector("#caseQueue");
  const count = document.querySelector("#caseQueueCount");
  const activeCases = items.filter((item) => item.priority_building_count > 0);
  const quietCaseCount = items.length - activeCases.length;
  const visibleItems = activeCases.length ? activeCases : items;
  count.textContent = `${formatCount(activeCases.length)} priority / ${formatCount(items.length)} total`;
  queue.replaceChildren(
    ...visibleItems.map((item) => {
      const row = document.createElement("button");
      const flaggedStructureLabel =
        item.priority_building_count === 1 ? "flagged structure" : "flagged structures";
      row.className = `case-row ${item.risk_level}`;
      row.type = "button";
      row.dataset.parcelId = item.parcel_id;
      row.setAttribute("aria-pressed", "false");
      row.innerHTML = `
        <span class="case-row-main">
          <strong>${escapeHtml(item.parcel_id)}</strong>
          <span>${escapeHtml(readableRisk(item.risk_level))} priority · ${formatCount(
            item.total_flagged_area_m2,
          )} m2 flagged · ${formatCount(item.priority_building_count)} ${flaggedStructureLabel}</span>
        </span>
        <span class="case-score">
          <span>Impact</span>
          <strong>${formatCount(item.impact_score)}</strong>
        </span>
      `;
      row.addEventListener("click", () => selectParcelCase(item.parcel_id));
      return row;
    }),
  );
  if (activeCases.length && quietCaseCount) {
    const summary = document.createElement("div");
    summary.className = "quiet-case-summary";
    summary.textContent = `${formatCount(quietCaseCount)} parcels have no current flags`;
    queue.appendChild(summary);
  }
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

function bindHomeButtonToPilotArea(bbox) {
  viewer.homeButton.viewModel.command.beforeExecute.addEventListener((commandInfo) => {
    commandInfo.cancel = true;
    focusPilotArea(bbox);
  });
}

function improveCesiumToolbarAccessibility() {
  const applyLabels = () => {
    const toolbar = document.querySelector(".cesium-viewer-toolbar");
    toolbar?.setAttribute("aria-label", "Map controls");
    setControlLabel(".cesium-geocoder-searchButton", "Search location");
    setControlLabel(".cesium-home-button", "Return to Split overview");
    setControlLabel(".cesium-navigation-help-button", "Map controls help");
    const searchInput = document.querySelector(".cesium-geocoder-input");
    searchInput?.setAttribute("aria-label", "Search location");
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
}

function renderParcelCase(parcelCase) {
  const inspector = document.querySelector("#inspector");
  inspector.innerHTML = `
    <div class="inspector-header">
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
}

function caseBuildingRow(building) {
  return `
    <div class="observation-row">
      <strong>${escapeHtml(building.id)}</strong>
      <span>${escapeHtml(readableDiscrepancy(building.discrepancy_type))} · ${formatCount(
        Math.round(building.area_m2 || 0),
      )} m2 · confidence ${Math.round((building.confidence || 0) * 100)}%</span>
      <span>${building.land_zone ? escapeHtml(building.land_zone) : "No land-zone label"}</span>
    </div>
  `;
}

function renderInspector(detail) {
  const inspector = document.querySelector("#inspector");
  inspector.innerHTML = `
    <div class="inspector-header">
      <div class="status-line">
        <span>${escapeHtml(readableDiscrepancy(detail.discrepancy_type))}</span>
        <span class="confidence">${Math.round(detail.confidence * 100)}% confidence</span>
      </div>
      <h2>${escapeHtml(detail.id)}</h2>
    </div>
    <div class="inspector-content">
      <div class="detail-grid">
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
