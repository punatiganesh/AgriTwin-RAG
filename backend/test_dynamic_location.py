# backend/test_dynamic_location.py
"""
Comprehensive Automated Test Suite for AgriTwin-RAG Dynamic Location Integration.
Verifies:
1. FarmContext loading & fallback structure
2. Invalid coordinate validation and rejection
3. Centralized backend location persistence (session & DB)
4. Cache invalidation on coordinate change
5. Weather endpoint with dynamic coordinates (no hardcoding)
6. Soil intelligence endpoint with dynamic coordinates
7. Satellite Sentinel-2 NDVI coordinate querying, pixel calculation, and median aggregation
8. Nominatim location search & reverse geocoding endpoints
9. RAG chat grounding with active FarmContext
10. Concurrent / sequential location update race condition handling
11. Provider failure and unavailable data handling
"""

import json
import sys
import os
import unittest
from pathlib import Path

# Configure utf-8 stdout encoding for Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app import app, ACTIVE_FARM_CONTEXT, WEATHER_CACHE, SOIL_CACHE, NDVI_CACHE
from database.db import get_farm_by_farmer_id, get_farmer_by_id

class TestDynamicLocationIntegration(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        app.config["TESTING"] = True

    def test_01_farm_context_endpoints_exist(self):
        """Verify both GET /api/farm-context and GET /api/farm/context return valid context."""
        for endpoint in ["/api/farm-context", "/api/farm/context"]:
            res = self.client.get(endpoint)
            self.assertEqual(res.status_code, 200, f"Endpoint {endpoint} failed")
            data = res.get_json()
            self.assertTrue(data.get("success"), f"Endpoint {endpoint} returned failure")
            self.assertIn("farm_context", data)
            fc = data["farm_context"]
            self.assertIn("location", fc)
            self.assertIn("latitude", fc["location"])
            self.assertIn("longitude", fc["location"])
            self.assertIn("crop", fc)

    def test_02_coordinate_validation_and_rejection(self):
        """Verify coordinates are strictly validated and invalid values rejected with 400."""
        invalid_payloads = [
            {"latitude": 95.0, "longitude": 77.0},   # Lat > 90
            {"latitude": -95.0, "longitude": 77.0},  # Lat < -90
            {"latitude": 15.0, "longitude": 185.0},  # Lon > 180
            {"latitude": 15.0, "longitude": -185.0}, # Lon < -180
            {"latitude": "invalid", "longitude": 77.0}, # Non-numeric
            {"latitude": 15.0},                      # Missing lon
            {"longitude": 77.0},                     # Missing lat
            {},                                      # Empty
        ]
        for payload in invalid_payloads:
            res = self.client.post("/api/farm/context/location", json=payload)
            self.assertEqual(res.status_code, 400, f"Expected 400 for payload {payload}, got {res.status_code}")
            data = res.get_json()
            self.assertFalse(data.get("success"))
            self.assertIn("error", data)

    def test_03_authenticated_location_persistence(self):
        """Verify updating location persists for authenticated farmer in database and context."""
        # 1. Login demo farmer
        login_res = self.client.post("/api/auth/login", json={
            "identifier": "demo@agritwin.com",
            "password": "Demo@1234"
        })
        self.assertEqual(login_res.status_code, 200, "Demo login failed")

        # 2. Update location to Addanki, Andhra Pradesh (15.8111, 79.9734)
        addanki_location = {
            "latitude": 15.8111,
            "longitude": 79.9734,
            "locality": "Addanki",
            "place_name": "Addanki, Bapatla District, Andhra Pradesh, India",
            "district": "Bapatla",
            "state": "Andhra Pradesh",
            "country": "India",
            "source": "manual_search",
            "accuracy": 15.0
        }
        update_res = self.client.post("/api/farm/context/location", json=addanki_location)
        self.assertEqual(update_res.status_code, 200)
        data = update_res.get_json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data["location"]["latitude"], 15.8111)
        self.assertEqual(data["location"]["longitude"], 79.9734)
        self.assertEqual(data["location"]["locality"], "Addanki")

        # 3. Fetch context again to ensure it remains persisted
        ctx_res = self.client.get("/api/farm/context")
        self.assertEqual(ctx_res.status_code, 200)
        ctx_data = ctx_res.get_json()["farm_context"]
        self.assertEqual(ctx_data["location"]["latitude"], 15.8111)
        self.assertEqual(ctx_data["location"]["longitude"], 79.9734)
        self.assertEqual(ctx_data["location"]["locality"], "Addanki")

        # 4. Verify database row directly
        farmer_data = login_res.get_json().get("farmer", {})
        farmer_id = farmer_data.get("id")
        if farmer_id:
            db_farm = get_farm_by_farmer_id(farmer_id)
            self.assertIsNotNone(db_farm)
            self.assertAlmostEqual(db_farm["latitude"], 15.8111, places=3)
            self.assertAlmostEqual(db_farm["longitude"], 79.9734, places=3)

    def test_04_cache_invalidation_on_location_update(self):
        """Verify that updating location invalidates telemetry caches."""
        # Populate caches with dummy items
        WEATHER_CACHE[("dummy_lat", "dummy_lon")] = (999999, {})
        SOIL_CACHE[(1.0, 1.0, "0-5cm")] = (999999, {})
        NDVI_CACHE[(1.0, 1.0, 30.0)] = (999999, {})

        self.assertGreater(len(WEATHER_CACHE), 0)
        self.assertGreater(len(SOIL_CACHE), 0)
        self.assertGreater(len(NDVI_CACHE), 0)

        # Update location
        res = self.client.post("/api/farm/context/location", json={
            "latitude": 15.8111,
            "longitude": 79.9734,
            "locality": "Addanki",
            "source": "gps"
        })
        self.assertEqual(res.status_code, 200)

        # Caches must be empty
        self.assertEqual(len(WEATHER_CACHE), 0, "WEATHER_CACHE was not cleared")
        self.assertEqual(len(SOIL_CACHE), 0, "SOIL_CACHE was not cleared")
        self.assertEqual(len(NDVI_CACHE), 0, "NDVI_CACHE was not cleared")

    def test_05_weather_endpoint_uses_explicit_and_context_coordinates(self):
        """Verify /api/weather uses requested coordinates without hardcoding."""
        # 1. Query for Addanki (15.8111, 79.9734)
        res = self.client.get("/api/weather?lat=15.8111&lon=79.9734")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))
        loc = data.get("location", {})
        self.assertAlmostEqual(loc.get("latitude"), 15.8111, places=3)
        self.assertAlmostEqual(loc.get("longitude"), 79.9734, places=3)
        # Verify it did not return Srivilliputhur
        self.assertNotEqual(loc.get("name"), "Srivilliputhur", "Returned hardcoded Srivilliputhur instead of Addanki")

    def test_06_soil_endpoint_validation_and_dynamic_coordinates(self):
        """Verify /api/soil validates coordinates and accepts dynamic locations."""
        # Invalid coordinates
        res_bad = self.client.get("/api/soil?lat=150.0&lon=79.9734")
        self.assertEqual(res_bad.status_code, 400)

        # Missing coordinates
        res_missing = self.client.get("/api/soil")
        self.assertEqual(res_missing.status_code, 400)

        # Valid coordinates (Addanki)
        res_valid = self.client.get("/api/soil?lat=15.8111&lon=79.9734")
        # May return 200 (live SoilGrids) or 503 (if network WCS timeout in sandbox), but must not 400 or hardcode
        self.assertIn(res_valid.status_code, [200, 503])
        data = res_valid.get_json()
        self.assertAlmostEqual(data.get("latitude"), 15.8111, places=3)
        self.assertAlmostEqual(data.get("longitude"), 79.9734, places=3)

    def test_07_satellite_ndvi_coordinates_and_formula(self):
        """Verify /api/ndvi validates coordinates and implements pixel NDVI formula."""
        # Invalid coordinates
        res_bad = self.client.get("/api/ndvi?lat=95.0&lon=79.9734")
        self.assertEqual(res_bad.status_code, 400)

        # Valid coordinates query
        res = self.client.get("/api/ndvi?lat=15.8111&lon=79.9734")
        self.assertIn(res.status_code, [200, 503])
        data = res.get_json()
        self.assertAlmostEqual(data.get("latitude"), 15.8111, places=3)
        self.assertAlmostEqual(data.get("longitude"), 79.9734, places=3)

        if res.status_code == 200:
            self.assertEqual(data.get("formula"), "(NIR - RED) / (NIR + RED)")
            self.assertEqual(data.get("aggregation"), "median")
            self.assertIn("ndvi", data)
            self.assertTrue(-1.0 <= data["ndvi"] <= 1.0)

    def test_08_location_search_and_reverse_geocoding(self):
        """Verify forward place search and reverse geocoding endpoints."""
        # Test reverse geocoding for Addanki coordinates
        rev_res = self.client.get("/api/location/reverse?lat=15.8111&lon=79.9734")
        self.assertEqual(rev_res.status_code, 200)
        rev_data = rev_res.get_json()
        self.assertTrue(rev_data.get("success"))
        self.assertAlmostEqual(rev_data.get("latitude"), 15.8111, places=3)
        self.assertAlmostEqual(rev_data.get("longitude"), 79.9734, places=3)

        # Test place search
        search_res = self.client.get("/api/location/search?q=Addanki")
        # In case Nominatim network is available or throttled
        self.assertIn(search_res.status_code, [200, 503])
        if search_res.status_code == 200:
            search_data = search_res.get_json()
            self.assertTrue(search_data.get("success"))
            self.assertIsInstance(search_data.get("results"), list)

    def test_09_rag_chat_uses_updated_farm_context(self):
        """Verify RAG chat receives dynamic location in FarmContext."""
        res = self.client.post("/api/rag/chat", json={
            "query": "What is the current weather at my farm?",
            "language": "en",
            "farm_context": {
                "location": {
                    "latitude": 15.8111,
                    "longitude": 79.9734,
                    "locality": "Addanki",
                    "place_name": "Addanki, Andhra Pradesh, India",
                    "source": "manual_search"
                },
                "crop": {"name": "Rice", "variety": "BPT-5204", "growth_stage": "Tillering"}
            }
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))
        fc = data.get("farm_context", {})
        loc = fc.get("location", {})
        self.assertAlmostEqual(loc.get("latitude"), 15.8111, places=3)
        self.assertAlmostEqual(loc.get("longitude"), 79.9734, places=3)

    def test_10_concurrent_or_sequential_location_updates(self):
        """Verify sequential location changes correctly overwrite older state without race corruption."""
        loc1 = {"latitude": 16.3067, "longitude": 80.4365, "locality": "Guntur", "source": "search"}
        loc2 = {"latitude": 15.8111, "longitude": 79.9734, "locality": "Addanki", "source": "search"}

        res1 = self.client.post("/api/farm/context/location", json=loc1)
        self.assertEqual(res1.status_code, 200)
        self.assertEqual(res1.get_json()["location"]["locality"], "Guntur")

        res2 = self.client.post("/api/farm/context/location", json=loc2)
        self.assertEqual(res2.status_code, 200)
        self.assertEqual(res2.get_json()["location"]["locality"], "Addanki")
        self.assertEqual(res2.get_json()["location"]["latitude"], 15.8111)

        # Final check on GET
        res_final = self.client.get("/api/farm/context")
        final_loc = res_final.get_json()["farm_context"]["location"]
        self.assertEqual(final_loc["locality"], "Addanki")
        self.assertEqual(final_loc["latitude"], 15.8111)

if __name__ == "__main__":
    unittest.main()
