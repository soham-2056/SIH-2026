import re

with open('backend/core/persistence_engine.py', 'r', encoding='utf-8') as f:
    code = f.read()

# Add database imports
import_str = '''
from core.database import SessionLocal, DBHotspotRecord
import json
'''
code = code.replace('from core.data_models import (', import_str + 'from core.data_models import (')

# In __init__, remove self.hotspot_repository and check if DB is empty
init_replace = '''
        # Long-term memory repository (hotspot_id -> HotspotRecord)
        self.hotspot_repository: Dict[str, HotspotRecord] = {}
        self._init_benchmark_hotspots()
'''
new_init = '''
        with SessionLocal() as db:
            count = db.query(DBHotspotRecord).count()
            if count == 0:
                self._init_benchmark_hotspots()
'''
code = code.replace(init_replace, new_init)

# Helper to convert DBHotspotRecord to HotspotRecord
helper = '''
    def _db_to_model(self, db_rec: DBHotspotRecord) -> HotspotRecord:
        h = HotspotRecord(
            hotspot_id=db_rec.hotspot_id,
            latitude=db_rec.latitude,
            longitude=db_rec.longitude,
            cluster_radius_m=db_rec.cluster_radius_m
        )
        h.name = db_rec.name
        h.first_detected = db_rec.first_detected
        h.last_detected = db_rec.last_detected
        h.total_detections = db_rec.total_detections
        h.unique_detection_days = db_rec.unique_detection_days
        h.observation_span_days = db_rec.observation_span_days
        h.recurrence_rate = db_rec.recurrence_rate
        h.average_detections_per_day = db_rec.average_detections_per_day
        h.max_gap_days = db_rec.max_gap_days
        
        h.average_frp = db_rec.average_frp
        h.maximum_frp = db_rec.maximum_frp
        h.average_confidence = db_rec.average_confidence
        h.high_confidence_detection_count = db_rec.high_confidence_detection_count
        
        h.persistence_score = db_rec.persistence_score
        h.persistence_status = db_rec.persistence_status
        h.persistence_color = db_rec.persistence_color
        
        h.classification = db_rec.classification
        h.classification_color = db_rec.classification_color
        h.classification_confidence = db_rec.classification_confidence
        
        h.risk_score = db_rec.risk_score
        h.risk_level = db_rec.risk_level
        h.risk_color = db_rec.risk_color
        
        h.nearest_facility = db_rec.nearest_facility
        h.facility_type = db_rec.facility_type
        h.facility_distance_m = db_rec.facility_distance_m
        h.state = db_rec.state
        h.district = db_rec.district
        
        h.explanation_checklist = db_rec.get_explanation_checklist()
        h.shap_features = [SHAPFeature(**f) for f in db_rec.get_shap_features()]
        h.satellite_breakdown = db_rec.get_satellite_breakdown()
        h.observations = [ObservationRecord(**o) for o in db_rec.get_observations()]
        return h

    def _model_to_db(self, h: HotspotRecord, db_rec: DBHotspotRecord = None) -> DBHotspotRecord:
        if not db_rec:
            db_rec = DBHotspotRecord(hotspot_id=h.hotspot_id)
        
        db_rec.name = h.name
        db_rec.latitude = h.latitude
        db_rec.longitude = h.longitude
        db_rec.cluster_radius_m = h.cluster_radius_m
        
        db_rec.first_detected = h.first_detected
        db_rec.last_detected = h.last_detected
        db_rec.total_detections = h.total_detections
        db_rec.unique_detection_days = h.unique_detection_days
        db_rec.observation_span_days = h.observation_span_days
        db_rec.recurrence_rate = h.recurrence_rate
        db_rec.average_detections_per_day = h.average_detections_per_day
        db_rec.max_gap_days = h.max_gap_days
        
        db_rec.average_frp = h.average_frp
        db_rec.maximum_frp = h.maximum_frp
        db_rec.average_confidence = h.average_confidence
        db_rec.high_confidence_detection_count = h.high_confidence_detection_count
        
        db_rec.persistence_score = h.persistence_score
        db_rec.persistence_status = h.persistence_status
        db_rec.persistence_color = h.persistence_color
        
        db_rec.classification = h.classification
        db_rec.classification_color = h.classification_color
        db_rec.classification_confidence = h.classification_confidence
        
        db_rec.risk_score = h.risk_score
        db_rec.risk_level = h.risk_level
        db_rec.risk_color = h.risk_color
        
        db_rec.nearest_facility = h.nearest_facility
        db_rec.facility_type = h.facility_type
        db_rec.facility_distance_m = h.facility_distance_m
        db_rec.state = h.state
        db_rec.district = h.district
        
        db_rec.set_explanation_checklist(h.explanation_checklist)
        db_rec.set_shap_features(h.shap_features)
        db_rec.set_satellite_breakdown(h.satellite_breakdown)
        db_rec.set_observations(h.observations)
        return db_rec
'''
code = code.replace('    def _init_benchmark_hotspots(self):', helper + '\n    def _init_benchmark_hotspots(self):')

init_find = '''        for bc in benchmark_configs:
            h = HotspotRecord(
                hotspot_id=bc['hotspot_id'],
                latitude=bc['lat'],
                longitude=bc['lon'],
                cluster_radius_m=220.0
            )'''
init_save = '''        with SessionLocal() as db:
            for bc in benchmark_configs:
                h = HotspotRecord(
                    hotspot_id=bc['hotspot_id'],
                    latitude=bc['lat'],
                    longitude=bc['lon'],
                    cluster_radius_m=220.0
                )'''
code = code.replace(init_find, init_save)

init_end_find = '''            # Mock observations
            h.observations = [
                ObservationRecord(
                    observation_id=f'OBS-{bc["hotspot_id"]}-01',
                    timestamp=now.strftime("%d %b %Y %H:%M IST"),
                    satellite="INSAT-3DS",
                    sensor="IMAGER",
                    confidence=bc['firms_conf'].lower(),
                    frp=bc['avg_frp'],
                    brightness_temp_k=bc['avg_bt'],
                    facility_distance_m=bc['facility_dist_m']
                )
            ]
            self.hotspot_repository[h.hotspot_id] = h'''

init_end_save = '''            # Mock observations
                h.observations = [
                    ObservationRecord(
                        observation_id=f'OBS-{bc["hotspot_id"]}-01',
                        timestamp=now.strftime("%d %b %Y %H:%M IST"),
                        satellite="INSAT-3DS",
                        sensor="IMAGER",
                        confidence=bc['firms_conf'].lower(),
                        frp=bc['avg_frp'],
                        brightness_temp_k=bc['avg_bt'],
                        facility_distance_m=bc['facility_dist_m']
                    )
                ]
                db_rec = self._model_to_db(h)
                db.add(db_rec)
            db.commit()'''
code = code.replace(init_end_find, init_end_save)

get_all_find = '''    def get_all_hotspots(
        self,
        classification: Optional[str] = None,
        persistence_status: Optional[str] = None,
        risk_level: Optional[str] = None,
        state_filter: Optional[str] = None
    ) -> List[HotspotRecord]:
        results = list(self.hotspot_repository.values())'''
get_all_rep = '''    def get_all_hotspots(
        self,
        classification: Optional[str] = None,
        persistence_status: Optional[str] = None,
        risk_level: Optional[str] = None,
        state_filter: Optional[str] = None
    ) -> List[HotspotRecord]:
        with SessionLocal() as db:
            db_records = db.query(DBHotspotRecord).all()
            results = [self._db_to_model(r) for r in db_records]'''
code = code.replace(get_all_find, get_all_rep)

get_id_find = '''    def get_hotspot_by_id(self, hotspot_id: str) -> Optional[HotspotRecord]:
        return self.hotspot_repository.get(hotspot_id)'''
get_id_rep = '''    def get_hotspot_by_id(self, hotspot_id: str) -> Optional[HotspotRecord]:
        with SessionLocal() as db:
            db_rec = db.query(DBHotspotRecord).filter(DBHotspotRecord.hotspot_id == hotspot_id).first()
            if db_rec:
                return self._db_to_model(db_rec)
        return None'''
code = code.replace(get_id_find, get_id_rep)

match_find = '''    def match_or_create_hotspot(
        self,
        lat: float,
        lon: float,
        detection_time: datetime,
        frp: float,
        confidence: str,
        satellite: str,
        nearest_facility: str = None,
        facility_type: str = None,
        facility_distance_m: float = None,
        state: str = "Unknown",
        district: str = "Unknown"
    ) -> HotspotRecord:
        matched_hotspot = None
        min_dist = 999999.0

        for h in self.hotspot_repository.values():
            dist = haversine_distance_m(lat, lon, h.latitude, h.longitude)
            if dist <= self.persistence_radius_m and dist < min_dist:
                min_dist = dist
                matched_hotspot = h'''
match_rep = '''    def match_or_create_hotspot(
        self,
        lat: float,
        lon: float,
        detection_time: datetime,
        frp: float,
        confidence: str,
        satellite: str,
        nearest_facility: str = None,
        facility_type: str = None,
        facility_distance_m: float = None,
        state: str = "Unknown",
        district: str = "Unknown"
    ) -> HotspotRecord:
        with SessionLocal() as db:
            db_records = db.query(DBHotspotRecord).all()
            all_h = [self._db_to_model(r) for r in db_records]
            
            matched_hotspot = None
            matched_db = None
            min_dist = 999999.0

            for h, db_rec in zip(all_h, db_records):
                dist = haversine_distance_m(lat, lon, h.latitude, h.longitude)
                if dist <= self.persistence_radius_m and dist < min_dist:
                    min_dist = dist
                    matched_hotspot = h
                    matched_db = db_rec'''
code = code.replace(match_find, match_rep)

match_end_find = '''        else:
            # Create new hotspot
            new_id = f"HT-{(len(self.hotspot_repository) + 1):06d}"
            matched_hotspot = HotspotRecord(
                hotspot_id=new_id,
                latitude=lat,
                longitude=lon,
                cluster_radius_m=100.0
            )
            matched_hotspot.first_detected = detection_time.strftime("%d %b %Y")
            matched_hotspot.nearest_facility = nearest_facility
            matched_hotspot.facility_type = facility_type
            matched_hotspot.facility_distance_m = facility_distance_m
            matched_hotspot.state = state
            matched_hotspot.district = district

            self.hotspot_repository[new_id] = matched_hotspot'''
match_end_rep = '''        else:
            # Create new hotspot
            new_id = f"HT-{(len(all_h) + 100):06d}"
            matched_hotspot = HotspotRecord(
                hotspot_id=new_id,
                latitude=lat,
                longitude=lon,
                cluster_radius_m=100.0
            )
            matched_hotspot.first_detected = detection_time.strftime("%d %b %Y")
            matched_hotspot.nearest_facility = nearest_facility
            matched_hotspot.facility_type = facility_type
            matched_hotspot.facility_distance_m = facility_distance_m
            matched_hotspot.state = state
            matched_hotspot.district = district'''
code = code.replace(match_end_find, match_end_rep)

ret_find = '''        return matched_hotspot'''
ret_rep = '''            db_rec_final = self._model_to_db(matched_hotspot, matched_db)
            db.add(db_rec_final)
            db.commit()
            return matched_hotspot'''
code = code.replace(ret_find, ret_rep, 1)

with open('backend/core/persistence_engine.py', 'w', encoding='utf-8') as f:
    f.write(code)

print('Updated persistence_engine.py')
