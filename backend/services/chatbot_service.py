import os
import re
import json
import uuid
from typing import Dict, Any, List, Optional
from core.data_models import FusedThermalEvent

# Try importing google generative ai
try:
    import google.generativeai as genai
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

class ChatbotService:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.use_llm = HAS_GENAI and self.api_key
        
        if self.use_llm:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-2.5-flash')
        
        # Keep a simple history map for demo purposes (in memory)
        self.conversations = {}

    def handle_message(
        self, 
        message: str, 
        conversation_id: str, 
        pipeline_data: tuple
    ) -> Dict[str, Any]:
        
        insat_obs, viirs_obs, fused, persistent, alerts = pipeline_data
        
        # Save minimal history context
        if conversation_id not in self.conversations:
            self.conversations[conversation_id] = []
        
        # If LLM is available, use it!
        if self.use_llm:
            try:
                return self._handle_with_llm(message, conversation_id, fused, alerts, persistent)
            except Exception as e:
                print(f"[ChatbotService] LLM Failed, falling back to heuristic: {e}")
                # Fallback to heuristic if quota exceeded or error
                pass
                
        # Heuristic / Rule-based fallback if no API key
        return self._handle_with_heuristics(message, conversation_id, fused, alerts, persistent)

    def _handle_with_llm(self, message: str, conv_id: str, fused: List, alerts: List, persistent: List) -> Dict[str, Any]:
        # Context generation
        context = "System Data Summary:\n"
        context += f"- Active Hotspots: {len(fused)}\n"
        context += f"- Active Alerts: {len(alerts)}\n"
        
        critical_alerts = [a for a in alerts if a['severity'] == 'CRITICAL']
        high_alerts = [a for a in alerts if a['severity'] == 'HIGH']
        
        context += f"- Critical Alerts: {len(critical_alerts)}\n"
        context += f"- High Alerts: {len(high_alerts)}\n\n"
        
        context += "Top Hotspots Details:\n"
        for idx, f in enumerate(sorted(fused, key=lambda x: x.risk_score, reverse=True)[:5]):
            context += f"ID: {f.hotspot_id}, Risk: {f.risk_score} ({f.risk_level}), FRP: {f.frp} MW, Facility: {f.nearest_facility}, Persistence: {f.persistence_status}\n"
            
        system_prompt = f"""You are Thermal AI, the intelligent assistant for the SIH 2026 Thermal Anomaly Platform.
You analyze satellite data (INSAT & VIIRS) to find industrial thermal anomalies.
Do not invent data. Use ONLY the following real-time data:
{context}

User's message: {message}

Respond concisely and professionally. If they ask for high or critical alerts, mention the numbers.
"""
        
        response = self.model.generate_content(system_prompt)
        text_resp = response.text
        
        # Very simple data extraction to populate UI cards based on intent
        data_payload = {"type": "none", "items": []}
        msg_lower = message.lower()
        if "critical" in msg_lower or "high" in msg_lower or "alert" in msg_lower:
            data_payload["type"] = "alerts"
            for a in (critical_alerts + high_alerts)[:3]:
                data_payload["items"].append({
                    "id": a['alert_id'],
                    "title": a['rule_name'],
                    "description": f"Severity: {a['severity']}. Classification: {a['classification']}",
                    "icon": "🚨" if a['severity'] == 'CRITICAL' else "⚠️"
                })
        elif "hotspot" in msg_lower:
            data_payload["type"] = "hotspots"
            for f in sorted(fused, key=lambda x: x.risk_score, reverse=True)[:3]:
                data_payload["items"].append({
                    "id": f.hotspot_id,
                    "title": f"Hotspot {f.hotspot_id}",
                    "description": f"Risk: {f.risk_level} ({f.risk_score}). FRP: {f.frp} MW.",
                    "icon": "🔥"
                })
                
        return {
            "message": text_resp,
            "conversation_id": conv_id,
            "data": data_payload if data_payload["items"] else None
        }

    def _handle_with_heuristics(self, message: str, conv_id: str, fused: List, alerts: List, persistent: List) -> Dict[str, Any]:
        """
        A very robust fallback intent matcher so the system works perfectly offline
        without an API key.
        """
        msg = message.lower()
        
        # 1. FRP Explanation
        if "what is frp" in msg or "mean by frp" in msg:
            return {
                "message": "FRP (Fire Radiative Power) represents the rate of thermal energy being emitted by a detected hotspot. In our platform, FRP is used as an indicator of thermal intensity and contributes to risk assessment.",
                "conversation_id": conv_id
            }
            
        # 2. Critical & High Alerts
        if "alert" in msg or "critical" in msg or "high risk" in msg or "high-risk" in msg:
            critical = [a for a in alerts if a['severity'] == 'CRITICAL']
            high = [a for a in alerts if a['severity'] == 'HIGH']
            
            resp = f"I found {len(critical) + len(high)} active alerts:\n\n"
            resp += f"🔴 Critical: {len(critical)}\n"
            resp += f"🟠 High: {len(high)}\n\n"
            resp += "Here are the most severe ones:"
            
            items = []
            for a in (critical + high)[:5]:
                items.append({
                    "id": a['alert_id'],
                    "title": a['classification'],
                    "description": f"Risk: {a['severity']}. Rule: {a['rule_name']}",
                    "icon": "🚨" if a['severity'] == 'CRITICAL' else "⚠️"
                })
                
            return {
                "message": resp,
                "conversation_id": conv_id,
                "data": {"type": "alerts", "items": items}
            }
            
        # 3. Latest Hotspots
        if "hotspot" in msg:
            sorted_fused = sorted(fused, key=lambda x: x.risk_score, reverse=True)
            resp = f"I found {len(fused)} active hotspots currently detected by the satellite fusion engine. Here are the top events:"
            
            items = []
            for f in sorted_fused[:4]:
                items.append({
                    "id": f.hotspot_id,
                    "title": f"Hotspot {f.hotspot_id}",
                    "description": f"Risk: {f.risk_score} — {f.risk_level}\\nPersistence: {f.persistence_status}\\nFRP: {f.frp} MW",
                    "icon": "🔥",
                    "action": f"hotspot-{f.hotspot_id}"
                })
                
            return {
                "message": resp,
                "conversation_id": conv_id,
                "data": {"type": "hotspots", "items": items}
            }
            
        # 4. Industrial Facilities
        if "industrial" in msg or "facility" in msg:
            industrial = [f for f in fused if f.anomaly_near_industrial_facility]
            resp = f"I found {len(industrial)} thermal events in close proximity to known industrial facilities."
            
            items = []
            for f in industrial[:3]:
                items.append({
                    "id": f.hotspot_id,
                    "title": f.nearest_facility,
                    "description": f"Classification: {f.scientific_classification}\\nDistance: {f.facility_distance_m}m",
                    "icon": "🏭"
                })
                
            return {
                "message": resp,
                "conversation_id": conv_id,
                "data": {"type": "industrial", "items": items}
            }
            
        # 5. Persistence
        if "persistent" in msg or "persistence" in msg:
            pers = [f for f in fused if f.persistence_status == "Persistent"]
            resp = f"There are {len(pers)} highly persistent thermal sources in the current active registry. These typically represent continuous industrial operations like gas flaring."
            
            items = []
            for f in pers[:3]:
                items.append({
                    "id": f.hotspot_id,
                    "title": f.nearest_facility,
                    "description": f"Status: PERSISTENT\\nAvg FRP: {f.frp} MW\\nClassification: {f.scientific_classification}",
                    "icon": "📈"
                })
                
            return {
                "message": resp,
                "conversation_id": conv_id,
                "data": {"type": "persistence", "items": items}
            }
            
        # 6. Specific Hotspot Query (e.g. "Why is HS-1024 critical?")
        hs_match = re.search(r'(HT-\d+)', message.upper())
        if hs_match:
            hs_id = hs_match.group(1)
            target = next((f for f in fused if f.hotspot_id == hs_id), None)
            if target:
                resp = f"Risk Score: {target.risk_score}/100\nSeverity: {target.risk_level}\n\nMain contributing factors:\n"
                resp += f"• Thermal intensity (FRP): {target.frp} MW\n"
                resp += f"• Satellite agreement: {target.satellite_agreement}\n"
                resp += f"• Persistence: {target.persistence_status}\n"
                resp += f"• Industrial proximity: {target.facility_distance_m} m"
                return {
                    "message": resp,
                    "conversation_id": conv_id
                }

        # 7. Default Fallback
        return {
            "message": "I'm your Thermal AI Assistant. You can ask me to show you high-risk hotspots, active alerts, persistent sources, or explain terms like FRP. How can I help you analyze the data?",
            "conversation_id": conv_id
        }

chatbot_service = ChatbotService()
