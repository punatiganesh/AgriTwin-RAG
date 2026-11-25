"""
AgriTwin-RAG — Crop Disease Prediction & Advisory Comprehensive Test Suite.
Tests API status, image upload validation, neural model inference, Grad-CAM generation,
ChromaDB ICAR RAG retrieval, Groq synthesis, and error handling.
"""

import io
import json
import unittest
from PIL import Image, ImageDraw
from app import app
from services.disease_service import (
    is_model_configured,
    load_model,
    get_class_names,
    predict_crop_disease,
    generate_disease_advisory,
    LOW_CONFIDENCE_THRESHOLD,
)


class TestCropDiseaseFeature(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = app.test_client()
        # Create a sample test image (simulated rice leaf)
        img = Image.new("RGB", (300, 300), color=(34, 139, 34))
        draw = ImageDraw.Draw(img)
        # Draw some leaf patterns and a lesion spot
        draw.ellipse([80, 80, 220, 220], fill=(139, 69, 19), outline=(160, 82, 45))
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        cls.sample_image_bytes = buf.getvalue()

    def test_01_model_configuration(self):
        """Verify model files and class labels are properly configured."""
        self.assertTrue(is_model_configured(), "rice_disease_model.pth should exist")
        class_names = get_class_names()
        self.assertIsInstance(class_names, list)
        self.assertEqual(len(class_names), 5)
        self.assertIn("Leaf Blast", class_names)
        self.assertIn("Healthy", class_names)
        self.assertIn("Bacterial Leaf Blight", class_names)
        self.assertIn("Brown Spot", class_names)
        self.assertIn("Sheath Blight", class_names)

    def test_02_status_endpoint(self):
        """Test GET /api/disease/status returns valid diagnostic schema."""
        res = self.client.get("/api/disease/status")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))
        self.assertTrue(data.get("model_configured"))
        self.assertEqual(data.get("target_crop"), "Rice")
        self.assertEqual(data.get("classes_count"), 5)
        self.assertEqual(data.get("low_confidence_threshold"), LOW_CONFIDENCE_THRESHOLD)
        self.assertTrue(data.get("gradcam_supported"))

    def test_03_predict_endpoint_valid_image(self):
        """Test POST /api/disease/predict with valid image file."""
        data = {
            "file": (io.BytesIO(self.sample_image_bytes), "sample_leaf.jpg")
        }
        res = self.client.post("/api/disease/predict", data=data, content_type="multipart/form-data")
        self.assertEqual(res.status_code, 200)
        result = res.get_json()

        # Schema Verification
        self.assertTrue(result.get("success"))
        self.assertEqual(result.get("crop"), "Rice")
        self.assertIn("disease", result)
        self.assertIn("confidence", result)
        self.assertGreater(result["confidence"], 0.0)
        self.assertLessEqual(result["confidence"], 1.0)
        self.assertIn("confidence_percentage", result)
        self.assertIn("top_predictions", result)
        self.assertEqual(len(result["top_predictions"]), 5)

        # Probabilities sum ~ 1.0
        prob_sum = sum(p["probability"] for p in result["top_predictions"])
        self.assertAlmostEqual(prob_sum, 1.0, places=2)

        # Grad-CAM verification
        gradcam = result.get("gradcam", {})
        self.assertTrue(gradcam.get("supported"))
        self.assertIsNotNone(gradcam.get("image_data"))
        self.assertTrue(gradcam.get("image_data", "").startswith("data:image/jpeg;base64,"))
        self.assertEqual(gradcam.get("label"), "Model attention visualization")

        # Provenance verification
        prov = result.get("provenance", {})
        self.assertIn("image_source", prov)
        self.assertIn("prediction_engine", prov)

    def test_04_predict_endpoint_errors(self):
        """Test error handling for missing file, invalid extension, corrupted bytes."""
        # 1. No file
        res = self.client.post("/api/disease/predict", data={})
        self.assertEqual(res.status_code, 400)
        self.assertFalse(res.get_json().get("success"))

        # 2. Invalid extension (.txt)
        res = self.client.post(
            "/api/disease/predict",
            data={"file": (io.BytesIO(b"dummy text"), "notes.txt")},
            content_type="multipart/form-data",
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("Unsupported file format", res.get_json().get("error", ""))

        # 3. Corrupted image bytes
        res = self.client.post(
            "/api/disease/predict",
            data={"file": (io.BytesIO(b"not an image"), "corrupted.jpg")},
            content_type="multipart/form-data",
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("Corrupted or invalid image", res.get_json().get("error", ""))

    def test_05_advisory_endpoint_disease(self):
        """Test POST /api/disease/advisory with detected disease and farm context."""
        payload = {
            "disease": "Leaf Blast",
            "confidence": 0.942,
            "farm_context": {
                "location": {
                    "latitude": 9.5123,
                    "longitude": 77.6321,
                    "village": "Srivilliputhur",
                    "district": "Virudhunagar",
                    "state": "Tamil Nadu",
                },
                "crop": {
                    "name": "Rice",
                    "variety": "MTU-1010",
                    "growth_stage": "Tillering / Vegetative",
                },
                "weather": {
                    "temperature": 31.5,
                    "humidity": 78,
                    "rainfall": 2.4,
                    "weather_condition": "Light Rain",
                },
                "soil": {
                    "soil_type": "Clay Loam",
                    "moisture": 32.0,
                    "ph": 6.8,
                },
                "satellite": {
                    "ndvi": 0.5421,
                },
            },
            "language": "en",
        }
        res = self.client.post(
            "/api/disease/advisory",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("disease"), "Leaf Blast")
        self.assertFalse(data.get("is_healthy"))
        self.assertIn("advisory_markdown", data)
        self.assertIn("rag_sources", data)
        self.assertIsInstance(data["rag_sources"], list)

        # Check provenance
        prov = data.get("data_provenance", {})
        self.assertEqual(prov.get("prediction"), "Rice Disease Classification Model")
        self.assertEqual(prov.get("agricultural_knowledge"), "ICAR + ChromaDB RAG")

    def test_06_advisory_endpoint_healthy(self):
        """Test POST /api/disease/advisory with Healthy crop status."""
        payload = {
            "disease": "Healthy",
            "confidence": 0.985,
            "farm_context": {
                "crop": {"name": "Rice", "variety": "BPT 5204"},
            },
            "language": "en",
        }
        res = self.client.post(
            "/api/disease/advisory",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))
        self.assertTrue(data.get("is_healthy"))
        self.assertIn("advisory_markdown", data)

    def test_07_page_routes(self):
        """Test GET /crop-disease and GET /crop-disease.html return 200."""
        with self.client.session_transaction() as sess:
            sess["farmer_id"] = 1
        for path in ["/crop-disease", "/crop-disease.html"]:
            res = self.client.get(path)
            self.assertEqual(res.status_code, 200, f"Route {path} should return 200")
            self.assertIn(b"Rice Leaf Disease Diagnostic Center", res.data)


if __name__ == "__main__":
    unittest.main()
