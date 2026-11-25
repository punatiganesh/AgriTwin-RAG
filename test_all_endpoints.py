# backend/test_all_endpoints.py
"""
End-to-End Integration Test Suite for AgriTwin-RAG
Covers all 14 Phases and validates live endpoints against the active daemon.
"""

import sys
import requests
import unittest

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_URL = "http://127.0.0.1:5000"

class TestAllAgriTwinEndpoints(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Health check
        try:
            r = requests.get(f"{BASE_URL}/api/farm-context", timeout=5)
            assert r.status_code == 200, f"Backend returned {r.status_code}"
        except Exception as e:
            raise RuntimeError(f"Backend daemon at {BASE_URL} is unreachable: {e}")

    def test_01_farm_context_and_revision(self):
        """Phase 2: Authoritative FarmContext and Revision Tracking."""
        r = requests.get(f"{BASE_URL}/api/farm-context", timeout=5)
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertTrue(data.get("success"))
        ctx = data.get("farm_context", {})
        self.assertIn("location", ctx)
        self.assertIn("crop", ctx)
        self.assertIn("weather", ctx)
        self.assertIn("soil", ctx)
        self.assertIn("satellite", ctx)
        self.assertIn("prediction", ctx)

    def test_02_update_location_and_boundary(self):
        """Phase 2 & Phase 13: Coordinate update, polygon boundary persistence, revision increment."""
        poly = [
            [15.8111, 79.9734],
            [15.8125, 79.9750],
            [15.8100, 79.9760],
            [15.8090, 79.9740]
        ]
        payload = {
            "location": {
                "latitude": 15.8111,
                "longitude": 79.9734,
                "locality": "Addanki Farm",
                "place_name": "Addanki, Bapatla District, Andhra Pradesh, India",
                "source": "Device GPS",
                "accuracy_m": 4.5,
                "boundary": poly
            }
        }
        r = requests.post(f"{BASE_URL}/api/farm/context/location", json=payload, timeout=5)
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertTrue(data.get("success"))
        self.assertGreaterEqual(data.get("location_revision", 0), 1)
        self.assertEqual(data.get("location", {}).get("locality"), "Addanki Farm")

    def test_03_geocoding_and_search(self):
        """Phase 3: Reverse geocoding & location search."""
        # Reverse geocoding
        r = requests.get(f"{BASE_URL}/api/location/reverse?lat=15.8111&lon=79.9734", timeout=10)
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertTrue(data.get("success"))
        self.assertIn("name", data)

        # Search
        r2 = requests.get(f"{BASE_URL}/api/location/search?q=Madurai", timeout=10)
        self.assertEqual(r2.status_code, 200)
        d2 = r2.json()
        self.assertTrue(d2.get("success"))
        self.assertGreater(len(d2.get("results", [])), 0)

    def test_04_weather_telemetry(self):
        """Phase 4: OpenWeather live telemetry without mock data."""
        r = requests.get(f"{BASE_URL}/api/weather/current?lat=15.8111&lon=79.9734", timeout=10)
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertTrue(data.get("success"))
        w = data.get("weather", {})
        self.assertIn("temperature", w)
        self.assertIn("humidity", w)
        self.assertIsNotNone(w.get("temperature"))
        self.assertNotEqual(data.get("location", {}).get("name"), "Srivilliputhur")

    def test_05_soil_telemetry(self):
        """Phase 5: ISRIC SoilGrids 2.0 telemetry with depth 0-5cm."""
        r = requests.get(f"{BASE_URL}/api/soil/current?lat=15.8111&lon=79.9734", timeout=15)
        self.assertIn(r.status_code, [200, 503])
        data = r.json()
        if r.status_code == 200:
            self.assertTrue(data.get("success"))
            self.assertIn("soil", data)
            self.assertIn("source", data)
            self.assertIn("ISRIC", data.get("source", ""))

    def test_06_satellite_ndvi(self):
        """Phase 6: Sentinel-2 Level-2A NDVI calculation."""
        r = requests.get(f"{BASE_URL}/api/satellite/ndvi?lat=15.8111&lon=79.9734", timeout=15)
        self.assertIn(r.status_code, [200, 503])
        data = r.json()
        if r.status_code == 200:
            self.assertIn("ndvi", data)
            self.assertIn("source", data)

    def test_07_farm_risk_assessment_section_12(self):
        """Phase 8: Section 12 4-tier biophysical risk assessment schema."""
        r = requests.get(f"{BASE_URL}/api/farm-risk", timeout=5)
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertTrue(data.get("success"))
        self.assertIn("risk_results", data)
        rr = data["risk_results"]
        # Must have 4 tiers: irrigation, crop_stress, disease, overall
        for tier in ["irrigation", "crop_stress", "disease", "overall"]:
            self.assertIn(tier, rr)
            self.assertIn("level", rr[tier])
            self.assertIn("score", rr[tier])
            self.assertIn("reasons", rr[tier])
            self.assertIn("evidence", rr[tier])

        self.assertIn("risks", data)
        self.assertIn("factors", data)
        self.assertIn("data_used", data)
        self.assertIn("model_attribution", data)

    def test_08_dynamic_recommendations_and_feedback(self):
        """Phase 11: 3 prioritized recommendations with ICAR evidence & farmer feedback logging."""
        # 1. Fetch recommendations
        r = requests.get(f"{BASE_URL}/api/recommendations", timeout=45)
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertTrue(data.get("success"))
        self.assertIn("cards", data)
        self.assertGreaterEqual(len(data["cards"]), 3)
        for card in data["cards"]:
            self.assertIn("priority", card)
            self.assertIn("title", card)
            self.assertIn("recommended_action", card)
            self.assertIn("evidence", card)
            self.assertIn("source", card["evidence"])

        # 2. Submit farmer feedback
        fb_payload = {
            "decision": "Accept",
            "feedback": "Automated regression test confirmation",
            "recommendation_title": data["cards"][0]["title"]
        }
        r_fb = requests.post(f"{BASE_URL}/api/feedback/submit", json=fb_payload, timeout=5)
        self.assertEqual(r_fb.status_code, 200)
        self.assertTrue(r_fb.json().get("success"))

        # 3. List feedback
        r_list = requests.get(f"{BASE_URL}/api/feedback/list", timeout=5)
        self.assertEqual(r_list.status_code, 200)
        self.assertTrue(r_list.json().get("success"))

    def test_09_evaluation_benchmark(self):
        """Phase 9: Empirical research evaluation comparing System A, B, and C."""
        r = requests.post(f"{BASE_URL}/api/evaluation/benchmark", json={"sample_count": 1}, timeout=60)
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertTrue(data.get("success"))
        self.assertIn("metrics_summary", data)
        self.assertIn("system_a_llm_only", data["metrics_summary"])
        self.assertIn("system_b_basic_rag", data["metrics_summary"])
        self.assertIn("system_c_agritwin_rag", data["metrics_summary"])

    def test_10_farm_reports_generation_and_history(self):
        """Phase 12: Immutable Farm Audit Report generation with complete provenance."""
        # 1. Generate Report
        r = requests.post(f"{BASE_URL}/api/reports/generate", json={}, timeout=10)
        self.assertEqual(r.status_code, 200)
        rpt = r.json()
        self.assertTrue(rpt.get("success"))
        self.assertIn("report_id", rpt)
        self.assertIn("telemetry_observations", rpt)
        self.assertIn("risk_assessment", rpt)
        self.assertIn("disclaimer", rpt)

        # 2. Get Report History
        r_hist = requests.get(f"{BASE_URL}/api/reports/history", timeout=5)
        self.assertEqual(r_hist.status_code, 200)
        hist = r_hist.json()
        self.assertTrue(hist.get("success"))
        self.assertGreater(hist.get("total", 0), 0)

    def test_11_disease_diagnostics(self):
        """Rice disease neural network status and diagnostics."""
        r = requests.get(f"{BASE_URL}/api/disease/status", timeout=5)
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertTrue(data.get("model_configured"))
        self.assertEqual(data.get("target_crop"), "Rice")

if __name__ == "__main__":
    unittest.main()
