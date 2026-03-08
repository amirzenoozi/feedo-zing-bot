from zoneinfo import ZoneInfo
from datetime import datetime
import requests


def get_timezone_from_coords(lat, lon):
    """
    Calls a free API to get timezone from coordinates.
    Returns (timezone_name, offset_hours)
    """
    try:
        url = f"https://api.bigdatacloud.net/data/reverse-geocode-client?latitude={lat}&longitude={lon}&localityLanguage=en"
        response = requests.get(url, timeout=10)
        data = response.json()

        # 1. Find the entry where the description is "time zone"
        informative_items = data.get("localityInfo", {}).get("informative", [])
        tz_name = "UTC"
        for item in informative_items:
            if item.get("description") == "time zone":
                tz_name = item.get("name")
                break

        # 2. Calculate Offset by comparing UTC to Local Time in that zone
        try:
            # Get the current time in that specific timezone
            local_now = datetime.now(ZoneInfo(tz_name))
            offset = local_now.utcoffset().total_seconds() / 3600
        except Exception as e:
            print(f"Timezone Offset Calculation Error: {e}")
            offset = 0.0

        return tz_name, offset
    except Exception as e:
        print(f"Timezone API Error: {e}")
        return "UTC", 0.0