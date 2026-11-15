import { useMemo, useState, type ReactNode } from "react";
import {
  Activity, Atom, Bell, BookOpen, ChevronRight, Compass, Database, Server,
  Globe2, Layers3, Map, Menu, Orbit, Search, Settings2, ShieldCheck,
  Sparkles, X, MapPin, RotateCcw, Mountain, Satellite, ExternalLink, Info
} from "lucide-react";
import AnalogMap from "./components/maps/AnalogMap";
import PlanetaryMap from "./components/maps/PlanetaryMap";
import { analogSites } from "./data/analogSites";
import { planetaryDataResources, planetaryLayers, type PlanetaryBody, type PlanetaryLayerKey } from "./data/planetaryLayers";
import SimilarityWorkspace from "./components/SimilarityWorkspace";
import DatasetWorkspace from "./components/DatasetWorkspace";
import AnalogComparisonWorkspace from "./components/AnalogComparisonWorkspace";
import BackendStatus from "./components/BackendStatus";
import EvidenceReviewWorkspace from "./components/EvidenceReviewWorkspace";
import ScientificReportsWorkspace from "./components/ScientificReportsWorkspace";
import MissionSuitabilityWorkspace from "./components/MissionSuitabilityWorkspace";
import MissionScenarioWorkspace from "./components/MissionScenarioWorkspace";
import MissionRiskWorkspace from "./components/MissionRiskWorkspace";
import LoginWorkspace from "./components/LoginWorkspace";
import AdminWorkspace from "./components/AdminWorkspace";
import { setApiAccessToken } from "./services/api";
import { useSessionLifecycle } from "./lib/session";
import { logout as revokeUserSession, type TerrascanUser } from "./lib/auth";

const navigation = [
  { label: "Overview", icon: Activity },
  { label: "Planetary Explorer", icon: Globe2 },
  { label: "Analog Discovery", icon: Sparkles },
  { label: "Similarity Engine", icon: Activity },
  { label: "Analog Comparison", icon: Layers3 },
  { label: "Dataset Integration", icon: Database },
  { label: "Backend & Database", icon: Server },
  { label: "Evidence Review", icon: ShieldCheck },
  { label: "Scientific Reports", icon: BookOpen },
  { label: "Earth Locations", icon: Map },
  { label: "Comparisons", icon: Layers3 },
  { label: "Mission Suitability", icon: Compass },
  { label: "Mission Scenarios", icon: Orbit },
  { label: "Mission Risk", icon: ShieldCheck },
  { label: "Research Reports", icon: BookOpen },
  { label: "Administration", icon: Settings2 },
];

function App() {
  const [active, setActive] = useState("Similarity Engine");
  const [sessionToken, setSessionToken] = useState<string | null>(null);
  const [sessionUser, setSessionUser] = useState<TerrascanUser | null>(null);
  const authRequired = import.meta.env.VITE_USER_AUTH_REQUIRED === "true";
  const expireSession = useMemo(() => () => { if (sessionToken) void revokeUserSession(sessionToken); setSessionToken(null); setSessionUser(null); setApiAccessToken(null); }, [sessionToken]);
  useSessionLifecycle(sessionToken, expireSession);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [planet, setPlanet] = useState<PlanetaryBody>("Mars");
  const [selectedSiteId, setSelectedSiteId] = useState<string | null>("atacama");
  const [search, setSearch] = useState("");
  const [layerKey, setLayerKey] = useState<PlanetaryLayerKey>("imagery");
  const [showResourceNotes, setShowResourceNotes] = useState(false);

  const selectedSite = analogSites.find((site) => site.id === selectedSiteId) ?? null;
  const filteredSites = useMemo(() => analogSites.filter((site) =>
    `${site.name} ${site.region} ${site.country}`.toLowerCase().includes(search.toLowerCase())
  ), [search]);

  const activePlanetaryLayer = planet === "Earth" ? null : planetaryLayers[planet][layerKey];
  const resourcesForBody = planetaryDataResources.filter((resource) => resource.body === planet || resource.body === "All");

  if (authRequired && (!sessionToken || !sessionUser)) {
    return <LoginWorkspace onAuthenticated={(token, user) => { setSessionToken(token); setSessionUser(user); setApiAccessToken(token); }} />;
  }

  return (
    <div className="app-shell">
      {sidebarOpen && <button className="mobile-scrim" aria-label="Close navigation" onClick={() => setSidebarOpen(false)} />}
      <aside className={`sidebar ${sidebarOpen ? "sidebar-open" : ""}`}>
        <div className="brand">
          <div className="brand-mark"><Orbit size={21} strokeWidth={1.8} /></div>
          <div><div className="brand-name">TERRASCAN</div><div className="brand-caption">PLANETARY ANALOG INTELLIGENCE</div></div>
          <button className="icon-button sidebar-close" onClick={() => setSidebarOpen(false)} aria-label="Close menu"><X size={17}/></button>
        </div>
        <div className="workspace-label">RESEARCH WORKSPACE</div>
        <nav className="nav-list" aria-label="Main navigation">
          {navigation.map(({ label, icon: Icon }) => (
            <button key={label} className={`nav-item ${active === label ? "nav-item-active" : ""}`} onClick={() => { setActive(label); setSidebarOpen(false); }}>
              <Icon size={17} strokeWidth={1.8} /><span>{label}</span>
              {label === "Planetary Explorer" && <span className="nav-live-dot" />}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="system-status"><span className="status-dot" /><div><strong>PLANETARY DATA</strong><small>USGS catalog configured</small></div></div>
          <button className="nav-item settings-item" onClick={() => setActive("Settings")}><Settings2 size={17}/><span>Settings</span></button>
          <div className="version-label">TERRASCAN <span>v3.8.0 · RELEASE CANDIDATE</span></div>
        </div>
      </aside>

      <main className="main-area">
        <header className="topbar">
          <div className="topbar-left">
            <button className="icon-button menu-button" onClick={() => setSidebarOpen(true)} aria-label="Open navigation"><Menu size={19}/></button>
            <div className="breadcrumb"><span>Workspace</span><ChevronRight size={14}/><strong>{active}</strong></div>
          </div>
          <div className="topbar-actions">
            <div className="system-pill"><span className="status-dot"/> SCIENCE DATA WORKSPACE</div>
            <button className="icon-button" aria-label="Search locations" onClick={() => document.getElementById("site-search")?.focus()}><Search size={17}/></button>
            <button className="icon-button notification-button" aria-label="Notifications"><Bell size={17}/><i/></button>
            <div className="avatar" title={sessionUser ? `${sessionUser.username} · ${sessionUser.role}` : "TERRASCAN"}>{sessionUser ? sessionUser.username.slice(0,2).toUpperCase() : "TS"}</div>{sessionUser && <button className="icon-button" onClick={expireSession} aria-label="Sign out">Sign out</button>}
          </div>
        </header>

        <div className="page-content">
          {active === "Administration" ? (
            <>
              <section className="page-heading"><div><div className="eyebrow"><span className="eyebrow-line"/> ACCESS CONTROL</div><h1>Administration</h1><p className="page-subtitle">Manage TERRASCAN accounts and roles.</p></div></section>
              {sessionToken && sessionUser ? <AdminWorkspace token={sessionToken} user={sessionUser} /> : <p>Sign in to administer users.</p>}
            </>
          ) : active === "Mission Risk" ? (
            <>
              <section className="page-heading"><div><div className="eyebrow"><span className="eyebrow-line"/> MISSION RISK & UNCERTAINTY</div><h1>Mission Risk Register</h1><p className="page-subtitle">Record qualitative hazards, uncertainty, evidence references and mitigations without inventing probabilities.</p></div><div className="heading-meta"><span className="meta-label">ASSESSMENT METHOD</span><div className="engine-status-pill">QUALITATIVE · NO RISK SCORES</div></div></section>
              <MissionRiskWorkspace />
              <footer className="page-footer"><span>© TERRASCAN · RISK & UNCERTAINTY</span><span>NO PROBABILITY CLAIMS · IMMUTABLE SNAPSHOTS <b>●</b></span></footer>
            </>
          ) : active === "Mission Scenarios" ? (
            <>
              <section className="page-heading"><div><div className="eyebrow"><span className="eyebrow-line"/> MISSION OPERATIONS PLANNING</div><h1>Mission Scenarios</h1><p className="page-subtitle">Build hypothetical operational timelines from explicit activities, dependencies and resource constraints.</p></div><div className="heading-meta"><span className="meta-label">PLANNING METHOD</span><div className="engine-status-pill">DEPENDENCY-BASED · USER INPUTS</div></div></section>
              <MissionScenarioWorkspace />
              <footer className="page-footer"><span>© TERRASCAN · MISSION SCENARIO PLANNING</span><span>NO PREDICTIVE CLAIMS · NO AUTO-AUTHORIZATION <b>●</b></span></footer>
            </>
          ) : active === "Mission Suitability" ? (
            <>
              <section className="page-heading"><div><div className="eyebrow"><span className="eyebrow-line"/> OPERATIONAL CONSTRAINT ASSESSMENT</div><h1>Mission Suitability</h1><p className="page-subtitle">Evaluate configured mission constraints independently from Earth–Moon–Mars analog similarity.</p></div><div className="heading-meta"><span className="meta-label">ASSESSMENT POLICY</span><div className="engine-status-pill">APPROVED EVIDENCE · FAIL-CLOSED</div></div></section>
              <MissionSuitabilityWorkspace />
              <footer className="page-footer"><span>© TERRASCAN · MISSION CONSTRAINTS</span><span>NO DEFAULT THRESHOLDS · NO AUTOMATIC CERTIFICATION <b>●</b></span></footer>
            </>
          ) : active === "Scientific Reports" ? (
            <>
              <section className="page-heading"><div><div className="eyebrow"><span className="eyebrow-line"/> TRACEABLE SCIENTIFIC OUTPUTS</div><h1>Scientific Reports</h1><p className="page-subtitle">Generate PDF and CSV reports from reviewed records, source provenance and target references.</p></div><div className="heading-meta"><span className="meta-label">REPORT STATE</span><div className="engine-status-pill">EVIDENCE-BACKED · NO FABRICATED SCORES</div></div></section>
              <ScientificReportsWorkspace />
              <footer className="page-footer"><span>© TERRASCAN · SCIENTIFIC REPORTING</span><span>PROVENANCE · REVIEW STATUS · LIMITATIONS <b>●</b></span></footer>
            </>
          ) : active === "Evidence Review" ? (
            <>
              <section className="page-heading"><div><div className="eyebrow"><span className="eyebrow-line"/> SCIENTIFIC QUALITY CONTROL</div><h1>Evidence Review</h1><p className="page-subtitle">Review source manifests and derived measurements before they enter scientific comparisons.</p></div><div className="heading-meta"><span className="meta-label">REVIEW POLICY</span><div className="engine-status-pill">HUMAN APPROVAL REQUIRED</div></div></section>
              <EvidenceReviewWorkspace />
              <footer className="page-footer"><span>© TERRASCAN · EVIDENCE QUALITY CONTROL</span><span>APPROVALS AUDITED · REJECTIONS RETAINED <b>●</b></span></footer>
            </>
          ) : active === "Backend & Database" ? (
            <>
              <section className="page-heading"><div><div className="eyebrow"><span className="eyebrow-line"/> PERSISTENT SCIENCE DATA SERVICES</div><h1>Backend & Database</h1><p className="page-subtitle">Local API connectivity, persistent records and evidence provenance controls.</p></div><div className="heading-meta"><span className="meta-label">BACKEND VERSION</span><div className="engine-status-pill">STAGE 12 · v1.2.0</div></div></section>
              <BackendStatus />
              <footer className="page-footer"><span>© TERRASCAN · BACKEND INTEGRATION</span><span>SQLITE · FASTAPI · PROVENANCE FIRST <b>●</b></span></footer>
            </>
          ) : active === "Dataset Integration" ? (
            <>
              <section className="page-heading">
                <div><div className="eyebrow"><span className="eyebrow-line"/> SCIENTIFIC DATA PIPELINE</div><h1>Dataset Integration</h1><p className="page-subtitle">Discover, inspect and prepare traceable planetary science products for reproducible analysis.</p></div>
                <div className="heading-meta"><span className="meta-label">PIPELINE STATUS</span><div className="engine-status-pill"><span className="status-dot"/> CATALOGUED · INGESTION PENDING</div></div>
              </section>
              <DatasetWorkspace />
              <footer className="page-footer"><span>© TERRASCAN · SCIENTIFIC DATA INTEGRATION</span><span>OFFICIAL SOURCES · PROVENANCE REQUIRED <b>●</b></span></footer>
            </>
          ) : active === "Analog Comparison" ? (
            <>
              <section className="page-heading">
                <div><div className="eyebrow"><span className="eyebrow-line"/> EARTH–PLANETARY FEATURE COMPARISON</div><h1>Analog Comparison</h1><p className="page-subtitle">Rank terrestrial candidate environments against Moon and Mars reference features using traceable measurements.</p></div>
                <div className="heading-meta"><span className="meta-label">COMPARISON STATUS</span><div className="engine-status-pill"><span className="status-dot"/> READY · AWAITING REVIEWED DATA</div></div>
              </section>
              <AnalogComparisonWorkspace />
              <footer className="page-footer"><span>© TERRASCAN · CROSS-ENVIRONMENT COMPARISON</span><span>NO FABRICATED RANKINGS <b>●</b></span></footer>
            </>
          ) : active === "Similarity Engine" ? (
            <>
              <section className="page-heading">
                <div><div className="eyebrow"><span className="eyebrow-line"/> SCIENTIFIC COMPARISON FRAMEWORK</div><h1>Analog Similarity Engine</h1><p className="page-subtitle">Evidence-backed comparison of terrestrial environments against lunar and Martian reference conditions.</p></div>
                <div className="heading-meta"><span className="meta-label">ENGINE STATUS</span><div className="engine-status-pill"><span className="status-dot"/> READY · AWAITING DATA</div></div>
              </section>
              <SimilarityWorkspace />
              <footer className="page-footer"><span>© TERRASCAN · SCIENTIFIC ANALOG ASSESSMENT</span><span>PROVENANCE FIRST · NO FABRICATED SCORES <b>●</b></span></footer>
            </>
          ) : (
          <>
          <section className="page-heading">
            <div>
              <div className="eyebrow"><span className="eyebrow-line"/> PLANETARY SURFACE INTELLIGENCE</div>
              <h1>Planetary Explorer</h1>
              <p className="page-subtitle">Explore Earth analog environments alongside lunar and Martian reference cartography.</p>
            </div>
            <div className="heading-meta"><span className="meta-label">SELECT TARGET BODY</span><div className="planet-switch body-switch">
              {(["Earth", "Moon", "Mars"] as const).map((body) => <button key={body} className={planet === body ? "selected" : ""} onClick={() => { setPlanet(body); setLayerKey("imagery"); }}>{body}</button>)}
            </div></div>
          </section>

          <section className="notice-bar">
            <div className="notice-icon"><ShieldCheck size={17}/></div>
            <div><strong>{planet === "Earth" ? "Earth geographic reference" : `${planet} planetary basemap selected`}</strong><span>{planet === "Earth" ? "Earth uses geographic web mapping. NASA GIBS provides separate Earth-observation visualization services." : "Planetary imagery is served from the USGS Astrogeology WMS catalog. Rendered browse layers are not raw science rasters."}</span></div>
            <span className="notice-tag">STAGE 4</span>
          </section>

          <section className="metric-grid" aria-label="Planetary explorer metrics">
            <Metric icon={<Globe2 size={17}/>} label="TARGET BODIES" value="03" detail="Earth · Moon · Mars"/>
            <Metric icon={<Layers3 size={17}/>} label="BROWSE LAYERS" value={planet === "Earth" ? "01" : "02"} detail="Layer options catalogued"/>
            <Metric icon={<Database size={17}/>} label="DATA RESOURCES" value={String(resourcesForBody.length).padStart(2, "0")} detail="Official source references"/>
            <Metric icon={<Activity size={17}/>} label="SCIENCE ANALYSES" value="00" detail="No measurements calculated"/>
          </section>

          <section className="stage3-grid stage4-grid">
            <div className="panel map-panel map-panel-live">
              <div className="panel-header">
                <div><div className="panel-kicker">{planet.toUpperCase()} · SURFACE CARTOGRAPHY</div><h2>{planet === "Earth" ? "Terrestrial analog reference map" : `${planet} global reference map`}</h2></div>
                <div className="map-actions">
                  {planet !== "Earth" && <button className="subtle-button" onClick={() => setLayerKey((value) => value === "imagery" ? "topography" : "imagery")}><Mountain size={14}/> {layerKey === "imagery" ? "Topography" : "Imagery"}</button>}
                  {planet === "Earth" && <button className="subtle-button" onClick={() => setSelectedSiteId(null)}><RotateCcw size={14}/> Global</button>}
                </div>
              </div>
              {planet === "Earth" ? (
                <div className="live-map-wrap">
                  <AnalogMap selectedSiteId={selectedSiteId} showCandidates={true} onSelectSite={setSelectedSiteId}/>
                  <div className="map-overlay-chip"><span className="status-dot"/> EARTH · OPENSTREETMAP</div>
                </div>
              ) : (
                <div className="live-map-wrap">
                  <PlanetaryMap body={planet} layerKey={layerKey}/>
                </div>
              )}
              <div className="map-footer">
                <span><i className="legend-dot cyan"/> {planet === "Earth" ? "Analog candidates" : "Planetary surface mosaic"}</span>
                <span><i className="legend-dot muted"/> {planet === "Earth" ? "Geographic reference" : "Global cylindrical view"}</span>
                <span className="footer-note">{planet === "Earth" ? "© OpenStreetMap contributors" : activePlanetaryLayer?.attribution}</span>
              </div>
            </div>

            <aside className="panel candidate-panel stage4-side-panel">
              {planet === "Earth" ? (
                <>
                  <div className="panel-header"><div><div className="panel-kicker">TERRESTRIAL DATABASE</div><h2>Candidate locations <span className="count-pill">{filteredSites.length}</span></h2></div><span className="candidate-indicator">INITIAL SET</span></div>
                  <div className="site-search"><Search size={14}/><input id="site-search" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search locations..." aria-label="Search candidate locations"/></div>
                  <div className="candidate-list">
                    {filteredSites.map((site, index) => (
                      <button key={site.id} className={`candidate-item ${selectedSiteId === site.id ? "candidate-selected" : ""}`} onClick={() => setSelectedSiteId(site.id)}>
                        <span className="candidate-index">{String(index + 1).padStart(2, "0")}</span>
                        <span className="candidate-copy"><strong>{site.name}</strong><small>{site.region}</small></span><ChevronRight size={15}/>
                      </button>
                    ))}
                    {filteredSites.length === 0 && <div className="empty-search">No matching candidate locations.</div>}
                  </div>
                  {selectedSite ? <div className="selected-site">
                    <div className="selected-site-top"><span className="panel-kicker">SELECTED LOCATION</span><span className="status-tag">CANDIDATE</span></div>
                    <h3>{selectedSite.name}</h3><p>{selectedSite.country} · {selectedSite.region}</p>
                    <div className="site-focus-label">POTENTIAL ANALOG FOCUS</div><div className="site-focus">{selectedSite.analogFocus}</div>
                    <div className="site-note">{selectedSite.note}</div>
                    <div className="coordinates-row"><span>APPROX. COORDINATES</span><strong>{Math.abs(selectedSite.coordinates[1]).toFixed(2)}° {selectedSite.coordinates[1] >= 0 ? "N" : "S"} · {Math.abs(selectedSite.coordinates[0]).toFixed(2)}° {selectedSite.coordinates[0] >= 0 ? "E" : "W"}</strong></div>
                  </div> : <div className="selected-empty"><MapPin size={19}/><span>Select a candidate marker or list entry to inspect its regional profile.</span></div>}
                </>
              ) : (
                <>
                  <div className="panel-header"><div><div className="panel-kicker">{planet.toUpperCase()} DATA LAYERS</div><h2>Surface products</h2></div><Satellite size={18} className="muted-icon"/></div>
                  <div className="planet-layer-options">
                    {(["imagery", "topography"] as const).map((key) => {
                      const item = planetaryLayers[planet][key];
                      return <button key={key} className={`planet-layer-option ${layerKey === key ? "planet-layer-active" : ""}`} onClick={() => setLayerKey(key)}>
                        <span className="layer-option-icon">{key === "imagery" ? <Globe2 size={16}/> : <Mountain size={16}/>}</span>
                        <span className="layer-option-copy"><strong>{item.label}</strong><small>{item.description}</small></span>
                        <span className="layer-radio">{layerKey === key ? "●" : "○"}</span>
                      </button>;
                    })}
                  </div>
                  {activePlanetaryLayer && <div className="planet-source-card">
                    <div className="panel-kicker">ACTIVE SOURCE</div>
                    <h3>{activePlanetaryLayer.sourceName}</h3>
                    <p>{activePlanetaryLayer.dataNotes}</p>
                    <div className="source-meta"><span>SOURCE MAP PROJECTION</span><strong>{activePlanetaryLayer.projection}</strong></div>
                    <a href={activePlanetaryLayer.sourceUrl} target="_blank" rel="noreferrer">Open USGS layer catalog <ExternalLink size={12}/></a>
                  </div>}
                  <button className="resource-toggle" onClick={() => setShowResourceNotes((value) => !value)}><Info size={14}/>{showResourceNotes ? "Hide" : "Show"} research data resources</button>
                  {showResourceNotes && <div className="resource-list">
                    {resourcesForBody.map((resource) => <a key={resource.title} href={resource.url} target="_blank" rel="noreferrer"><span><strong>{resource.title}</strong><small>{resource.organization} · {resource.role}</small></span><ExternalLink size={12}/></a>)}
                  </div>}
                </>
              )}
            </aside>
          </section>

          <section className="bottom-grid">
            <div className="panel compact-panel">
              <div className="panel-header"><div><div className="panel-kicker">PLANET-AWARE ARCHITECTURE</div><h2>Separate cartographic systems</h2></div><span className="step-number">04</span></div>
              <p>Earth uses web geographic mapping. Moon and Mars use their own USGS Astrogeology WMS mapfiles and planetary layer identifiers. This prevents Earth map tiles from being misrepresented as planetary data.</p>
              <div className="integrity-tags"><span>EARTH · WEB MAP</span><span>MOON · LOLA / LROC</span><span>MARS · MOLA / THEMIS</span></div>
            </div>
            <div className="panel compact-panel">
              <div className="panel-header"><div><div className="panel-kicker">SCIENCE DATA POLICY</div><h2>Browse imagery ≠ analysis raster</h2></div><Atom size={18} className="muted-icon"/></div>
              <p>WMS layers are rendered visualizations for exploration. Quantitative elevation, illumination and geology analysis must use documented source products with units, scale, processing history and provenance.</p>
              <div className="integrity-tags"><span>PROVENANCE</span><span>UNITS</span><span>RESOLUTION</span><span>UNCERTAINTY</span></div>
            </div>
          </section>

          <footer className="page-footer"><span>© TERRASCAN · PLANETARY ANALOG INTELLIGENCE PLATFORM</span><span>USGS ASTROGEOLOGY · NASA PDS · NASA EARTHDATA <b>●</b></span></footer>
          </>
          )}
        </div>
      </main>
    </div>
  );
}

function Metric({ icon, label, value, detail }: { icon: ReactNode; label: string; value: string; detail: string }) {
  return <div className="panel metric-card"><div className="metric-top"><span className="metric-icon">{icon}</span><span className="metric-label">{label}</span></div><div className="metric-value">{value}</div><div className="metric-detail">{detail}</div></div>;
}

export default App;
