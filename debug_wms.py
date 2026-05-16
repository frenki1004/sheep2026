# debug_wms.py — pronalazi točne nazive layera na DGU serveru
import requests
import xml.etree.ElementTree as ET

# Pravi endpoint (iz GetCapabilities odgovora)
WMS_URL = "https://geoportal.dgu.hr/services/geoportal/ows"

print("=== Dohvaćam listu svih dostupnih layera... ===\n")

r = requests.get(WMS_URL, params={
    "SERVICE": "WMS",
    "REQUEST": "GetCapabilities",
    "VERSION": "1.3.0"
}, timeout=20)

# Parsiraj XML i izvuci sve <Name> tagove unutar <Layer>
ns = {"wms": "http://www.opengis.net/wms"}
root = ET.fromstring(r.content)

layeri = root.findall(".//wms:Layer/wms:Name", ns)
print(f"Pronađeno {len(layeri)} layera:\n")
for layer in layeri:
    print(f"  → {layer.text}")

print("\n=== Test GetMap s novim endpointom ===")
params = {
    "SERVICE": "WMS",
    "REQUEST": "GetMap",
    "VERSION": "1.3.0",
    "LAYERS": layeri[0].text if layeri else "DKP",
    "CRS": "EPSG:4326",
    "BBOX": "43.490,16.480,43.510,16.510",
    "WIDTH": "256",
    "HEIGHT": "256",
    "FORMAT": "image/png",
    "TRANSPARENT": "TRUE",
    "STYLES": "",
}
r2 = requests.get(WMS_URL, params=params, timeout=20)
print(f"Status: {r2.status_code} | Content-Type: {r2.headers.get('Content-Type')}")
if "xml" in r2.headers.get("Content-Type", ""):
    print(f"Greška: {r2.text[:500]}")
else:
    with open("test_layer.png", "wb") as f:
        f.write(r2.content)
    print(f"Slika spremljena ({len(r2.content)} bajtova) → test_layer.png")
