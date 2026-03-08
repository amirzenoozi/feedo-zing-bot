import requests


def get_timezone_from_coords(lat, lon):
    """
    Calls a free API to get timezone from coordinates.
    Returns (timezone_name, offset_hours)
    """
    try:
        # BigDataCloud Free Reverse Geocoding API
        url = f"https://api.bigdatacloud.net/data/reverse-geocode-client?latitude={lat}&longitude={lon}&localityLanguage=en"
        response = requests.get(url, timeout=5)
        data = response.json()

        # Note: We don't store exact Lat/Lon for privacy,
        # just the resulting Timezone/Offset
        # We simulate the offset for this example (e.g., +1.0)
        # In a real scenario, you'd use a library or a specific TZ API
        # but for simplicity, let's assume we get the timezone string:
        return data.get("timezone", "UTC"), 0.0
    except Exception as e:
        print(f"API Error: {e}")
        return "UTC", 0.0