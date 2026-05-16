# analiza_anomalija.py — Urbani Čuvar
# Uspoređuje HOK (DGU službena karta) vs Google Satelit
# Detektira razlike → GPS koordinate → sprema JSON za frontend

import json, sys, math, io
import requests
import numpy as np
import cv2
from PIL import Image

# ─── Konfiguracija ────────────────────────────────────────────────────────────

WMS_URL = "https://geoportal.dgu.hr/services/geoportal/ows"

# Mejaši, Split
BBOX = {
    "jug":    43.513,
    "zapad":  16.418,
    "sjever": 43.528,
    "istok":  16.442,
}

ZOOM        = 17       # zoom razina za Google tile-ove (17 = ~1m/px)
IMG_W       = 1024     # dimenzije izlazne slike
IMG_H       = 1024
MIN_POVRSINA_PX = 200  # minimalna veličina konture

# ─── Pomoćne funkcije: tile koordinate ───────────────────────────────────────

def deg_u_tile(lat, lon, z):
    """Pretvori GPS koordinate u tile x,y za dani zoom."""
    n = 2 ** z
    x = int((lon + 180) / 360 * n)
    lat_r = math.radians(lat)
    y = int((1 - math.log(math.tan(lat_r) + 1 / math.cos(lat_r)) / math.pi) / 2 * n)
    return x, y

def tile_u_deg(x, y, z):
    """Pretvori tile koordinate u GPS (gornji lijevi kut tile-a)."""
    n = 2 ** z
    lon = x / n * 360 - 180
    lat_r = math.atan(math.sinh(math.pi * (1 - 2 * y / n)))
    lat = math.degrees(lat_r)
    return lat, lon

# ─── Preuzimanje Google Satelit tile-ova i spajanje ──────────────────────────

def preuzmi_google_satelit(bbox, zoom):
    """Preuzme Google tile-ove za BBOX, spoji ih i obreže na točan BBOX."""
    headers = {"User-Agent": "Mozilla/5.0"}

    x_min, y_max = deg_u_tile(bbox["jug"],    bbox["zapad"], zoom)
    x_max, y_min = deg_u_tile(bbox["sjever"], bbox["istok"], zoom)

    # Provjeri broj tile-ova (ne preuzimamo previše)
    n_x = x_max - x_min + 1
    n_y = y_max - y_min + 1
    print(f"[i] Google tile-ovi: {n_x} × {n_y} = {n_x*n_y} kom (zoom {zoom})")

    if n_x * n_y > 100:
        print("[!] Previše tile-ova — smanji zoom ili BBOX"); sys.exit(1)

    tile_px = 256  # svaki tile je 256×256 px
    mozaik = Image.new("RGB", (n_x * tile_px, n_y * tile_px))

    for ix, tx in enumerate(range(x_min, x_max + 1)):
        for iy, ty in enumerate(range(y_min, y_max + 1)):
            url = f"https://mt1.google.com/vt/lyrs=s&x={tx}&y={ty}&z={zoom}"
            try:
                r = requests.get(url, headers=headers, timeout=10)
                r.raise_for_status()
                tile_img = Image.open(io.BytesIO(r.content)).convert("RGB")
                mozaik.paste(tile_img, (ix * tile_px, iy * tile_px))
            except Exception as e:
                print(f"  [!] Tile ({tx},{ty}) greška: {e}")

    # Koordinate cijelog mozaika
    lat_sjever_moz, lon_zapad_moz = tile_u_deg(x_min,     y_min,     zoom)
    lat_jug_moz,    lon_istok_moz = tile_u_deg(x_max + 1, y_max + 1, zoom)

    moz_w, moz_h = mozaik.size

    # Obreži mozaik na točni BBOX
    def geo_u_px(lat, lon):
        px = (lon - lon_zapad_moz) / (lon_istok_moz - lon_zapad_moz) * moz_w
        py = (lat_sjever_moz - lat) / (lat_sjever_moz - lat_jug_moz) * moz_h
        return int(px), int(py)

    lx, ty_ = geo_u_px(bbox["sjever"], bbox["zapad"])
    rx, by  = geo_u_px(bbox["jug"],    bbox["istok"])
    obrezan = mozaik.crop((lx, ty_, rx, by))

    # Skaliranje na IMG_W × IMG_H
    obrezan = obrezan.resize((IMG_W, IMG_H), Image.LANCZOS)
    slika_cv = cv2.cvtColor(np.array(obrezan), cv2.COLOR_RGB2BGR)
    cv2.imwrite("google_satelit.png", slika_cv)
    print("[✓] Google Satelit preuzet i spojen → google_satelit.png")
    return slika_cv

# ─── Preuzimanje HOK s DGU WMS-a ─────────────────────────────────────────────

def preuzmi_hok(bbox):
    bbox_str = f"{bbox['jug']},{bbox['zapad']},{bbox['sjever']},{bbox['istok']}"
    params = {
        "SERVICE":"WMS","REQUEST":"GetMap","VERSION":"1.3.0",
        "CRS":"EPSG:4326","BBOX":bbox_str,
        "WIDTH":str(IMG_W),"HEIGHT":str(IMG_H),
        "LAYERS":"HOK","FORMAT":"image/png",
        "TRANSPARENT":"TRUE","STYLES":"",
    }
    print("[↓] Preuzimam HOK s DGU Geoportala...")
    r = requests.get(WMS_URL, params=params, timeout=30)
    r.raise_for_status()
    if "xml" in r.headers.get("Content-Type","").lower():
        print(f"[!] WMS greška: {r.text[:300]}"); sys.exit(1)
    slika = cv2.imdecode(np.frombuffer(r.content, np.uint8), cv2.IMREAD_COLOR)
    cv2.imwrite("hok_sirovi.png", slika)
    print("[✓] HOK preuzet → hok_sirovi.png")
    return slika

# ─── Piksel → GPS ─────────────────────────────────────────────────────────────

def piksel_u_gps(px, py, bbox):
    lon = bbox["zapad"] + (px / IMG_W) * (bbox["istok"] - bbox["zapad"])
    lat = bbox["sjever"] - (py / IMG_H) * (bbox["sjever"] - bbox["jug"])
    return round(lat, 6), round(lon, 6)

# ─── Analiza ──────────────────────────────────────────────────────────────────

slika_sat = preuzmi_google_satelit(BBOX, ZOOM)
slika_hok = preuzmi_hok(BBOX)

print("\n[→] Uspoređujem Google Satelit vs HOK...")

def rubovi(slika):
    siva = cv2.cvtColor(slika, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(siva, (5, 5), 0)
    return cv2.Canny(blur, 30, 100)

rubovi_sat = rubovi(slika_sat)
rubovi_hok = rubovi(slika_hok)

# Razlika: što postoji na satelitu a nema na HOK karti
razlika = cv2.absdiff(rubovi_sat, rubovi_hok)
_, maska = cv2.threshold(razlika, 25, 255, cv2.THRESH_BINARY)

kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (4, 4))
maska = cv2.dilate(maska, kernel, iterations=2)
maska = cv2.morphologyEx(maska, cv2.MORPH_CLOSE, kernel, iterations=2)

konture, _ = cv2.findContours(maska, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
konture = [k for k in konture if cv2.contourArea(k) > MIN_POVRSINA_PX]
print(f"[✓] Pronađeno {len(konture)} anomalija")

# GPS koordinate + procjena površine
m_lat = (BBOX["sjever"] - BBOX["jug"]) * 111000 / IMG_H
m_lon = (BBOX["istok"]  - BBOX["zapad"]) * 71000  / IMG_W

anomalije = []
for i, k in enumerate(konture):
    x, y, w, h = cv2.boundingRect(k)
    cx, cy = x + w // 2, y + h // 2
    lat, lon = piksel_u_gps(cx, cy, BBOX)
    povrsina = int(w * m_lon * h * m_lat)
    ozbiljnost = "visoka" if povrsina > 200 else ("srednja" if povrsina > 80 else "niska")
    anomalije.append({"id":i+1,"lat":lat,"lon":lon,"povrsina_m2":povrsina,"ozbiljnost":ozbiljnost,"bbox_px":[x,y,x+w,y+h]})
    print(f"  #{i+1}: ({lat}, {lon}) | {povrsina} m² | {ozbiljnost}")

# Spremi JSON
with open("public/anomalije.json","w",encoding="utf-8") as f:
    json.dump({"bbox":BBOX,"anomalije":anomalije}, f, ensure_ascii=False, indent=2)
print("[✓] public/anomalije.json ažuriran")

# Vizualizacija
izlaz = slika_sat.copy()
for a in anomalije:
    x1,y1,x2,y2 = a["bbox_px"]
    boja = {"visoka":(0,0,255),"srednja":(0,165,255),"niska":(255,165,0)}[a["ozbiljnost"]]
    cv2.rectangle(izlaz,(x1,y1),(x2,y2),boja,2)
    cv2.putText(izlaz,f"#{a['id']} {a['povrsina_m2']}m2",(x1+2,y1+14),cv2.FONT_HERSHEY_SIMPLEX,0.42,boja,1,cv2.LINE_AA)

cv2.rectangle(izlaz,(0,0),(500,28),(15,15,15),-1)
cv2.putText(izlaz,f"URBANI CUVAR | Satelit vs HOK | {len(anomalije)} anomalija",(6,18),cv2.FONT_HERSHEY_SIMPLEX,0.52,(0,255,100),1,cv2.LINE_AA)
cv2.imwrite("public/anomalija_izlaz.png", izlaz)
print("[✓] public/anomalija_izlaz.png ažuriran")
print(f"\n[i] Refreshaj http://localhost:5173")
