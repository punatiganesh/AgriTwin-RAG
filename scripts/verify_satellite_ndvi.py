import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

import app as backend_app

def run_tests():
    print("Initializing Flask test client...")
    client = backend_app.app.test_client()

    print("\nTest 1: Invalid coordinates (latitude > 90)...")
    res_bad = client.get("/api/ndvi?lat=95.0&lon=79.9734")
    print(f"Status: {res_bad.status_code}")
    assert res_bad.status_code == 400, f"Expected 400, got {res_bad.status_code}"
    print("Passed Test 1!")

    print("\nTest 2: Valid coordinates (lat=9.571529, lon=77.675734, max_cloud=30)...")
    res = client.get("/api/ndvi?lat=9.571529&lon=77.675734&max_cloud=30")
    print(f"Status: {res.status_code}")
    data = res.get_json()
    print("Response JSON:")
    for k, v in data.items():
        if k in ("success", "latitude", "longitude", "ndvi", "source", "formula", "vegetation_condition", "red_reflectance", "nir_reflectance", "acquisition_date", "cloud_percentage", "image_url"):
            print(f"  {k}: {v}")

    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    assert data.get("success") is True
    assert data.get("formula") == "(NIR - RED) / (NIR + RED)"
    assert data.get("aggregation") == "median"
    assert -1.0 <= data.get("ndvi") <= 1.0
    assert data.get("red_band") == "B04"
    assert data.get("nir_band") == "B08"
    assert "image_url" in data
    print("Passed Test 2!")

    print("\nTest 3: Checking /api/satellite/image endpoint...")
    img_res = client.get("/api/satellite/image?lat=9.571529&lon=77.675734")
    print(f"Image endpoint status: {img_res.status_code}")
    assert img_res.status_code in (200, 302), f"Expected 200 or 302, got {img_res.status_code}"
    if img_res.status_code == 302:
        print(f"Redirect location: {img_res.headers.get('Location', '')[:100]}...")
    print("Passed Test 3!")

    print("\nAll satellite verification tests passed successfully!")

if __name__ == "__main__":
    run_tests()
