# vizualizacija.py — nacrta MS building footprints na Google Satelit slici
# Crveno = potencijalna anomalija (nije u OSM), Zeleno = registrirana zgrada

import json, math, io, sys
sys.stdout.reconfigure(encoding='utf-8')
import requests
from PIL import Image, ImageDraw, ImageFont

BBOX = {
    "jug":    43.513,
    "zapad":  16.418,
    "sjever": 43.528,
    "istok":  16.442,
}
ZOOM = 16
TILE_PX = 256

def deg_u_tile(lat, lon, z):
    n = 2 ** z
    x = int((lon + 180) / 360 * n)
    lat_r = math.radians(lat)
    y = int((1 - math.log(math.tan(lat_r) + 1 / math.cos(lat_r)) / math.pi) / 2 * n)
    return x, y

def tile_u_deg(x, y, z):
    n = 2 ** z
    lon = x / n * 360 - 180
    lat_r = math.atan(math.sinh(math.pi * (1 - 2 * y / n)))
    return math.degrees(lat_r), lon

# ─── Preuzmi satelitske tile-ove ─────────────────────────────────────────────

x_min, y_max = deg_u_tile(BBOX["jug"],    BBOX["zapad"], ZOOM)
x_max, y_min = deg_u_tile(BBOX["sjever"], BBOX["istok"], ZOOM)
n_x = x_max - x_min + 1
n_y = y_max - y_min + 1

print(f"[→] Preuzimam {n_x}×{n_y} Google tile-ova (zoom {ZOOM})...")
headers = {"User-Agent": "Mozilla/5.0"}
mozaik = Image.new("RGB", (n_x * TILE_PX, n_y * TILE_PX))

for ix, tx in enumerate(range(x_min, x_max + 1)):
    for iy, ty in enumerate(range(y_min, y_max + 1)):
        url = f"https://mt1.google.com/vt/lyrs=s&x={tx}&y={ty}&z={ZOOM}"
        try:
            r = requests.get(url, headers=headers, timeout=15)
            r.raise_for_status()
            tile = Image.open(io.BytesIO(r.content)).convert("RGB")
            mozaik.paste(tile, (ix * TILE_PX, iy * TILE_PX))
        except Exception as e:
            print(f"  [!] Tile ({tx},{ty}): {e}")

# Obreži mozaik točno na BBOX
lat_sj_moz, lon_zp_moz = tile_u_deg(x_min,     y_min,     ZOOM)
lat_jg_moz, lon_is_moz = tile_u_deg(x_max + 1, y_max + 1, ZOOM)
moz_w, moz_h = mozaik.size

def geo_u_px_moz(lat, lon):
    px = (lon - lon_zp_moz) / (lon_is_moz - lon_zp_moz) * moz_w
    py = (lat_sj_moz - lat) / (lat_sj_moz - lat_jg_moz) * moz_h
    return int(px), int(py)

lx, ty_ = geo_u_px_moz(BBOX["sjever"], BBOX["zapad"])
rx, by  = geo_u_px_moz(BBOX["jug"],    BBOX["istok"])
satelit = mozaik.crop((lx, ty_, rx, by))
IMG_W, IMG_H = satelit.size
print(f"[✓] Satelitska slika: {IMG_W}×{IMG_H}px")

# ─── Projekcija geo → pixel za obrezanu sliku ─────────────────────────────────

def geo_u_px(lat, lon):
    px = (lon - BBOX["zapad"]) / (BBOX["istok"]  - BBOX["zapad"]) * IMG_W
    py = (BBOX["sjever"] - lat) / (BBOX["sjever"] - BBOX["jug"])   * IMG_H
    return int(px), int(py)

# ─── Učitaj MS footprinte ─────────────────────────────────────────────────────

try:
    with open("public/ms_footprints.json", encoding="utf-8") as f:
        ms_data = json.load(f)
    ms_feats = ms_data.get("features", [])
    print(f"[✓] {len(ms_feats)} MS footprinta")
except FileNotFoundError:
    print("[!] public/ms_footprints.json ne postoji — pokreni: npm run podatci")
    ms_feats = []

try:
    with open("public/katastrar.json", encoding="utf-8") as f:
        kat_data = json.load(f)
    kat_feats = kat_data.get("features", [])
    print(f"[✓] {len(kat_feats)} OSM zgrada")
except FileNotFoundError:
    kat_feats = []

# ─── Crtanje ─────────────────────────────────────────────────────────────────

# Sloj za transparentne boje (RGBA)
overlay = Image.new("RGBA", (IMG_W, IMG_H), (0, 0, 0, 0))
draw = ImageDraw.Draw(overlay)

def crtaj_poligon(draw, coords, boja_fill, boja_rub):
    pikseli = [geo_u_px(lat, lon) for lon, lat in coords]
    if len(pikseli) < 3:
        return
    draw.polygon(pikseli, fill=boja_fill, outline=boja_rub)

# Nacrtaj OSM zgrade (plavo, tanko) — referentni sloj
for feat in kat_feats:
    geom = feat.get("geometry", {})
    if geom.get("type") == "Polygon":
        coords = geom["coordinates"][0]
        crtaj_poligon(draw, coords, (0, 120, 255, 50), (0, 120, 255, 200))

# Nacrtaj MS footprinte — crveno = anomalija, zeleno = registrirana
anomalije = 0
registrirane = 0
for feat in ms_feats:
    geom = feat.get("geometry", {})
    status = feat.get("properties", {}).get("status", "anomalija")
    if status == "anomalija":
        fill = (255, 40, 40, 120)
        rub  = (255, 0, 0, 255)
        anomalije += 1
    else:
        fill = (40, 220, 40, 100)
        rub  = (0, 200, 0, 230)
        registrirane += 1

    if geom.get("type") == "Polygon":
        coords = geom["coordinates"][0]
        crtaj_poligon(draw, coords, fill, rub)

print(f"[i] Nacrtano: {anomalije} anomalija (crveno), {registrirane} registriranih (zeleno), {len(kat_feats)} OSM (plavo)")

# Spoji slojeve
satelit_rgba = satelit.convert("RGBA")
rezultat = Image.alpha_composite(satelit_rgba, overlay).convert("RGB")

# Legenda
draw2 = ImageDraw.Draw(rezultat)
legenda = [
    ((255, 40, 40),   f"Neregistrirane zgrade: {anomalije}"),
    ((40, 200, 40),   f"Registrirane zgrade: {registrirane}"),
    ((0, 120, 255),   f"OSM baza: {len(kat_feats)}"),
]
x0, y0 = 12, 12
draw2.rectangle([x0-4, y0-4, x0+300, y0 + len(legenda)*22 + 4], fill=(10, 10, 10, 200))
for i, (boja, tekst) in enumerate(legenda):
    y = y0 + i * 22
    draw2.rectangle([x0, y+3, x0+14, y+16], fill=boja)
    draw2.text((x0+20, y), tekst, fill=(255, 255, 255))

izlaz = "public/vizualizacija.png"
rezultat.save(izlaz, quality=92)
print(f"[✓] Spremljeno → {izlaz}")
print(f"[i] Otvori: http://localhost:5173/vizualizacija.png")
