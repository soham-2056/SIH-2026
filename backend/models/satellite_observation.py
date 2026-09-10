from sqlalchemy import Column, Integer, String, Float, DateTime
from core.database import Base
from datetime import datetime

class DBSatelliteObservation(Base):
    __tablename__ = "satellite_observations"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    source = Column(String, index=True) # NASA_FIRMS, MOSDAC
    product = Column(String) # VIIRS_NOAA21_NRT
    satellite = Column(String) # NOAA-21, INSAT-3DR
    instrument = Column(String) # VIIRS, IMAGER

    latitude = Column(Float, index=True)
    longitude = Column(Float, index=True)

    observation_timestamp = Column(DateTime, index=True)
    acq_date = Column(String)
    acq_time = Column(String)

    confidence = Column(String) # For FIRMS: n, l, h, or number
    frp = Column(Float)
    bright_ti5 = Column(Float)

    scan = Column(Float, nullable=True)
    track = Column(Float, nullable=True)
    daynight = Column(String, nullable=True)
    version = Column(String, nullable=True)
    type = Column(String, nullable=True)

    source_record_id = Column(String, unique=True, index=True) # Unique ID for deduplication
    
    ingested_at = Column(DateTime, default=datetime.utcnow)
    raw_data = Column(String) # JSON payload

