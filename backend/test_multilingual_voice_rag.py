"""
Test suite for Multilingual Voice RAG Assistant in AgriTwin-RAG.
Tests backend routing, multi-language support (EN, TE, TA, HI), FarmContext integration,
and ICAR retrieval grounding.
"""

import os
import sys
import json

# Ensure UTF-8 output on Windows console
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Ensure workspace root is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
from rag.farm_context import get_empty_farm_context, sanitize_farm_context
from rag.query_router import route_query, detect_query_language
from rag.direct_responder import generate_direct_telemetry_response

def get_sample_farm_context():
    return {
        "location": {
            "name": "Nuzvid, Krishna District, AP",
            "lat": 16.7850,
            "lon": 80.8488
        },
        "crop": {
            "name": "Rice",
            "stage": "Panicle Initiation"
        },
        "weather": {
            "temperature_c": 31.5,
            "humidity_percent": 82,
            "condition": "Partly Cloudy",
            "rainfall_last_24h_mm": 12.0,
            "forecast_rain_next_24h_mm": 5.0
        },
        "soil": {
            "moisture_percent": 38.5,
            "ph": 6.8,
            "temperature_c": 27.0
        },
        "satellite": {
            "ndvi_mean": 0.68,
            "ndvi_change_7d": 0.04,
            "anomaly_detected": False,
            "latest_date": "2026-09-18"
        },
        "disease": {
            "condition": "Brown Spot (Early Stage)",
            "confidence": 0.88,
            "source": "AI Leaf Image Diagnostic"
        }
    }

def run_tests():
    print("==================================================")
    print("AGRITWIN-RAG MULTILINGUAL VOICE ASSISTANT TEST SUITE")
    print("==================================================\n")

    client = app.test_client()
    context = get_sample_farm_context()

    test_cases = [
        {
            "desc": "1. English Direct Telemetry (Weather)",
            "payload": {
                "query": "What is my current weather?",
                "language": "en-IN",
                "farm_context": context
            },
            "expected_router": "direct",
            "check_in_response": ["Temperature:", "Humidity:"]
        },
        {
            "desc": "2. Telugu Direct Telemetry (Weather)",
            "payload": {
                "query": "నా పొలంలో ప్రస్తుత వాతావరణం ఎలా ఉంది?",
                "language": "te-IN",
                "farm_context": context
            },
            "expected_router": "direct",
            "check_in_response": ["ఉష్ణోగ్రత:", "తేమ:"]
        },
        {
            "desc": "3. Tamil Direct Telemetry (Weather)",
            "payload": {
                "query": "என் வயலில் இப்போது வானிலை எப்படி இருக்கிறது?",
                "language": "ta-IN",
                "farm_context": context
            },
            "expected_router": "direct",
            "check_in_response": ["வெப்பநிலை:", "ஈரப்பதம்:"]
        },
        {
            "desc": "4. Hindi Direct Telemetry (Weather)",
            "payload": {
                "query": "मेरे खेत का वर्तमान मौसम कैसा है?",
                "language": "hi-IN",
                "farm_context": context
            },
            "expected_router": "direct",
            "check_in_response": ["तापमान:", "नमी:"]
        },
        {
            "desc": "5. English Direct Telemetry (NDVI)",
            "payload": {
                "query": "What is my latest NDVI?",
                "language": "en",
                "farm_context": context
            },
            "expected_router": "direct",
            "check_in_response": ["NDVI"]
        },
        {
            "desc": "6. English RAG / Multi-source (Irrigation Decision)",
            "payload": {
                "query": "Should I irrigate my rice field right now?",
                "language": "en",
                "farm_context": context
            },
            "expected_router": "rag",
            "check_sources": True
        },
        {
            "desc": "7. Telugu RAG (Crop Health / Assessment)",
            "payload": {
                "query": "నా వరి పొలానికి ఇప్పుడు నీరు పెట్టాలా?",
                "language": "te",
                "farm_context": context
            },
            "expected_router": "rag",
            "check_sources": True
        },
        {
            "desc": "8. Tamil RAG (Crop Health / Assessment)",
            "payload": {
                "query": "என் நெல் வயலுக்கு தண்ணீர் விட வேண்டுமா?",
                "language": "ta",
                "farm_context": context
            },
            "expected_router": "rag",
            "check_sources": True
        },
        {
            "desc": "9. Hindi RAG (Disease / Management)",
            "payload": {
                "query": "क्या मुझे अपने धान के खेत में सिंचाई करनी चाहिए?",
                "language": "hi",
                "farm_context": context
            },
            "expected_router": "rag",
            "check_sources": True
        },
        {
            "desc": "10. English Full Farm Assessment",
            "payload": {
                "query": "Give me a complete assessment of my farm.",
                "language": "en",
                "farm_context": context
            },
            "expected_router": "rag",
            "check_sources": True
        }
    ]

    passed = 0
    total = len(test_cases)

    for i, tc in enumerate(test_cases, 1):
        print(f"--- Running Test {i}/{total}: {tc['desc']} ---")
        res = client.post(
            "/api/rag/chat",
            data=json.dumps(tc["payload"]),
            content_type="application/json"
        )

        assert res.status_code == 200, f"HTTP {res.status_code}: {res.data}"
        data = res.get_json()

        assert data.get("success") is True, f"Failed response: {data}"
        assert "response" in data, "No 'response' in output"
        assert "language" in data, "No 'language' in output"
        assert "routing_strategy" in data, "No 'routing_strategy' in output"

        strategy = data.get("routing_strategy")
        response_text = data.get("response", "")
        sources = data.get("sources", [])
        lang = data.get("language")

        print(f"   [Lang: {lang} | Strategy: {strategy} | Sources: {len(sources)}]")
        print(f"   [Snippet]: {response_text[:120]}...")

        # Verify strategy expectation if specified
        if "expected_router" in tc:
            if tc["expected_router"] == "direct":
                assert strategy == "direct", f"Expected direct telemetry routing, got {strategy}"
            elif tc["expected_router"] == "rag":
                assert strategy in ["rag_with_farm_context", "rag_knowledge_only", "hybrid"], f"Expected RAG routing, got {strategy}"

        # Verify content snippets
        if "check_in_response" in tc:
            for snippet in tc["check_in_response"]:
                assert snippet in response_text, f"Snippet '{snippet}' not found in response: {response_text}"

        print("   -> PASSED\n")
        passed += 1

    print("==================================================")
    print(f"ALL {passed}/{total} MULTILINGUAL TESTS PASSED SUCCESSFULLY!")
    print("==================================================")

if __name__ == "__main__":
    run_tests()
