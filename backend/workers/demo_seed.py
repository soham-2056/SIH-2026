import os
import sys
import random
from datetime import datetime, timezone
import logging

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy.orm import Session
from core.database import SessionLocal, engine, Base
from models.satellite_observation import DBSatelliteObservation
from core.persistence_engine import PersistenceEngine

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("DemoSeed")

def generate_demo_data(num_points=15):
    logger.info(f"Generating {num_points} demo thermal observations across India...")
    
    db = SessionLocal()
    persistence_engine = PersistenceEngine()
    
    now = datetime.now(timezone.utc)
    
    # Bounding box roughly for India
    min_lat, max_lat = 8.4, 37.6
    min_lon, max_lon = 68.7, 97.25
    
    new_records = 0
    
    try:
        from core.insat_provider import INDIAN_INDUSTRIAL_ANCHORS
        for i in range(num_points):
            anchor = INDIAN_INDUSTRIAL_ANCHORS[i % len(INDIAN_INDUSTRIAL_ANCHORS)]
            
            # Add small random jitter (approx 20km) around the anchor
            lat = round(anchor["lat"] + random.uniform(-0.15, 0.15), 4)
            lon = round(anchor["lon"] + random.uniform(-0.15, 0.15), 4)
            
            # Manipulate frp and confidence based on index to cover all classifications
            if i % 8 == 0:
                frp = round(random.uniform(50.0, 150.0), 1)
                confidence = "HIGH"
                # For Critical Possible Industrial Thermal Event (high conf, near facility)
                lat, lon = anchor["lat"] + random.uniform(-0.002, 0.002), anchor["lon"] + random.uniform(-0.002, 0.002)
            elif i % 8 == 1:
                frp = round(random.uniform(10.0, 40.0), 1)
                confidence = "HIGH"
                # Gas Flare (if anchor has flare expected)
            elif i % 8 == 2:
                frp = round(random.uniform(45.0, 80.0), 1)
                confidence = "HIGH"
                # Forest Fire (high FRP, far from facility)
                lat, lon = anchor["lat"] + random.uniform(0.3, 0.6), anchor["lon"] + random.uniform(0.3, 0.6)
            elif i % 8 == 3:
                frp = round(random.uniform(26.0, 39.0), 1)
                confidence = "NOMINAL"
                # Agricultural Burn (medium FRP, far from facility)
                lat, lon = anchor["lat"] + random.uniform(0.3, 0.6), anchor["lon"] + random.uniform(0.3, 0.6)
            elif i % 8 == 4:
                frp = round(random.uniform(10.0, 24.0), 1)
                confidence = "HIGH"
                # Waste Fire (low FRP, high confidence, far)
                lat, lon = anchor["lat"] + random.uniform(0.3, 0.6), anchor["lon"] + random.uniform(0.3, 0.6)
            elif i % 8 == 5:
                frp = round(random.uniform(10.0, 50.0), 1)
                confidence = "HIGH"
                # Industrial Heat (high conf, < 1500m)
                lat, lon = anchor["lat"] + random.uniform(-0.008, 0.008), anchor["lon"] + random.uniform(-0.008, 0.008)
            elif i % 8 == 6:
                frp = round(random.uniform(10.0, 50.0), 1)
                confidence = "NOMINAL"
                # Possible Industrial Fire (< 3000m, nominal conf)
                lat, lon = anchor["lat"] + random.uniform(-0.02, 0.02), anchor["lon"] + random.uniform(-0.02, 0.02)
            else:
                frp = round(random.uniform(5.0, 20.0), 1)
                confidence = "LOW"
                # Other Thermal Source
                lat, lon = anchor["lat"] + random.uniform(0.3, 0.6), anchor["lon"] + random.uniform(0.3, 0.6)

            satellite = random.choice(["NOAA-21", "NOAA-20", "SNPP"])
            
            source_record_id = f"DEMO_{satellite}_{now.strftime('%Y%m%d_%H%M%S')}_{lat:.4f}_{lon:.4f}_{i}"
            
            obs = DBSatelliteObservation(
                source="NASA_FIRMS",
                product=f"VIIRS_{satellite.replace('-', '')}_NRT",
                satellite=satellite,
                instrument="VIIRS",
                latitude=lat,
                longitude=lon,
                observation_timestamp=now,
                acq_date=now.strftime("%Y-%m-%d"),
                acq_time=now.strftime("%H%M"),
                confidence=confidence,
                frp=frp,
                source_record_id=source_record_id,
                raw_data="{}"
            )
            db.add(obs)
            
            # Match or create hotspot
            hp = persistence_engine.match_or_create_hotspot(
                lat=lat,
                lon=lon,
                detection_time=now,
                frp=frp,
                confidence=confidence,
                satellite=satellite
            )
            
            # Update DB with changes to the hotspot repository
            db_rec = db.query(persistence_engine._model_to_db(hp).__class__).filter_by(hotspot_id=hp.hotspot_id).first()
            if db_rec:
                persistence_engine._model_to_db(hp, db_rec)
            else:
                db_rec = persistence_engine._model_to_db(hp)
                db.add(db_rec)
                
            db.commit()
            new_records += 1
            
        logger.info(f"Successfully inserted {new_records} new demo records.")
        
    except Exception as e:
        logger.error(f"Error generating demo data: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    generate_demo_data(25)
