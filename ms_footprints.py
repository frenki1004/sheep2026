# ms_footprints.py — Urbani Čuvar
# Preuzima Microsoft AI Building Footprints za Mejaše
# Uspoređuje s katastarskim česticama → pronalazi potencijalno ilegalne zgrade
# Sprema rezultat u public/ za React frontend

import gzip, io, csv, json, sys
sys.stdout.reconfigure(encoding='utf-8')
import requests
import pandas as pd
from shapely.geometry import shape, box, mapping
from shapely.ops import unary_union

# ─── Konfiguracija ────────────────────────────────────────────────────────────

BBOX = {
    "jug":    43.513,
    "zapad":  16.418,
    "sjever": 43.528,
    "istok":  16.442,
}

# Shapely objekt za BBOX — za brzu provjeru intersects
BBOX_SHAPE = box(BBOX["zapad"], BBOX["jug"], BBOX["istok"], BBOX["sjever"])

# ─── Korak 1: Dohvati listu svih Microsoft dataset datoteka ──────────────────

print("=== Microsoft Global Building Footprints ===\n")
print("[→] Dohvaćam listu dataset datoteka...")

LINKS_URL = "https://minedbuildings.z5.web.core.windows.net/global-buildings/dataset-links.csv"
try:
    r = requests.get(LINKS_URL, timeout=30)
    r.raise_for_status()
except Exception as e:
    print(f"[!] Ne mogu dohvatiti dataset links: {e}")
    sys.exit(1)

df = pd.read_csv(io.StringIO(r.text))
print(f"[i] Ukupno datoteka u datasetu: {len(df)}")

# Filtriraj na Croatia
croatia_df = df[df["Location"].str.contains("Croatia", case=False, na=False)]
print(f"[i] Croatia datoteke: {len(croatia_df)}")

if croatia_df.empty:
    # Pokušaj bez filtera lokacije — potraži po URL-u
    croatia_df = df[df["Url"].str.contains("Croatia", case=False, na=False)]
    print(f"[i] Croatia po URL-u: {len(croatia_df)}")

if croatia_df.empty:
    print(f"[!] Nema Croatia datoteka. Dostupne lokacije (prvih 20):")
    print(df["Location"].unique()[:20])
    empty = {"type": "FeatureCollection", "features": [], "statistike": {"ukupno_ms": 0, "registrirane": 0, "anomalije": 0, "bbox": BBOX}}
    with open("public/ms_footprints.json", "w", encoding="utf-8") as f:
        json.dump({"type": "FeatureCollection", "features": []}, f)
    with open("public/anomalije.json", "w", encoding="utf-8") as f:
        json.dump(empty, f)
    sys.exit(0)

# ─── Korak 2: Preuzmi i filtriraj footprints za BBOX ─────────────────────────

print(f"\n[→] Preuzimam {len(croatia_df)} datoteka za Hrvatsku...")
print("[i] Filtriram na BBOX Mejaša...")

ms_footprints = []

for idx, row in croatia_df.iterrows():
    url = row["Url"]
    print(f"  [{idx+1}/{len(croatia_df)}] {url.split('/')[-1]}...")

    try:
        r = requests.get(url, timeout=120, stream=True)
        r.raise_for_status()

        # Datoteke su gzip komprimirani CSV ili line-delimited JSON
        sadrzaj = b""
        for chunk in r.iter_content(chunk_size=1024*1024):
            sadrzaj += chunk

        with gzip.open(io.BytesIO(sadrzaj), "rt", encoding="utf-8") as f:
            prva = f.readline().strip()
            f.seek(0)

            if prva.startswith("{"):
                # Line-delimited GeoJSON (.geojsonl)
                for linija in f:
                    linija = linija.strip()
                    if not linija:
                        continue
                    try:
                        feat = json.loads(linija)
                        geom = shape(feat["geometry"])
                        if geom.intersects(BBOX_SHAPE):
                            feat.setdefault("properties", {})
                            feat["properties"]["source"] = "Microsoft"
                            ms_footprints.append(feat)
                    except Exception:
                        continue
            else:
                # CSV format s WKT geometry stupcem
                from shapely import wkt as shapely_wkt
                reader = csv.DictReader(f)
                for red in reader:
                    try:
                        geom = shapely_wkt.loads(red["geometry"])
                        if geom.intersects(BBOX_SHAPE):
                            ms_footprints.append({
                                "type": "Feature",
                                "geometry": mapping(geom),
                                "properties": {
                                    "confidence": float(red.get("confidence", 0)),
                                    "source": "Microsoft",
                                },
                            })
                    except Exception:
                        continue

    except Exception as e:
        print(f"  [!] Greška: {e}")
        continue

print(f"\n[✓] Microsoft footprints u BBOX-u: {len(ms_footprints)}")

if len(ms_footprints) == 0:
    print("[!] Nema footprints u BBOX-u — spremi prazne datoteke i nastavi")
    empty = {"type": "FeatureCollection", "features": [], "statistike": {"ukupno_ms": 0, "registrirane": 0, "anomalije": 0, "bbox": BBOX}}
    with open("public/ms_footprints.json", "w", encoding="utf-8") as f:
        json.dump({"type": "FeatureCollection", "features": []}, f)
    with open("public/anomalije.json", "w", encoding="utf-8") as f:
        json.dump(empty, f)
    sys.exit(0)

# Spremi Microsoft footprints za prikaz na mapi
with open("public/ms_footprints.json", "w", encoding="utf-8") as f:
    json.dump({"type": "FeatureCollection", "features": ms_footprints}, f)
print("[✓] public/ms_footprints.json")

# ─── Korak 3: Učitaj katastarske čestice ─────────────────────────────────────

print("\n[→] Učitavam katastarske čestice...")
try:
    with open("public/katastrar.json", encoding="utf-8") as f:
        katastrar = json.load(f)
    katastrar_geoms = [shape(feat["geometry"]) for feat in katastrar.get("features", [])
                       if feat.get("geometry")]
    print(f"[✓] {len(katastrar_geoms)} katastarskih objekata")
except FileNotFoundError:
    print("[!] public/katastrar.json ne postoji — pokreni python dohvati_katastrar.py")
    katastrar_geoms = []

# ─── Korak 4: Spatial join — pronađi zgrade bez katastarske čestice ──────────

print("\n[→] Uspoređujem Microsoft footprints s katastarskim česticama...")

# Spoji sve katastarske geometrije u jedan objekt za brže provjere
if katastrar_geoms:
    katastrar_union = unary_union(katastrar_geoms)
else:
    katastrar_union = None

anomalije = []
registrirane = []

for feat in ms_footprints:
    geom = shape(feat["geometry"])

    if katastrar_union is None:
        # Nema katastarskih podataka — sve su potencijalne anomalije
        anomalije.append(feat)
        continue

    # Provjeri preklapa li se Microsoft footprint s katastarskom česticom
    # Koristimo threshold od 30% — ako je manje od 30% pokriveno = anomalija
    try:
        presjek = geom.intersection(katastrar_union).area
        pokrivenost = presjek / geom.area if geom.area > 0 else 0
    except Exception:
        pokrivenost = 0

    if pokrivenost < 0.30:
        # Zgrada nije (dovoljno) pokrivena katastarskom česticom → potencijalna anomalija
        feat["properties"]["pokrivenost_pct"] = round(pokrivenost * 100, 1)
        feat["properties"]["status"] = "anomalija"
        anomalije.append(feat)
    else:
        feat["properties"]["pokrivenost_pct"] = round(pokrivenost * 100, 1)
        feat["properties"]["status"] = "registrirana"
        registrirane.append(feat)

print(f"[✓] Registrirane zgrade:        {len(registrirane)}")
print(f"[✓] Potencijalne anomalije:     {len(anomalije)}")

# ─── Korak 5: Spremi rezultate ────────────────────────────────────────────────

# Sve zgrade (za prikaz na mapi)
sve = {"type": "FeatureCollection", "features": ms_footprints}
with open("public/ms_footprints.json", "w", encoding="utf-8") as f:
    json.dump(sve, f, ensure_ascii=False)

# Samo anomalije (za sidebar)
anom_geojson = {
    "type": "FeatureCollection",
    "features": anomalije,
    "statistike": {
        "ukupno_ms": len(ms_footprints),
        "registrirane": len(registrirane),
        "anomalije": len(anomalije),
        "bbox": BBOX,
    }
}
with open("public/anomalije.json", "w", encoding="utf-8") as f:
    json.dump(anom_geojson, f, ensure_ascii=False)

print(f"\n[✓] public/ms_footprints.json — sve zgrade")
print(f"[✓] public/anomalije.json     — samo anomalije ({len(anomalije)})")
print(f"\n[i] Refreshaj http://localhost:5173")
