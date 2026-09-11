"""
Agni-Netra // Multi-Source Satellite Intelligence Platform for India.
FastAPI Application serving ISRO INSAT-3 Series, NASA VIIRS Fusion, and UI assets.

Implements:
- 10 Visual Classification Categories and 3 Independent Dimensions (Classification, Risk, Persistence)
- Persistence Tracking Engine with Hotspot Memory ("We remember them.")
- Hotspot History Deep Dive API (/api/hotspots/{id})
- Persistent Sources Dashboard API (/api/persistent-sources)
- Analytics & Distribution API (/api/analytics/distribution)
- Official SIH Report Generator API (/api/reports/summary)
"""

import os
import sys
from typing import Dict, Any, Optional, List
from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# Ensure core modules are importable
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.data_models import (
    INSATObservation,
    FusedThermalEvent,
    CLASSIFICATION_DEFINITIONS,
    RISK_DEFINITIONS,
    PERSISTENCE_DEFINITIONS,
    DATA_QUALITY_DEFINITIONS,
    SATELLITE_SOURCE_BADGES
)
from core.insat_provider import INSATDataProvider, INDIAN_INDUSTRIAL_ANCHORS
from core.viirs_loader import VIIRSDataLoader
from core.spatial_matcher import SpatialTemporalMatcher
from core.persistence_engine import PersistenceEngine
from core.alert_engine import AlertEngine

from apscheduler.schedulers.background import BackgroundScheduler
from workers.firms_ingestion import run_ingestion_job
import logging

app = FastAPI(
    title="Agni-Netra // Multi-Source Satellite Intelligence Platform",
    description="ISRO INSAT-3 Series Integration alongside NASA VIIRS / FIRMS with Long-Term Persistence for SIH 2026",
    version="2.5.0"
)

# Enable CORS for local dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Core Services
current_mode = "DEMO"  # "DEMO" or "LIVE"
insat_provider = INSATDataProvider(mode=current_mode)
viirs_loader = VIIRSDataLoader()
spatial_matcher = SpatialTemporalMatcher(max_spatial_distance_km=8.0, max_time_diff_minutes=180.0)
persistence_engine = PersistenceEngine()
alert_engine = AlertEngine()

# Initialize Scheduler
scheduler = BackgroundScheduler()
scheduler.add_job(run_ingestion_job, "interval", minutes=15)

@app.on_event("startup")
def startup_event():
    logging.info("Starting background scheduler for NASA FIRMS ingestion...")
    scheduler.start()
    # Optionally trigger a job immediately on startup for LIVE data
    # run_ingestion_job()

@app.on_event("shutdown")
def shutdown_event():
    logging.info("Shutting down background scheduler...")
    scheduler.shutdown()



from pydantic import BaseModel
from services.chatbot_service import chatbot_service

def get_pipeline_data():
    """Refreshes and caches pipeline data across providers."""
    insat_obs = insat_provider.fetch_observations()
    viirs_obs = viirs_loader.load_samples(INDIAN_INDUSTRIAL_ANCHORS)
    fused = spatial_matcher.fuse_events(insat_obs, viirs_obs, INDIAN_INDUSTRIAL_ANCHORS)
    persistent = persistence_engine.evaluate_persistent_sources(INDIAN_INDUSTRIAL_ANCHORS, insat_obs, viirs_obs)
    alerts = alert_engine.evaluate_events(fused)
    return insat_obs, viirs_obs, fused, persistent, alerts

class ChatRequest(BaseModel):
    message: str
    conversation_id: str

@app.post("/api/chat")
def handle_chat(request: ChatRequest):
    try:
        pipeline_data = get_pipeline_data()
        response = chatbot_service.handle_message(
            message=request.message,
            conversation_id=request.conversation_id,
            pipeline_data=pipeline_data
        )
        return response
    except Exception as e:
        logging.error(f"Chatbot API Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error in Chatbot Service")


@app.get("/api/system/schema")
def get_system_schema():
    """
    Returns visual classification system schema, risk definitions,
    persistence standards, data quality colors, and source badges.
    """
    return {
        "classifications": CLASSIFICATION_DEFINITIONS,
        "risks": RISK_DEFINITIONS,
        "persistence": PERSISTENCE_DEFINITIONS,
        "data_quality": DATA_QUALITY_DEFINITIONS,
        "satellite_sources": SATELLITE_SOURCE_BADGES
    }


@app.get("/api/insat/nrt")
def get_insat_nrt_telemetry():
    """
    Returns NRT Telemetry metadata for INSAT:
    - Operator: ISRO / INDIA
    - Last Observation
    - Last Retrieved
    - Data Age
    - Availability Status & Disclaimers
    """
    return insat_provider.get_nrt_telemetry_status()


@app.get("/api/insat/observations")
def list_insat_observations(satellite: Optional[str] = None, quality: Optional[str] = None):
    """Lists validated INSAT observations with footprints."""
    insat_obs, _, _, _, _ = get_pipeline_data()
    results = insat_obs
    if satellite:
        results = [o for o in results if o.satellite.upper() == satellite.upper()]
    if quality:
        results = [o for o in results if o.quality.upper() == quality.upper()]
    return {
        "count": len(results),
        "operator": "ISRO / INDIA",
        "observations": results
    }


@app.get("/api/events")
def list_fused_events(
    agreement: Optional[str] = None,
    classification: Optional[str] = None,
    risk: Optional[str] = None
):
    """Lists multi-satellite fused thermal events with independent 3 dimensions."""
    _, _, fused, _, _ = get_pipeline_data()
    results = fused
    if agreement:
        results = [e for e in results if e.satellite_agreement.upper() == agreement.upper()]
    if classification:
        results = [e for e in results if classification.lower() in e.scientific_classification.lower()]
    if risk:
        results = [e for e in results if e.risk_level.upper() == risk.upper()]
    return {
        "count": len(results),
        "events": results
    }


@app.get("/api/events/{event_id}")
def get_event_detail(event_id: str):
    """Detailed event record with dedicated INSAT Evidence and VIIRS breakdown."""
    _, _, fused, _, _ = get_pipeline_data()
    for e in fused:
        if e.id == event_id:
            return e
    raise HTTPException(status_code=404, detail=f"Thermal event '{event_id}' not found")


# =====================================================================
# HOTSPOT IDENTITY & LONG-TERM MEMORY ("We remember them.")
# =====================================================================

@app.get("/api/hotspots")
def list_hotspots(
    classification: Optional[str] = None,
    persistence_status: Optional[str] = None,
    risk_level: Optional[str] = None,
    state: Optional[str] = None
):
    """
    Lists long-term remembered hotspots with complete temporal persistence metrics.
    """
    records = persistence_engine.get_all_hotspots(
        classification=classification,
        persistence_status=persistence_status,
        risk_level=risk_level,
        state_filter=state
    )
    return {
        "count": len(records),
        "hotspots": records
    }


@app.get("/api/hotspots/{hotspot_id}")
def get_hotspot_detail(hotspot_id: str):
    """
    Dedicated Hotspot History endpoint (/hotspots/[id]):
    Returns overview, historical activity, thermal behavior, spatial spread,
    multi-satellite evidence, AI explanation, and SHAP feature importance.
    """
    hotspot = persistence_engine.get_hotspot_by_id(hotspot_id)
    if not hotspot:
        raise HTTPException(status_code=404, detail=f"Hotspot '{hotspot_id}' not found in long-term memory")
    return hotspot


# =====================================================================
# CHRONIC PERSISTENT SOURCES DASHBOARD (/persistent-sources)
# =====================================================================

@app.get("/api/persistent-sources")
def get_persistent_sources():
    """
    Dedicated chronic sources payload:
    Returns candidates list + summary KPIs + leaderboards.
    """
    insat_obs, viirs_obs, _, persistent, _ = get_pipeline_data()
    kpis = persistence_engine.get_chronic_dashboard_kpis()
    return {
        "count": len(persistent),
        "candidates": persistent,
        "kpis": kpis["summary_kpis"],
        "rankings": kpis["rankings"]
    }


@app.get("/api/kpis")
def get_dashboard_kpis():
    """
    Primary Dashboard KPIs required for SIH 2026.
    """
    insat_obs, viirs_obs, fused, persistent, _ = get_pipeline_data()
    all_hotspots = persistence_engine.get_all_hotspots()

    insat_events_count = len(insat_obs)
    insat_confirmed_count = sum(1 for e in fused if e.insat_detected == "YES" and e.viirs_detected == "YES")
    multi_satellite_count = sum(1 for e in fused if e.satellite_agreement in ["HIGH", "MEDIUM"])
    persistent_sources_count = sum(1 for h in all_hotspots if h.persistence_status in ["Persistent", "Recurring"])

    return {
        "insat_events": {
            "label": "INSAT EVENTS",
            "value": insat_events_count,
            "subtext": "ISRO / INDIA (INSAT-3D/3DR/3DS)",
            "unit": "observations"
        },
        "insat_confirmed_events": {
            "label": "INSAT-CONFIRMED EVENTS",
            "value": insat_confirmed_count,
            "subtext": "Corroborated by Geostationary INSAT",
            "unit": "events"
        },
        "multi_satellite_events": {
            "label": "MULTI-SATELLITE EVENTS",
            "value": multi_satellite_count,
            "subtext": "High/Med Agreement (ISRO + NASA)",
            "unit": "cross-verified"
        },
        "persistent_insat_sources": {
            "label": "PERSISTENT SOURCES",
            "value": persistent_sources_count,
            "subtext": "Long-Term Thermal Memories Recorded",
            "unit": "hotspots"
        }
    }


# =====================================================================
# ANALYTICS & DISTRIBUTION
# =====================================================================

@app.get("/api/analytics/distribution")
def get_analytics_distribution():
    """
    Thermal Source Classification Distribution Chart data and Risk breakdown.
    Adheres strictly to the 10 classification colors.
    """
    hotspots = persistence_engine.get_all_hotspots()
    total = max(1, len(hotspots))

    # Calculate exact counts and percentages
    class_counts = {}
    for h in hotspots:
        class_counts[h.classification] = class_counts.get(h.classification, 0) + 1

    distribution = []
    for c_name, c_def in CLASSIFICATION_DEFINITIONS.items():
        cnt = class_counts.get(c_name, 0)
        pct = round((cnt / total) * 100.0, 1)
        distribution.append({
            "classification": c_name,
            "color": c_def["hex"],
            "icon": c_def["icon"],
            "count": cnt,
            "percentage": pct
        })

    # Sort distribution desc by percentage
    distribution.sort(key=lambda d: d["percentage"], reverse=True)

    # Risk distribution
    risk_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for h in hotspots:
        risk_counts[h.risk_level] = risk_counts.get(h.risk_level, 0) + 1

    risk_dist = [
        {"risk": r, "color": RISK_DEFINITIONS[r]["hex"], "count": risk_counts[r], "percentage": round((risk_counts[r] / total) * 100.0, 1)}
        for r in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
    ]

    # Persistence distribution
    persist_counts = {"Persistent": 0, "Recurring": 0, "Temporary": 0, "Unknown": 0}
    for h in hotspots:
        persist_counts[h.persistence_status] = persist_counts.get(h.persistence_status, 0) + 1

    persist_dist = [
        {"status": p, "color": PERSISTENCE_DEFINITIONS[p]["hex"], "count": persist_counts[p], "percentage": round((persist_counts[p] / total) * 100.0, 1)}
        for p in ["Persistent", "Recurring", "Temporary", "Unknown"]
    ]

    return {
        "total_hotspots": total,
        "classification_distribution": distribution,
        "risk_distribution": risk_dist,
        "persistence_distribution": persist_dist
    }


# =====================================================================
# OFFICIAL REPORT GENERATOR (/api/reports/summary)
# =====================================================================

@app.get("/api/reports/summary")
def get_report_summary():
    """
    Returns official report data complete with:
    - Classification Legend (10 items)
    - Risk Legend (4 items)
    - Persistence Legend (4 items)
    - Top critical hotspots and chronic sources
    """
    hotspots = persistence_engine.get_all_hotspots()
    insat_obs, viirs_obs, fused, _, alerts = get_pipeline_data()

    critical_hotspots = [h for h in hotspots if h.risk_level == "CRITICAL"]
    primary_industrial = [h for h in hotspots if h.classification == "Possible Industrial Thermal Event"]

    return {
        "title": "AGNI-NETRA // NATIONAL THERMAL PERSISTENCE & CLASSIFICATION AUDIT",
        "generated_at": "11 Sep 2026 00:30 IST",
        "authority": "Smart India Hackathon 2026 // Ministry of Earth Sciences & ISRO Collaboration",
        "summary": {
            "total_monitored_hotspots": len(hotspots),
            "critical_risk_count": len(critical_hotspots),
            "possible_industrial_thermal_events": len(primary_industrial),
            "insat_active_passes": len(insat_obs),
            "nasa_viirs_detections": len(viirs_obs),
            "active_alerts": len(alerts)
        },
        "classification_legend": [
            {"classification": k, "color": v["hex"], "icon": v["icon"], "meaning": v["meaning"]}
            for k, v in CLASSIFICATION_DEFINITIONS.items()
        ],
        "risk_legend": [
            {"risk": k, "color": v["hex"], "icon": v["icon"], "score_range": f"{v['min_score']}–{v['max_score']}"}
            for k, v in RISK_DEFINITIONS.items()
        ],
        "persistence_legend": [
            {"status": k, "color": v["hex"], "icon": v["icon"], "meaning": v["meaning"]}
            for k, v in PERSISTENCE_DEFINITIONS.items()
        ],
        "critical_incidents": critical_hotspots,
        "primary_industrial_sources": primary_industrial
    }


@app.get("/api/satellite-evidence")
def get_satellite_evidence_panel(event_id: Optional[str] = None):
    """
    Unified satellite evidence status panel adhering to prompt:
    🇮🇳 ISRO: INSAT-3D, INSAT-3DR, INSAT-3DS
    🇺🇸 NASA: VIIRS SNPP, VIIRS NOAA-20, VIIRS NOAA-21
    🇪🇺 COPERNICUS: Sentinel-1, Sentinel-2
    🇺🇸 USGS: Landsat-8/9
    """
    insat_obs, viirs_obs, _, _, _ = get_pipeline_data()

    has_insat_3ds = any(o.satellite == "INSAT-3DS" for o in insat_obs)
    has_insat_3dr = any(o.satellite == "INSAT-3DR" for o in insat_obs)
    has_insat_3d = any(o.satellite == "INSAT-3D" for o in insat_obs)

    has_viirs_snpp = any("SNPP" in v.satellite for v in viirs_obs)
    has_viirs_noaa20 = any("NOAA-20" in v.satellite for v in viirs_obs)
    has_viirs_noaa21 = any("NOAA-21" in v.satellite for v in viirs_obs)

    return {
        "providers": [
            {
                "country": "INDIA",
                "agency": "ISRO",
                "agency_display": "🇮🇳 ISRO",
                "satellites": [
                    {"name": "INSAT-3DS", "available": has_insat_3ds, "role": "NRT Fire / Smoke / Weather", "type": "Geostationary 74°E"},
                    {"name": "INSAT-3DR", "available": has_insat_3dr, "role": "NRT Fire / Sounder", "type": "Geostationary 74°E"},
                    {"name": "INSAT-3D", "available": has_insat_3d, "role": "Fire / Meteorological Archive", "type": "Geostationary 82°E"}
                ]
            },
            {
                "country": "USA",
                "agency": "NASA",
                "agency_display": "🇺🇸 NASA",
                "satellites": [
                    {"name": "VIIRS SNPP", "available": has_viirs_snpp, "role": "375m Active Fire", "type": "Sun-synchronous LEO"},
                    {"name": "VIIRS NOAA-20", "available": has_viirs_noaa20, "role": "375m Active Fire", "type": "Sun-synchronous LEO"},
                    {"name": "VIIRS NOAA-21", "available": has_viirs_noaa21, "role": "375m Active Fire", "type": "Sun-synchronous LEO"}
                ]
            },
            {
                "country": "EUROPE",
                "agency": "COPERNICUS",
                "agency_display": "🇪🇺 COPERNICUS",
                "satellites": [
                    {"name": "Sentinel-1", "available": False, "role": "SAR Radar Burn Scar Verification", "type": "Polar SAR (C-band)"},
                    {"name": "Sentinel-2", "available": False, "role": "20m Optical SWIR Plume Imagery", "type": "Multispectral MSI"}
                ]
            },
            {
                "country": "USA",
                "agency": "USGS",
                "agency_display": "🇺🇸 USGS",
                "satellites": [
                    {"name": "Landsat-8/9", "available": False, "role": "30m High-Res Thermal Mapping", "type": "TIRS / OLI"}
                ]
            }
        ]
    }


@app.get("/api/alerts")
def get_active_alerts():
    """Returns real-time multi-satellite alerts."""
    _, _, _, _, alerts = get_pipeline_data()
    return {
        "count": len(alerts),
        "alerts": alerts
    }


@app.get("/api/mosdac/catalog")
def get_mosdac_catalog():
    """Exposes verified MOSDAC catalog entries for dynamic discovery."""
    return insat_provider.discover_datasets()


@app.post("/api/mode/toggle")
def toggle_system_mode(target_mode: str = Query(..., pattern="^(DEMO|LIVE)$")):
    """Toggles platform between DEMO benchmark and LIVE MOSDAC mode."""
    global insat_provider
    target = target_mode.upper()
    insat_provider = INSATDataProvider(mode=target)
    insat_provider.fetch_observations(force_refresh=True)
    return {
        "status": "success",
        "current_mode": target,
        "is_authenticated": insat_provider.authenticated,
        "telemetry": insat_provider.get_nrt_telemetry_status()
    }


# Mount static files for the frontend application
frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend"))
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=False)
