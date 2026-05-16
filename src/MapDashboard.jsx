// MapDashboard.jsx — Urbani Čuvar
// Microsoft Building Footprints vs. Katastarske čestice
// Crveno = potencijalno ilegalno, Zeleno = registrirano, Plavo = katastarska čestica

import { useState, useEffect, useRef, useCallback } from "react";
import {
  MapContainer, TileLayer, WMSTileLayer, GeoJSON,
  CircleMarker, Popup, Tooltip, useMap, useMapEvents,
} from "react-leaflet";
import "leaflet/dist/leaflet.css";

// ─── Sinkronizacija mapa ──────────────────────────────────────────────────────
function MapSync({ druga }) {
  const ova = useMap();
  useEffect(() => {
    if (!druga) return;
    const sync = () => druga.setView(ova.getCenter(), ova.getZoom(), { animate: false });
    ova.on("move", sync);
    return () => ova.off("move", sync);
  }, [ova, druga]);
  return null;
}

function KlikHandler({ aktivan, onKlik }) {
  useMapEvents({ click(e) { if (aktivan) onKlik(e.latlng); } });
  return null;
}

function FlyTo({ cilj }) {
  const mapa = useMap();
  const prev = useRef(null);
  useEffect(() => {
    if (!cilj) return;
    if (!prev.current || prev.current[0] !== cilj[0] || prev.current[1] !== cilj[1]) {
      mapa.flyTo(cilj, 18, { duration: 1.2 });
      prev.current = cilj;
    }
  }, [cilj, mapa]);
  return null;
}

// ─── Stilovi ─────────────────────────────────────────────────────────────────
const S = {
  wrapper:    { display:"flex", height:"100vh", width:"100vw", overflow:"hidden", fontFamily:"system-ui,sans-serif", backgroundColor:"#030712" },
  sidebar:    { width:280, flexShrink:0, display:"flex", flexDirection:"column", backgroundColor:"#111827", borderRight:"1px solid #374151", zIndex:10, boxShadow:"4px 0 20px rgba(0,0,0,.5)" },
  header:     { padding:14, borderBottom:"1px solid #374151", backgroundColor:"#1f2937" },
  h1:         { color:"#fff", fontSize:16, fontWeight:700, margin:0 },
  subtitle:   { color:"#9ca3af", fontSize:11, margin:"2px 0 0" },
  statRow:    { display:"flex", gap:6, marginTop:8, flexWrap:"wrap" },
  stat: (bg, c) => ({ fontSize:11, fontWeight:700, backgroundColor:bg, color:c, padding:"3px 8px", borderRadius:6 }),
  list:       { flex:1, overflowY:"auto" },
  listLabel:  { fontSize:10, fontWeight:700, color:"#6b7280", textTransform:"uppercase", letterSpacing:".08em", padding:"10px 14px 4px" },
  btn: (a)=>  ({ width:"100%", textAlign:"left", padding:"10px 14px", borderBottom:"1px solid #1f2937", borderLeft: a?"4px solid #ef4444":"4px solid transparent", backgroundColor: a?"#1c0a0a":"transparent", cursor:"pointer", display:"block" }),
  footer:     { padding:"8px 14px", borderTop:"1px solid #374151", backgroundColor:"#1f2937", textAlign:"center", color:"#6b7280", fontSize:10 },
  mapWrap:    { flex:1, position:"relative", overflow:"hidden" },
  prijavaBtn: (a) => ({ width:"100%", padding:"8px", borderRadius:8, border:"none", cursor:"pointer", fontWeight:700, fontSize:12, backgroundColor: a?"#ef4444":"#4f46e5", color:"#fff" }),
  label: (side) => ({
    position:"absolute", top:10, zIndex:1000, pointerEvents:"none",
    backgroundColor: side==="left" ? "rgba(5,46,22,0.9)" : "rgba(23,37,84,0.9)",
    color:"#fff", fontSize:12, fontWeight:700, padding:"4px 10px", borderRadius:6,
    ...(side==="left" ? { left:10 } : { right:10 }),
  }),
  divider:    { position:"absolute", top:0, bottom:0, width:4, backgroundColor:"#fff", zIndex:999, cursor:"ew-resize", boxShadow:"0 0 8px rgba(0,0,0,.5)" },
  dividerBtn: { position:"absolute", top:"50%", left:"50%", transform:"translate(-50%,-50%)", width:32, height:32, borderRadius:"50%", backgroundColor:"#fff", display:"flex", alignItems:"center", justifyContent:"center", fontSize:16, boxShadow:"0 2px 8px rgba(0,0,0,.4)", userSelect:"none" },
  legenda:    { position:"absolute", bottom:20, left:14, zIndex:1000, backgroundColor:"rgba(17,24,39,.93)", color:"#fff", fontSize:11, padding:"10px 14px", borderRadius:10, pointerEvents:"none", lineHeight:1.9 },
  legendaRed: { display:"flex", alignItems:"center", gap:8 },
  box: (c, fill) => ({ width:14, height:10, border:`2px solid ${c}`, backgroundColor: fill, flexShrink:0, borderRadius:2 }),
};

// ─── Stilovi za GeoJSON slojeve ───────────────────────────────────────────────
const stilMS = (feat) => {
  const status = feat?.properties?.status;
  if (status === "anomalija")
    return { color:"#ef4444", weight:2, fillColor:"#ef4444", fillOpacity:0.25 };
  return { color:"#22c55e", weight:1.5, fillColor:"#22c55e", fillOpacity:0.15 };
};
const stilKatastrar = { color:"#60a5fa", weight:1.5, fillColor:"#60a5fa", fillOpacity:0.06, dashArray:"4" };

// ─── Glavna komponenta ────────────────────────────────────────────────────────
export default function MapDashboard() {
  const [katastrar, setKatastrar]       = useState(null);
  const [msFootprints, setMsFootprints] = useState(null);
  const [anomalije, setAnomalije]       = useState(null);
  const [statistike, setStatistike]     = useState(null);
  const [greska, setGreska]             = useState(null);
  const [ucitava, setUcitava]           = useState(true);
  const [odabraniId, setOdabraniId]     = useState(null);
  const [cilj, setCilj]                 = useState(null);
  const [prijavaMod, setPrijavaMod]     = useState(false);
  const [prijave, setPrijave]           = useState([]);
  const [swipe, setSwipe]               = useState(50);
  const vuceSe                          = useRef(false);
  const mapWrapRef                      = useRef(null);
  const [mapaHOK, setMapaHOK]           = useState(null);
  const [mapaSat, setMapaSat]           = useState(null);

  useEffect(() => {
    Promise.all([
      fetch("/katastrar.json").then(r => r.ok ? r.json() : null).catch(() => null),
      fetch("/ms_footprints.json").then(r => r.ok ? r.json() : null).catch(() => null),
      fetch("/anomalije.json").then(r => {
        if (!r.ok) throw new Error("Pokreni: python ms_footprints.py");
        return r.json();
      }),
    ]).then(([kat, ms, anom]) => {
      setKatastrar(kat);
      setMsFootprints(ms);
      setAnomalije({ type:"FeatureCollection", features: anom.features });
      setStatistike(anom.statistike);
      setUcitava(false);
    }).catch((e) => {
      setGreska(e.message);
      setUcitava(false);
    });
  }, []);

  // Swipe drag
  const onMouseMove = useCallback((e) => {
    if (!vuceSe.current || !mapWrapRef.current) return;
    const rect = mapWrapRef.current.getBoundingClientRect();
    setSwipe(Math.min(Math.max((e.clientX - rect.left) / rect.width * 100, 5), 95));
  }, []);
  const onMouseUp = () => { vuceSe.current = false; };
  useEffect(() => {
    window.addEventListener("mousemove", onMouseMove);
    window.addEventListener("mouseup", onMouseUp);
    return () => { window.removeEventListener("mousemove", onMouseMove); window.removeEventListener("mouseup", onMouseUp); };
  }, [onMouseMove]);

  function handleKlikMapa(latlng) {
    const opis = prompt("Opiši anomaliju:");
    if (!opis) return;
    setPrijave(p => [{ id:Date.now(), lat:latlng.lat, lon:latlng.lng, opis, datum:new Date().toLocaleDateString("hr-HR") }, ...p]);
    setCilj([latlng.lat, latlng.lng]);
    setPrijavaMod(false);
  }

  const zajednickiProps = {
    center: [43.520, 16.430], zoom: 15,
    zoomControl: false, attributionControl: false,
    style: { height:"100%", width:"100%", position:"absolute", top:0, left:0 },
  };

  // GeoJSON key za re-render kad se podaci promijene
  const geoKey = msFootprints ? "loaded" : "empty";

  return (
    <div style={S.wrapper}>
      {/* ── Sidebar ── */}
      <aside style={S.sidebar}>
        <div style={S.header}>
          <div style={{ display:"flex", alignItems:"center", gap:8 }}>
            <span style={{ fontSize:20 }}>🏙️</span>
            <div>
              <h1 style={S.h1}>Urbani Čuvar</h1>
              <p style={S.subtitle}>Mejaši · Split</p>
            </div>
          </div>

          {statistike && (
            <div style={S.statRow}>
              <span style={S.stat("#052e16","#86efac")}>✓ {statistike.registrirane} reg.</span>
              <span style={S.stat("#450a0a","#fca5a5")}>⚠ {statistike.anomalije} anomalija</span>
              <span style={S.stat("#172554","#93c5fd")}>∑ {statistike.ukupno_ms} zgrada</span>
            </div>
          )}

          {ucitava && <p style={{ color:"#9ca3af", fontSize:11, marginTop:8 }}>⏳ Učitavam...</p>}
          {greska && (
            <div style={{ marginTop:8, backgroundColor:"#1c0a0a", borderRadius:6, padding:"6px 8px" }}>
              <p style={{ color:"#f87171", fontSize:11, margin:0 }}>⚠️ {greska}</p>
            </div>
          )}
        </div>

        {/* Prijava */}
        <div style={{ padding:"10px 14px" }}>
          <button style={S.prijavaBtn(prijavaMod)} onClick={() => setPrijavaMod(v => !v)}>
            {prijavaMod ? "✕ Odustani" : "⚑ Prijavi anomaliju ručno"}
          </button>
          {prijavaMod && <p style={{ color:"#f59e0b", fontSize:11, textAlign:"center", margin:"6px 0 0" }}>Klikni na lokaciju na mapi →</p>}
        </div>

        {/* Automatski detektirane anomalije */}
        <div style={S.list}>
          <p style={S.listLabel}>
            Automatski detektirano ({anomalije?.features?.length ?? 0})
          </p>

          {anomalije?.features?.map((feat, i) => {
            const coords = feat.geometry?.coordinates?.[0]?.[0] ?? [0, 0];
            const lat = coords[1], lon = coords[0];
            const id = feat.properties?.id ?? i;
            const pokr = feat.properties?.pokrivenost_pct ?? 0;
            return (
              <button key={id} style={S.btn(odabraniId === id)}
                onClick={() => { setOdabraniId(id); setCilj([lat, lon]); }}
                onMouseEnter={e => { if(odabraniId!==id) e.currentTarget.style.backgroundColor="#1f0a0a"; }}
                onMouseLeave={e => { if(odabraniId!==id) e.currentTarget.style.backgroundColor="transparent"; }}
              >
                <div style={{ display:"flex", justifyContent:"space-between", marginBottom:2 }}>
                  <span style={{ color:"#f87171", fontSize:12, fontWeight:700 }}>⚠ Zgrada #{i+1}</span>
                  <span style={{ color:"#6b7280", fontSize:10 }}>{pokr}% pokrivena</span>
                </div>
                <p style={{ color:"#9ca3af", fontSize:11, margin:0 }}>
                  Microsoft AI detektirao zgradu bez katastarske čestice
                </p>
                <p style={{ color:"#4b5563", fontSize:10, margin:"3px 0 0" }}>
                  {lat.toFixed(5)}, {lon.toFixed(5)}
                </p>
              </button>
            );
          })}

          {/* Ručne prijave */}
          {prijave.length > 0 && (
            <>
              <p style={S.listLabel}>Ručne prijave ({prijave.length})</p>
              {prijave.map(p => (
                <button key={p.id} style={S.btn(odabraniId===p.id)}
                  onClick={() => { setOdabraniId(p.id); setCilj([p.lat, p.lon]); }}
                  onMouseEnter={e => { if(odabraniId!==p.id) e.currentTarget.style.backgroundColor="#1f2937"; }}
                  onMouseLeave={e => { if(odabraniId!==p.id) e.currentTarget.style.backgroundColor="transparent"; }}
                >
                  <span style={{ color:"#fbbf24", fontSize:12, fontWeight:700 }}>✎ {p.opis}</span>
                  <p style={{ color:"#6b7280", fontSize:10, margin:"2px 0 0" }}>{p.datum}</p>
                </button>
              ))}
            </>
          )}
        </div>

        <div style={S.footer}>Microsoft AI Footprints · DGU WFS · OSM</div>
      </aside>

      {/* ── Mapa: swipe ── */}
      <div ref={mapWrapRef} style={S.mapWrap}>
        <div style={S.label("left")}>◀ HOK (evidentirano)</div>
        <div style={S.label("right")}>Satelit (stvarnost) ▶</div>

        {/* Lijeva mapa: HOK */}
        <div style={{ position:"absolute", inset:0, clipPath:`inset(0 ${100-swipe}% 0 0)`, zIndex:1 }}>
          <MapContainer {...zajednickiProps} ref={setMapaHOK}>
            {mapaHOK && mapaSat && <MapSync druga={mapaSat} />}
            <FlyTo cilj={cilj} />
            <KlikHandler aktivan={prijavaMod} onKlik={handleKlikMapa} />
            <WMSTileLayer url="https://geoportal.dgu.hr/services/geoportal/ows"
              layers="HOK" format="image/png" transparent={false} version="1.3.0" />
            {katastrar && <GeoJSON key="kat-l" data={katastrar} style={() => stilKatastrar} />}
            {msFootprints && <GeoJSON key={`ms-l-${geoKey}`} data={msFootprints} style={stilMS}
              onEachFeature={(feat, layer) => {
                const s = feat.properties?.status;
                layer.bindTooltip(s === "anomalija" ? "⚠️ Nije u katastru" : "✓ Registrirano", { sticky:true });
              }} />}
            {prijave.map(p => (
              <CircleMarker key={p.id} center={[p.lat,p.lon]} radius={8}
                pathOptions={{ color:"#fff", weight:2, fillColor:"#f59e0b", fillOpacity:0.95 }}>
                <Popup><strong>{p.opis}</strong></Popup>
              </CircleMarker>
            ))}
          </MapContainer>
        </div>

        {/* Desna mapa: Google Satelit */}
        <div style={{ position:"absolute", inset:0, clipPath:`inset(0 0 0 ${swipe}%)`, zIndex:1 }}>
          <MapContainer {...zajednickiProps} ref={setMapaSat}>
            {mapaHOK && mapaSat && <MapSync druga={mapaHOK} />}
            <TileLayer url="https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}" maxZoom={20} />
            {katastrar && <GeoJSON key="kat-r" data={katastrar} style={() => stilKatastrar} />}
            {msFootprints && <GeoJSON key={`ms-r-${geoKey}`} data={msFootprints} style={stilMS}
              onEachFeature={(feat, layer) => {
                const s = feat.properties?.status;
                layer.bindTooltip(s === "anomalija" ? "⚠️ Nije u katastru" : "✓ Registrirano", { sticky:true });
              }} />}
            {prijave.map(p => (
              <CircleMarker key={p.id} center={[p.lat,p.lon]} radius={8}
                pathOptions={{ color:"#fff", weight:2, fillColor:"#f59e0b", fillOpacity:0.95 }}>
                <Popup><strong>{p.opis}</strong></Popup>
              </CircleMarker>
            ))}
          </MapContainer>
        </div>

        {/* Divider */}
        <div style={{ ...S.divider, left:`calc(${swipe}% - 2px)` }} onMouseDown={() => { vuceSe.current = true; }}>
          <div style={S.dividerBtn}>⇔</div>
        </div>

        {/* Legenda */}
        <div style={S.legenda}>
          <div style={S.legendaRed}><span style={S.box("#ef4444","rgba(239,68,68,0.25)")} /> Potencijalno ilegalno (MS AI)</div>
          <div style={S.legendaRed}><span style={S.box("#22c55e","rgba(34,197,94,0.15)")} /> Registrirano u katastru</div>
          <div style={S.legendaRed}><span style={S.box("#60a5fa","rgba(96,165,250,0.06)")} style2={{ borderStyle:"dashed" }} /> Katastarska čestica</div>
          <div style={S.legendaRed}><span style={{ width:10, height:10, borderRadius:"50%", backgroundColor:"#f59e0b", flexShrink:0 }} /> Ručna prijava</div>
        </div>
      </div>
    </div>
  );
}
