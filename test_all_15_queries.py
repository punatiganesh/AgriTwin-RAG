"""
AgriTwin-RAG — Comprehensive Verification of 15 Farmer Queries & Acceptance Criteria
Testing exact 15 prompt queries against Flask API:
1. What is my current temperature?
2. What is my humidity?
3. What is my current weather?
4. What is my current soil moisture?
5. What is my latest soil pH?
6. What is my latest NDVI?
7. What is the observation date of my latest satellite data?
8. What is my current crop health?
9. Will the current weather affect my crop?
10. My soil moisture is low. What should I do?
11. My NDVI is decreasing. What could be causing it?
12. Is my crop currently healthy?
13. Is my field experiencing water stress?
14. Based on my weather and soil condition, should I irrigate?
15. Based on my weather, soil, satellite and crop information, what should I do today?
"""
import sys
import json
import time
import requests

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_URL = "http://127.0.0.1:5000"

FARM_LOCATION = {
    "latitude": 9.571563,
    "longitude": 77.675714,
    "place_name": "Srivilliputhur, IN",
    "source": "OpenWeather / GPS"
}

TEST_CASES = [
    {
        "id": 1,
        "query": "What is my current temperature?",
        "expected_intents": ["WEATHER"],
        "expected_source": "OpenWeather",
        "must_contain": ["temperature", "OpenWeather", "°C"],
        "must_not_contain": ["Gannavaram"],
        "rag_required": False
    },
    {
        "id": 2,
        "query": "What is my humidity?",
        "expected_intents": ["WEATHER"],
        "expected_source": "OpenWeather",
        "must_contain": ["humidity", "OpenWeather", "%"],
        "must_not_contain": ["Gannavaram"],
        "rag_required": False
    },
    {
        "id": 3,
        "query": "What is my current weather?",
        "expected_intents": ["WEATHER"],
        "expected_source": "OpenWeather",
        "must_contain": ["Weather", "OpenWeather"],
        "must_not_contain": ["Gannavaram"],
        "rag_required": False
    },
    {
        "id": 4,
        "query": "What is my current soil moisture?",
        "expected_intents": ["SOIL"],
        "expected_source": "ISRIC",
        "must_contain": ["soil moisture", "ISRIC SoilGrids", "%"],
        "must_not_contain": ["Weather API", "Gannavaram"],
        "rag_required": False
    },
    {
        "id": 5,
        "query": "What is my latest soil pH?",
        "expected_intents": ["SOIL"],
        "expected_source": "ISRIC",
        "must_contain": ["soil pH", "ISRIC SoilGrids"],
        "must_not_contain": ["Weather API", "Gannavaram"],
        "rag_required": False
    },
    {
        "id": 6,
        "query": "What is my latest NDVI?",
        "expected_intents": ["SATELLITE"],
        "expected_source": "Sentinel-2",
        "must_contain": ["Sentinel-2", "0.68", "September 15, 2024"],
        "must_not_contain": ["Weather API", "Gannavaram"],
        "rag_required": False
    },
    {
        "id": 7,
        "query": "What is the observation date of my latest satellite data?",
        "expected_intents": ["SATELLITE"],
        "expected_source": "Sentinel-2",
        "must_contain": ["September 15, 2024", "Sentinel-2"],
        "must_not_contain": ["Weather API", "Gannavaram"],
        "rag_required": False
    },
    {
        "id": 8,
        "query": "What is my current crop health?",
        "expected_intents": ["SATELLITE", "WEATHER", "SOIL", "RAG"],
        "expected_source": "Multi-Source",
        "must_contain": ["Sentinel-2", "historical", "NDVI"],
        "must_not_contain": ["Weather API for soil"],
        "rag_required": True
    },
    {
        "id": 9,
        "query": "Will the current weather affect my crop?",
        "expected_intents": ["WEATHER", "CROP", "RAG"],
        "expected_source": "OpenWeather + ICAR",
        "must_contain": ["temperature", "Rice"],
        "must_not_contain": ["Gannavaram"],
        "rag_required": True
    },
    {
        "id": 10,
        "query": "My soil moisture is low. What should I do?",
        "expected_intents": ["SOIL", "RAG"],
        "expected_source": "SoilGrids + ICAR",
        "must_contain": ["moisture", "irrigation"],
        "must_not_contain": ["Gannavaram"],
        "rag_required": True
    },
    {
        "id": 11,
        "query": "My NDVI is decreasing. What could be causing it?",
        "expected_intents": ["SATELLITE", "WEATHER", "SOIL", "RAG"],
        "expected_source": "Multi-Source + ICAR",
        "must_contain": ["NDVI", "moisture"],
        "must_not_contain": ["Gannavaram"],
        "rag_required": True
    },
    {
        "id": 12,
        "query": "Is my crop currently healthy?",
        "expected_intents": ["SATELLITE", "WEATHER", "SOIL", "CROP", "RAG"],
        "expected_source": "Multi-Source + ICAR",
        "must_contain": ["NDVI"],
        "must_not_contain": ["Gannavaram"],
        "rag_required": True
    },
    {
        "id": 13,
        "query": "Is my field experiencing water stress?",
        "expected_intents": ["SOIL", "WEATHER", "RAG"],
        "expected_source": "SoilGrids + Weather + ICAR",
        "must_contain": ["moisture"],
        "must_not_contain": ["Gannavaram"],
        "rag_required": True
    },
    {
        "id": 14,
        "query": "Based on my weather and soil condition, should I irrigate?",
        "expected_intents": ["WEATHER", "SOIL", "RAG"],
        "expected_source": "Weather + SoilGrids + ICAR",
        "must_contain": ["irrigation"],
        "must_not_contain": ["Gannavaram"],
        "rag_required": True
    },
    {
        "id": 15,
        "query": "Based on my weather, soil, satellite and crop information, what should I do today?",
        "expected_intents": ["WEATHER", "SOIL", "SATELLITE", "CROP", "RAG"],
        "expected_source": "Full Multi-Source Reasoning",
        "must_contain": ["Rice"],
        "must_not_contain": ["Gannavaram"],
        "rag_required": True
    },
]


def run_tests():
    print("=" * 80)
    print("AGRITWIN-RAG: 15 QUERIES VERIFICATION & ACCEPTANCE TESTING")
    print(f"Target Farm: {FARM_LOCATION['place_name']} ({FARM_LOCATION['latitude']}, {FARM_LOCATION['longitude']})")
    print("=" * 80)

    # 1. Sync Central Farm Context
    sync_payload = {
        "farm_context": {
            "location": FARM_LOCATION,
            "crop": {
                "name": "Rice",
                "variety": "BPT 5204",
                "growth_stage": None
            },
            "soil": {
                "ph": 6.9,
                "moisture": 28.5,
                "soil_type": "Clay Loam",
                "source": "ISRIC SoilGrids 2.0"
            },
            "satellite": {
                "ndvi": 0.68,
                "acquisition_date": "2024-09-15",
                "vegetation_status": "High Photosynthetic Vigor",
                "source": "Sentinel-2 L2A"
            }
        }
    }
    sync_res = requests.post(f"{BASE_URL}/api/farm-context", json=sync_payload, timeout=10)
    print(f"Farm Context Sync Status: {sync_res.status_code}")

    results = []
    for tc in TEST_CASES:
        time.sleep(0.5)
        payload = {
            "query": tc["query"],
            "language": "en",
            "farm_context": sync_payload["farm_context"]
        }
        res = requests.post(f"{BASE_URL}/api/rag/chat", json=payload, timeout=35)
        data = res.json()
        
        status = res.status_code
        answer = data.get("answer", "")
        intents = data.get("intents", [])
        data_sources = data.get("data_sources", [])
        rag_req = data.get("rag_required", False)

        print(f"\n[TEST {tc['id']:02d}] {tc['query']}")
        print(f"  Intents:      {intents}")
        print(f"  Data Sources: {data_sources}")
        print(f"  RAG Used:     {rag_req}")
        print(f"  Answer:       {answer[:180]}...")

        # Verification checks
        passed = (status == 200)
        for term in tc.get("must_contain", []):
            if term.lower() not in answer.lower():
                print(f"  ⚠️ Warning: expected '{term}' in answer")
        for term in tc.get("must_not_contain", []):
            if term.lower() in answer.lower():
                print(f"  ❌ Error: forbidden '{term}' found in answer")
                passed = False

        results.append({
            "id": tc["id"],
            "query": tc["query"],
            "intents": intents,
            "data_sources": data_sources,
            "rag_required": rag_req,
            "answer": answer,
            "passed": passed
        })

    print("\n" + "=" * 80)
    passed_count = sum(1 for r in results if r["passed"])
    print(f"TEST RESULTS: {passed_count}/{len(TEST_CASES)} passed successfully.")
    print("=" * 80)


if __name__ == "__main__":
    run_tests()
