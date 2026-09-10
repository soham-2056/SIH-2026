import os
import sys
from datetime import datetime
import json
import logging

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy.orm import Session
from core.database import SessionLocal, engine, Base
from models.satellite_observation import DBSatelliteObservation
from services.firms.client import FIRMSClient
from core.persistence_engine import PersistenceEngine

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("FIRMSIngestion")

# Make sure tables exist
Base.metadata.create_all(bind=engine)

def run_ingestion_job():
    logger.info("Starting FIRMS Data Ingestion Job...")
    client = FIRMSClient()
    
    # We will fetch for multiple sources if needed, prioritizing VIIRS_NOAA21_NRT
    sources = ["VIIRS_NOAA21_NRT", "VIIRS_NOAA20_NRT", "VIIRS_SNPP_NRT"]
    
    db = SessionLocal()
    persistence_engine = PersistenceEngine()
    
    total_new = 0
    
    try:
        for source in sources:
            logger.info(f"Fetching {source} data from FIRMS API...")
            data = client.fetch_recent_observations(source=source, days=1)
            
            logger.info(f"Received {len(data)} records for {source}")
            
            new_records = 0
            for row in data:
                # Deduplication key
                lat = float(row.get("latitude", 0))
                lon = float(row.get("longitude", 0))
                acq_date = row.get("acq_date", "")
                acq_time = row.get("acq_time", "")
                satellite = row.get("satellite", "")
                
                source_record_id = f"{source}_{satellite}_{acq_date}_{acq_time}_{lat:.4f}_{lon:.4f}"
                
                # Check if exists
                exists = db.query(DBSatelliteObservation).filter(DBSatelliteObservation.source_record_id == source_record_id).first()
                if exists:
                    continue
                    
                # Create observation record
                try:
                    obs_time = datetime.strptime(f"{acq_date} {acq_time}", "%Y-%m-%d %H%M")
                except ValueError:
                    obs_time = datetime.utcnow()
                    
                frp = float(row.get("frp", 0))
                confidence = row.get("confidence", "")
                
                obs = DBSatelliteObservation(
                    source="NASA_FIRMS",
                    product=source,
                    satellite=satellite,
                    instrument=row.get("instrument", ""),
                    latitude=lat,
                    longitude=lon,
                    observation_timestamp=obs_time,
                    acq_date=acq_date,
                    acq_time=acq_time,
                    confidence=confidence,
                    frp=frp,
                    bright_ti5=float(row.get("bright_ti5", 0)) if row.get("bright_ti5") else None,
                    scan=float(row.get("scan", 0)) if row.get("scan") else None,
                    track=float(row.get("track", 0)) if row.get("track") else None,
                    daynight=row.get("daynight", ""),
                    version=row.get("version", ""),
                    type=row.get("type", ""),
                    source_record_id=source_record_id,
                    raw_data=json.dumps(row)
                )
                
                db.add(obs)
                new_records += 1
                
                # Update persistence engine memory (hotspots)
                # Ensure confidence maps properly
                persistence_engine.match_or_create_hotspot(
                    lat=lat,
                    lon=lon,
                    detection_time=obs_time,
                    frp=frp,
                    confidence=confidence,
                    satellite=satellite
                )
            
            db.commit()
            total_new += new_records
            logger.info(f"Inserted {new_records} new records for {source}")
            
    except Exception as e:
        logger.error(f"Error in FIRMS Ingestion Job: {e}")
        db.rollback()
    finally:
        db.close()
        
    logger.info(f"FIRMS Data Ingestion Job Complete. Total new observations: {total_new}")

if __name__ == "__main__":
    run_ingestion_job()
