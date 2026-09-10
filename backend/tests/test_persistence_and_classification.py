"""
Unit tests for the Visual Classification System, Risk and Persistence Separation,
and Long-Term Hotspot Tracking Engine.
"""

import unittest
import os
import sys
from datetime import datetime, timezone

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.data_models import (
    CLASSIFICATION_DEFINITIONS,
    RISK_DEFINITIONS,
    PERSISTENCE_DEFINITIONS,
    DATA_QUALITY_DEFINITIONS,
    HotspotRecord
)
from core.persistence_engine import PersistenceEngine, haversine_distance_m
from core.spatial_matcher import SpatialTemporalMatcher
from core.alert_engine import AlertEngine


class TestClassificationAndPersistence(unittest.TestCase):

    def setUp(self):
        self.persistence = PersistenceEngine(
            persistence_radius_m=800.0,
            min_repeat_count=3,
            min_observation_span_days=14
        )
        self.matcher = SpatialTemporalMatcher()
        self.alert_engine = AlertEngine()

    def test_ten_classification_categories(self):
        """All 10 required visual classification categories must be defined with exact hex codes."""
        expected_categories = {
            "Possible Industrial Thermal Event": "#EF4444",
            "Possible Industrial Fire": "#F97316",
            "Gas Flare": "#A855F7",
            "Industrial Heat": "#F59E0B",
            "Agricultural Burn": "#22C55E",
            "Forest Fire": "#16A34A",
            "Waste Fire": "#A16207",
            "Other Thermal Source": "#3B82F6",
            "Unknown": "#6B7280",
            "Unverified": "#374151"
        }

        self.assertEqual(len(CLASSIFICATION_DEFINITIONS), 10)
        for cat_name, expected_hex in expected_categories.items():
            self.assertIn(cat_name, CLASSIFICATION_DEFINITIONS)
            self.assertEqual(CLASSIFICATION_DEFINITIONS[cat_name]["hex"], expected_hex)
            self.assertIn("meaning", CLASSIFICATION_DEFINITIONS[cat_name])
            self.assertIn("icon", CLASSIFICATION_DEFINITIONS[cat_name])

    def test_risk_colors_independent_of_classification(self):
        """Risk colors must follow: Low Green, Medium Yellow, High Orange, Critical Red."""
        self.assertEqual(RISK_DEFINITIONS["LOW"]["hex"], "#22C55E")
        self.assertEqual(RISK_DEFINITIONS["MEDIUM"]["hex"], "#EAB308")
        self.assertEqual(RISK_DEFINITIONS["HIGH"]["hex"], "#F97316")
        self.assertEqual(RISK_DEFINITIONS["CRITICAL"]["hex"], "#DC2626")

    def test_persistence_colors_independent(self):
        """Persistence colors must follow: Temporary Gray, Recurring Blue, Persistent Purple, Unknown Light Gray."""
        self.assertEqual(PERSISTENCE_DEFINITIONS["Temporary"]["hex"], "#94A3B8")
        self.assertEqual(PERSISTENCE_DEFINITIONS["Recurring"]["hex"], "#3B82F6")
        self.assertEqual(PERSISTENCE_DEFINITIONS["Persistent"]["hex"], "#A855F7")
        self.assertEqual(PERSISTENCE_DEFINITIONS["Unknown"]["hex"], "#CBD5E1")

    def test_primary_sih_classification_rule(self):
        """
        Primary SIH rule verification:
        if anomaly_near_industrial_facility and firms_confidence_is_high and detection_repeats_over_time:
            classification = 'Possible Industrial Thermal Event'
        """
        hotspots = self.persistence.get_all_hotspots()
        primary_events = [h for h in hotspots if h.classification == "Possible Industrial Thermal Event"]
        self.assertGreater(len(primary_events), 0)

        for pe in primary_events:
            self.assertIsNotNone(pe.nearest_facility)
            self.assertLessEqual(pe.facility_distance_m, 1000.0)
            self.assertGreater(pe.total_detections, 1)
            self.assertGreaterEqual(pe.average_confidence, 80.0)
            self.assertIn("✓ High-confidence FIRMS detections", pe.explanation_checklist)
            self.assertIn("✓ Recurring thermal signature", pe.explanation_checklist)

    def test_hotspot_spatial_matching_memory(self):
        """New observation within persistence radius must associate with existing hotspot ID."""
        now = datetime.now(timezone.utc)
        # Coordinates very close to Pune benchmark (18.6280, 73.8120)
        pune_lat, pune_lon = 18.6285, 73.8123
        matched = self.persistence.match_or_create_hotspot(
            lat=pune_lat,
            lon=pune_lon,
            detection_time=now,
            frp=22.0,
            confidence="high",
            satellite="VIIRS NOAA-20"
        )
        self.assertEqual(matched.hotspot_id, "HT-000124")
        self.assertGreaterEqual(matched.total_detections, 28)

    def test_hotspot_shap_explanation(self):
        """Hotspot history deep dive must include SHAP feature importance attributions."""
        hotspot = self.persistence.get_hotspot_by_id("HT-000124")
        self.assertIsNotNone(hotspot)
        self.assertGreater(len(hotspot.shap_features), 0)
        feature_names = [f.feature_name for f in hotspot.shap_features]
        self.assertIn("anomaly_near_industrial_facility", feature_names)
        self.assertIn("firms_confidence_is_high", feature_names)
        self.assertIn("detection_repeats_over_time", feature_names)

    def test_chronic_dashboard_kpis(self):
        """Persistence dashboard must compute aggregate statistics and ranking leaderboards."""
        kpis = self.persistence.get_chronic_dashboard_kpis()
        self.assertIn("summary_kpis", kpis)
        self.assertIn("rankings", kpis)
        self.assertGreater(kpis["summary_kpis"]["total_persistent"], 0)
        self.assertIn("highest_persistence_scores", kpis["rankings"])
        self.assertIn("longest_running", kpis["rankings"])


if __name__ == "__main__":
    unittest.main()
