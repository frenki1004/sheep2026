from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_frontend_uses_cesium_native_building_layers():
    index_html = (PROJECT_ROOT / "frontend" / "index.html").read_text()
    app_js = (PROJECT_ROOT / "frontend" / "app.js").read_text()

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
    assert "heightReference" not in app_js
    assert "extrudedHeight" not in app_js
    assert "clampToGround: true" in app_js
    assert "resetInspector();" in app_js
    assert "improveCesiumToolbarAccessibility();" in app_js
    assert "aria-label" in app_js
    assert 'id="caseQueue"' in index_html
    assert 'fetchJson("/api/parcels/queue")' in app_js
    assert "selectParcelCase" in app_js
    assert "const visibleItems = activeCases.length ? activeCases : items;" in app_js
    assert "quiet-case-summary" in app_js
    assert "Priority Parcels" in index_html
    assert "priority /" in app_js
    assert "flagged structures" in app_js
    assert "Impact" in app_js
    assert "parcels have no current flags" in app_js


def test_frontend_keeps_cesium_toolbar_clear_of_side_panels():
    styles_css = (PROJECT_ROOT / "frontend" / "styles.css").read_text()

    assert ".cesium-viewer-toolbar" in styles_css
    assert "toolbar-safe-left" in styles_css
    assert "toolbar-safe-right" in styles_css
    assert "html {\n  overflow: hidden;" in styles_css
    assert "min-width: 48px" in styles_css
    assert "min-height: 48px" in styles_css
    assert ".case-queue" in styles_css
    assert ".case-row" in styles_css
    assert ".quiet-case-summary" in styles_css
    assert "max-height: min(42vh, 420px)" in styles_css


def test_local_token_config_is_loaded_but_gitignored():
    index_html = (PROJECT_ROOT / "frontend" / "index.html").read_text()
    gitignore = (PROJECT_ROOT / ".gitignore").read_text()

    assert 'src="/assets/ion-token.local.js"' in index_html
    assert "frontend/ion-token.local.js" in gitignore
