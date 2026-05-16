# dohvati_katastrar.py — dohvaća OSM zgrade za Mejaše (referentni sloj za spatial join)

import json, sys
sys.stdout.reconfigure(encoding='utf-8')
import requests

BBOX = {
    "jug":    43.513,
    "zapad":  16.418,
    "sjever": 43.528,
    "istok":  16.442,
}

HEADERS = {"User-Agent": "UrbanCuvar/1.0"}

print("=== OSM Overpass — zgrade Mejaši ===")

# Dohvati sve zgrade iz OSM-a za BBOX
query = f"""
[out:json][timeout:60];
(
  way["building"]({BBOX['jug']},{BBOX['zapad']},{BBOX['sjever']},{BBOX['istok']});
  relation["building"]({BBOX['jug']},{BBOX['zapad']},{BBOX['sjever']},{BBOX['istok']});
);
out body; >; out skel qt;
"""

print("[→] Dohvaćam zgrade iz OpenStreetMap...")
try:
    r = requests.post(
        "https://overpass-api.de/api/interpreter",
        data={"data": query},
        headers=HEADERS,
        timeout=60,
    )
    r.raise_for_status()
    osm = r.json()
    nodes = {e["id"]: e for e in osm["elements"] if e["type"] == "node"}
    features = []
    for el in osm["elements"]:
        if el["type"] == "way" and "nodes" in el:
            coords = [[nodes[n]["lon"], nodes[n]["lat"]]
                      for n in el["nodes"] if n in nodes]
            if len(coords) < 3:
                continue
            tags = el.get("tags", {})
            features.append({
                "type": "Feature",
                "properties": {
                    "id": el["id"],
                    "source": "OSM",
                    **tags,
                },
                "geometry": {"type": "Polygon", "coordinates": [coords]},
            })
    geojson = {"type": "FeatureCollection", "features": features}
    print(f"[✓] OSM: {len(features)} zgrada")
except Exception as e:
    print(f"[!] OSM greška: {e}")
    geojson = {"type": "FeatureCollection", "features": []}

with open("public/katastrar.json", "w", encoding="utf-8") as f:
    json.dump(geojson, f, ensure_ascii=False)

n = len(geojson.get("features", []))
print(f"[✓] Spremljeno {n} featura → public/katastrar.json")
