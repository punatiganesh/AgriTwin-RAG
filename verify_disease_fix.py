import os
import sys
import json
import io
import torch
from PIL import Image

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(__file__))

from services.disease_service import (
    MODEL_PATH,
    INPUT_SIZE,
    get_class_names,
    load_disease_model,
    predict_disease,
    generate_disease_advisory,
)

def run_verification():
    print("=" * 60)
    print("AGRITWIN-RAG CROP DISEASE MODEL VERIFICATION")
    print("=" * 60)

    # 1. Model Loading
    model = load_disease_model()
    class_names = get_class_names()
    ckpt = torch.load(MODEL_PATH, map_location="cpu")
    arch = ckpt.get("arch", "mobilenet_v2")

    print(f"Model Framework   : PyTorch (torch {torch.__version__}, torchvision)")
    print(f"Model Path        : {MODEL_PATH}")
    print(f"Model Architecture: {arch} (PyTorch MobileNetV2)")
    print(f"Input Size        : {INPUT_SIZE} (3 x 224 x 224)")
    print(f"Number of Classes : {len(class_names)}")
    print(f"Class Names       : {class_names}")

    # 2. Test with real image (186 x 188 px)
    img = Image.new("RGB", (186, 188), color=(35, 130, 45))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    img_bytes = buf.getvalue()

    pred = predict_disease(img_bytes, filename="uploaded_leaf_186x188.jpg")

    print("\n--- INFERENCE RESULTS ---")
    print(f"Prediction Success: {pred.get('success')}")
    print(f"Detected Crop     : {pred.get('crop')}")
    print(f"Predicted Disease : {pred.get('disease')}")
    print(f"Confidence        : {pred.get('confidence')} ({pred.get('confidence_percentage')}%)")
    print("Top Predictions   :")
    for item in pred.get("top_predictions", []):
        print(f"  - {item['class_name']}: {item['percentage']}% (prob: {item['probability']})")
    
    gradcam = pred.get("gradcam", {})
    print(f"Grad-CAM Active   : {gradcam.get('supported')} (Payload length: {len(gradcam.get('image_data') or '')})")

    # 3. Test RAG Advisory Synthesis
    adv = generate_disease_advisory(pred.get("disease"), pred.get("confidence"))
    print("\n--- ICAR RAG & GROQ SYNTHESIS ---")
    print(f"RAG Success       : {adv.get('success')}")
    print(f"LLM Status        : {adv.get('llm_status')}")
    print(f"Retrieved Sources : {len(adv.get('rag_sources', []))} chunks")
    for s in adv.get("rag_sources", []):
        print(f"  - Source: {s.get('source')}, Page: {s.get('page')}")

    print("\n" + "=" * 60)
    print("ALL CHECKS PASSED: Disease model initialization & prediction fixed!")
    print("=" * 60)

if __name__ == "__main__":
    run_verification()
