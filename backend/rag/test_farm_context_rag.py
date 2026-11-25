"""
AgriTwin-RAG - Step 7 Farm Context Integration Automated Test Suite
Tests all 7 test scenarios specified in the project requirements.
"""
import json
import sys
from pathlib import Path

# Configure utf-8 output encoding for Windows terminals
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

print("[INFO] Loading Flask application...", flush=True)
from app import app
print("[INFO] Flask application loaded successfully.", flush=True)


def run_all_tests():
    print("==================================================", flush=True)
    print("STEP 7: FARM CONTEXT RAG INTEGRATION TEST SUITE", flush=True)
    print("==================================================", flush=True)
    print(flush=True)

    client = app.test_client()
    results = {}

    # -------------------------------------------------------------
    # TEST 1: NORMAL RAG (No farm_context)
    # -------------------------------------------------------------
    print("TEST 1 — NORMAL RAG (No farm_context)", flush=True)
    payload1 = {
        "query": "What are the management practices for rice?"
    }
    res1 = client.post("/api/rag/chat", json=payload1)
    data1 = res1.get_json()
    print(f"Status Code: {res1.status_code}", flush=True)
    print(f"Response success: {data1.get('success')}", flush=True)
    print(f"Retrieved sources count: {len(data1.get('sources', []))}", flush=True)
    print(f"Farm context used: {data1.get('farm_context_used')}", flush=True)
    print(f"Answer preview: {str(data1.get('answer'))[:150]}...", flush=True)

    t1_pass = (
        res1.status_code == 200
        and data1.get("success") is True
        and bool(data1.get("answer"))
        and len(data1.get("sources", [])) > 0
        and data1.get("farm_context_used") is False
    )
    results["TEST 1 (Normal RAG)"] = "PASS" if t1_pass else "FAIL"
    print(f"Result: {results['TEST 1 (Normal RAG)']}\n" + "-" * 50, flush=True)

    # -------------------------------------------------------------
    # TEST 2: WEATHER + RAG
    # -------------------------------------------------------------
    print("TEST 2 — WEATHER + RAG", flush=True)
    payload2 = {
        "query": "Should I irrigate my rice field today?",
        "farm_context": {
            "crop": {
                "name": "Rice",
                "growth_stage": "Tillering"
            },
            "weather": {
                "temperature": 31,
                "humidity": 72,
                "rainfall": 0,
                "weather_condition": "Sunny"
            },
            "soil": {
                "moisture": 45
            }
        }
    }
    res2 = client.post("/api/rag/chat", json=payload2)
    data2 = res2.get_json()
    print(f"Status Code: {res2.status_code}", flush=True)
    print(f"Response success: {data2.get('success')}", flush=True)
    print(f"Farm context used: {data2.get('farm_context_used')}", flush=True)
    print(f"Answer preview: {str(data2.get('answer'))[:200]}...", flush=True)

    t2_pass = (
        res2.status_code == 200
        and data2.get("success") is True
        and bool(data2.get("answer"))
        and data2.get("farm_context_used") is True
    )
    results["TEST 2 (Weather + RAG)"] = "PASS" if t2_pass else "FAIL"
    print(f"Result: {results['TEST 2 (Weather + RAG)']}\n" + "-" * 50, flush=True)

    # -------------------------------------------------------------
    # TEST 3: SOIL + RAG
    # -------------------------------------------------------------
    print("TEST 3 — SOIL + RAG", flush=True)
    payload3 = {
        "query": "What fertilizer management should I follow?",
        "farm_context": {
            "crop": {
                "name": "Rice",
                "variety": "BPT 5204"
            },
            "soil": {
                "soil_type": "Clay Loam",
                "ph": 6.5,
                "nitrogen": 1.2,
                "phosphorus": None,
                "potassium": None
            }
        }
    }
    res3 = client.post("/api/rag/chat", json=payload3)
    data3 = res3.get_json()
    print(f"Status Code: {res3.status_code}", flush=True)
    print(f"Response success: {data3.get('success')}", flush=True)
    print(f"Farm context used: {data3.get('farm_context_used')}", flush=True)
    print(f"Answer preview: {str(data3.get('answer'))[:200]}...", flush=True)

    t3_pass = (
        res3.status_code == 200
        and data3.get("success") is True
        and bool(data3.get("answer"))
        and data3.get("farm_context_used") is True
    )
    results["TEST 3 (Soil + RAG)"] = "PASS" if t3_pass else "FAIL"
    print(f"Result: {results['TEST 3 (Soil + RAG)']}\n" + "-" * 50, flush=True)

    # -------------------------------------------------------------
    # TEST 4: CROP STAGE + RAG
    # -------------------------------------------------------------
    print("TEST 4 — CROP STAGE + RAG", flush=True)
    payload4 = {
        "query": "What management practices should I follow at the tillering stage?",
        "farm_context": {
            "crop": {
                "name": "Rice",
                "growth_stage": "Tillering"
            }
        }
    }
    res4 = client.post("/api/rag/chat", json=payload4)
    data4 = res4.get_json()
    print(f"Status Code: {res4.status_code}", flush=True)
    print(f"Response success: {data4.get('success')}", flush=True)
    print(f"Farm context used: {data4.get('farm_context_used')}", flush=True)
    print(f"Answer preview: {str(data4.get('answer'))[:200]}...", flush=True)

    t4_pass = (
        res4.status_code == 200
        and data4.get("success") is True
        and bool(data4.get("answer"))
        and data4.get("farm_context_used") is True
    )
    results["TEST 4 (Crop Stage + RAG)"] = "PASS" if t4_pass else "FAIL"
    print(f"Result: {results['TEST 4 (Crop Stage + RAG)']}\n" + "-" * 50, flush=True)

    # -------------------------------------------------------------
    # TEST 5: FULL FARM CONTEXT
    # -------------------------------------------------------------
    print("TEST 5 — FULL FARM CONTEXT", flush=True)
    payload5 = {
        "query": "What should I do on my farm today?",
        "farm_context": {
            "location": {
                "latitude": 16.50,
                "longitude": 80.64,
                "place_name": "Vijayawada"
            },
            "crop": {
                "name": "Rice",
                "variety": "BPT 5204",
                "growth_stage": "Tillering"
            },
            "weather": {
                "temperature": 31,
                "humidity": 72,
                "rainfall": 0,
                "wind_speed": 3.2,
                "pressure": 1008,
                "weather_condition": "Clear"
            },
            "soil": {
                "soil_type": "Clay",
                "ph": 6.5,
                "moisture": 45,
                "nitrogen": None,
                "phosphorus": None,
                "potassium": None
            },
            "satellite": {
                "ndvi": None,
                "vegetation_status": "Not available"
            }
        }
    }
    res5 = client.post("/api/rag/chat", json=payload5)
    data5 = res5.get_json()
    print(f"Status Code: {res5.status_code}", flush=True)
    print(f"Response success: {data5.get('success')}", flush=True)
    print(f"Farm context used: {data5.get('farm_context_used')}", flush=True)
    print(f"Sources count: {len(data5.get('sources', []))}", flush=True)
    print(f"Answer preview: {str(data5.get('answer'))[:250]}...", flush=True)

    t5_pass = (
        res5.status_code == 200
        and data5.get("success") is True
        and bool(data5.get("answer"))
        and data5.get("farm_context_used") is True
        and data5.get("farm_context", {}).get("location", {}).get("place_name") == "Vijayawada"
    )
    results["TEST 5 (Full Farm Context)"] = "PASS" if t5_pass else "FAIL"
    print(f"Result: {results['TEST 5 (Full Farm Context)']}\n" + "-" * 50, flush=True)

    # -------------------------------------------------------------
    # TEST 6: MISSING DATA HANDLING
    # -------------------------------------------------------------
    print("TEST 6 — MISSING DATA HANDLING", flush=True)
    payload6 = {
        "query": "What are the management practices for rice?",
        "farm_context": {
            "location": {"latitude": None, "longitude": None, "place_name": None},
            "crop": {"name": None, "variety": None, "growth_stage": None},
            "weather": {"temperature": None, "humidity": None, "rainfall": None},
            "soil": {"soil_type": None, "ph": None, "moisture": None},
            "satellite": {"ndvi": None, "vegetation_status": "Not available"}
        }
    }
    res6 = client.post("/api/rag/chat", json=payload6)
    data6 = res6.get_json()
    print(f"Status Code: {res6.status_code}", flush=True)
    print(f"Response success: {data6.get('success')}", flush=True)
    print(f"Farm context used: {data6.get('farm_context_used')}", flush=True)

    t6_pass = (
        res6.status_code == 200
        and data6.get("success") is True
        and bool(data6.get("answer"))
        and data6.get("farm_context_used") is False
    )
    results["TEST 6 (Missing Data)"] = "PASS" if t6_pass else "FAIL"
    print(f"Result: {results['TEST 6 (Missing Data)']}\n" + "-" * 50, flush=True)

    # -------------------------------------------------------------
    # TEST 7: INVALID REQUEST HANDLING
    # -------------------------------------------------------------
    print("TEST 7 — INVALID REQUEST", flush=True)
    payload7 = {
        "query": "   ",
        "farm_context": {
            "crop": {"name": "Rice"}
        }
    }
    res7 = client.post("/api/rag/chat", json=payload7)
    data7 = res7.get_json()
    print(f"Status Code: {res7.status_code}", flush=True)
    print(f"Response error: {data7.get('error')}", flush=True)

    t7_pass = (
        res7.status_code == 400
        and data7.get("success") is False
        and data7.get("error") == "Query is required."
    )
    results["TEST 7 (Invalid Request)"] = "PASS" if t7_pass else "FAIL"
    print(f"Result: {results['TEST 7 (Invalid Request)']}\n" + "-" * 50, flush=True)

    # Summary
    print("\n==================================================", flush=True)
    print("TEST SUMMARY", flush=True)
    print("==================================================", flush=True)
    all_passed = True
    for test_name, result in results.items():
        print(f"{test_name}: {result}", flush=True)
        if result != "PASS":
            all_passed = False

    print("==================================================", flush=True)
    print(f"OVERALL STATUS: {'ALL TESTS PASSED' if all_passed else 'SOME TESTS FAILED'}", flush=True)
    print("==================================================", flush=True)

    if not all_passed:
        sys.exit(1)


if __name__ == "__main__":
    run_all_tests()
