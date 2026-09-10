"""
Automated unit tests for ISRO INSAT-3 Series Data Provider,
Spatial-Temporal Matcher, Persistence Engine, and Alert Rules.
"""

import unittest
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.data_models import INSATObservation, VIIRSObservation
from core.insat_provider import INSATDataProvider, MOSDAC_CATALOG_REGISTRY, INDIAN_INDUSTRIAL_ANCHORS
from core.spatial_matcher import SpatialTemporalMatcher, haversine_distance_km
from core.persistence_engine import PersistenceEngine
from core.alert_engine import AlertEngine


class TestINSATIntegration(unittest.TestCase):

    def setUp(self):
        self.provider = INSATDataProvider(mode="DEMO")
        self.matcher = SpatialTemporalMatcher(max_spatial_distance_km=8.0, max_time_diff_minutes=180.0)
        self.persistence = PersistenceEngine()
        self.alert_engine = AlertEngine()

    def test_mosdac_catalog_discovery(self):
        """Catalog should contain verified INSAT-3D, INSAT-3DR, and INSAT-3DS product IDs."""
        catalog = self.provider.discover_datasets()
        self.assertIn("INSAT-3DS", catalog)
        self.assertIn("INSAT-3DR", catalog)
        self.assertIn("INSAT-3D", catalog)
        
        # Verify Level-2 Fire Product identifiers
        self.assertEqual(catalog["INSAT-3DS"]["FIRE_L2P"]["dataset_id"], "3SIMG_L2P_FIR")
        self.assertEqual(catalog["INSAT-3DR"]["FIRE_L2P"]["dataset_id"], "3RIMG_L2P_FIR")
        self.assertEqual(catalog["INSAT-3D"]["FIRE_L2P"]["dataset_id"], "3DIMG_L2P_FIR")

    def test_nrt_telemetry_fields(self):
        """NRT Telemetry must track Last Observation, Last Retrieved, Data Age, and strict disclaimers."""
        status = self.provider.get_nrt_telemetry_status()
        self.assertEqual(status["operator"], "ISRO / INDIA")
        self.assertIn("last_observation", status)
        self.assertIn("last_retrieved", status)
        self.assertIn("data_age", status)
        self.assertIn("status_label", status)
        # Verify strict demo disclaimer
        self.assertEqual(status["disclaimer"], "DEMO INSAT DATA — SYNTHETIC / NOT ACTUAL ISRO OBSERVATION")

    def test_spatial_distance_haversine(self):
        """Test Haversine distance accuracy."""
        # Jamnagar (22.4707, 70.0577) to slightly offset point
        dist = haversine_distance_km(22.4707, 70.0577, 22.4800, 70.0600)
        self.assertGreater(dist, 0.5)
        self.assertLess(dist, 2.5)

    def test_multi_satellite_agreement_calculation(self):
        """Spatial matcher must evaluate satellite agreement correctly."""
        insat_obs = INSATObservation(
            id="INSAT-3DS_TEST_01",
            satellite="INSAT-3DS",
            instrument="Imager",
            product="3SIMG_L2P_FIR",
            product_level="L2P",
            observation_timestamp="10 Sep 2026 10:00 IST",
            retrieval_timestamp="10 Sep 2026 10:15 IST",
            latitude=22.4707,
            longitude=70.0577,
            geometry={"type": "Polygon", "coordinates": []},
            fire_flag=True,
            smoke_flag=True,
            brightness_temperature=348.5,
            quality="GOOD",
            cloud_information="CLEAR",
            source_url="https://mosdac.gov.in",
            processing_version="v2.1",
            data_age="1h 12m",
            availability_status="DEMO_SYNTHETIC"
        )

        viirs_obs = VIIRSObservation(
            id="VIIRS_TEST_01",
            satellite="VIIRS NOAA-20",
            instrument="VIIRS",
            latitude=22.4720,
            longitude=70.0585,
            bright_ti4=352.0,
            bright_ti5=300.0,
            frp=8.5,
            confidence="high",
            acq_date="10-09-2026",
            acq_time="1012",
            daynight="D"
        )

        score, match_status = self.matcher.compute_match_score(
            distance_km=0.35,
            time_diff_mins=12.0,
            insat_quality="GOOD",
            cloud_info="CLEAR"
        )
        self.assertGreaterEqual(score, 0.80)
        self.assertEqual(match_status, "CONFIRMED_MATCH")

        insat_det, viirs_det, agreement = self.matcher.determine_satellite_agreement(
            insat_obs, viirs_obs, score, distance_km=0.35
        )
        self.assertEqual(insat_det, "YES")
        self.assertEqual(viirs_det, "YES")
        self.assertEqual(agreement, "HIGH")

    def test_overcast_cloud_does_not_force_negative_detection(self):
        """Missing or cloud-obscured INSAT observation must be UNKNOWN, never a false negative."""
        insat_cloudy = INSATObservation(
            id="INSAT-3DR_CLOUDY",
            satellite="INSAT-3DR",
            instrument="Imager",
            product="3RIMG_L2P_FIR",
            product_level="L2P",
            observation_timestamp="10 Sep 2026 10:00 IST",
            retrieval_timestamp="10 Sep 2026 10:15 IST",
            latitude=20.0,
            longitude=80.0,
            geometry={"type": "Polygon", "coordinates": []},
            fire_flag=False,
            quality="POOR",
            cloud_information="OVERCAST",
            source_url="https://mosdac.gov.in",
            processing_version="v2.1",
            data_age="2h 10m",
            availability_status="AVAILABLE"
        )

        insat_det, _, _ = self.matcher.determine_satellite_agreement(
            insat_cloudy, None, 0.0, 0.0
        )
        self.assertEqual(insat_det, "UNKNOWN")

    def test_persistence_engine_calculations(self):
        """Persistence engine should evaluate frequency, day/night curve, and classification."""
        candidates = self.persistence.evaluate_persistent_sources(
            facilities=INDIAN_INDUSTRIAL_ANCHORS[:3],
            insat_observations=[],
            viirs_observations=[]
        )
        self.assertGreaterEqual(len(candidates), 3)
        self.assertTrue(any("Flare" in c.classification for c in candidates))
        self.assertTrue(any("Jamnagar" in c.facility_name for c in candidates))


if __name__ == "__main__":
    unittest.main()
