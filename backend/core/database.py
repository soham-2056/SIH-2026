import os
import json
from sqlalchemy import create_engine, Column, Integer, String, Float, Text
from sqlalchemy.orm import declarative_base, sessionmaker

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "agni_netra.db")
engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class DBHotspotRecord(Base):
    __tablename__ = "hotspots"

    hotspot_id = Column(String, primary_key=True, index=True)
    name = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)
    cluster_radius_m = Column(Float)
    
    first_detected = Column(String)
    last_detected = Column(String)
    total_detections = Column(Integer)
    unique_detection_days = Column(Integer)
    observation_span_days = Column(Integer)
    recurrence_rate = Column(Float)
    average_detections_per_day = Column(Float)
    max_gap_days = Column(Integer)
    
    average_frp = Column(Float)
    maximum_frp = Column(Float)
    average_confidence = Column(Float)
    high_confidence_detection_count = Column(Integer)
    
    persistence_score = Column(Float)
    persistence_status = Column(String)
    persistence_color = Column(String)
    
    classification = Column(String)
    classification_color = Column(String)
    classification_confidence = Column(Float)
    
    risk_score = Column(Float)
    risk_level = Column(String)
    risk_color = Column(String)
    
    nearest_facility = Column(String, nullable=True)
    facility_type = Column(String, nullable=True)
    facility_distance_m = Column(Float, nullable=True)
    state = Column(String)
    district = Column(String)
    
    # Store JSON strings for complex types
    explanation_checklist = Column(Text)
    shap_features = Column(Text)
    satellite_breakdown = Column(Text)
    observations = Column(Text)

    def set_explanation_checklist(self, data):
        self.explanation_checklist = json.dumps(data)

    def get_explanation_checklist(self):
        return json.loads(self.explanation_checklist) if self.explanation_checklist else []

    def set_shap_features(self, data):
        self.shap_features = json.dumps([f.__dict__ if hasattr(f, "__dict__") else f for f in data])

    def get_shap_features(self):
        return json.loads(self.shap_features) if self.shap_features else []

    def set_satellite_breakdown(self, data):
        self.satellite_breakdown = json.dumps(data)

    def get_satellite_breakdown(self):
        return json.loads(self.satellite_breakdown) if self.satellite_breakdown else {}

    def set_observations(self, data):
        self.observations = json.dumps([o.__dict__ if hasattr(o, "__dict__") else o for o in data])

    def get_observations(self):
        return json.loads(self.observations) if self.observations else []


# Import models here to ensure they are registered with Base before create_all
try:
    from models.satellite_observation import DBSatelliteObservation
except ImportError:
    pass

# Create all tables
Base.metadata.create_all(bind=engine)
