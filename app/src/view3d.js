import * as Cesium from "cesium";
import "cesium/Build/Cesium/Widgets/widgets.css";

let viewer = null;

const colorByStatus = {
  matched: Cesium.Color.fromCssColorString("#64c864").withAlpha(0.58),
  unregistered: Cesium.Color.fromCssColorString("#dc3232").withAlpha(0.68),
  illegal_protected: Cesium.Color.fromCssColorString("#8b0000").withAlpha(0.75),
  katastarOnly: Cesium.Color.fromCssColorString("#ffa500").withAlpha(0.62),
};

const outlineByStatus = {
  matched: Cesium.Color.fromCssColorString("#c8ffd5"),
  unregistered: Cesium.Color.fromCssColorString("#ffd0d0"),
  illegal_protected: Cesium.Color.fromCssColorString("#ff9999"),
  katastarOnly: Cesium.Color.fromCssColorString("#ffe0a0"),
};

export async function init3D(container) {
  Cesium.Ion.defaultAccessToken = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJqdGkiOiI4MzBmYzI3My1hYjY4LTQ2M2EtOGJlMC05NmVjY2M5MzMxNWMiLCJpZCI6NDMyMzc5LCJzdWIiOiJNYXJ0aW5WcmJvdmNhbiIsImlzcyI6Imh0dHBzOi8vaW9uLmNlc2l1bS5jb20iLCJhdWQiOiJTaGVlcEFJIiwiaWF0IjoxNzc4OTUwOTg2fQ.UvKEfn5zoMIagOAxBu1SefvAt6iHwoRTi-nBgFK8qMY";

  viewer = new Cesium.Viewer(container, {
    terrain: Cesium.Terrain.fromWorldTerrain(),
    sceneMode: Cesium.SceneMode.SCENE3D,
    baseLayerPicker: false,
    geocoder: true,
    homeButton: false,
    sceneModePicker: false,
    navigationHelpButton: true,
    animation: false,
    timeline: false,
    fullscreenButton: false,
    selectionIndicator: false,
    infoBox: false,
  });

  viewer.scene.globe.depthTestAgainstTerrain = true;
  viewer.useBrowserRecommendedResolution = false;
  viewer.resolutionScale = window.devicePixelRatio || 1;

  const controller = viewer.scene.screenSpaceCameraController;
  // Pan: left drag
  controller.rotateEventTypes = [Cesium.CameraEventType.LEFT_DRAG];
  // Zoom: right drag, scroll wheel
  controller.zoomEventTypes = [
    Cesium.CameraEventType.RIGHT_DRAG,
    Cesium.CameraEventType.WHEEL,
    Cesium.CameraEventType.PINCH,
  ];
  // Rotate: middle drag, Ctrl+left drag, Ctrl+right drag
  controller.tiltEventTypes = [
    Cesium.CameraEventType.MIDDLE_DRAG,
    { eventType: Cesium.CameraEventType.LEFT_DRAG, modifier: Cesium.KeyboardEventModifier.CTRL },
    { eventType: Cesium.CameraEventType.RIGHT_DRAG, modifier: Cesium.KeyboardEventModifier.CTRL },
  ];

  viewer.resize();

  // Google Photorealistic 3D Tiles
  try {
    const tileset = await Cesium.createGooglePhotorealistic3DTileset({
      onlyUsingWithGoogleGeocoder: true,
    });
    tileset.maximumScreenSpaceError = 12;
    tileset.dynamicScreenSpaceError = true;
    viewer.scene.primitives.add(tileset);
  } catch (e) {
    console.warn("Google 3D tiles failed, falling back to satellite", e);
    viewer.imageryLayers.addImageryProvider(
      await Cesium.ArcGisMapServerImageryProvider.fromUrl(
        "https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer"
      )
    );
  }

  // Fly to Split
  viewer.camera.setView({
    destination: Cesium.Cartesian3.fromDegrees(16.44, 43.495, 2000),
    orientation: {
      heading: Cesium.Math.toRadians(340),
      pitch: Cesium.Math.toRadians(-30),
      roll: 0,
    },
  });

  // Load only problem buildings visible in camera view
  const resp = await fetch("/data/buildings.geojson");
  const data = await resp.json();

  const problemFeatures = data.features.filter(f => f.properties.status !== "matched");

  // Precompute centroids for fast bbox checks
  const featureCentroids = problemFeatures.map(f => {
    const ring = f.geometry.type === "MultiPolygon"
      ? f.geometry.coordinates[0][0]
      : f.geometry.coordinates[0];
    let cx = 0, cy = 0;
    for (const [x, y] of ring) { cx += x; cy += y; }
    return [cx / ring.length, cy / ring.length];
  });

  const dataSource = new Cesium.CustomDataSource("buildings");
  viewer.dataSources.add(dataSource);

  let loadedIds = new Set();
  let debounceTimer = null;

  function loadVisibleBuildings() {
    const rect = viewer.camera.computeViewRectangle();
    if (!rect) return;

    const west = Cesium.Math.toDegrees(rect.west);
    const east = Cesium.Math.toDegrees(rect.east);
    const south = Cesium.Math.toDegrees(rect.south);
    const north = Cesium.Math.toDegrees(rect.north);

    let added = 0;
    for (let i = 0; i < problemFeatures.length; i++) {
      if (loadedIds.has(i)) continue;
      const [lon, lat] = featureCentroids[i];
      if (lon < west || lon > east || lat < south || lat > north) continue;

      const f = problemFeatures[i];
      const status = f.properties.status;
      const fillColor = colorByStatus[status];
      const outlineColor = outlineByStatus[status];
      if (!fillColor) continue;

      const rings = f.geometry.type === "MultiPolygon"
        ? f.geometry.coordinates[0]
        : f.geometry.coordinates;

      const outerRing = rings[0];
      const positions = Cesium.Cartesian3.fromDegreesArray(outerRing.flat());

      const holes = rings.slice(1).map(hole =>
        new Cesium.PolygonHierarchy(Cesium.Cartesian3.fromDegreesArray(hole.flat()))
      );

      dataSource.entities.add({
        polygon: {
          hierarchy: new Cesium.PolygonHierarchy(positions, holes),
          material: fillColor,
          classificationType: Cesium.ClassificationType.BOTH,
        },
        polyline: {
          positions: positions,
          clampToGround: true,
          width: 2,
          material: outlineColor,
        },
        properties: f.properties,
      });

      loadedIds.add(i);
      added++;
      if (added >= 500) break;
    }
  }

  // Load initial view
  loadVisibleBuildings();

  // Reload when camera moves
  viewer.camera.changed.addEventListener(() => {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(loadVisibleBuildings, 300);
  });
  viewer.camera.percentageChanged = 0.1;

  return viewer;
}

export function destroy3D() {
  if (viewer) {
    viewer.destroy();
    viewer = null;
  }
}
