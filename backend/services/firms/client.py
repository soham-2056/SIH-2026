import os
import requests
import csv
from io import StringIO
from typing import List, Dict, Any
from datetime import datetime
import json
from dotenv import load_dotenv

load_dotenv()

class FIRMSClient:
    """Client for NASA FIRMS API."""

    def __init__(self):
        self.api_key = os.getenv("FIRMS_MAP_KEY", "DEMO_KEY")
        self.base_url = os.getenv("FIRMS_BASE_URL", "https://firms.modaps.eosdis.nasa.gov/api/")
        
        # We will use area or country bounds. For India:
        # MAP_KEY/VIIRS_NOAA21_NRT/world/1
        # Or bounds for India roughly: 68.7,8.4,97.25,37.6
    
    def fetch_recent_observations(self, source: str = "VIIRS_NOAA21_NRT", area: str = "India", days: int = 1) -> List[Dict[str, Any]]:
        """
        Fetch recent active fire data from FIRMS.
        For a specific area, we use the country/region API or global API with bounding box.
        For simplicity, using area approach if supported, or pulling world and filtering.
        """
        # Note: The actual FIRMS API for area: https://firms.modaps.eosdis.nasa.gov/api/area/csv/[MAP_KEY]/[SOURCE]/[BBOX]/[DAYS]
        # India BBOX approx: 68.1,6.5,97.4,35.5 (min_lon, min_lat, max_lon, max_lat)
        bbox = "68.0,6.0,98.0,36.0"
        
        url = f"{self.base_url}area/csv/{self.api_key}/{source}/{bbox}/{days}"
        
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            # Parse CSV
            data = []
            if response.text.strip():
                reader = csv.DictReader(StringIO(response.text))
                for row in reader:
                    data.append(row)
            return data
            
        except requests.exceptions.RequestException as e:
            print(f"Error fetching FIRMS data: {e}")
            return []

if __name__ == "__main__":
    client = FIRMSClient()
    print("Testing FIRMS Client...")
    data = client.fetch_recent_observations(source="VIIRS_NOAA21_NRT", days=1)
    print(f"Fetched {len(data)} records.")
