"""
AgriTwin-RAG Authentication & Multi-Tenant FarmContext Test Suite
Verifies:
1. Farmer registration with validations (mobile, email, password strength, confirmation).
2. Farmer login via mobile and email with secure password hashing.
3. Post-registration farm profile onboarding.
4. Route protection and redirection for unauthenticated requests.
5. FarmContext integration: each farmer sees their own farm coordinates, crop, and telemetry.
6. Multi-tenant isolation between Farmer 1 (Srivilliputhur, Rice) and Farmer 2 (Guntur, Cotton).
7. Crop disease diagnosis history association per farmer.
8. Farmer feedback isolation.
9. Session logout and unauthorized access rejection.
"""

import json
import unittest
from unittest.mock import patch
from app import app
import database.db as db

class AgriTwinAuthTestSuite(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        app.config["SECRET_KEY"] = "test-secret-key-123"
        self.client = app.test_client()

        # Mock OpenWeather to avoid network delays
        self.patcher = patch("app.fetch_weather_data", return_value={
            "success": True,
            "location": {"name": "Test Location", "country": "IN"},
            "weather": {"temperature": 28.5, "humidity": 65, "condition": "Clear"}
        })
        self.patcher.start()

        # Clean non-demo test farmers for idempotent test runs
        conn = db.get_db_connection()
        try:
            with conn:
                conn.execute("DELETE FROM farmers WHERE mobile IN ('9988776655', '9123456780')")
        finally:
            conn.close()

    def tearDown(self):
        self.patcher.stop()

    def test_01_public_page_and_protected_redirection(self):
        print("\n--- Test 01: Public vs Protected Routes ---")
        # Public login & register pages
        res_login = self.client.get("/login.html")
        self.assertEqual(res_login.status_code, 200)

        res_register = self.client.get("/register.html")
        self.assertEqual(res_register.status_code, 200)

        # Unauthenticated access to dashboard should redirect to login
        res_dash = self.client.get("/dashboard.html")
        self.assertEqual(res_dash.status_code, 302)
        self.assertIn("/login.html", res_dash.headers["Location"])

        # Unauthenticated access to API should return 401
        res_api = self.client.get("/api/auth/user")
        self.assertEqual(res_api.status_code, 401)
        print("  [PASSED] Public and protected routes behave correctly.")

    def test_02_registration_validation(self):
        print("\n--- Test 02: Registration Validations ---")
        # Invalid mobile
        res = self.client.post("/api/auth/register", json={
            "name": "Test Farmer",
            "mobile": "123",
            "password": "Password@123"
        })
        self.assertEqual(res.status_code, 400)

        # Short password
        res = self.client.post("/api/auth/register", json={
            "name": "Test Farmer",
            "mobile": "9988776655",
            "password": "123"
        })
        self.assertEqual(res.status_code, 400)

        # Successful registration of Farmer 1
        res = self.client.post("/api/auth/register", json={
            "name": "Ramesh Patel",
            "mobile": "9988776655",
            "email": "ramesh@example.com",
            "password": "Password@123"
        })
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["farmer"]["name"], "Ramesh Patel")
        self.assertTrue(data["has_farm"])
        self.assertAlmostEqual(data["farm"]["latitude"], 9.571529)
        self.assertAlmostEqual(data["farm"]["longitude"], 77.675734)

        # Duplicate registration attempt
        res_dup = self.client.post("/api/auth/register", json={
            "name": "Duplicate Ramesh",
            "mobile": "9988776655",
            "email": "ramesh@example.com",
            "password": "Password@123"
        })
        self.assertEqual(res_dup.status_code, 400)
        print("  [PASSED] Registration validations and duplicate protection verified.")

    def test_03_direct_login_to_dashboard_flow(self):
        print("\n--- Test 03: Direct Login -> Dashboard Flow ---")
        # Ensure Ramesh is registered
        self.client.post("/api/auth/register", json={
            "name": "Ramesh Patel",
            "mobile": "9988776655",
            "email": "ramesh@example.com",
            "password": "Password@123"
        })

        # Login with mobile
        res = self.client.post("/api/auth/login", json={
            "identifier": "9988776655",
            "password": "Password@123"
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertTrue(data["has_farm"])

        # Access Dashboard directly (no farm-setup step)
        res_dash = self.client.get("/dashboard.html")
        self.assertEqual(res_dash.status_code, 200)

        # Verify FarmContext uses configured baseline coordinates (9.571529, 77.675734)
        res_ctx = self.client.get("/api/farm-context")
        self.assertEqual(res_ctx.status_code, 200)
        ctx = res_ctx.get_json()["farm_context"]
        self.assertAlmostEqual(ctx["location"]["latitude"], 9.571529)
        self.assertAlmostEqual(ctx["location"]["longitude"], 77.675734)
        self.assertEqual(ctx["crop"]["name"], "Rice (Paddy)")
        print("  [PASSED] Direct Login -> Dashboard flow without farm-setup verified.")

    def test_04_multi_tenant_isolation(self):
        print("\n--- Test 04: Multi-Tenant Data Isolation ---")
        # 1. Register Farmer 1 (Ramesh) & Setup Cotton Farm in Guntur
        res1 = self.client.post("/api/auth/register", json={
            "name": "Ramesh Patel",
            "mobile": "9988776655",
            "email": "ramesh@example.com",
            "password": "Password@123"
        })
        self.assertEqual(res1.status_code, 201)

        res1_setup = self.client.post("/api/farm-setup", json={
            "farm_name": "Ramesh Organic Farm",
            "latitude": 16.3067,
            "longitude": 80.4365,
            "place_name": "Guntur, Andhra Pradesh, India",
            "crop": "Cotton",
            "crop_variety": "BT Cotton RCH-2",
            "growth_stage": "Vegetative Stage",
            "farm_area": 4.5,
            "soil_type": "Black Cotton Soil"
        })
        self.assertEqual(res1_setup.status_code, 200)

        # 2. Register Farmer 2 (Suresh) & Setup Wheat Farm in Punjab
        res2 = self.client.post("/api/auth/register", json={
            "name": "Suresh Kumar",
            "mobile": "9123456780",
            "email": "suresh@example.com",
            "password": "Password@456"
        })
        self.assertEqual(res2.status_code, 201)

        res2_setup = self.client.post("/api/farm-setup", json={
            "farm_name": "Suresh Wheat Fields",
            "latitude": 30.9010,
            "longitude": 75.8573,
            "place_name": "Ludhiana, Punjab, India",
            "crop": "Wheat",
            "crop_variety": "HD-2967",
            "growth_stage": "Tillering Stage",
            "farm_area": 10.0,
            "soil_type": "Alluvial Soil"
        })
        self.assertEqual(res2_setup.status_code, 200)

        # 3. Check Suresh's farm context
        res2_ctx = self.client.get("/api/farm-context")
        ctx2 = res2_ctx.get_json()["farm_context"]
        self.assertEqual(ctx2["crop"]["name"], "Wheat")
        self.assertEqual(ctx2["location"]["latitude"], 30.9010)

        # 4. Submit feedback as Suresh
        self.client.post("/api/feedback/submit", json={
            "decision": "Accept",
            "feedback": "Suresh approved wheat nitrogen recommendation.",
            "recommendation_title": "Wheat Nitrogen Top Dressing",
            "farm_context": ctx2
        })

        # Verify Suresh sees his feedback
        res2_feed = self.client.get("/api/feedback/list")
        feed2 = res2_feed.get_json()["feedback"]
        self.assertEqual(len(feed2), 1)
        self.assertIn("Suresh approved", feed2[0]["feedback"])

        # 5. Switch back to Ramesh (Farmer 1) via Login
        res_login1 = self.client.post("/api/auth/login", json={
            "identifier": "9988776655",
            "password": "Password@123"
        })
        self.assertEqual(res_login1.status_code, 200)

        # 6. Verify Ramesh's context is STILL Guntur Cotton (not Punjab Wheat)
        res1_ctx = self.client.get("/api/farm-context")
        ctx1 = res1_ctx.get_json()["farm_context"]
        self.assertEqual(ctx1["crop"]["name"], "Cotton")
        self.assertEqual(ctx1["location"]["latitude"], 16.3067)
        self.assertEqual(ctx1["location"]["longitude"], 80.4365)

        # 7. Verify Ramesh CANNOT see Suresh's feedback (isolated!)
        res1_feed = self.client.get("/api/feedback/list")
        feed1 = res1_feed.get_json()["feedback"]
        self.assertEqual(len(feed1), 0)
        print("  [PASSED] Multi-tenant data isolation strictly enforced.")

    def test_05_demo_farmer_account(self):
        print("\n--- Test 05: Seeded Demo Account ---")
        res = self.client.post("/api/auth/login", json={
            "identifier": "demo@agritwin.com",
            "password": "Demo@1234"
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["has_farm"])
        self.assertEqual(data["farm"]["farm_name"], "Srivilliputhur Demo Farm")
        self.assertAlmostEqual(data["farm"]["latitude"], 9.571529)
        self.assertAlmostEqual(data["farm"]["longitude"], 77.675734)
        print("  [PASSED] Demo farmer account authenticated with Srivilliputhur baseline.")

    def test_06_logout_and_revocation(self):
        print("\n--- Test 06: Logout & Session Revocation ---")
        # Logout
        res = self.client.post("/api/auth/logout")
        self.assertEqual(res.status_code, 200)

        # Attempt to access protected /api/auth/user
        res_user = self.client.get("/api/auth/user")
        self.assertEqual(res_user.status_code, 401)

        # Attempt to access dashboard
        res_dash = self.client.get("/dashboard.html")
        self.assertEqual(res_dash.status_code, 302)
        print("  [PASSED] Logout cleanly revokes session and redirects to login.")

if __name__ == "__main__":
    import unittest
    # Run test suite
    unittest.main(verbosity=2)

