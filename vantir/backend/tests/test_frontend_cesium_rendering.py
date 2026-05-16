from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_frontend_uses_cesium_native_building_layers():
    index_html = (PROJECT_ROOT / "frontend" / "index.html").read_text()
    app_js = (PROJECT_ROOT / "frontend" / "app.js").read_text()

    assert "<title>Vantir Technologies</title>" in index_html
    assert "<h1>Vantir Technologies</h1>" in index_html
    assert 'href="/assets/vantir-favicon.jpeg' in index_html
    assert 'type="image/jpeg"' in index_html
    assert 'src="/assets/vantir-logo.jpeg"' not in index_html
    assert 'class="brand-logo"' not in index_html
    assert (PROJECT_ROOT / "frontend" / "vantir-favicon.jpeg").exists()
    assert "Split Ontology" not in index_html
    assert "Split Building Ontology MVP" not in index_html
    assert "Local v3 dataset" in index_html
    assert "Local v2 dataset" not in index_html
    assert 'src="/assets/ion-token.local.js"' in index_html
    assert 'id="buildingOverlay"' not in index_html
    assert "querySelector(\"#buildingOverlay\")" not in app_js
    assert "projectToScreen" not in app_js
    assert "new Cesium.CustomDataSource" in app_js
    assert "ClassificationType.BOTH" in app_js
    assert "selectionIndicator: false" in app_js
    assert "infoBox: false" in app_js
    assert "homeButton: false" in app_js
    assert "geocoder: false" in app_js
    assert "bindHomeButtonToPilotArea" not in app_js
    assert ".cesium-home-button" not in app_js
    assert "/api/search" in app_js
    assert "Search Split buildings, parcels, zones, places" in index_html
    assert "Enter an address" not in index_html
    assert "Enter an address" not in app_js
    assert "IonGeocoderService" in app_js
    assert "IonGeocodeProviderType?.GOOGLE" in app_js
    assert "google_maps" in app_js
    assert "googleResultMatchesQuery" in app_js
    assert "normalizeSearchText" in app_js
    assert "Searching Split and Google Maps" in app_js
    assert "No Split dataset or Google Maps results" in app_js
    assert "/api/addresses/reverse" in app_js
    assert "Looking up address" in app_js
    assert "Internal ID" in app_js
    assert "heightReference" not in app_js
    assert "extrudedHeight" not in app_js
    assert "clampToGround: true" in app_js
    assert "resetInspector();" in app_js
    assert "bindInspectorClose();" in app_js
    assert "inspector-open" in app_js
    assert "data-inspector-close" in app_js
    assert 'aria-hidden="true"' in index_html
    assert "improveCesiumToolbarAccessibility();" in app_js
    assert "aria-label" in app_js
    assert 'id="caseQueue"' in index_html
    assert "parcelSampleQueue" not in index_html
    assert 'fetchJson("/api/priority-cases")' in app_js
    assert 'fetchJson("/api/parcels/queue")' in app_js
    assert "selectParcelCase" in app_js
    assert "Flagged parcels in sample" not in app_js
    assert "quiet-case-summary" not in app_js
    assert "Priority Cases" in index_html
    assert "Priority Parcels" not in index_html
    assert "building flags" in app_js
    assert "Parcel sample" in app_js
    assert "priority /" not in app_js
    assert "priority-case-row" in app_js
    assert "Impact" in app_js
    assert "Load more" in app_js


def test_frontend_keeps_cesium_toolbar_clear_of_side_panels():
    styles_css = (PROJECT_ROOT / "frontend" / "styles.css").read_text()

    assert ".cesium-viewer-toolbar" in styles_css
    assert ".brand-logo-frame" not in styles_css
    assert ".brand-logo" not in styles_css
    assert ".local-search" in styles_css
    assert ".search-results" in styles_css
    assert "toolbar-safe-left" in styles_css
    assert "toolbar-safe-right" in styles_css
    assert "html {\n  overflow: hidden;" in styles_css
    assert "min-width: 48px" in styles_css
    assert "min-height: 48px" in styles_css
    assert ".case-queue" in styles_css
    assert "body.inspector-open" in styles_css
    assert ".inspector-close" in styles_css
    assert ".case-row" in styles_css
    assert ".priority-case-row" in styles_css
    assert "min-height: 104px" in styles_css
    assert ".parcel-sample-queue" not in styles_css
    assert ".quiet-case-summary" not in styles_css
    assert "max-height: min(42vh, 420px)" in styles_css


def test_local_token_config_is_loaded_but_gitignored():
    index_html = (PROJECT_ROOT / "frontend" / "index.html").read_text()
    gitignore = (PROJECT_ROOT / ".gitignore").read_text()

    assert 'src="/assets/ion-token.local.js"' in index_html
    assert "frontend/ion-token.local.js" in gitignore
