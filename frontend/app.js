/**
 * AGNI-NETRA // MULTI-SOURCE SATELLITE INTELLIGENCE
 * SIH 2026: Persistence & Classification Edition
 * 
 * Implements:
 * - 10-class visual classification system
 * - Independent Persistence & Risk dimensions
 * - Persistent Hotspot tracking ("We remember them.")
 * - Custom Leaflet DivIcons with pulsing critical rings
 * - Deep-Dive AI Explanations & SHAP Feature Importance
 */

const API_BASE = window.location.origin.includes('8000') ? window.location.origin : 'http://127.0.0.1:8000';

const state = {
  mode: 'DEMO',
  schema: null,
  hotspots: [],
  filteredHotspots: [],
  selectedHotspotId: null,
  persistentData: null,
  analyticsData: null,
  reportData: null,
  alerts: [],
  map: null,
  mapMarkers: [],
  activeFilters: new Set(), // Classification names
  layers: {
    insat3ds: null,
    insat3dr: null,
    viirs: null,
    industrial: null
  }
};

// ===================================================================
// INITIALIZATION
// ===================================================================
document.addEventListener('DOMContentLoaded', async () => {
  await fetchSchema();
  initNav();
  initModeSwitch();
  initMap();
  initLegendToggle();
  initDeepDiveModal();
  
  await refreshAllData();
  
  // Auto-refresh telemetry every 60s
  setInterval(refreshTelemetry, 60000);
});

async function fetchSchema() {
  try {
    const res = await fetch(`${API_BASE}/api/system/schema`);
    state.schema = await res.json();
    renderClassificationFilters();
    renderMapLegend();
  } catch (err) {
    console.error('Failed to load system schema', err);
  }
}

// ===================================================================
// MAIN VIEW NAVIGATION
// ===================================================================
function initNav() {
  const navBtns = document.querySelectorAll('.nav-tab-btn');
  navBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      navBtns.forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.view-panel').forEach(p => p.classList.remove('active'));
      
      btn.classList.add('active');
      const targetView = document.getElementById(btn.dataset.view);
      if (targetView) targetView.classList.add('active');
      
      // Ensure map resizes correctly when revealed
      if (btn.dataset.view === 'view-radar' && state.map) {
        setTimeout(() => state.map.invalidateSize(), 100);
      }
    });
  });
}

function initModeSwitch() {
  const btnDemo = document.getElementById('btnDemoMode');
  const btnLive = document.getElementById('btnLiveMode');
  
  btnDemo.addEventListener('click', () => setMode('DEMO'));
  btnLive.addEventListener('click', () => setMode('LIVE'));
}

async function setMode(mode) {
  if (state.mode === mode) return;
  try {
    await fetch(`${API_BASE}/api/mode/toggle?target_mode=${mode}`, { method: 'POST' });
    state.mode = mode;
    
    document.getElementById('btnDemoMode').classList.toggle('active', mode === 'DEMO');
    document.getElementById('btnLiveMode').classList.toggle('active', mode === 'LIVE');
    
    const banner = document.getElementById('modeDisclaimerBanner');
    const txt = document.getElementById('disclaimerText');
    if (mode === 'DEMO') {
      banner.className = 'disclaimer-banner demo-banner';
      banner.style.background = '';
      txt.innerText = 'DEMO BENCHMARK DATA — CALIBRATED ISRO MOSDAC & NASA FIRMS OBSERVATIONS';
    } else {
      banner.className = 'disclaimer-banner';
      banner.style.background = 'rgba(239, 68, 68, 0.15)';
      txt.innerText = 'LIVE MOSDAC MODE: Authentication credentials required for payload retrieval.';
    }
    await refreshAllData();
  } catch (e) {
    console.error('Mode toggle failed', e);
  }
}

// ===================================================================
// DATA ORCHESTRATION
// ===================================================================
async function refreshAllData() {
  await Promise.all([
    refreshTelemetry(),
    fetchHotspots(),
    fetchPersistentSources(),
    fetchAnalytics(),
    fetchReport(),
    fetchAlerts(),
    fetchSatellitePanel()
  ]);
}

async function refreshTelemetry() {
  try {
    const res = await fetch(`${API_BASE}/api/insat/nrt`);
    const nrt = await res.json();
    
    document.getElementById('nrtStatusBadge').innerText = nrt.status_label;
    document.getElementById('lastObsVal').innerText = nrt.last_observation;
    document.getElementById('dataAgeVal').innerText = nrt.data_age;

    const kpiRes = await fetch(`${API_BASE}/api/kpis`);
    const kpis = await kpiRes.json();
    
    document.getElementById('valInsatEvents').innerText = kpis.insat_events.value;
    document.getElementById('valInsatConfirmed').innerText = kpis.insat_confirmed_events.value;
    document.getElementById('valMultiSatellite').innerText = kpis.multi_satellite_events.value;
    document.getElementById('valPersistentSources').innerText = kpis.persistent_insat_sources.value;
  } catch (err) {
    console.error('Telemetry error:', err);
  }
}

// ===================================================================
// VIEW 1: GIS RADAR & MAP
// ===================================================================
function initMap() {
  state.map = L.map('satelliteMap', {
    center: [21.8, 79.5],
    zoom: 5,
    minZoom: 4,
    maxZoom: 14,
    zoomControl: false,
    attributionControl: true
  });
  
  L.control.zoom({ position: 'topright' }).addTo(state.map);

  const darkMap = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}', {
    maxZoom: 16,
    attribution: '&copy; <a href="https://www.esri.com/">Esri</a>, HERE, Garmin, FAO, NOAA, USGS, EPA'
  });

  const osmMap = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
  });

  // Default to Dark Map to preserve the command center aesthetic
  darkMap.addTo(state.map);

  const baseMaps = {
    "Dark Command Center": darkMap,
    "Standard OSM (Day)": osmMap
  };

  // Add the base layer control to the map
  L.control.layers(baseMaps, null, { position: 'topleft' }).addTo(state.map);

}

function initLegendToggle() {
  const btn = document.getElementById('btnToggleLegend');
  const body = document.getElementById('legendBody');
  const header = document.getElementById('legendHeaderToggle');
  
  if (header) {
    header.addEventListener('click', () => {
      body.classList.toggle('collapsed');
      btn.innerText = body.classList.contains('collapsed') ? '+' : '−';
    });
  }
}

function renderClassificationFilters() {
  const container = document.getElementById('filterChipsContainer');
  if (!container || !state.schema) return;
  container.innerHTML = '';
  
  Object.entries(state.schema.classifications).forEach(([name, def]) => {
    const chip = document.createElement('div');
    chip.className = 'filter-chip';
    chip.innerHTML = `<span class="chip-dot" style="background:${def.hex}"></span> ${name}`;
    
    chip.addEventListener('click', () => {
      chip.classList.toggle('active');
      if (chip.classList.contains('active')) {
        state.activeFilters.add(name);
      } else {
        state.activeFilters.delete(name);
      }
      applyFilters();
    });
    container.appendChild(chip);
  });
  
  document.getElementById('btnClearFilters').addEventListener('click', () => {
    state.activeFilters.clear();
    document.querySelectorAll('.filter-chip').forEach(c => c.classList.remove('active'));
    applyFilters();
  });
}

function renderMapLegend() {
  if (!state.schema) return;
  
  const classGrid = document.getElementById('legendClassificationGrid');
  if (classGrid) {
    classGrid.innerHTML = '';
    Object.entries(state.schema.classifications).forEach(([name, def]) => {
      classGrid.innerHTML += `
        <div class="legend-item" title="${def.meaning}">
          <span class="legend-dot" style="background:${def.hex}"></span>
          <span>${def.icon} ${name}</span>
        </div>`;
    });
  }
}

async function fetchHotspots() {
  try {
    const res = await fetch(`${API_BASE}/api/hotspots`);
    const data = await res.json();
    state.hotspots = data.hotspots || [];
    applyFilters();
    renderHotspotsTable();
  } catch (err) {
    console.error('Fetch hotspots error:', err);
  }
}

function applyFilters() {
  if (state.activeFilters.size === 0) {
    state.filteredHotspots = state.hotspots;
  } else {
    state.filteredHotspots = state.hotspots.filter(h => state.activeFilters.has(h.classification));
  }
  renderMapMarkers();
}

function renderMapMarkers() {
  state.mapMarkers.forEach(m => state.map.removeLayer(m));
  state.mapMarkers = [];
  
  state.filteredHotspots.forEach(h => {
    // Determine Icon based on Classification
    const classDef = state.schema.classifications[h.classification];
    const iconStr = classDef ? classDef.icon : '⚪';
    const hex = classDef ? classDef.hex : '#6b7280';
    
    let html = `<div class="custom-radar-marker">
                  <div class="marker-symbol-box" style="background: rgba(0,0,0,0.6); border-color: ${hex}; color: ${hex};">
                    ${iconStr}
                  </div>`;
                  
    // Add pulsing ring if CRITICAL
    if (h.risk_level === 'CRITICAL') {
      html += `<div class="pulsing-outer-ring"></div>`;
    }
    html += `</div>`;
    
    const icon = L.divIcon({
      html: html,
      className: '',
      iconSize: [28, 28],
      iconAnchor: [14, 14]
    });
    
    const marker = L.marker([h.latitude, h.longitude], { icon }).addTo(state.map);
    
    marker.on('click', () => {
      selectHotspot(h);
    });
    
    state.mapMarkers.push(marker);
  });
}

function selectHotspot(h) {
  state.selectedHotspotId = h.hotspot_id;
  
  // 1. Show Map Overlay Card
  const overlay = document.getElementById('hotspotCardOverlay');
  overlay.classList.remove('hidden');
  
  document.getElementById('cardClassBadge').innerHTML = `${h.classification_color ? '●' : ''} ${h.classification.toUpperCase()}`;
  document.getElementById('cardClassBadge').style.color = h.classification_color;
  document.getElementById('cardClassBadge').style.borderColor = h.classification_color;
  document.getElementById('cardClassBadge').style.background = `${h.classification_color}20`; // 20% opacity
  
  document.getElementById('cardHotspotId').innerText = `Hotspot: ${h.hotspot_id}`;
  document.getElementById('cardLocation').innerText = `${h.district}, ${h.state}`;
  
  document.getElementById('cardRiskPill').innerText = `${state.schema.risks[h.risk_level].icon} ${h.risk_level} ${h.risk_score}/100`;
  document.getElementById('cardRiskPill').style.color = h.risk_color;
  
  const confIcon = h.average_confidence >= 80 ? '🟢' : '🟡';
  document.getElementById('cardConfPill').innerText = `${confIcon} ${h.average_confidence >= 80 ? 'HIGH' : 'NOMINAL'} ${h.average_confidence}%`;
  
  const persDef = state.schema.persistence[h.persistence_status];
  document.getElementById('cardPersistPill').innerText = `${persDef.icon} ${h.persistence_status.toUpperCase()}`;
  document.getElementById('cardPersistPill').style.color = h.persistence_color;
  
  document.getElementById('cardDetectionsCount').innerText = h.total_detections;
  document.getElementById('cardFirstSeen').innerText = h.first_detected;
  document.getElementById('cardLastSeen').innerText = h.last_detected;
  document.getElementById('cardFactoryDist').innerText = h.facility_distance_m ? `${h.facility_distance_m}m` : 'N/A';
  
  document.getElementById('btnCloseCardOverlay').onclick = () => overlay.classList.add('hidden');
  document.getElementById('btnCardInspectDeepDive').onclick = () => openDeepDive(h.hotspot_id);
  
  // 2. Update Sidebar Inspector
  document.getElementById('detailEventId').innerText = h.hotspot_id;
  document.getElementById('detailRiskBadge').innerText = `${h.risk_level} RISK`;
  document.getElementById('detailRiskBadge').className = `event-risk-badge risk-${h.risk_level.toLowerCase()}`;
  
  document.getElementById('prominentClassBanner').style.borderColor = h.classification_color;
  document.getElementById('prominentClassBanner').style.background = `${h.classification_color}15`;
  document.getElementById('detailClassIcon').innerText = state.schema.classifications[h.classification].icon;
  document.getElementById('detailClassTitle').innerText = h.classification.toUpperCase();
  document.getElementById('detailClassTitle').style.color = h.classification_color;
  document.getElementById('detailClassConfidence').innerText = `Classification confidence: ${h.classification_confidence}%`;
  
  document.getElementById('detailHeadline').innerText = h.name;
  document.getElementById('detailFacilitySub').innerText = `${h.facility_type || 'Regional Area'} • ${h.latitude.toFixed(4)}°N, ${h.longitude.toFixed(4)}°E`;
  
  document.getElementById('dimFirmsConf').innerText = h.average_confidence >= 80 ? 'HIGH' : 'NOMINAL';
  document.getElementById('dimPersistence').innerText = h.persistence_status.toUpperCase();
  document.getElementById('dimPersistence').style.color = h.persistence_color;
  document.getElementById('dimIndustrialContext').innerText = h.facility_distance_m ? `${h.facility_distance_m}m` : 'N/A';
  
  document.getElementById('btnSidebarOpenDeepDive').onclick = () => openDeepDive(h.hotspot_id);
  
  state.map.setView([h.latitude, h.longitude], 10, { animate: true });
}

// ===================================================================
// DEEP DIVE MODAL (/hotspots/[id])
// ===================================================================
function initDeepDiveModal() {
  const modal = document.getElementById('hotspotDeepDiveModal');
  const btnClose = document.getElementById('btnCloseDeepDive');
  
  btnClose.onclick = () => modal.classList.add('hidden');
  
  const tabs = document.querySelectorAll('.dd-tab');
  tabs.forEach(t => {
    t.addEventListener('click', () => {
      tabs.forEach(x => x.classList.remove('active'));
      document.querySelectorAll('.dd-tab-content').forEach(c => c.classList.remove('active'));
      t.classList.add('active');
      document.getElementById(t.dataset.ddtab).classList.add('active');
    });
  });
}

async function openDeepDive(hotspot_id) {
  try {
    const res = await fetch(`${API_BASE}/api/hotspots/${hotspot_id}`);
    const h = await res.json();
    
    const modal = document.getElementById('hotspotDeepDiveModal');
    modal.classList.remove('hidden');
    
    // Header
    document.getElementById('ddHotspotId').innerText = h.hotspot_id;
    document.getElementById('ddClassBadge').innerText = `${state.schema.classifications[h.classification].icon} ${h.classification.toUpperCase()}`;
    document.getElementById('ddClassBadge').style.color = h.classification_color;
    
    document.getElementById('ddRiskBadge').innerText = `${state.schema.risks[h.risk_level].icon} ${h.risk_level} ${h.risk_score}/100`;
    document.getElementById('ddRiskBadge').style.color = h.risk_color;
    
    document.getElementById('ddPersistBadge').innerText = `${state.schema.persistence[h.persistence_status].icon} ${h.persistence_status.toUpperCase()}`;
    document.getElementById('ddPersistBadge').style.color = h.persistence_color;
    
    // Tab 1: Overview
    document.getElementById('ddFacilityName').innerText = h.nearest_facility || 'N/A';
    document.getElementById('ddFacilityType').innerText = h.facility_type || 'N/A';
    document.getElementById('ddStateDist').innerText = `${h.state} • ${h.district}`;
    document.getElementById('ddCoords').innerText = `${h.latitude.toFixed(5)}°N, ${h.longitude.toFixed(5)}°E`;
    document.getElementById('ddFirstSeen').innerText = h.first_detected;
    document.getElementById('ddLastSeen').innerText = h.last_detected;
    document.getElementById('ddSpanDays').innerText = `${h.observation_span_days} days`;
    document.getElementById('ddUniqueDays').innerText = `${h.unique_detection_days} days`;
    document.getElementById('ddRecurrenceRate').innerText = `${(h.recurrence_rate * 100).toFixed(1)}%`;
    
    const clCont = document.getElementById('ddChecklistContainer');
    clCont.innerHTML = h.explanation_checklist.map(item => `<div class="check-item">${item}</div>`).join('');
    
    const shapCont = document.getElementById('ddShapContainer');
    shapCont.innerHTML = h.shap_features.map(f => {
      const w = Math.min(100, Math.abs(f.shap_value) * 150);
      return `
        <div class="shap-row">
          <div class="shap-label" title="${f.display_name}">${f.display_name}</div>
          <div class="shap-bar-track">
            <div class="shap-bar-fill ${f.impact.toLowerCase()}" style="width: ${w}%"></div>
          </div>
          <div class="shap-val ${f.impact === 'POSITIVE' ? 'text-green' : 'text-red'}">${f.shap_value > 0 ? '+' : ''}${f.shap_value.toFixed(2)}</div>
        </div>
      `;
    }).join('');
    
    // Tab 2: Timeline
    document.getElementById('ddAvgFrp').innerText = `${h.average_frp.toFixed(1)} MW`;
    document.getElementById('ddMaxFrp').innerText = `${h.maximum_frp.toFixed(1)} MW`;
    document.getElementById('ddTotalDetections').innerText = h.total_detections;
    
    const tbody = document.getElementById('ddObsTableBody');
    tbody.innerHTML = h.observations.map(o => `
      <tr>
        <td class="code-font">${o.observation_id}</td>
        <td>${o.timestamp}</td>
        <td>${o.satellite}</td>
        <td>${o.sensor}</td>
        <td class="${o.confidence === 'high' ? 'text-green' : 'text-yellow'}">${o.confidence.toUpperCase()}</td>
        <td class="code-font">${o.frp.toFixed(1)}</td>
        <td class="code-font">${o.brightness_temp_k ? o.brightness_temp_k.toFixed(1) : '-'}</td>
      </tr>
    `).join('');
    
    // Tab 3: Spatial
    document.getElementById('ddSpatialCenter').innerText = `${h.latitude.toFixed(5)}°N, ${h.longitude.toFixed(5)}°E`;
    document.getElementById('ddSpatialRadius').innerText = `${h.cluster_radius_m} m`;
    document.getElementById('ddSpatialDistance').innerText = h.facility_distance_m ? `${h.facility_distance_m} m` : 'N/A';
    
    // Tab 4: Satellite
    const satCont = document.getElementById('ddSatelliteBreakdown');
    satCont.innerHTML = Object.entries(h.satellite_breakdown).map(([sat, count]) => `
      <div class="check-item" style="display:inline-flex; margin:4px;">${sat}: ${count} passes</div>
    `).join('');
    
  } catch (err) {
    console.error('Deep dive error', err);
  }
}

// ===================================================================
// VIEW 2: HOTSPOT REGISTRY TABLE
// ===================================================================
function renderHotspotsTable() {
  const tbody = document.getElementById('hotspotsTableBody');
  if (!tbody) return;
  tbody.innerHTML = '';
  
  state.hotspots.forEach(h => {
    const classDef = state.schema.classifications[h.classification];
    const riskDef = state.schema.risks[h.risk_level];
    const persistDef = state.schema.persistence[h.persistence_status];
    
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td class="code-font" style="color:#38bdf8; font-weight:700;">${h.hotspot_id}</td>
      <td>
        <div class="badge-table-class" style="color:${classDef.hex}; border-color:${classDef.hex}; background:${classDef.hex}15;">
          ${classDef.icon} ${h.classification}
        </div>
      </td>
      <td style="text-align:right;">${h.average_confidence >= 80 ? '🟢' : '🟡'} ${h.average_confidence.toFixed(1)}%</td>
      <td>
        <div class="badge-table-persist" style="color:${persistDef.hex}; background:${persistDef.hex}20;">
          ${h.persistence_status}
        </div>
      </td>
      <td>
        <div class="badge-table-risk risk-${h.risk_level.toLowerCase()}" style="color:${riskDef.hex}; border-color:${riskDef.hex}; background:${riskDef.hex}20;">
          ${riskDef.icon} ${h.risk_level}
        </div>
      </td>
      <td style="text-align:right;" class="code-font">${h.average_frp.toFixed(1)} / ${h.maximum_frp.toFixed(1)}</td>
      <td style="text-align:right;"><b>${h.total_detections}</b> in ${h.observation_span_days}d</td>
      <td>${h.facility_distance_m ? h.facility_distance_m + 'm' : '-'}</td>
      <td>
        <button class="btn-table-action" onclick="openDeepDive('${h.hotspot_id}')">Inspect</button>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

// ===================================================================
// VIEW 3: PERSISTENT SOURCES DASHBOARD
// ===================================================================
async function fetchPersistentSources() {
  try {
    const res = await fetch(`${API_BASE}/api/persistent-sources`);
    state.persistentData = await res.json();
    renderPersistentDashboard();
  } catch (err) {
    console.error('Persistent sources error', err);
  }
}

function renderPersistentDashboard() {
  if (!state.persistentData) return;
  const { kpis, rankings, candidates } = state.persistentData;
  
  // KPIs
  document.getElementById('pkpiTotal').innerText = kpis.total_persistent;
  document.getElementById('pkpiNew').innerText = kpis.new_persistent;
  document.getElementById('pkpiRecurring').innerText = kpis.recurring_sources;
  document.getElementById('pkpiIndustrial').innerText = kpis.industrial_associated;
  
  // Leaderboards
  const ll = document.getElementById('listLongestRunning');
  if (ll) {
    ll.innerHTML = rankings.longest_running.map(r => `
      <li class="leaderboard-item" onclick="openDeepDive('${r.hotspot_id}')">
        <span><b class="code-font" style="color:#38bdf8">${r.hotspot_id}</b> ${r.name.substring(0,20)}...</span>
        <span style="color:#a855f7; font-weight:bold;">${r.span_days} days</span>
      </li>
    `).join('');
  }
  
  const mf = document.getElementById('listMostFrequent');
  if (mf) {
    mf.innerHTML = rankings.most_frequently_detected.map(r => `
      <li class="leaderboard-item" onclick="openDeepDive('${r.hotspot_id}')">
        <span><b class="code-font" style="color:#38bdf8">${r.hotspot_id}</b> ${r.name.substring(0,20)}...</span>
        <span style="color:#22c55e; font-weight:bold;">${r.detections} det.</span>
      </li>
    `).join('');
  }

  const hf = document.getElementById('listHighestFrp');
  if (hf) {
    hf.innerHTML = rankings.highest_frp.map(r => `
      <li class="leaderboard-item" onclick="openDeepDive('${r.hotspot_id}')">
        <span><b class="code-font" style="color:#38bdf8">${r.hotspot_id}</b> ${r.name.substring(0,20)}...</span>
        <span style="color:#f97316; font-weight:bold;">${r.max_frp.toFixed(1)} MW</span>
      </li>
    `).join('');
  }
  
  // Cards
  const grid = document.getElementById('persistentGridCards');
  if (grid) {
    grid.innerHTML = candidates.map(c => `
      <div class="chronic-card" onclick="openDeepDive('${c.hotspot_id}')">
        <div class="chronic-card-top">
          <div class="chronic-card-title">${c.facility_name}</div>
          <div class="badge-table-class" style="color:${c.classification_color}; background:${c.classification_color}15;">${c.classification}</div>
        </div>
        <div style="font-size:0.7rem; color:#94a3b8;">${c.facility_type} • ${c.state}</div>
        <div style="display:flex; justify-content:space-between; margin-top:10px; font-size:0.75rem;">
          <div><b style="color:#e2e8f0">${c.total_detections}</b> Detections</div>
          <div>Span: <b style="color:#e2e8f0">${c.observation_span_days}d</b></div>
        </div>
      </div>
    `).join('');
  }
}

// ===================================================================
// VIEW 4: ANALYTICS & DISTRIBUTION
// ===================================================================
async function fetchAnalytics() {
  try {
    const res = await fetch(`${API_BASE}/api/analytics/distribution`);
    state.analyticsData = await res.json();
    renderAnalytics();
  } catch (err) {
    console.error('Analytics error', err);
  }
}

function renderAnalytics() {
  if (!state.analyticsData) return;
  const { classification_distribution, risk_distribution, persistence_distribution } = state.analyticsData;
  
  const cBar = document.getElementById('classificationDistributionBars');
  if (cBar) {
    cBar.innerHTML = classification_distribution.map(d => `
      <div class="dist-row">
        <div class="dist-label">${d.icon} ${d.classification}</div>
        <div class="dist-bar-track">
          <div class="dist-bar-fill" style="width:${d.percentage}%; background:${d.color};"></div>
        </div>
        <div class="dist-percentage">${d.percentage}%</div>
      </div>
    `).join('');
  }
  
  const rBar = document.getElementById('riskDistributionBars');
  if (rBar) {
    rBar.innerHTML = risk_distribution.map(d => `
      <div class="dist-row">
        <div class="dist-label" style="color:${d.color}">${d.risk}</div>
        <div class="dist-bar-track">
          <div class="dist-bar-fill" style="width:${d.percentage}%; background:${d.color};"></div>
        </div>
        <div class="dist-percentage">${d.percentage}%</div>
      </div>
    `).join('');
  }
  
  const pBar = document.getElementById('persistenceDistributionBars');
  if (pBar) {
    pBar.innerHTML = persistence_distribution.map(d => `
      <div class="dist-row">
        <div class="dist-label" style="color:${d.color}">${d.status}</div>
        <div class="dist-bar-track">
          <div class="dist-bar-fill" style="width:${d.percentage}%; background:${d.color};"></div>
        </div>
        <div class="dist-percentage">${d.percentage}%</div>
      </div>
    `).join('');
  }
}

// ===================================================================
// VIEW 5: REPORTS
// ===================================================================
async function fetchReport() {
  try {
    const res = await fetch(`${API_BASE}/api/reports/summary`);
    state.reportData = await res.json();
    renderReport();
  } catch (err) {
    console.error('Report error', err);
  }
}

function renderReport() {
  if (!state.reportData) return;
  const r = state.reportData;
  
  document.getElementById('reportGenTime').innerText = r.generated_at;
  document.getElementById('repTotalHotspots').innerText = r.summary.total_monitored_hotspots;
  document.getElementById('repCriticalCount').innerText = r.summary.critical_risk_count;
  document.getElementById('repPrimaryCount').innerText = r.summary.possible_industrial_thermal_events;
  
  // Legends
  const cl = document.getElementById('reportClassLegendList');
  if (cl) {
    cl.innerHTML = r.classification_legend.map(i => `
      <div class="report-legend-item">
        <span style="color:${i.color}; font-weight:bold;">${i.icon} ${i.classification}</span>
      </div>
    `).join('');
  }
  
  const rl = document.getElementById('reportRiskLegendList');
  if (rl) {
    rl.innerHTML = r.risk_legend.map(i => `
      <div class="report-legend-item">
        <span style="color:${i.color}; font-weight:bold;">${i.icon} ${i.risk}</span>
        <span style="color:#64748b; font-size:0.65rem; margin-left:auto;">${i.score_range}</span>
      </div>
    `).join('');
  }
  
  const pl = document.getElementById('reportPersistLegendList');
  if (pl) {
    pl.innerHTML = r.persistence_legend.map(i => `
      <div class="report-legend-item">
        <span style="color:${i.color}; font-weight:bold;">${i.icon} ${i.status}</span>
      </div>
    `).join('');
  }
  
  // Table
  const tb = document.getElementById('reportTableContainer');
  if (tb) {
    tb.innerHTML = `
      <table class="styled-hotspot-table">
        <thead>
          <tr>
            <th>Hotspot ID</th>
            <th>Name</th>
            <th>Classification</th>
            <th>Risk</th>
            <th>Total Det.</th>
          </tr>
        </thead>
        <tbody>
          ${r.critical_incidents.map(c => `
            <tr>
              <td class="code-font">${c.hotspot_id}</td>
              <td>${c.name}</td>
              <td style="color:${c.classification_color}">${c.classification}</td>
              <td style="color:${c.risk_color}; font-weight:bold;">${c.risk_level}</td>
              <td>${c.total_detections}</td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    `;
  }
}

// ===================================================================
// VIEW 6: NRT ALERTS & SATELLITE EVIDENCE
// ===================================================================
async function fetchAlerts() {
  try {
    const res = await fetch(`${API_BASE}/api/alerts`);
    const data = await res.json();
    state.alerts = data.alerts || [];
    
    document.getElementById('topAlertCount').innerText = state.alerts.length;
    
    const list = document.getElementById('alertsStreamList');
    if (!list) return;
    list.innerHTML = state.alerts.map(a => `
      <div class="alert-card" style="border-left: 4px solid ${a.severity_color}; background:var(--bg-glass-card); padding:12px; margin-bottom:10px; border-radius:6px; cursor:pointer;" onclick="openDeepDive('${a.hotspot_id}')">
        <div style="display:flex; justify-content:space-between; margin-bottom:6px;">
          <b style="color:#ffffff;">${a.rule_name}</b>
          <span style="background:${a.severity_color}20; color:${a.severity_color}; padding:2px 8px; border-radius:4px; font-weight:bold; font-size:0.7rem;">${a.severity}</span>
        </div>
        <div style="font-size:0.75rem; color:#94a3b8; margin-bottom:8px;">${a.rule_description}</div>
        <div style="display:flex; gap:12px; font-size:0.7rem;">
          <span style="color:${a.classification_color}">${a.classification_icon} ${a.classification}</span>
          <span style="color:#cbd5e1;">📍 ${a.facility}</span>
          <span style="color:#94a3b8; margin-left:auto;">${a.triggered_at}</span>
        </div>
      </div>
    `).join('');
  } catch (err) {
    console.error('Alerts error', err);
  }
}

async function fetchSatellitePanel() {
  try {
    const res = await fetch(`${API_BASE}/api/satellite-evidence`);
    const data = await res.json();
    const container = document.getElementById('satelliteChecklistGrid');
    if (!container) return;
    
    container.innerHTML = data.providers.map(p => `
      <div class="agency-evidence-group">
        <div class="agency-group-header">
          <span>${p.agency_display}</span>
          <span>${p.country}</span>
        </div>
        ${p.satellites.map(s => `
          <div class="satellite-item-row">
            <div>
              <span class="sat-name-tag">${s.name}</span>
              <span class="sat-role-sub">${s.role}</span>
            </div>
            <div>${s.available ? '<span class="active-check">✓ ACTIVE</span>' : '<span class="unavail-circle">○ unavailable</span>'}</div>
          </div>
        `).join('')}
      </div>
    `).join('');
  } catch (err) {
    console.error('Satellite panel error', err);
  }
}
