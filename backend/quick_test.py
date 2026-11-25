import requests

BASE_URL = "http://127.0.0.1:5000"

payload = {
    "farm_context": {
        "location": {
            "latitude": 9.571563,
            "longitude": 77.675714,
            "place_name": "Srivilliputhur, IN",
            "source": "OpenWeather / GPS"
        },
        "crop": {
            "name": "Rice",
            "variety": "BPT 5204",
            "growth_stage": None
        }
    }
}

try:
    r = requests.post(f"{BASE_URL}/api/farm-context", json=payload)
    print("Status:", r.status_code)
    print("Response text:", r.text[:300])
except Exception as e:
    print("Error:", e)
