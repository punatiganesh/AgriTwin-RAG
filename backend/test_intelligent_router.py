"""
AgriTwin-RAG — Comprehensive Verification Suite for Intelligent Query Router & Multi-Source Copilot
Tests all 16 required test cases specified in the requirement.
"""
import sys
import json
import time
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

print("[SETUP] Importing Flask app and Query Router...", flush=True)
from app import app
from rag.query_router import route_query

client = app.test_client()

# Sample 16 Required Questions with expected routing behavior
TEST_CASES = [
    {
        "id": 1,
        "query": "What is my current temperature?",
        "expected_intents": ["WEATHER"],
        "expect_rag": False,
        "description": "Pure live weather inquiry -> Weather API only, RAG bypassed"
    },
    {
        "id": 2,
        "query": "What is today's humidity?",
        "expected_intents": ["WEATHER"],
        "expect_rag": False,
        "description": "Pure live humidity inquiry -> Weather API only, RAG bypassed"
    },
    {
        "id": 3,
        "query": "Will it rain today?",
        "expected_intents": ["WEATHER"],
        "expect_rag": False,
        "description": "Precipitation forecast inquiry -> Weather API only, RAG bypassed"
    },
    {
        "id": 4,
        "query": "What is my current soil moisture?",
        "expected_intents": ["SOIL"],
        "expect_rag": False,
        "description": "Pure live soil moisture inquiry -> Soil API only, RAG bypassed"
    },
    {
        "id": 5,
        "query": "What is my soil pH?",
        "expected_intents": ["SOIL"],
        "expect_rag": False,
        "description": "Pure live soil pH inquiry -> Soil API only, RAG bypassed"
    },
    {
        "id": 6,
        "query": "Is my soil suitable for rice?",
        "expected_intents": ["SOIL", "RAG"],
        "expect_rag": True,
        "description": "Soil suitability evaluation -> Soil Telemetry + ICAR Knowledge"
    },
    {
        "id": 7,
        "query": "What is my latest NDVI?",
        "expected_intents": ["SATELLITE"],
        "expect_rag": False,
        "description": "Pure NDVI spectral inquiry -> Satellite observation only, RAG bypassed"
    },
    {
        "id": 8,
        "query": "Is my crop healthy according to satellite data?",
        "expected_intents": ["SATELLITE"],
        "expect_rag": False,
        "description": "Crop health remote sensing inquiry -> Satellite data only, RAG bypassed"
    },
    {
        "id": 9,
        "query": "What fertilizer is recommended for rice?",
        "expected_intents": ["RAG"],
        "expect_rag": True,
        "description": "Pure agronomic fertilizer guidance -> ICAR RAG knowledge base"
    },
    {
        "id": 10,
        "query": "Will today's temperature affect my rice crop?",
        "expected_intents": ["WEATHER", "RAG"],
        "expect_rag": True,
        "description": "Thermal effect on crop stage -> Live Weather + ICAR Knowledge"
    },
    {
        "id": 11,
        "query": "My soil moisture is low. What should I do?",
        "expected_intents": ["SOIL", "RAG"],
        "expect_rag": True,
        "description": "Soil moisture stress action -> Soil Telemetry + ICAR Practices"
    },
    {
        "id": 12,
        "query": "My satellite shows low vegetation health. What could be the reason?",
        "expected_intents": ["SATELLITE", "WEATHER", "SOIL", "RAG"],
        "expect_rag": True,
        "description": "Vegetation stress diagnosis -> Satellite + Weather + Soil + ICAR RAG"
    },
    {
        "id": 13,
        "query": "My soil moisture is low and rainfall is not expected. Should I irrigate?",
        "expected_intents": ["WEATHER", "SOIL", "RAG"],
        "expect_rag": True,
        "description": "Irrigation decision support -> Weather + Soil + ICAR Practices"
    },
    {
        "id": 14,
        "query": "My crop health is decreasing and the temperature is high. What could be causing this?",
        "expected_intents": ["SATELLITE", "WEATHER", "SOIL", "RAG"],
        "expect_rag": True,
        "description": "Stress diagnosis -> Satellite + Weather + Soil + ICAR RAG"
    },
    {
        "id": 15,
        "query": "Based on my current weather, soil and satellite data, what should I do today?",
        "expected_intents": ["WEATHER", "SOIL", "SATELLITE", "RAG"],
        "expect_rag": True,
        "description": "Holistic daily farm copilot -> Weather + Soil + Satellite + ICAR RAG"
    },
    {
        "id": 16,
        "query": "Analyze my field using all available live data and agricultural knowledge.",
        "expected_intents": ["WEATHER", "SOIL", "SATELLITE", "RAG"],
        "expect_rag": True,
        "description": "Complete field audit -> Weather + Soil + Satellite + ICAR RAG"
    }
]


def run_router_tests():
    print("=" * 80, flush=True)
    print("AGRITWIN-RAG INTELLIGENT ROUTER & MULTI-SOURCE COPILOT VERIFICATION", flush=True)
    print("=" * 80, flush=True)

    report = []
    all_passed = True

    # First test router classification standalone
    print("\n--- PHASE 1: STANDALONE INTENT ROUTER CLASSIFICATION (16 CASES) ---", flush=True)
    for tc in TEST_CASES:
        res = route_query(tc["query"])
        intents = res["intents"]
        rag_req = res["rag_required"]
        
        # Check if all expected intents are present
        intents_match = all(exp in intents for exp in tc["expected_intents"])
        rag_match = (rag_req == tc["expect_rag"])
        passed = intents_match and rag_match

        status_str = "[PASS]" if passed else "[FAIL]"
        if not passed:
            all_passed = False
        print(f"{status_str} Test {tc['id']:02d}: \"{tc['query']}\"")
        print(f"       -> Intents: {intents} | RAG Required: {rag_req} | Data Sources: {res['data_sources']}")

    print("\n--- PHASE 2: END-TO-END COPILOT INFERENCE VALIDATION ---", flush=True)
    sample_e2e_cases = [1, 4, 7, 9, 10, 13, 15]  # Representative spread across single & multi-source

    for tc_id in sample_e2e_cases:
        tc = next(t for t in TEST_CASES if t["id"] == tc_id)
        print(f"\n[E2E Test {tc['id']:02d}] \"{tc['query']}\"", flush=True)
        print(f"Goal: {tc['description']}", flush=True)

        payload = {
            "query": tc["query"],
            "language": "en"
        }

        t0 = time.time()
        resp = client.post("/api/rag/chat", json=payload)
        latency = round(time.time() - t0, 2)
        data = resp.get_json() or {}

        status_code = resp.status_code
        success = data.get("success", False)
        answer = data.get("answer", "")
        intents = data.get("intents", [])
        sources = data.get("sources", [])
        rag_req = data.get("rag_required", False)

        print(f"Status: {status_code} | Latency: {latency}s | Success: {success}")
        print(f"Intents: {intents} | RAG Required: {rag_req} | Sources: {len(sources)}")
        print(f"Answer Preview:\n{answer[:280]}...\n")

        # Verify
        passed = (status_code == 200) and success and (len(answer) > 20)
        if tc["expect_rag"]:
            if not rag_req or len(sources) == 0:
                passed = False
        else:
            if rag_req or len(sources) > 0:
                passed = False

        test_result = {
            "test_id": tc["id"],
            "query": tc["query"],
            "status": "PASS" if passed else "FAIL",
            "latency": latency,
            "intents": intents,
            "rag_required": rag_req,
            "sources_count": len(sources),
        }
        report.append(test_result)
        if not passed:
            all_passed = False

        print(f"-> VERDICT: {'[PASS]' if passed else '[FAIL]'}")
        time.sleep(2)

    print("\n" + "=" * 80)
    print("FINAL SUMMARY REPORT — INTELLIGENT ROUTER & COPILOT")
    print("=" * 80)
    for r in report:
        print(f"Test {r['test_id']:02d}: [{r['status']}] \"{r['query']}\" | Intents: {r['intents']} | RAG: {r['rag_required']} | Sources: {r['sources_count']}")

    print("\nOVERALL VERDICT:", "ALL 16 ROUTER & MULTI-SOURCE TESTS PASSED [100% SUCCESS]" if all_passed else "SOME TESTS FAILED")
    return all_passed


if __name__ == "__main__":
    success = run_router_tests()
    sys.exit(0 if success else 1)
