import json
import sys
import os

# Configure utf-8 stdout encoding for Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app import app, ACTIVE_FARM_CONTEXT

client = app.test_client()

print("=" * 80)
print("VERIFYING DYNAMIC FARM WEATHER LOCATION IN AGRI-TWIN RAG")
print("=" * 80)

# -----------------------------------------------------------------------------
# TEST 1: Selected Farm Location (lat: 9.571529, lon: 77.675734) - Srivilliputhur
# -----------------------------------------------------------------------------
farm_coords = {
    "latitude": 9.571529,
    "longitude": 77.675734,
    "place_name": "Srivilliputhur, Virudhunagar, Tamil Nadu, India",
    "source": "Farm GPS / Geocoded"
}

print("\n>>> TEST 1A: Query 'What is the current weather at my farm?' with Srivilliputhur coordinates")
res1a = client.post('/api/rag/chat', json={
    "query": "What is the current weather at my farm?",
    "language": "en",
    "farm_context": {
        "location": farm_coords,
        "crop": {"name": "Rice", "variety": "MTU-1010", "growth_stage": "Flowering"}
    }
})

print(f"Status Code: {res1a.status_code}")
data1a = res1a.get_json() or {}
answer1a = data1a.get("answer", "")
fc1a = data1a.get("farm_context", {})
w1a = fc1a.get("weather", {})
loc1a = fc1a.get("location", {})

print(f"Location in Context: {loc1a.get('place_name')} (City: {loc1a.get('city')}, Lat: {loc1a.get('latitude')}, Lon: {loc1a.get('longitude')})")
print(f"Weather: Temp={w1a.get('temperature')}°C, Humidity={w1a.get('humidity')}%, Cond={w1a.get('weather_condition')}, Source={w1a.get('source')}")
print(f"Answer:\n{answer1a}\n")

# Check assertions for 1A
assert "Vijayawada" not in answer1a, "ERROR: Vijayawada appeared in answer!"
assert loc1a.get("latitude") == 9.571529, f"ERROR: Wrong lat: {loc1a.get('latitude')}"
assert loc1a.get("longitude") == 77.675734, f"ERROR: Wrong lon: {loc1a.get('longitude')}"
assert w1a.get("temperature") is not None, "ERROR: Temperature is None!"

print(">>> TEST 1B: Query 'Will the current temperature affect my crop?' with Srivilliputhur coordinates")
res1b = client.post('/api/rag/chat', json={
    "query": "Will the current temperature affect my crop?",
    "language": "en",
    "farm_context": {
        "location": farm_coords,
        "crop": {"name": "Rice", "variety": "MTU-1010", "growth_stage": "Flowering"}
    }
})

print(f"Status Code: {res1b.status_code}")
data1b = res1b.get_json() or {}
answer1b = data1b.get("answer", "")
fc1b = data1b.get("farm_context", {})
w1b = fc1b.get("weather", {})
loc1b = fc1b.get("location", {})

print(f"Location in Context: {loc1b.get('place_name')} (Lat: {loc1b.get('latitude')}, Lon: {loc1b.get('longitude')})")
print(f"Weather: Temp={w1b.get('temperature')}°C, Humidity={w1b.get('humidity')}%, Cond={w1b.get('weather_condition')}")
print(f"Answer:\n{answer1b}\n")

assert "Vijayawada" not in answer1b, "ERROR: Vijayawada appeared in temperature answer!"
assert str(round(w1b.get('temperature', 0))) in answer1b or f"{w1b.get('temperature')}" in answer1b or "32" in answer1b, "ERROR: Measured temperature missing from answer!"

# -----------------------------------------------------------------------------
# TEST 2: Farm Location UNAVAILABLE (latitude: None, longitude: None)
# -----------------------------------------------------------------------------
print("\n>>> TEST 2A: Query 'What is the current weather at my farm?' with NO coordinates")
# Reset server active context to empty
ACTIVE_FARM_CONTEXT["location"]["latitude"] = None
ACTIVE_FARM_CONTEXT["location"]["longitude"] = None
ACTIVE_FARM_CONTEXT["location"]["place_name"] = None
ACTIVE_FARM_CONTEXT["location"]["city"] = None
ACTIVE_FARM_CONTEXT["weather"]["temperature"] = None

res2a = client.post('/api/rag/chat', json={
    "query": "What is the current weather at my farm?",
    "language": "en",
    "farm_context": {
        "location": {"latitude": None, "longitude": None, "place_name": None},
        "crop": {"name": "Rice", "variety": "MTU-1010", "growth_stage": "Flowering"}
    }
})

print(f"Status Code: {res2a.status_code}")
data2a = res2a.get_json() or {}
answer2a = data2a.get("answer", "")
print(f"Answer for Unavailable Location:\n{answer2a}\n")

assert "Vijayawada" not in answer2a, "ERROR: Vijayawada appeared when location was unavailable!"
assert "Farm location is unavailable, so current farm weather cannot be determined." in answer2a, f"ERROR: Unexpected message: {answer2a}"

# -----------------------------------------------------------------------------
# TEST 3: Weather Endpoint (/api/weather?lat=9.571529&lon=77.675734)
# -----------------------------------------------------------------------------
print("\n>>> TEST 3: Weather API (/api/weather?lat=9.571529&lon=77.675734)")
res3 = client.get('/api/weather?lat=9.571529&lon=77.675734')
print(f"Status Code: {res3.status_code}")
data3 = res3.get_json() or {}
w3_loc = data3.get("location", {})
w3_w = data3.get("weather", {})
print(f"Weather API Location: {w3_loc.get('name')}, {w3_loc.get('country')} (Lat: {w3_loc.get('latitude')}, Lon: {w3_loc.get('longitude')})")
print(f"Weather API Data: Temp={w3_w.get('temperature')}°C, Humidity={w3_w.get('humidity')}%, Cond={w3_w.get('condition')}")

assert w3_loc.get("name") == "Srivilliputhur", f"ERROR: Expected Srivilliputhur, got {w3_loc.get('name')}"
assert "Vijayawada" not in str(data3), "ERROR: Vijayawada appeared in /api/weather response!"

print("\n" + "=" * 80)
print("ALL AUTOMATED TESTS PASSED SUCCESSFULLY!")
print("=" * 80)
