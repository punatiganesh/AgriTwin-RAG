import sys
import os
import json

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app import app

def run():
    client = app.test_client()

    print("\n--- 1. Testing GET /api/farm-context ---")
    r1 = client.get("/api/farm-context")
    assert r1.status_code == 200
    d1 = r1.get_json()
    assert d1["farm_id"] == "FARM-001"
    assert "provenance" in d1
    print(f"Status {r1.status_code} - FarmContext OK (ID: {d1['farm_id']})")

    print("\n--- 2. Testing POST /api/simulation/evaluate ---")
    r2 = client.post("/api/simulation/evaluate", json={"farm_context": d1, "scenario": "no_irrigation_3_days"})
    assert r2.status_code == 200
    d2 = r2.get_json()
    assert d2["success"] is True
    print(f"Status {r2.status_code} - Simulation OK (Simulated Moisture: {d2['simulated_state']['moisture']}%)")

    print("\n--- 3. Testing POST /api/recommendations/generate ---")
    r3 = client.post("/api/recommendations/generate", json={"farm_context": d1, "language": "en"})
    assert r3.status_code == 200
    d3 = r3.get_json()
    assert d3["success"] is True
    print(f"Status {r3.status_code} - Recommendations OK (Crop: {d3.get('crop')})")

    print("\n--- 4. Testing Feedback POST & GET ---")
    r4a = client.post("/api/feedback/submit", json={"decision": "Accept", "feedback": "Irrigated on schedule", "farm_context": d1})
    assert r4a.status_code == 200
    r4b = client.get("/api/feedback/list")
    assert r4b.status_code == 200
    d4b = r4b.get_json()
    assert d4b["success"] is True
    print(f"Status {r4b.status_code} - Feedback OK (Total logs: {len(d4b.get('feedback', []))})")

    print("\n--- 5. Testing POST /api/evaluation/run (sample_count=1) ---")
    r5 = client.post("/api/evaluation/run", json={"sample_count": 1})
    assert r5.status_code == 200
    d5 = r5.get_json()
    assert d5["success"] is True
    print(f"Status {r5.status_code} - Benchmark Evaluation OK")

    print("\n--- 6. Testing All HTML Routes ---")
    routes = [
        "/",
        "/dashboard.html",
        "/digital-twin.html",
        "/prediction.html",
        "/xai.html",
        "/recommendations.html",
        "/assistant.html",
        "/reports.html",
        "/evaluation.html",
    ]
    for route in routes:
        r = client.get(route)
        assert r.status_code == 200, f"Route {route} failed with {r.status_code}"
        print(f" Route {route} -> 200 OK")

    print("\n==================================================")
    print("ALL 6 CAPSTONE TEST SUITES PASSED (100% SUCCESS)")
    print("==================================================")

if __name__ == "__main__":
    run()
