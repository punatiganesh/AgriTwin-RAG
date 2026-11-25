"""
AgriTwin-RAG — Dataset Builder and Data Integrity Validator.
Consolidates raw rice pathology images across authentic datasets into standard 5 classes:
1. Bacterial Leaf Blight
2. Brown Spot
3. Leaf Blast
4. Sheath Blight
5. Healthy

Performs:
- PIL image validation and corrupted file exclusion
- MD5 hash deduplication across the entire corpus
- Stratified 70% Train / 15% Val / 15% Test partitioning
- Zero data leakage validation (ensuring disjoint image sets)
- Class distribution reporting
"""

import hashlib
import json
import os
import random
import shutil
from pathlib import Path
from typing import Dict, List, Tuple
from PIL import Image

TARGET_CLASSES = [
    "Bacterial Leaf Blight",
    "Brown Spot",
    "Leaf Blast",
    "Sheath Blight",
    "Healthy",
]

# Source folder mappings
SOURCE_MAPPINGS = {
    "Bacterial Leaf Blight": [
        "data/sharmin3_extracted/Rice Leaf Disease/Bacterialblight",
        "data/philippines/extra_resized_raw_images/extra_resized_raw_images/bacterial_leaf_blight",
        "data/philippines/resized_raw_images/resized_raw_images/bacterial_leaf_blight",
        "data/vbookshelf/rice_leaf_diseases/Bacterial leaf blight",
        "data/goanpanda/Rice_Diseases/Bacterial Blight Disease",
    ],
    "Brown Spot": [
        "data/sharmin3_extracted/Rice Leaf Disease/Brownspot",
        "data/philippines/extra_resized_raw_images/extra_resized_raw_images/brown_spot",
        "data/philippines/resized_raw_images/resized_raw_images/brown_spot",
        "data/vbookshelf/rice_leaf_diseases/Brown spot",
        "data/goanpanda/Rice_Diseases/Brown Spot Disease",
    ],
    "Leaf Blast": [
        "data/sharmin3_extracted/Rice Leaf Disease/Blast",
        "data/philippines/extra_resized_raw_images/extra_resized_raw_images/rice_blast",
        "data/philippines/resized_raw_images/resized_raw_images/rice_blast",
        "data/goanpanda/Rice_Diseases/Blast Disease",
    ],
    "Sheath Blight": [
        "data/philippines/extra_resized_raw_images/extra_resized_raw_images/sheath_blight",
        "data/philippines/resized_raw_images/resized_raw_images/sheath_blight",
    ],
    "Healthy": [
        "data/sharmin3_extracted/Rice Leaf Disease/Healthy",
        "data/philippines/extra_resized_raw_images/extra_resized_raw_images/healthy_rice_plant",
        "data/philippines/resized_raw_images/resized_raw_images/healthy_rice_plant",
    ],
}

OUTPUT_DIR = Path("dataset")


def compute_file_hash(filepath: Path) -> str:
    """Compute MD5 hash for image deduplication."""
    hasher = hashlib.md5()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def validate_image(filepath: Path) -> bool:
    """Verify that file is a valid non-corrupted image with minimum dimensions."""
    try:
        with Image.open(filepath) as img:
            img.verify()
        with Image.open(filepath) as img:
            w, h = img.size
            if w < 32 or h < 32:
                return False
        return True
    except Exception:
        return False


def build_and_split_dataset(
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15,
    seed: int = 42,
    max_per_class: int = 600,
) -> Dict[str, any]:
    random.seed(seed)
    assert abs(train_ratio + val_ratio + test_ratio - 1.0) < 1e-4

    # Prepare destination directories
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    
    for split in ["train", "val", "test"]:
        for cls in TARGET_CLASSES:
            (OUTPUT_DIR / split / cls).mkdir(parents=True, exist_ok=True)

    seen_hashes = set()
    collected_by_class: Dict[str, List[Tuple[Path, str]]] = {cls: [] for cls in TARGET_CLASSES}
    corrupted_count = 0
    duplicate_count = 0

    print("=== Scanning Source Datasets ===")
    for cls, source_paths in SOURCE_MAPPINGS.items():
        for sp in source_paths:
            path_obj = Path(sp)
            if not path_obj.exists():
                continue
            for img_path in path_obj.rglob("*"):
                if img_path.is_file() and img_path.suffix.lower() in [".jpg", ".jpeg", ".png"]:
                    if not validate_image(img_path):
                        corrupted_count += 1
                        continue
                    
                    file_hash = compute_file_hash(img_path)
                    if file_hash in seen_hashes:
                        duplicate_count += 1
                        continue
                    
                    seen_hashes.add(file_hash)
                    collected_by_class[cls].append((img_path, file_hash))

    print(f"Total unique images found across classes: {sum(len(v) for v in collected_by_class.values())}")
    print(f"Duplicates filtered: {duplicate_count}, Corrupted filtered: {corrupted_count}")

    # Report class counts before split
    for cls in TARGET_CLASSES:
        print(f"  {cls}: {len(collected_by_class[cls])} unique images")

    # Split dataset into train/val/test
    split_counts = {
        "train": {cls: 0 for cls in TARGET_CLASSES},
        "val": {cls: 0 for cls in TARGET_CLASSES},
        "test": {cls: 0 for cls in TARGET_CLASSES},
    }
    
    train_hashes = set()
    val_hashes = set()
    test_hashes = set()

    for cls in TARGET_CLASSES:
        items = collected_by_class[cls]
        random.shuffle(items)
        # Cap if desired to balance excessive classes while retaining full sheath blight
        if max_per_class and len(items) > max_per_class:
            items = items[:max_per_class]

        n = len(items)
        n_train = int(n * train_ratio)
        n_val = int(n * val_ratio)
        n_test = n - n_train - n_val

        train_items = items[:n_train]
        val_items = items[n_train:n_train + n_val]
        test_items = items[n_train + n_val:]

        for img_path, fhash in train_items:
            dest = OUTPUT_DIR / "train" / cls / f"{cls.lower().replace(' ', '_')}_{fhash[:10]}.jpg"
            shutil.copyfile(img_path, dest)
            train_hashes.add(fhash)
            split_counts["train"][cls] += 1

        for img_path, fhash in val_items:
            dest = OUTPUT_DIR / "val" / cls / f"{cls.lower().replace(' ', '_')}_{fhash[:10]}.jpg"
            shutil.copyfile(img_path, dest)
            val_hashes.add(fhash)
            split_counts["val"][cls] += 1

        for img_path, fhash in test_items:
            dest = OUTPUT_DIR / "test" / cls / f"{cls.lower().replace(' ', '_')}_{fhash[:10]}.jpg"
            shutil.copyfile(img_path, dest)
            test_hashes.add(fhash)
            split_counts["test"][cls] += 1

    # Zero Data Leakage Check
    train_test_leak = train_hashes.intersection(test_hashes)
    train_val_leak = train_hashes.intersection(val_hashes)
    val_test_leak = val_hashes.intersection(test_hashes)

    print("\n=== Data Leakage Check ===")
    print(f"Train vs Test overlap: {len(train_test_leak)}")
    print(f"Train vs Val overlap: {len(train_val_leak)}")
    print(f"Val vs Test overlap: {len(val_test_leak)}")
    assert len(train_test_leak) == 0, "Data leakage detected between Train and Test sets!"
    assert len(train_val_leak) == 0, "Data leakage detected between Train and Val sets!"
    assert len(val_test_leak) == 0, "Data leakage detected between Val and Test sets!"
    print("Zero data leakage verified across all splits!")

    report = {
        "classes": TARGET_CLASSES,
        "split_counts": split_counts,
        "total_train": sum(split_counts["train"].values()),
        "total_val": sum(split_counts["val"].values()),
        "total_test": sum(split_counts["test"].values()),
        "duplicates_removed": duplicate_count,
        "corrupted_removed": corrupted_count,
    }

    with open("dataset/dataset_summary.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print("\n=== Final Dataset Distribution ===")
    print(f"Total Train images: {report['total_train']}")
    print(f"Total Val images: {report['total_val']}")
    print(f"Total Test images: {report['total_test']}")
    print(json.dumps(split_counts, indent=2))
    return report


if __name__ == "__main__":
    build_and_split_dataset()
