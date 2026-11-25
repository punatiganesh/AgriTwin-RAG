"""
AgriTwin-RAG — Model Evaluation and Calibration Diagnostics.
Calculates:
- Overall Accuracy
- Macro & Weighted Precision, Recall, F1-score
- Per-class Precision, Recall, F1-score
- Confusion Matrix
- Expected Calibration Error (ECE) and confidence reliability statistics
- Individual test case predictions for each class
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
import torchvision.models as tv_models
import torchvision.transforms as transforms

CLASSES = [
    "Bacterial Leaf Blight",
    "Brown Spot",
    "Leaf Blast",
    "Sheath Blight",
    "Healthy",
]

NORM_MEAN = [0.485, 0.456, 0.406]
NORM_STD = [0.229, 0.224, 0.225]

eval_transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=NORM_MEAN, std=NORM_STD),
])


def load_model_from_path(model_path: str, num_classes: int = 5) -> torch.nn.Module:
    """Load PyTorch MobileNetV2 model checkpoint."""
    checkpoint = torch.load(model_path, map_location=torch.device("cpu"))
    model = tv_models.mobilenet_v2(weights=None)
    in_features = model.classifier[1].in_features
    model.classifier[1] = torch.nn.Linear(in_features, num_classes)

    if isinstance(checkpoint, dict) and "model_state_dict" in checkpoint:
        model.load_state_dict(checkpoint["model_state_dict"])
    elif isinstance(checkpoint, dict) and any(k.startswith("features.") for k in checkpoint.keys()):
        model.load_state_dict(checkpoint)
    elif isinstance(checkpoint, torch.nn.Module):
        model = checkpoint
    else:
        raise ValueError(f"Unrecognized checkpoint format in {model_path}")

    model.eval()
    return model


def compute_ece(probs: np.ndarray, labels: np.ndarray, n_bins: int = 10) -> float:
    """Compute Expected Calibration Error (ECE)."""
    confidences = np.max(probs, axis=1)
    predictions = np.argmax(probs, axis=1)
    accuracies = (predictions == labels).astype(float)

    bin_boundaries = np.linspace(0, 1, n_bins + 1)
    ece = 0.0

    for i in range(n_bins):
        bin_lower = bin_boundaries[i]
        bin_upper = bin_boundaries[i + 1]
        in_bin = (confidences > bin_lower) & (confidences <= bin_upper)
        prop_in_bin = np.mean(in_bin)

        if prop_in_bin > 0:
            accuracy_in_bin = np.mean(accuracies[in_bin])
            avg_confidence_in_bin = np.mean(confidences[in_bin])
            ece += np.abs(avg_confidence_in_bin - accuracy_in_bin) * prop_in_bin

    return float(ece)


def evaluate_model_on_dataset(
    model: torch.nn.Module,
    dataset_dir: str = "dataset/test",
) -> Dict[str, any]:
    """Run full evaluation on dataset split."""
    y_true = []
    y_pred = []
    all_probs = []
    sample_details = []

    for cls_idx, cls_name in enumerate(CLASSES):
        cls_dir = Path(dataset_dir) / cls_name
        if not cls_dir.exists():
            continue
        
        for img_file in cls_dir.glob("*.jpg"):
            try:
                with Image.open(img_file).convert("RGB") as pil_img:
                    tensor = eval_transform(pil_img).unsqueeze(0)
                    with torch.no_grad():
                        logits = model(tensor)
                        probs = F.softmax(logits, dim=1).numpy()[0]
                    
                    pred_idx = int(np.argmax(probs))
                    conf = float(probs[pred_idx])
                    
                    y_true.append(cls_idx)
                    y_pred.append(pred_idx)
                    all_probs.append(probs)

                    # Top-3 predictions
                    top3_indices = np.argsort(probs)[::-1][:3]
                    top3_preds = [
                        {"class": CLASSES[i], "confidence": round(float(probs[i]), 4)}
                        for i in top3_indices
                    ]

                    if len([s for s in sample_details if s["actual"] == cls_name]) < 2:
                        sample_details.append({
                            "image": img_file.name,
                            "actual": cls_name,
                            "predicted": CLASSES[pred_idx],
                            "confidence": round(conf, 4),
                            "correct": (pred_idx == cls_idx),
                            "top_3": top3_preds,
                        })
            except Exception as e:
                print(f"Error evaluating {img_file}: {e}")

    y_true = np.array(y_true)
    y_pred = np.array(y_pred)
    all_probs = np.array(all_probs)

    acc = float(accuracy_score(y_true, y_pred))
    macro_p = float(precision_score(y_true, y_pred, average="macro", zero_division=0))
    macro_r = float(recall_score(y_true, y_pred, average="macro", zero_division=0))
    macro_f1 = float(f1_score(y_true, y_pred, average="macro", zero_division=0))
    weighted_f1 = float(f1_score(y_true, y_pred, average="weighted", zero_division=0))

    cm = confusion_matrix(y_true, y_pred, labels=list(range(len(CLASSES)))).tolist()
    ece = compute_ece(all_probs, y_true)

    # Per-class metrics
    per_class = {}
    for idx, name in enumerate(CLASSES):
        cls_mask_true = (y_true == idx)
        cls_mask_pred = (y_pred == idx)
        tp = np.sum(cls_mask_true & cls_mask_pred)
        fp = np.sum(~cls_mask_true & cls_mask_pred)
        fn = np.sum(cls_mask_true & ~cls_mask_pred)
        
        prec = float(tp / (tp + fp)) if (tp + fp) > 0 else 0.0
        rec = float(tp / (tp + fn)) if (tp + fn) > 0 else 0.0
        f1 = float(2 * prec * rec / (prec + rec)) if (prec + rec) > 0 else 0.0
        
        per_class[name] = {
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1_score": round(f1, 4),
            "support": int(np.sum(cls_mask_true)),
        }

    return {
        "accuracy": round(acc, 4),
        "macro_precision": round(macro_p, 4),
        "macro_recall": round(macro_r, 4),
        "macro_f1": round(macro_f1, 4),
        "weighted_f1": round(weighted_f1, 4),
        "ece": round(ece, 4),
        "confusion_matrix": cm,
        "classes": CLASSES,
        "per_class": per_class,
        "total_samples": len(y_true),
        "sample_predictions": sample_details,
    }


if __name__ == "__main__":
    import sys
    model_path = sys.argv[1] if len(sys.argv) > 1 else "models/rice_disease_model_v1.pth"
    split = sys.argv[2] if len(sys.argv) > 2 else "dataset/test"
    print(f"=== Evaluating Model: {model_path} on {split} ===")
    model = load_model_from_path(model_path)
    results = evaluate_model_on_dataset(model, dataset_dir=split)
    print(json.dumps(results, indent=2))
