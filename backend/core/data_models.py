"""
ISRO INSAT-3 Series & Multi-Satellite Data Models.
Implements:
1. Classification & Color System (10 categories with strict hex codes and icons)
2. Three Independent Visual Dimensions: Classification, Risk, Persistence
3. Data Quality & Satellite Source standards
4. Hotspot Record with spatial-temporal persistence metrics and explainability (SHAP)
"""

from typing import Optional, Dict, Any, List
from enum import Enum
from pydantic import BaseModel, Field


# =====================================================================
# 1. VISUAL CLASSIFICATION SYSTEM (10 Categories)
# =====================================================================

CLASSIFICATION_DEFINITIONS = {
    "Possible Industrial Thermal Event": {
        "hex": "#EF4444",
        "color_name": "Red",
        "icon": "🔴",
        "svg_icon": "flame",
        "meaning": "High-confidence anomaly near industrial facility with repeated detections",
        "is_sih_primary": True
    },
    "Possible Industrial Fire": {
        "hex": "#F97316",
        "color_name": "Orange",
        "icon": "🟠",
        "svg_icon": "fire-alert",
        "meaning": "Evidence suggests a possible industrial fire",
        "is_sih_primary": False
    },
    "Gas Flare": {
        "hex": "#A855F7",
        "color_name": "Purple",
        "icon": "🟣",
        "svg_icon": "flare",
        "meaning": "Persistent/repeated thermal activity associated with a likely flare",
        "is_sih_primary": False
    },
    "Industrial Heat": {
        "hex": "#F59E0B",
        "color_name": "Yellow/Amber",
        "icon": "🟡",
        "svg_icon": "factory",
        "meaning": "Persistent industrial thermal source without sufficient fire evidence",
        "is_sih_primary": False
    },
    "Agricultural Burn": {
        "hex": "#22C55E",
        "color_name": "Green",
        "icon": "🟢",
        "svg_icon": "tractor",
        "meaning": "Thermal activity likely associated with agricultural burning",
        "is_sih_primary": False
    },
    "Forest Fire": {
        "hex": "#16A34A",
        "color_name": "Forest Green",
        "icon": "🟢",
        "svg_icon": "tree",
        "meaning": "Thermal activity associated with forest/vegetation area",
        "is_sih_primary": False
    },
    "Waste Fire": {
        "hex": "#A16207",
        "color_name": "Brown",
        "icon": "🟤",
        "svg_icon": "trash",
        "meaning": "Thermal activity associated with waste/landfill facilities",
        "is_sih_primary": False
    },
    "Other Thermal Source": {
        "hex": "#3B82F6",
        "color_name": "Blue",
        "icon": "🔵",
        "svg_icon": "anomaly",
        "meaning": "Thermal anomaly with another probable explanation",
        "is_sih_primary": False
    },
    "Unknown": {
        "hex": "#6B7280",
        "color_name": "Gray",
        "icon": "⚪",
        "svg_icon": "question",
        "meaning": "Insufficient evidence for reliable classification",
        "is_sih_primary": False
    },
    "Unverified": {
        "hex": "#374151",
        "color_name": "Dark Gray",
        "icon": "⚫",
        "svg_icon": "shield-alert",
        "meaning": "Detection exists but supporting evidence is unavailable",
        "is_sih_primary": False
    }
}


# =====================================================================
# 2. RISK SYSTEM (Answers: "How concerning is it?")
# =====================================================================

RISK_DEFINITIONS = {
    "LOW": {
        "hex": "#22C55E",
        "color_name": "Green",
        "icon": "🟢",
        "min_score": 0,
        "max_score": 39
    },
    "MEDIUM": {
        "hex": "#EAB308",
        "color_name": "Yellow",
        "icon": "🟡",
        "min_score": 40,
        "max_score": 69
    },
    "HIGH": {
        "hex": "#F97316",
        "color_name": "Orange",
        "icon": "🟠",
        "min_score": 70,
        "max_score": 84
    },
    "CRITICAL": {
        "hex": "#DC2626",
        "color_name": "Red",
        "icon": "🔴",
        "min_score": 85,
        "max_score": 100
    }
}


# =====================================================================
# 3. PERSISTENCE SYSTEM (Answers: "How often does it happen?")
# =====================================================================

PERSISTENCE_DEFINITIONS = {
    "Temporary": {
        "hex": "#94A3B8",
        "color_name": "Gray",
        "icon": "⚪",
        "meaning": "One-time or short-duration detection"
    },
    "Recurring": {
        "hex": "#3B82F6",
        "color_name": "Blue",
        "icon": "🔵",
        "meaning": "Repeated detections at the same location"
    },
    "Persistent": {
        "hex": "#A855F7",
        "color_name": "Purple",
        "icon": "🟣",
        "meaning": "Repeated activity over a substantial observation period"
    },
    "Unknown": {
        "hex": "#CBD5E1",
        "color_name": "Light Gray",
        "icon": "⚪",
        "meaning": "Insufficient historical evidence"
    }
}


# =====================================================================
# 4. DATA QUALITY & SATELLITE SOURCES
# =====================================================================

DATA_QUALITY_DEFINITIONS = {
    "VERIFIED": {"hex": "#22C55E", "color_name": "Green", "icon": "🟢"},
    "PARTIAL": {"hex": "#3B82F6", "color_name": "Blue", "icon": "🔵"},
    "STALE": {"hex": "#F59E0B", "color_name": "Amber", "icon": "🟡"},
    "MISSING": {"hex": "#6B7280", "color_name": "Gray", "icon": "⚪"},
    "ERROR": {"hex": "#EF4444", "color_name": "Red", "icon": "🔴"},
    "DEMO": {"hex": "#A855F7", "color_name": "Purple", "icon": "🟣"}
}

SATELLITE_SOURCE_BADGES = {
    "ISRO": {"display": "🇮🇳 ISRO / MOSDAC", "country": "INDIA"},
    "NASA": {"display": "🇺🇸 NASA / FIRMS", "country": "USA"},
    "COPERNICUS": {"display": "🇪🇺 COPERNICUS", "country": "EUROPE"},
    "USGS": {"display": "🇺🇸 USGS / LANDSAT", "country": "USA"}
}


# =====================================================================
# DATA MODELS
# =====================================================================

class INSATObservation(BaseModel):
    """INSAT Observation Model."""
    id: str
    satellite: str = Field(..., description="ISRO satellite: INSAT-3D, INSAT-3DR, INSAT-3DS")
    instrument: str = Field("Imager", description="Sensor onboard: Imager or Sounder")
    product: str = Field(..., description="MOSDAC product name e.g. 3SIMG_L2P_FIR")
    product_level: str = Field("L2P", description="Processing level: L1B, L2P, L2B")
    observation_timestamp: str = Field(..., description="Timestamp in UTC and IST format")
    retrieval_timestamp: str = Field(..., description="Ingestion timestamp")
    latitude: float
    longitude: float
    geometry: Dict[str, Any] = Field(..., description="GeoJSON Point or Polygon footprint (~4km resolution)")
    fire_flag: Optional[bool] = Field(None, description="Fire detection flag from MIR & TIR-1")
    smoke_flag: Optional[bool] = Field(None, description="Smoke flag if available")
    brightness_temperature: Optional[float] = Field(None, description="Brightness temperature in Kelvin (MIR/TIR)")
    quality: str = Field("GOOD", description="Quality flag: GOOD, PARTIAL, POOR, MISSING, STALE")
    cloud_information: Optional[str] = Field(None, description="Cloud mask info: CLEAR, PARTLY_CLOUDY, OVERCAST")
    source_url: str = Field(..., description="MOSDAC repository URL")
    processing_version: str = Field("v2.1", description="Algorithm processing version")
    data_age: str = Field(..., description="Time elapsed since observation")
    availability_status: str = Field("AVAILABLE", description="Status: AVAILABLE, ACCESS_REQUIRED, DEMO")


class EventSourceRelationship(BaseModel):
    """Spatial-temporal relationship between two satellite observations."""
    source_a: str = Field(..., description="ID of first observation (e.g. INSAT)")
    source_b: str = Field(..., description="ID of second observation (e.g. VIIRS)")
    distance: float = Field(..., description="Spatial distance in kilometers")
    time_difference: float = Field(..., description="Time difference in minutes")
    match_score: float = Field(..., description="Matching score 0.0 - 1.0")
    match_status: str = Field(..., description="CONFIRMED_MATCH, POSSIBLE_SAME_EVENT, INDEPENDENT_EVENT")


class VIIRSObservation(BaseModel):
    """NASA VIIRS Observation Model."""
    id: str
    satellite: str = Field(..., description="VIIRS SNPP, VIIRS NOAA-20, VIIRS NOAA-21")
    instrument: str = Field("VIIRS", description="Visible Infrared Imaging Radiometer Suite")
    latitude: float
    longitude: float
    bright_ti4: float = Field(..., description="I-4 thermal band (375m) brightness temp in K")
    bright_ti5: float = Field(..., description="I-5 thermal band brightness temp in K")
    frp: float = Field(..., description="Fire Radiative Power in MW")
    confidence: str = Field(..., description="Confidence: low, nominal, high")
    acq_date: str
    acq_time: str
    daynight: str


class ObservationRecord(BaseModel):
    """Individual historical observation for a hotspot."""
    observation_id: str
    timestamp: str
    date_str: str
    latitude: float
    longitude: float
    satellite: str
    sensor: str
    confidence: str
    confidence_pct: float
    frp: float
    brightness_temp_k: Optional[float] = None
    facility_distance_m: Optional[float] = None
    satellite_agency: str = "NASA"


class SHAPFeature(BaseModel):
    """SHAP feature attribution for explainable AI classification."""
    feature_name: str
    display_name: str
    value: Any
    shap_value: float
    impact: str  # POSITIVE or NEGATIVE


class HotspotRecord(BaseModel):
    """
    Long-term Hotspot Record.
    Core principle: "We don't just detect hotspots. We remember them."
    """
    hotspot_id: str = Field(..., description="Stable identifier e.g. HT-000124")
    name: str
    state: str
    district: str
    latitude: float
    longitude: float
    cluster_radius_m: float = 250.0

    # Temporal Persistence Metrics
    first_detected: str
    last_detected: str
    total_detections: int
    unique_detection_days: int
    observation_span_days: int
    average_detections_per_day: float
    maximum_gap_days: int
    recurrence_rate: float  # unique_days / span_days

    # Thermal Characteristics
    average_frp: float
    maximum_frp: float
    average_confidence: float
    high_confidence_detection_count: int

    # Persistence Dimension
    persistence_score: float = Field(..., description="Normalized multi-factor score 0-100")
    persistence_status: str = Field(..., description="Temporary, Recurring, Persistent, Unknown")
    persistence_color: str

    # Classification Dimension (What is it?)
    classification: str = Field(..., description="One of 10 visual classification categories")
    classification_color: str
    classification_confidence: float

    # Risk Dimension (How concerning is it?)
    risk_score: float = Field(..., description="0-100 Risk Score")
    risk_level: str = Field(..., description="LOW, MEDIUM, HIGH, CRITICAL")
    risk_color: str

    # Industrial Context
    nearest_facility: Optional[str] = None
    facility_type: Optional[str] = None
    facility_distance_m: Optional[float] = None

    # Scientific Explanation & SIH Checklist
    explanation_checklist: List[str] = []
    shap_features: List[SHAPFeature] = []

    # Historical Observations
    observations: List[ObservationRecord] = []

    # Multi-Satellite Breakdown
    satellite_breakdown: Dict[str, int] = {}


class FusedThermalEvent(BaseModel):
    """Multi-Satellite Fused Thermal Event."""
    id: str
    hotspot_id: Optional[str] = None
    title: str
    latitude: float
    longitude: float
    timestamp: str

    # Multi-Satellite Verification
    insat_detected: str = Field("UNKNOWN", description="YES / NO / UNKNOWN")
    viirs_detected: str = Field("UNKNOWN", description="YES / NO / UNKNOWN")
    satellite_agreement: str = Field("UNKNOWN", description="HIGH / MEDIUM / LOW / UNKNOWN")

    # Observations
    insat_observation: Optional[INSATObservation] = None
    viirs_observation: Optional[VIIRSObservation] = None
    relationship: Optional[EventSourceRelationship] = None

    # Context
    nearest_facility: Optional[str] = None
    facility_type: Optional[str] = None
    facility_distance_m: Optional[float] = None

    # 3 Independent Visual Dimensions
    scientific_classification: str
    classification_color: str = "#6B7280"
    confidence_score: float
    firms_confidence: str = "HIGH"

    risk_level: str = Field("MEDIUM", description="CRITICAL, HIGH, MEDIUM, LOW")
    risk_score: float = 65.0
    risk_color: str = "#EAB308"

    persistence_status: str = Field("Recurring", description="Temporary, Recurring, Persistent, Unknown")
    persistence_color: str = "#3B82F6"
    persistence_score: float = 72.0


class PersistentSourceCandidate(BaseModel):
    """Persistent Source candidate for chronic view."""
    id: str
    hotspot_id: str
    facility_name: str
    facility_type: str
    state: str
    district: str
    latitude: float
    longitude: float

    # Temporal & Radiative Metrics
    insat_detection_count: int
    insat_observation_frequency: str
    insat_temporal_coverage: float
    insat_day_night_behavior: str
    insat_thermal_intensity: Optional[float] = None
    insat_consistency_with_viirs: str

    persistence_score: float
    persistence_status: str
    persistence_color: str

    classification: str
    classification_color: str

    risk_level: str
    risk_score: float
    risk_color: str

    observation_span_days: int
    total_detections: int
    avg_frp: float
    max_frp: float
    status: str
    last_detected: str
