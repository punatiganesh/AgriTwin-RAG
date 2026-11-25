import json
import sys
from app import app, ACTIVE_FARM_CONTEXT

# Configure utf-8 stdout encoding for Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

client = app.test_client()

queries = [
    "Will the current temperature affect my crop?",
    "Should I irrigate my rice field?",
    "What does my current NDVI indicate?",
    "Is my soil suitable for rice?",
    "What should I do on my farm today?"
]

results = []

print("======================================================================")
print("RUNNING AGRI-TWIN RAG CONTEXT INTEGRATION VERIFICATION")
print("======================================================================")

for q in queries:
    print(f"\n>>> TESTING QUERY: '{q}'")
    res = client.post('/api/rag/chat', json={"query": q, "language": "en"})
    print(f"HTTP Status: {res.status_code}")
    data = res.get_json() or {}
    
    success = data.get("success", False)
    answer = data.get("answer", "")
    fc = data.get("farm_context") or {}
    weather = fc.get("weather") or {}
    soil = fc.get("soil") or {}
    sat = fc.get("satellite") or {}
    crop = fc.get("crop") or {}
    sources = data.get("sources") or []
    
    temp = weather.get("temperature")
    humidity = weather.get("humidity")
    moisture = soil.get("moisture")
    ndvi = sat.get("ndvi")
    crop_name = crop.get("name")
    growth_stage = crop.get("growth_stage")
    
    print(f"Success: {success}")
    print(f"Farm Context - Crop: {crop_name} ({growth_stage})")
    print(f"Farm Context - Weather: Temp={temp}°C, Humidity={humidity}%")
    print(f"Farm Context - Soil: Moisture={moisture}%, pH={soil.get('ph')}, Type={soil.get('soil_type')}")
    print(f"Farm Context - Satellite: NDVI={ndvi}, Date={sat.get('acquisition_date')}")
    print(f"Retrieved Sources Count: {len(sources)}")
    for s in sources:
        print(f"  • {s.get('source')} — pages {s.get('page')}")
    print("\nGenerated Answer Preview:\n" + ("-" * 40))
    print(answer)
    print("-" * 40)
    
    results.append({
        "query": q,
        "success": success,
        "temp": temp,
        "crop": crop_name,
        "stage": growth_stage,
        "sources_count": len(sources),
        "answer_len": len(answer)
    })

print("\n======================================================================")
print("VERIFICATION SUMMARY")
print("======================================================================")
for r in results:
    print(f"Query: {r['query']}")
    print(f"  Success: {r['success']} | Temp: {r['temp']}°C | Crop: {r['crop']} | Stage: {r['stage']} | Sources: {r['sources_count']}")
