"""
AgriTwin-RAG 10-Point Verification Script
Tests all 10 explicit criteria from the User Prompt
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
from unittest.mock import patch
from app import app
import database.db as db

class AgriTwin10PointTest(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        app.config["SECRET_KEY"] = "test-verification-secret"
        self.client = app.test_client()

        self.patcher = patch("app.fetch_weather_data", return_value={
            "success": True,
            "location": {"name": "Test Location", "country": "IN"},
            "weather": {"temperature": 28.5, "humidity": 65, "condition": "Clear"}
        })
        self.patcher.start()

        # Clean test user if exists
        conn = db.get_db_connection()
        try:
            with conn:
                conn.execute("DELETE FROM farmers WHERE mobile = '9876543210'")
        finally:
            conn.close()

    def tearDown(self):
        self.patcher.stop()

    def test_full_user_flow(self):
        print("\n=======================================================")
        print("RUNNING 10-POINT USER REQUIREMENT VERIFICATION")
        print("=======================================================")

        # --- TEST 1: Open /login while logged out ---
        res_login_page = self.client.get("/login.html")
        self.assertEqual(res_login_page.status_code, 200)
        login_page_text = res_login_page.get_data(as_text=True)
        self.assertIn("AgriTwin-RAG", login_page_text)
        print("  [TEST 1 PASSED] Open /login while logged out -> Login page rendered (status 200).")

        # --- TEST 9: Mobile and responsive markup check ---
        self.assertIn("viewport", login_page_text)
        self.assertIn("password-toggle", login_page_text)
        res_reg_page = self.client.get("/register.html")
        self.assertEqual(res_reg_page.status_code, 200)
        self.assertIn("viewport", res_reg_page.get_data(as_text=True))
        print("  [TEST 9 PASSED] Login and registration pages include responsive viewport and password toggle.")

        # --- REGISTRATION ---
        reg_res = self.client.post("/api/auth/register", json={
            "name": "Gani",
            "mobile": "9876543210",
            "email": "gani@example.com",
            "password": "FarmerPassword@123"
        })
        self.assertEqual(reg_res.status_code, 201)
        print("  [OK] Registration: Farmer 'Gani' registered successfully.")

        # Logout right after registration to test fresh login flow
        self.client.post("/api/auth/logout")

        # --- TEST 2: Login with valid credentials ---
        login_res = self.client.post("/api/auth/login", json={
            "identifier": "9876543210",
            "password": "FarmerPassword@123"
        })
        self.assertEqual(login_res.status_code, 200)
        login_data = login_res.get_json()
        self.assertTrue(login_data["success"])
        self.assertEqual(login_data["farmer"]["name"], "Gani")
        self.assertEqual(login_data["redirect_to"], "/dashboard.html")
        print("  [TEST 2 PASSED] Login with valid credentials -> Direct redirect to /dashboard.html.")

        # --- TEST 3: Check top-right header user info ---
        user_res = self.client.get("/api/auth/user")
        self.assertEqual(user_res.status_code, 200)
        user_data = user_res.get_json()
        self.assertEqual(user_data["farmer"]["name"], "Gani")
        self.assertAlmostEqual(user_data["farm"]["latitude"], 9.571529)
        self.assertAlmostEqual(user_data["farm"]["longitude"], 77.675734)
        print("  [TEST 3 PASSED] Authenticated farmer name ('Gani') and profile data verified.")

        # --- TEST 4: Open profile dropdown / check HTML templates ---
        dash_res = self.client.get("/dashboard.html")
        self.assertEqual(dash_res.status_code, 200)
        dash_html = dash_res.get_data(as_text=True)
        self.assertIn('id="userMenuWrapper"', dash_html)
        self.assertIn('id="userDropdownMenu"', dash_html)
        self.assertIn('id="topbarLogoutBtn"', dash_html)
        print("  [TEST 4 PASSED] Profile dropdown structure with Logout button is present on pages.")

        # --- TEST 5: Click Logout ---
        logout_res = self.client.post("/api/auth/logout")
        self.assertEqual(logout_res.status_code, 200)
        logout_data = logout_res.get_json()
        self.assertTrue(logout_data["success"])
        print("  [TEST 5 PASSED] Logout API destroys session successfully.")

        # --- TEST 6: Manually open /dashboard after logout ---
        dash_unauth = self.client.get("/dashboard.html")
        self.assertEqual(dash_unauth.status_code, 302)
        self.assertIn("/login.html", dash_unauth.headers["Location"])
        print("  [TEST 6 PASSED] Opening /dashboard after logout redirects to /login.html.")

        # --- TEST 7: Login again ---
        login2_res = self.client.post("/api/auth/login", json={
            "identifier": "gani@example.com",
            "password": "FarmerPassword@123"
        })
        self.assertEqual(login2_res.status_code, 200)
        dash_auth = self.client.get("/dashboard.html")
        self.assertEqual(dash_auth.status_code, 200)
        print("  [TEST 7 PASSED] Logged in again with email identifier -> Dashboard opens normally.")

        # --- TEST 8: Refresh browser while logged in ---
        user_refresh = self.client.get("/api/auth/user")
        self.assertEqual(user_refresh.status_code, 200)
        self.assertEqual(user_refresh.get_json()["farmer"]["name"], "Gani")
        print("  [TEST 8 PASSED] Session persists correctly across requests.")

        # --- TEST 10: Verify no Farm Profile Configuration after login ---
        self.assertEqual(login_data["redirect_to"], "/dashboard.html")
        self.assertNotEqual(login_data["redirect_to"], "/farm-setup.html")
        setup_page = self.client.get("/farm-setup.html")
        self.assertEqual(setup_page.status_code, 302)
        self.assertIn("/dashboard.html", setup_page.headers["Location"])
        print("  [TEST 10 PASSED] Zero post-login setup screens; direct path to /dashboard.html.")
        print("=======================================================\n")

if __name__ == "__main__":
    unittest.main(verbosity=2)
