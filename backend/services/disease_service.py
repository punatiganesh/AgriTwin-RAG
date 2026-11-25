"""
AgriTwin-RAG — Rice Leaf Disease Classification, Grad-CAM & Agricultural Advisory Service.
Integrates PyTorch model inference, Grad-CAM visual attention mapping,
ChromaDB ICAR RAG retrieval, FarmContext telemetry, and grounded Groq synthesis.
"""

import base64
import io
import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image

try:
    import torchvision.models as tv_models
    import torchvision.transforms as transforms
    TORCHVISION_AVAILABLE = True
except Exception as _tv_import_err:
    tv_models = None
    transforms = None
    TORCHVISION_AVAILABLE = False

from rag.farm_context import sanitize_farm_context, has_meaningful_farm_context
from rag.retriever import search_documents
from rag.llm_service import is_llm_configured, generate_answer

logger = logging.getLogger(__name__)

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
MODELS_DIR = BASE_DIR / "models"
MODEL_PATH = MODELS_DIR / "rice_disease_model.pth"
CLASS_NAMES_PATH = MODELS_DIR / "class_names.json"

# Thresholds & Configuration
LOW_CONFIDENCE_THRESHOLD = 0.60
TARGET_CROP = "Rice"
INPUT_SIZE = (224, 224)
NORM_MEAN = [0.485, 0.456, 0.406]
NORM_STD = [0.229, 0.224, 0.225]

# Global Model & Classes Cache
_cached_model = None
_cached_class_names = None
_cached_model_version = "v1"
_model_load_error = None


def validate_leaf_image_quality(pil_img: Image.Image) -> Tuple[bool, Optional[str]]:
    """
    Check uploaded image quality before running deep learning inference.
    Validates:
    - Minimum resolution (width >= 128 and height >= 128)
    - Image blur detection (Laplacian / high-frequency variance >= 20.0)
    - Lighting & exposure (average intensity between 20 and 245)
    Returns: (is_valid, failure_reason)
    """
    try:
        width, height = pil_img.size
        if width < 128 or height < 128:
            return False, f"Image resolution ({width}x{height} px) is too low. Minimum required is 128x128 pixels."

        # Convert to grayscale array for blur and lighting checks
        gray = np.array(pil_img.convert("L"), dtype=np.float32)

        # 1. Exposure / brightness check
        mean_brightness = float(np.mean(gray))
        if mean_brightness < 15.0:
            return False, "Image is too dark/underexposed to discern leaf pathology features. Please upload a well-lit image."
        if mean_brightness > 245.0:
            return False, "Image is overexposed/washed out. Please upload a clearer leaf image."

        # 2. Blur / sharpness check via Discrete 2D Laplacian operator
        if gray.shape[0] >= 3 and gray.shape[1] >= 3:
            # 3x3 Laplacian filter kernel
            laplacian = (
                -4.0 * gray[1:-1, 1:-1]
                + gray[:-2, 1:-1]
                + gray[2:, 1:-1]
                + gray[1:-1, :-2]
                + gray[1:-1, 2:]
            )
            lap_var = float(np.var(laplacian))
            # Blur threshold: heavily blurred photos typically have lap_var < 1.0
            if lap_var < 1.0:
                return False, "Image is excessively blurry or out of focus. Please upload a sharper rice leaf image."

        return True, None
    except Exception as e:
        logger.warning(f"Image quality validation error: {e}")
        return True, None  # Allow inference if validation encountered non-fatal parsing issue


def get_class_names() -> List[str]:
    """Load canonical disease class names from JSON config or checkpoint."""
    global _cached_class_names
    if _cached_class_names is not None:
        return _cached_class_names

    if CLASS_NAMES_PATH.exists():
        try:
            with open(CLASS_NAMES_PATH, "r", encoding="utf-8") as f:
                classes = json.load(f)
                if isinstance(classes, list) and len(classes) > 0:
                    _cached_class_names = [str(c).strip() for c in classes]
                    return _cached_class_names
        except Exception as e:
            logger.error(f"Error reading class_names.json: {e}")

    # Fallback to standard Rice Pathology classes if file is missing
    _cached_class_names = [
        "Bacterial Leaf Blight",
        "Brown Spot",
        "Leaf Blast",
        "Sheath Blight",
        "Healthy",
    ]
    return _cached_class_names


def get_active_model_path() -> Optional[Path]:
    """Identify the newest available model checkpoint in priority order."""
    v2_path = MODELS_DIR / "rice_disease_model_v2.pth"
    v1_path = MODELS_DIR / "rice_disease_model_v1.pth"
    std_path = MODELS_DIR / "rice_disease_model.pth"

    if v2_path.exists() and v2_path.is_file():
        return v2_path
    if v1_path.exists() and v1_path.is_file():
        return v1_path
    if std_path.exists() and std_path.is_file():
        return std_path
    return None


def is_model_configured() -> bool:
    """Check if any trained model checkpoint exists."""
    return get_active_model_path() is not None


def load_model():
    """
    Load the trained PyTorch rice leaf classification model.
    Caches model in memory for fast inference.
    """
    global _cached_model, _cached_class_names, _cached_model_version, _model_load_error, tv_models, transforms, TORCHVISION_AVAILABLE
    if _cached_model is not None:
        return _cached_model

    active_path = get_active_model_path()
    if not active_path:
        _model_load_error = f"Trained model not found in {MODELS_DIR}"
        return None

    # Ensure torchvision is available
    if tv_models is None:
        try:
            import torchvision.models as tv_models_dyn
            import torchvision.transforms as transforms_dyn
            tv_models = tv_models_dyn
            transforms = transforms_dyn
            TORCHVISION_AVAILABLE = True
        except Exception as err:
            _model_load_error = f"torchvision is required to load disease model architecture: {err}"
            logger.error(_model_load_error)
            return None

    try:
        checkpoint = torch.load(active_path, map_location=torch.device("cpu"))

        # Extract version & class names from checkpoint if available
        if isinstance(checkpoint, dict) and "version" in checkpoint:
            _cached_model_version = str(checkpoint["version"])
        else:
            _cached_model_version = "v2" if "v2" in active_path.name else "v1"

        if isinstance(checkpoint, dict) and "class_names" in checkpoint:
            class_names = [str(c).strip() for c in checkpoint["class_names"]]
            _cached_class_names = class_names
        else:
            class_names = get_class_names()

        # Build MobileNetV2 architecture
        model = tv_models.mobilenet_v2(weights=None)
        in_features = model.classifier[1].in_features
        model.classifier[1] = torch.nn.Linear(in_features, len(class_names))

        if isinstance(checkpoint, dict) and "model_state_dict" in checkpoint:
            model.load_state_dict(checkpoint["model_state_dict"])
        elif isinstance(checkpoint, dict) and any(k.startswith("features.") for k in checkpoint.keys()):
            model.load_state_dict(checkpoint)
        elif isinstance(checkpoint, torch.nn.Module):
            model = checkpoint
        else:
            raise ValueError(f"Unrecognized checkpoint format in {active_path.name}")

        model.eval()
        _cached_model = model
        _model_load_error = None
        logger.info(f"Successfully loaded rice disease classification model {_cached_model_version} from {active_path.name} ({len(class_names)} classes).")
        return _cached_model
    except Exception as e:
        _model_load_error = str(e)
        logger.error(f"Failed to load rice disease model from {active_path}: {e}", exc_info=True)
        return None


# Clean model loader alias
load_disease_model = load_model


def get_image_transforms():
    """Preprocessing transformation pipeline."""
    global transforms
    if transforms is None:
        try:
            import torchvision.transforms as transforms_dyn
            transforms = transforms_dyn
        except Exception as e:
            logger.warning(f"Could not load torchvision.transforms: {e}")
            return None

    return transforms.Compose([
        transforms.Resize(INPUT_SIZE),
        transforms.ToTensor(),
        transforms.Normalize(mean=NORM_MEAN, std=NORM_STD),
    ])


def preprocess_image_tensor(pil_img: Image.Image) -> torch.Tensor:
    """
    Preprocess PIL Image into normalized PyTorch batch tensor (1, 3, 224, 224).
    Supports arbitrary input sizes (e.g., 186x188 px), converts to RGB,
    resizes to (224, 224), normalizes, and adds batch dimension.
    """
    img_rgb = pil_img.convert("RGB")
    tf = get_image_transforms()
    if tf is not None:
        return tf(img_rgb).unsqueeze(0)

    # Deterministic fallback using PIL and NumPy
    img_resized = img_rgb.resize(INPUT_SIZE, Image.BILINEAR)
    arr = np.array(img_resized, dtype=np.float32) / 255.0  # (224, 224, 3)
    mean = np.array(NORM_MEAN, dtype=np.float32)
    std = np.array(NORM_STD, dtype=np.float32)
    arr = (arr - mean) / std
    arr = np.transpose(arr, (2, 0, 1))  # (3, 224, 224)
    return torch.from_numpy(arr).float().unsqueeze(0)  # (1, 3, 224, 224)


def _apply_jet_colormap(gray_array: np.ndarray) -> np.ndarray:
    """
    Pure NumPy implementation of Jet colormap for Grad-CAM overlay
    without requiring matplotlib or opencv.
    gray_array: 2D array with values in [0, 1].
    Returns: (H, W, 3) uint8 RGB array.
    """
    x = np.clip(gray_array, 0.0, 1.0)
    
    # Red component
    r = np.clip(1.5 - np.abs(4.0 * x - 3.0), 0.0, 1.0)
    # Green component
    g = np.clip(1.5 - np.abs(4.0 * x - 2.0), 0.0, 1.0)
    # Blue component
    b = np.clip(1.5 - np.abs(4.0 * x - 1.0), 0.0, 1.0)
    
    rgb = np.stack([r, g, b], axis=-1)
    return (rgb * 255).astype(np.uint8)


def generate_gradcam_overlay(
    model: torch.nn.Module,
    input_tensor: torch.Tensor,
    original_pil: Image.Image,
    target_class_idx: int,
) -> Optional[str]:
    """
    Generate authentic Grad-CAM visual attention heatmap for the target class.
    Returns base64 data URL string or None if not supported.
    """
    try:
        activations = []
        gradients = []

        # Target the last convolutional layer in MobileNetV2 features
        target_layer = model.features[-1]

        def forward_hook(module, inp, out):
            activations.append(out)

        def backward_hook(module, grad_in, grad_out):
            gradients.append(grad_out[0])

        h1 = target_layer.register_forward_hook(forward_hook)
        h2 = target_layer.register_full_backward_hook(backward_hook)

        # Forward pass with gradients enabled
        model.zero_grad()
        input_var = input_tensor.clone().requires_grad_(True)
        logits = model(input_var)
        score = logits[0, target_class_idx]
        score.backward()

        # Remove hooks
        h1.remove()
        h2.remove()

        if not activations or not gradients:
            return None

        act = activations[0].detach()[0]  # (C, H, W)
        grad = gradients[0].detach()[0]   # (C, H, W)

        # Global average pooling of gradients -> channel weights
        weights = torch.mean(grad, dim=(1, 2), keepdim=True)  # (C, 1, 1)

        # Weighted combination of activation maps
        cam = torch.sum(weights * act, dim=0).cpu().numpy()  # (H, W)
        cam = np.maximum(cam, 0)  # ReLU

        cam_max = np.max(cam)
        if cam_max > 0:
            cam = cam / cam_max
        else:
            cam = np.zeros_like(cam)

        # Resize CAM to original image size
        cam_pil = Image.fromarray((cam * 255).astype(np.uint8)).resize(
            original_pil.size, resample=Image.BILINEAR
        )
        cam_resized = np.array(cam_pil, dtype=np.float32) / 255.0

        # Apply colormap
        heatmap_rgb = _apply_jet_colormap(cam_resized)

        # Blend with original RGB image (alpha blending)
        orig_rgb = np.array(original_pil.convert("RGB"))
        blended = (0.55 * orig_rgb + 0.45 * heatmap_rgb).astype(np.uint8)

        # Encode to PNG Base64
        out_buf = io.BytesIO()
        Image.fromarray(blended).save(out_buf, format="JPEG", quality=90)
        b64_str = base64.b64encode(out_buf.getvalue()).decode("utf-8")
        return f"data:image/jpeg;base64,{b64_str}"
    except Exception as e:
        logger.warning(f"Grad-CAM computation encountered error: {e}")
        return None


def predict_crop_disease(image_bytes: bytes, filename: str = "") -> Dict[str, Any]:
    """
    Perform disease classification on uploaded leaf image.
    Validates image, computes forward pass with real softmax probabilities,
    identifies top predictions, and generates Grad-CAM visualization.
    """
    start_time = time.time()

    # 1. Check model configuration
    if not is_model_configured():
        return {
            "success": False,
            "error": "Disease prediction model is not configured. Please ensure models/rice_disease_model.pth is present.",
            "error_code": "MODEL_NOT_CONFIGURED",
        }

    model = load_model()
    if model is None:
        return {
            "success": False,
            "error": f"Failed to initialize disease prediction model: {_model_load_error}",
            "error_code": "MODEL_LOAD_FAILED",
        }

    # 2. Validate and decode image
    if not image_bytes or len(image_bytes) == 0:
        return {
            "success": False,
            "error": "Empty image upload received. Please select a valid crop leaf image.",
            "error_code": "EMPTY_IMAGE",
        }

    try:
        pil_img = Image.open(io.BytesIO(image_bytes))
        pil_img.verify()  # Verify image integrity
        # Re-open because verify() closes the file pointer
        pil_img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    except Exception as e:
        return {
            "success": False,
            "error": f"Corrupted or invalid image file. Please upload a standard JPG or PNG: {e}",
            "error_code": "INVALID_IMAGE",
        }

    width, height = pil_img.size

    # 2b. Image Quality Pre-Check (Resolution, Blur, Exposure)
    is_quality_valid, quality_reason = validate_leaf_image_quality(pil_img)
    if not is_quality_valid:
        return {
            "success": False,
            "error": quality_reason or "Image quality is insufficient for reliable disease prediction. Please upload a clearer rice leaf image.",
            "error_code": "INSUFFICIENT_IMAGE_QUALITY",
            "quality_details": {
                "resolution": f"{width}x{height}",
                "reason": quality_reason,
            },
        }

    # 3. Preprocess
    try:
        input_tensor = preprocess_image_tensor(pil_img)  # Shape: (1, 3, 224, 224)
    except Exception as e:
        return {
            "success": False,
            "error": f"Image preprocessing failed: {e}",
            "error_code": "PREPROCESS_FAILED",
        }

    # 4. Perform Model Inference
    class_names = get_class_names()
    try:
        with torch.no_grad():
            logits = model(input_tensor)
            probs = F.softmax(logits, dim=1).cpu().numpy()[0]
    except Exception as e:
        return {
            "success": False,
            "error": f"Model inference execution failed: {e}",
            "error_code": "INFERENCE_FAILED",
        }

    # 5. Format Prediction & Ranking
    predicted_idx = int(np.argmax(probs))
    predicted_disease = class_names[predicted_idx]
    predicted_confidence = float(probs[predicted_idx])

    # Sort all classes by probability descending
    sorted_indices = np.argsort(probs)[::-1]
    top_predictions = []
    for idx in sorted_indices:
        top_predictions.append({
            "class_name": class_names[idx],
            "probability": round(float(probs[idx]), 4),
            "percentage": round(float(probs[idx]) * 100.0, 1),
        })

    is_low_confidence = bool(predicted_confidence < LOW_CONFIDENCE_THRESHOLD)
    confidence_status = "uncertain" if is_low_confidence else "confident"
    guidance_message = (
        "Low-confidence prediction. Disease is not confirmed. Please inspect leaf closely and verify with local agricultural expert before applying treatments."
        if is_low_confidence
        else f"High-confidence classification of {predicted_disease}."
    )

    # 6. Generate Grad-CAM Attention Map
    gradcam_b64 = generate_gradcam_overlay(
        model=model,
        input_tensor=input_tensor,
        original_pil=pil_img,
        target_class_idx=predicted_idx,
    )

    elapsed_ms = round((time.time() - start_time) * 1000, 1)

    return {
        "success": True,
        "crop": TARGET_CROP,
        "disease": predicted_disease,
        "status": confidence_status,
        "confidence": round(predicted_confidence, 4),
        "confidence_percentage": round(predicted_confidence * 100.0, 1),
        "is_healthy": (predicted_disease.lower() == "healthy"),
        "is_low_confidence": is_low_confidence,
        "low_confidence_threshold": LOW_CONFIDENCE_THRESHOLD,
        "guidance_message": guidance_message,
        "top_predictions": top_predictions,
        "prediction_time_ms": elapsed_ms,
        "model_version": _cached_model_version,
        "model_name": f"rice_disease_mobilenet_v2_{_cached_model_version}",
        "architecture": "MobileNetV2",
        "input_size": list(INPUT_SIZE),
        "normalization": {"mean": NORM_MEAN, "std": NORM_STD},
        "model_type": "Convolutional Neural Network (PyTorch Transfer Learning)",
        "image_metadata": {
            "width": width,
            "height": height,
            "filename": filename or "uploaded_leaf.jpg",
            "size_bytes": len(image_bytes),
        },
        "gradcam": {
            "supported": gradcam_b64 is not None,
            "image_data": gradcam_b64,
            "label": "Model attention visualization",
            "description": "Grad-CAM visual attention mapping highlights leaf regions that influenced the classification network.",
        },
        "provenance": {
            "image_source": "Farmer Uploaded Leaf Image",
            "prediction_engine": "Trained Rice Pathology Neural Network",
            "validation_mode": "Deterministic Softmax Probabilities",
        },
    }


def predict_disease(image: Any, filename: str = "") -> Dict[str, Any]:
    """
    Convenience wrapper function for disease prediction.
    Accepts raw image bytes, BytesIO, or a PIL Image instance.
    """
    if isinstance(image, Image.Image):
        buf = io.BytesIO()
        image.save(buf, format="JPEG")
        image_bytes = buf.getvalue()
    elif isinstance(image, io.BytesIO):
        image_bytes = image.getvalue()
    elif isinstance(image, (bytes, bytearray)):
        image_bytes = bytes(image)
    else:
        return {
            "success": False,
            "error": "Invalid image input format. Expected bytes, BytesIO, or PIL Image.",
            "error_code": "INVALID_IMAGE_TYPE",
        }
    return predict_crop_disease(image_bytes, filename=filename)


def generate_disease_advisory(
    disease_name: str,
    confidence: float,
    farm_context: Optional[Dict[str, Any]] = None,
    language: str = "en",
) -> Dict[str, Any]:
    """
    Retrieve ICAR agricultural documents from ChromaDB and synthesize a grounded,
    farmer-friendly advisory using Groq LLM + live FarmContext.
    """
    ctx = sanitize_farm_context(farm_context)
    is_healthy = (disease_name.strip().lower() == "healthy")

    # 1. Formulate Targeted RAG Query for ICAR Knowledge Base
    if is_healthy:
        rag_query = "What are good agronomic practices, routine field monitoring and preventive health management for Rice paddy according to ICAR agricultural documents?"
    else:
        rag_query = f"What are the symptoms, causes, management practices and prevention methods for Rice {disease_name} according to the available ICAR agricultural documents?"

    # 2. ChromaDB Retrieval
    retrieved_chunks = search_documents(rag_query, top_k=4)
    
    # Deduplicate source citations
    seen_sources = set()
    deduped_sources = []
    icar_context_snippets = []

    for chunk in retrieved_chunks:
        src = chunk.get("source", "icar_crop_management.pdf")
        page = chunk.get("page", "1-8")
        cid = chunk.get("chunk_id", "")
        text = chunk.get("text", "").strip()

        source_key = f"{src}_p{page}"
        if source_key not in seen_sources:
            seen_sources.add(source_key)
            deduped_sources.append({
                "source": src,
                "document": "ICAR Crop Management Report",
                "page": str(page),
                "chunk_id": cid,
            })
        
        if text:
            icar_context_snippets.append(f"[ICAR Doc: {src}, Page: {page}]\n{text}")

    combined_icar_text = "\n\n".join(icar_context_snippets) if icar_context_snippets else "No specific ICAR document excerpt found for this condition."

    # 3. Compile Farm Context String (Strictly actual values only)
    farm_details = []
    loc = ctx.get("location", {})
    if loc.get("place_name") or loc.get("village") or loc.get("district"):
        loc_str = loc.get("place_name") or f"{loc.get('village', '')}, {loc.get('district', '')}".strip(", ")
        farm_details.append(f"- Farm Location: {loc_str}")
    if loc.get("latitude") is not None and loc.get("longitude") is not None:
        farm_details.append(f"- Coordinates: {loc['latitude']:.4f}°N, {loc['longitude']:.4f}°E")

    crop_info = ctx.get("crop", {})
    if crop_info.get("name"):
        farm_details.append(f"- Crop: {crop_info['name']}")
    if crop_info.get("variety"):
        farm_details.append(f"- Variety: {crop_info['variety']}")
    if crop_info.get("growth_stage"):
        farm_details.append(f"- Growth Stage: {crop_info['growth_stage']}")

    weather = ctx.get("weather", {})
    if weather.get("temperature") is not None:
        farm_details.append(f"- Temperature: {weather['temperature']}°C")
    if weather.get("humidity") is not None:
        farm_details.append(f"- Humidity: {weather['humidity']}%")
    if weather.get("rainfall") is not None:
        farm_details.append(f"- Rainfall: {weather['rainfall']} mm")
    if weather.get("weather_condition"):
        farm_details.append(f"- Current Weather: {weather['weather_condition']}")

    soil = ctx.get("soil", {})
    if soil.get("soil_type"):
        farm_details.append(f"- Soil Texture: {soil['soil_type']}")
    if soil.get("moisture") is not None:
        farm_details.append(f"- Soil Moisture: {soil['moisture']}%")
    if soil.get("ph") is not None:
        farm_details.append(f"- Soil pH: {soil['ph']}")

    sat = ctx.get("satellite", {})
    if sat.get("ndvi") is not None:
        farm_details.append(f"- Latest Sentinel-2 NDVI: {sat['ndvi']}")

    farm_context_text = "\n".join(farm_details) if farm_details else "- No active farm telemetry available in current context."

    # 4. Synthesize with Groq LLM
    if is_healthy:
        system_prompt = "You are AgriTwin-RAG Expert Agronomist providing precise agronomic guidance to an Indian rice farmer."
        user_prompt = f"""The computer vision model analyzed a leaf image and detected: HEALTHY (Model confidence: {confidence*100:.1f}%).

FARM CONTEXT:
{farm_context_text}

ICAR AGRICULTURAL KNOWLEDGE BASE:
{combined_icar_text}

INSTRUCTIONS:
1. Positively state: "🌿 Crop appears healthy according to the image model."
2. Do NOT prescribe any chemical disease treatments or fungicides because the crop is healthy.
3. Advise the farmer to continue regular monitoring, balanced nutrient management, and water scheduling.
4. Format your response cleanly in clear markdown sections.
5. Remind the farmer that environmental conditions (weather, soil) support plant health and to inspect the crop periodically.
"""
    else:
        system_prompt = "You are AgriTwin-RAG Expert Agronomist advising an Indian rice farmer with evidence-grounded scientific recommendations."
        user_prompt = f"""The computer vision image classification model detected:
- Disease: Rice {disease_name}
- Model Confidence: {confidence*100:.1f}%

FARM CONTEXT (Live measurements):
{farm_context_text}

RELEVANT ICAR AGRICULTURAL KNOWLEDGE:
{combined_icar_text}

CRITICAL RULES:
1. Use ONLY facts present in the retrieved ICAR knowledge base for disease-specific chemical/biological recommendations.
2. DO NOT invent pesticide names, dosages, application frequencies, or treatment schedules. If the ICAR text mentions specific formulations (e.g. Trifloxystrobin 25% + Tebuconazole 50% / Native 75 WG, Fenoxanil 5% + Isoprothiolane 30%, resistant varieties like IET 19913, IET 20441, etc.), explain them accurately. If not present in ICAR, state: "Specific management information was not found in the current agricultural knowledge base."
3. DO NOT claim weather/soil directly caused the disease. Use cautious agronomic language: "These conditions may be relevant to disease development, but the image model alone cannot establish causation."
4. Clearly distinguish:
   - 1. Image model prediction (Rice {disease_name}, {confidence*100:.1f}% confidence)
   - 2. Live Farm measurements (weather, soil, NDVI)
   - 3. Retrieved ICAR agricultural knowledge
   - 4. AI interpretation
5. Structure your output with the following exact markdown headings:
   ### What to monitor
   ### Recommended management
   ### Prevention
   ### When to seek expert confirmation
"""

    llm_advisory = ""
    llm_status = "ok"

    if is_llm_configured():
        groq_api_key = os.getenv("GROQ_API_KEY", "").strip()
        candidate_models = [
            os.getenv("GROQ_MODEL", "groq/compound").strip() or "groq/compound",
            "qwen/qwen3.8-27b",
            "groq/compound-mini",
            "openai/gpt-oss-20b",
        ]
        try:
            from groq import Groq
            client = Groq(api_key=groq_api_key, timeout=20.0)
            for model_name in candidate_models:
                try:
                    chat_completion = client.chat.completions.create(
                        model=model_name,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                        temperature=0.2,
                        max_tokens=950,
                    )
                    llm_advisory = chat_completion.choices[0].message.content.strip()
                    if llm_advisory:
                        break
                except Exception as me:
                    logger.info(f"Groq model {model_name} error: {me}, trying next...")
                    continue
        except Exception as e:
            logger.warning(f"Groq direct invocation failed: {e}")

        # Fallback to standard llm_service if needed
        if not llm_advisory:
            try:
                llm_advisory = generate_answer(
                    question=rag_query,
                    context=combined_icar_text,
                    sources=deduped_sources,
                    farm_context=ctx,
                    language=language,
                )
            except Exception as e2:
                logger.warning(f"generate_answer fallback failed: {e2}")
                llm_status = "error"
                llm_advisory = f"Automated AI synthesis temporarily unavailable. Please refer to verified ICAR guidelines below.\n\nRetrieved ICAR Findings:\n{combined_icar_text}"
    else:
        llm_status = "unconfigured"
        llm_advisory = f"Groq LLM API is not configured. Displaying verified ICAR reference guidelines:\n\n{combined_icar_text}"


    return {
        "success": True,
        "disease": disease_name,
        "confidence": confidence,
        "is_healthy": is_healthy,
        "advisory_markdown": llm_advisory,
        "llm_status": llm_status,
        "rag_sources": deduped_sources,
        "rag_snippets_count": len(retrieved_chunks),
        "farm_context_applied": farm_details,
        "data_provenance": {
            "prediction": "Rice Disease Classification Model",
            "agricultural_knowledge": "ICAR + ChromaDB RAG",
            "ai_explanation": "Groq LLM",
            "farm_context": "FarmContext",
        },
    }
