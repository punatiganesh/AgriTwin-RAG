"""
AgriTwin-RAG — Two-Stage Transfer Learning Trainer for Rice Crop Disease Classification.
Trains MobileNetV2 across 5 canonical classes:
1. Bacterial Leaf Blight
2. Brown Spot
3. Leaf Blast
4. Sheath Blight
5. Healthy

Features:
- Stage 1: Frozen backbone linear probe head warmup.
- Stage 2: Selective upper-backbone unfreezing & low-LR fine-tuning.
- Realistic agricultural data augmentations.
- Class-weighted Cross-Entropy loss for handling natural class imbalance.
- AdamW optimizer with CosineAnnealingLR scheduling.
- Validation checkpointing based on Macro F1.
- Saves model to models/rice_disease_model_v2.pth
"""

import json
import os
import time
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, Dataset
from PIL import Image
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
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


class RiceDataset(Dataset):
    """PyTorch Dataset for Rice Leaf Images."""

    def __init__(self, root_dir: str, transform=None):
        self.root_dir = Path(root_dir)
        self.transform = transform
        self.samples = []

        for class_idx, class_name in enumerate(CLASSES):
            class_folder = self.root_dir / class_name
            if not class_folder.exists():
                continue
            for img_path in class_folder.glob("*.jpg"):
                self.samples.append((str(img_path), class_idx))

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        img_path, label = self.samples[idx]
        with Image.open(img_path).convert("RGB") as pil_img:
            if self.transform:
                tensor = self.transform(pil_img)
            else:
                tensor = transforms.ToTensor()(pil_img)
        return tensor, label


def get_transforms():
    """Realistic Agricultural Data Augmentation Pipeline."""
    train_transform = transforms.Compose([
        transforms.Resize((240, 240)),
        transforms.RandomResizedCrop(224, scale=(0.85, 1.0)),
        transforms.RandomHorizontalFlip(p=0.5),
        transforms.RandomRotation(degrees=15),
        transforms.ColorJitter(brightness=0.15, contrast=0.15, saturation=0.10),
        transforms.ToTensor(),
        transforms.Normalize(mean=NORM_MEAN, std=NORM_STD),
    ])

    val_transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=NORM_MEAN, std=NORM_STD),
    ])

    return train_transform, val_transform


def compute_class_weights(train_dataset: RiceDataset) -> torch.Tensor:
    """Compute balanced class weights for Cross-Entropy Loss."""
    labels = [label for _, label in train_dataset.samples]
    class_counts = [labels.count(i) for i in range(len(CLASSES))]
    total = len(labels)
    weights = [total / (len(CLASSES) * max(c, 1)) for c in class_counts]
    # Smooth extreme weights slightly to maintain gradient stability
    weights = np.array(weights, dtype=np.float32)
    weights = weights / np.mean(weights)
    print(f"Class counts in training: {class_counts}")
    print(f"Calculated Class weights: {weights.tolist()}")
    return torch.tensor(weights, dtype=torch.float32)


def evaluate(model: nn.Module, data_loader: DataLoader, criterion: nn.Module, device: torch.device) -> Tuple[float, float, float]:
    """Evaluate model on validation/test DataLoader."""
    model.eval()
    total_loss = 0.0
    all_preds = []
    all_targets = []

    with torch.no_grad():
        for images, labels in data_loader:
            images = images.to(device)
            labels = labels.to(device)
            outputs = model(images)
            loss = criterion(outputs, labels)

            total_loss += loss.item() * images.size(0)
            preds = torch.argmax(outputs, dim=1).cpu().numpy()
            all_preds.extend(preds)
            all_targets.extend(labels.cpu().numpy())

    avg_loss = total_loss / len(data_loader.dataset)
    acc = accuracy_score(all_targets, all_preds)
    macro_f1 = f1_score(all_targets, all_preds, average="macro", zero_division=0)
    return avg_loss, float(acc), float(macro_f1)


def train_two_stage_model(
    train_dir: str = "dataset/train",
    val_dir: str = "dataset/val",
    output_model_path: str = "models/rice_disease_model_v2.pth",
    stage1_epochs: int = 5,
    stage2_epochs: int = 10,
    batch_size: int = 32,
    device_str: str = "cpu",
):
    device = torch.device(device_str)
    print(f"Using device: {device}")

    train_tf, val_tf = get_transforms()
    train_ds = RiceDataset(train_dir, transform=train_tf)
    val_ds = RiceDataset(val_dir, transform=val_tf)

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False, num_workers=0)

    class_weights = compute_class_weights(train_ds).to(device)
    criterion = nn.CrossEntropyLoss(weight=class_weights)

    # 1. Initialize MobileNetV2 with ImageNet pretrained backbone
    print("\n--- Initializing Pretrained MobileNetV2 ---")
    try:
        model = tv_models.mobilenet_v2(weights=tv_models.MobileNet_V2_Weights.DEFAULT)
    except Exception as e:
        print(f"Default weights warning: {e}, using IMAGENET1K_V1...")
        model = tv_models.mobilenet_v2(weights=tv_models.MobileNet_V2_Weights.IMAGENET1K_V1)

    in_features = model.classifier[1].in_features
    # Replace final linear layer with 5-class head
    model.classifier = nn.Sequential(
        nn.Dropout(p=0.2, inplace=False),
        nn.Linear(in_features, len(CLASSES)),
    )
    model.to(device)

    # -------------------------------------------------------------
    # STAGE 1: Train Classifier Head (Backbone Frozen)
    # -------------------------------------------------------------
    print("\n==================================================")
    print(f"STAGE 1: Linear Probe Warmup ({stage1_epochs} Epochs)")
    print("==================================================")
    for param in model.features.parameters():
        param.requires_grad = False

    optimizer_stage1 = optim.AdamW(model.classifier.parameters(), lr=1e-3, weight_decay=1e-4)

    best_val_f1 = 0.0
    best_state_dict = None

    for epoch in range(1, stage1_epochs + 1):
        model.train()
        running_loss = 0.0
        start_t = time.time()

        for images, labels in train_loader:
            images = images.to(device)
            labels = labels.to(device)

            optimizer_stage1.zero_grad()
            outputs = model(images)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer_stage1.step()

            running_loss += loss.item() * images.size(0)

        train_loss = running_loss / len(train_ds)
        val_loss, val_acc, val_f1 = evaluate(model, val_loader, criterion, device)
        elapsed = time.time() - start_t

        print(f"[Stage 1 - Epoch {epoch}/{stage1_epochs}] Train Loss: {train_loss:.4f} | Val Loss: {val_loss:.4f} | Val Acc: {val_acc*100:.2f}% | Val Macro F1: {val_f1:.4f} ({elapsed:.1f}s)")

        if val_f1 > best_val_f1:
            best_val_f1 = val_f1
            best_state_dict = model.state_dict().copy()

    # -------------------------------------------------------------
    # STAGE 2: Fine-Tune Upper Backbone (Low Learning Rate)
    # -------------------------------------------------------------
    print("\n==================================================")
    print(f"STAGE 2: Fine-Tuning Upper Backbone ({stage2_epochs} Epochs)")
    print("==================================================")
    
    # Load best weights from Stage 1
    if best_state_dict is not None:
        model.load_state_dict(best_state_dict)

    # Unfreeze upper blocks: features[14:] through features[18]
    for idx, child in enumerate(model.features):
        if idx >= 14:
            for param in child.parameters():
                param.requires_grad = True
        else:
            for param in child.parameters():
                param.requires_grad = False

    trainable_params = [p for p in model.parameters() if p.requires_grad]
    optimizer_stage2 = optim.AdamW(trainable_params, lr=1e-4, weight_decay=1e-4)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer_stage2, T_max=stage2_epochs, eta_min=1e-6)

    for epoch in range(1, stage2_epochs + 1):
        model.train()
        running_loss = 0.0
        start_t = time.time()

        for images, labels in train_loader:
            images = images.to(device)
            labels = labels.to(device)

            optimizer_stage2.zero_grad()
            outputs = model(images)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer_stage2.step()

            running_loss += loss.item() * images.size(0)

        scheduler.step()
        train_loss = running_loss / len(train_ds)
        val_loss, val_acc, val_f1 = evaluate(model, val_loader, criterion, device)
        elapsed = time.time() - start_t

        print(f"[Stage 2 - Epoch {epoch}/{stage2_epochs}] Train Loss: {train_loss:.4f} | Val Loss: {val_loss:.4f} | Val Acc: {val_acc*100:.2f}% | Val Macro F1: {val_f1:.4f} ({elapsed:.1f}s)")

        if val_f1 > best_val_f1:
            best_val_f1 = val_f1
            best_state_dict = model.state_dict().copy()
            print(f"  -> New Best Validation Macro F1: {best_val_f1:.4f}! Checkpoint cached.")

    # Save final best checkpoint
    print(f"\nSaving Best Checkpoint to {output_model_path} (Best Val Macro F1: {best_val_f1:.4f})...")
    os.makedirs(os.path.dirname(output_model_path), exist_ok=True)
    
    checkpoint_payload = {
        "model_state_dict": best_state_dict if best_state_dict is not None else model.state_dict(),
        "class_names": CLASSES,
        "arch": "mobilenet_v2",
        "input_size": [3, 224, 224],
        "mean": NORM_MEAN,
        "std": NORM_STD,
        "best_val_macro_f1": float(best_val_f1),
        "version": "v2",
        "training_date": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    torch.save(checkpoint_payload, output_model_path)
    print("Model training successfully completed and saved!")


if __name__ == "__main__":
    train_two_stage_model()
