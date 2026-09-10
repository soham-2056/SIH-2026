"""
Configurable Multi-Satellite Alert Engine.
Prioritizes Risk Severity while keeping Classification distinct.

Rule:
"Alerts should prioritize risk severity.
 Do NOT make every industrial event red automatically.
 The classification and risk remain separate."
"""

from typing import List, Dict, Any
from datetime import datetime, timezone
from core.data_models import (
    FusedThermalEvent,
    CLASSIFICATION_DEFINITIONS,
    RISK_DEFINITIONS,
    PERSISTENCE_DEFINITIONS
)


class AlertRule:
    def __init__(self, rule_id: str, name: str, description: str, severity: str, condition_fn):
        self.rule_id = rule_id
        self.name = name
        self.description = description
        self.severity = severity  # CRITICAL, HIGH, MEDIUM, LOW
        self.condition_fn = condition_fn


class AlertEngine:
    """
    Manages and evaluates configurable multi-satellite alert rules.
    """

    def __init__(self):
        self.rules: List[AlertRule] = []
        self._init_default_rules()

    def _init_default_rules(self):
        # Rule 1: Critical Risk Multi-Satellite Escalation
        self.rules.append(
            AlertRule(
                rule_id="RULE_01",
                name="Critical Industrial Proximity Alert",
                description="High-confidence multi-satellite anomaly near high-density infrastructure",
                severity="CRITICAL",
                condition_fn=lambda event: (
                    event.risk_level == "CRITICAL" and
                    event.satellite_agreement in ["HIGH", "MEDIUM"]
                )
            )
        )

        # Rule 2: Possible Industrial Thermal Event Notification
        self.rules.append(
            AlertRule(
                rule_id="RULE_02",
                name="Primary SIH Industrial Anomaly Notification",
                description="High-confidence repeat thermal anomaly within industrial perimeter",
                severity="HIGH",
                condition_fn=lambda event: (
                    event.scientific_classification == "Possible Industrial Thermal Event"
                )
            )
        )

        # Rule 3: Chronic Flaring Persistence Advisory
        self.rules.append(
            AlertRule(
                rule_id="RULE_03",
                name="Gas Flare Operational Monitoring",
                description="Persistent thermal flaring signature active under normal parameters",
                severity="MEDIUM",
                condition_fn=lambda event: (
                    event.scientific_classification == "Gas Flare" and
                    event.risk_level != "CRITICAL"
                )
            )
        )

        # Rule 4: Geostationary Rapid Alert (Pending polar pass)
        self.rules.append(
            AlertRule(
                rule_id="RULE_04",
                name="Geostationary Rapid Alert (Pending VIIRS Pass)",
                description="INSAT fire flag detected ahead of polar VIIRS overpass",
                severity="MEDIUM",
                condition_fn=lambda event: (
                    event.insat_detected == "YES" and
                    event.viirs_detected in ["NO", "UNKNOWN"]
                )
            )
        )

    def evaluate_events(self, events: List[FusedThermalEvent]) -> List[Dict[str, Any]]:
        """Evaluates all active rules against fused events."""
        triggered_alerts = []
        now_str = datetime.now(timezone.utc).strftime("%d %b %Y %H:%M IST")

        for event in events:
            for rule in self.rules:
                if rule.condition_fn(event):
                    risk_info = RISK_DEFINITIONS.get(rule.severity, RISK_DEFINITIONS["MEDIUM"])
                    class_info = CLASSIFICATION_DEFINITIONS.get(
                        event.scientific_classification,
                        CLASSIFICATION_DEFINITIONS["Unknown"]
                    )
                    persist_info = PERSISTENCE_DEFINITIONS.get(
                        event.persistence_status,
                        PERSISTENCE_DEFINITIONS["Unknown"]
                    )

                    triggered_alerts.append({
                        "alert_id": f"ALT_{rule.rule_id}_{event.id}",
                        "rule_name": rule.name,
                        "rule_description": rule.description,
                        "severity": rule.severity,
                        "severity_color": risk_info["hex"],
                        "risk_score": event.risk_score,
                        "event_id": event.id,
                        "hotspot_id": event.hotspot_id,
                        "facility": event.nearest_facility or "Regional Cluster",
                        "facility_distance_m": event.facility_distance_m,
                        "location": f"{event.latitude:.4f}°N, {event.longitude:.4f}°E",
                        "agreement": event.satellite_agreement,
                        "classification": event.scientific_classification,
                        "classification_color": class_info["hex"],
                        "classification_icon": class_info["icon"],
                        "persistence_status": event.persistence_status,
                        "persistence_color": persist_info["hex"],
                        "timestamp": event.timestamp,
                        "triggered_at": now_str
                    })

        # Prioritize alerts strictly by severity: CRITICAL -> HIGH -> MEDIUM -> LOW
        severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        triggered_alerts.sort(key=lambda a: severity_order.get(a["severity"], 99))
        return triggered_alerts
