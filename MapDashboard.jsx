// MapDashboard.jsx — Urbani Čuvar · Hackathon Split
// Zahtjevi: npm install react-leaflet leaflet

import { useRef, useState } from "react";
import {
  MapContainer,
  TileLayer,
  WMSTileLayer,
  LayersControl,
  useMap,
} from "react-leaflet";
import "leaflet/dist/leaflet.css";

const { BaseLayer, Overlay } = LayersControl;

// ─── Lažni alarmi za ilegalnu gradnju ────────────────────────────────────────
const ALARMI = [
  {
    id: 1,
    lokacija: "Žnjan — Plaža",
    opis: "Bespravna terasa 42 m² na zaštićenom obalnom pojasu",
    koordinate: [43.4978, 16.4901],
    ozbiljnost: "visoka",
    datum: "2024-05-12",
  },
  {
    id: 2,
    lokacija: "Mejaši — Ul. Bana Berislavića",
    opis: "Nadogradnja kata bez dozvole, ~80 m²",
    koordinate: [43.5201, 16.4312],
    ozbiljnost: "visoka",
    datum: "2024-05-08",
  },
  {
    id: 3,
    lokacija: "Sirobuja — Gornji dio",
    opis: "Nova pomoćna građevina izvan katastarske parcele",
    koordinate: [43.5312, 16.4089],
    ozbiljnost: "srednja",
    datum: "2024-05-15",
  },
  {
    id: 4,
    lokacija: "Kman — Industrijska zona",
    opis: "Proširenje skladišta bez građevinske dozvole",
    koordinate: [43.5398, 16.4201],
    ozbiljnost: "srednja",
    datum: "2024-05-10",
  },
  {
    id: 5,
    lokacija: "Trstenik — Obala",
    opis: "Ilegalni priključak na komunalnu infrastrukturu",
    koordinate: [43.5089, 16.4723],
    ozbiljnost: "niska",
    datum: "2024-05-14",
  },
  {
    id: 6,
    lokacija: "Brda — Stobreč",
    opis: "Betonski temelji bez ishođene dozvole",
    koordinate: [43.5021, 16.5289],
    ozbiljnost: "visoka",
    datum: "2024-05-11",
  },
];

// Boje prema razini ozbiljnosti
const BOJA_BADGE = {
  visoka: "bg-red-600 text-white",
  srednja: "bg-yellow-400 text-gray-900",
  niska: "bg-blue-500 text-white",
};

// ─── Interni hook: leti na koordinate u Leaflet mapi ─────────────────────────
function FlyToController({ cilj }) {
  const mapa = useMap();
  if (cilj) {
    mapa.flyTo(cilj, 17, { duration: 1.4 });
  }
  return null;
}

// ─── Glavna komponenta ────────────────────────────────────────────────────────
export default function MapDashboard() {
  const [aktivniAlarm, setAktivniAlarm] = useState(null);
  const [odabraniAlarmId, setOdabraniAlarmId] = useState(null);

  function handleKlikAlarm(alarm) {
    setOdabraniAlarmId(alarm.id);
    // Postavi cilj leta — FlyToController će reagirati
    setAktivniAlarm([...alarm.koordinate]);
  }

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-gray-950 font-sans">
      {/* ── Sidebar ── */}
      <aside className="w-80 flex-shrink-0 flex flex-col bg-gray-900 border-r border-gray-700 z-10 shadow-2xl">
        {/* Zaglavlje */}
        <div className="px-4 py-4 border-b border-gray-700 bg-gray-800">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-2xl">🏙️</span>
            <h1 className="text-lg font-bold text-white tracking-tight leading-tight">
              Urbani Čuvar
            </h1>
          </div>
          <p className="text-xs text-gray-400">
            Admin Dashboard · Grad Split
          </p>
          <div className="mt-2 flex gap-2">
            <span className="text-xs bg-red-900 text-red-300 px-2 py-0.5 rounded-full font-medium">
              ● {ALARMI.filter((a) => a.ozbiljnost === "visoka").length} Kritično
            </span>
            <span className="text-xs bg-yellow-900 text-yellow-300 px-2 py-0.5 rounded-full font-medium">
              ● {ALARMI.filter((a) => a.ozbiljnost === "srednja").length} Srednje
            </span>
          </div>
        </div>

        {/* Lista alarma */}
        <div className="flex-1 overflow-y-auto py-2">
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider px-4 py-2">
            Detektirani alarmi ({ALARMI.length})
          </p>
          {ALARMI.map((alarm) => (
            <button
              key={alarm.id}
              onClick={() => handleKlikAlarm(alarm)}
              className={`w-full text-left px-4 py-3 border-b border-gray-800 transition-all hover:bg-gray-700 focus:outline-none ${
                odabraniAlarmId === alarm.id
                  ? "bg-indigo-900 border-l-4 border-l-indigo-400"
                  : ""
              }`}
            >
              <div className="flex justify-between items-start mb-1">
                <span className="text-sm font-semibold text-white leading-tight">
                  {alarm.lokacija}
                </span>
                <span
                  className={`text-xs px-1.5 py-0.5 rounded font-bold ml-2 flex-shrink-0 ${
                    BOJA_BADGE[alarm.ozbiljnost]
                  }`}
                >
                  {alarm.ozbiljnost.toUpperCase()}
                </span>
              </div>
              <p className="text-xs text-gray-400 leading-snug">{alarm.opis}</p>
              <p className="text-xs text-gray-600 mt-1">📅 {alarm.datum}</p>
            </button>
          ))}
        </div>

        {/* Podnožje */}
        <div className="px-4 py-3 border-t border-gray-700 bg-gray-800">
          <p className="text-xs text-gray-500 text-center">
            Podaci: DGU Geoportal · WMS 1.3.0
          </p>
        </div>
      </aside>

      {/* ── Mapa ── */}
      <div className="flex-1 relative">
        <MapContainer
          center={[43.5081, 16.4521]}
          zoom={13}
          className="h-full w-full"
          zoomControl={true}
        >
          {/* FlyTo kontroler — leti na alarm kad se promijeni cilj */}
          <FlyToController cilj={aktivniAlarm} />

          <LayersControl position="topright">
            {/* ── Bazni sloj: Google Satelit ── */}
            <BaseLayer checked name="🛰️ Google Satelit">
              <TileLayer
                url="https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}"
                attribution="&copy; Google"
                maxZoom={20}
              />
            </BaseLayer>

            {/* ── Bazni sloj: OSM (fallback) ── */}
            <BaseLayer name="🗺️ OpenStreetMap">
              <TileLayer
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                attribution='&copy; <a href="https://osm.org/copyright">OpenStreetMap</a>'
              />
            </BaseLayer>

            {/* ── Overlay: HOK — Hrvatska osnovna karta (DGU) ── */}
            <Overlay checked name="📐 Osnovna karta (HOK)">
              <WMSTileLayer
                url="https://geoportal.dgu.hr/services/geoportal/ows"
                layers="HOK"
                format="image/png"
                transparent={true}
                version="1.3.0"
                opacity={0.75}
                attribution="&copy; DGU Geoportal"
              />
            </Overlay>

            {/* ── Overlay: DOF — Digitalni ortofoto (DGU) ── */}
            <Overlay name="📷 Ortofoto (DOF)">
              <WMSTileLayer
                url="https://geoportal.dgu.hr/services/geoportal/ows"
                layers="DOF"
                format="image/png"
                transparent={true}
                version="1.3.0"
                opacity={0.85}
                attribution="&copy; DGU Geoportal"
              />
            </Overlay>
          </LayersControl>
        </MapContainer>

        {/* Overlay natpis na mapi — hackathon branding */}
        <div className="absolute bottom-6 right-4 z-[1000] bg-gray-900 bg-opacity-80 text-white text-xs px-3 py-2 rounded-xl shadow-lg pointer-events-none">
          🔍 Usporedba: Katastarski plan vs. Stvarno stanje
        </div>
      </div>
    </div>
  );
}
