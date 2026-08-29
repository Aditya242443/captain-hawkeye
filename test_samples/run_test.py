# test_samples/run_live_test.py
import os
import sys
from pathlib import Path
from datetime import datetime

import cv2
from dotenv import load_dotenv

# --- Load LOCAL env explicitly, so this test never touches the shared Supabase DB ---
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env.local")

# Ensure project root is importable
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.database import SessionLocal
from backend.anpr.pipeline import ANPRPipeline, CameraConfig
from backend.anpr.detection import get_detector


# --- Configuration ---
CAMERA_CONFIG = CameraConfig(
    camera_id="TEST_CAM_01",
    gps_lat=23.1815,
    gps_lng=79.9864,
    location_name="Live Test Camera"
)

IMAGE_DIRS = [
    "test_samples/indian_noplt/test/images",
    "test_samples/indian_noplt/train/images",
    "test_samples/indian_noplt/valid/images",
]

OUTPUT_DIR = "test_samples/outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)


def collect_image_paths(limit=None):
    """Gathers image file paths from all configured directories."""
    paths = []
    for d in IMAGE_DIRS:
        if not os.path.exists(d):
            print(f"  (skipping missing folder: {d})")
            continue
        for f in os.listdir(d):
            if f.lower().endswith((".jpg", ".jpeg", ".png")):
                paths.append(os.path.join(d, f))
    if limit:
        paths = paths[:limit]
    return paths


def visualize_one(image_path):
    """Saves an annotated copy of one image showing detected boxes."""
    img = cv2.imread(image_path)
    if img is None:
        print(f"Could not load image: {image_path}")
        return

    detector = get_detector()
    result = detector.detect(img)

    for v in result.vehicles:
        x1, y1, x2, y2 = v.bbox
        cv2.rectangle(img, (x1, y1), (x2, y2), (255, 0, 0), 2)
        cv2.putText(img, v.vehicle_type, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)

    for p in result.plates:
        x1, y1, x2, y2 = p.bbox
        cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)

    out_name = "annotated_" + os.path.basename(image_path)
    out_path = os.path.join(OUTPUT_DIR, out_name)
    cv2.imwrite(out_path, img)
    print(f"Saved: {out_path}  (vehicles={len(result.vehicles)}, plates={len(result.plates)})")


def run_batch_test(limit=None):
    """Runs the full pipeline (detect -> track -> OCR -> validate -> DB write) on a batch of images."""
    image_paths = collect_image_paths(limit=limit)
    print(f"\nFound {len(image_paths)} images to test")

    pipeline = ANPRPipeline(camera_config=CAMERA_CONFIG)
    db = SessionLocal()

    total_sightings = 0
    total_no_detection = 0
    total_errors = 0

    try:
        for i, path in enumerate(image_paths, start=1):
            img = cv2.imread(path)
            if img is None:
                print(f"  [{i}/{len(image_paths)}] Could not load: {os.path.basename(path)}")
                total_errors += 1
                continue

            try:
                sightings = pipeline.process_frame(img, timestamp=datetime.utcnow(), db=db)
                sightings += pipeline.flush_and_resolve_all(db)
            except Exception as e:
                print(f"  [{i}/{len(image_paths)}] ERROR on {os.path.basename(path)}: {e}")
                total_errors += 1
                continue

            if sightings:
                for s in sightings:
                    print(f"  [{i}/{len(image_paths)}] {os.path.basename(path)} -> "
                          f"Plate: {s.plate_text} | Confidence: {s.confidence:.2f}")
                total_sightings += len(sightings)
            else:
                total_no_detection += 1

        print("\n=== Summary ===")
        print(f"Total images processed : {len(image_paths)}")
        print(f"Sightings created      : {total_sightings}")
        print(f"No detection           : {total_no_detection}")
        print(f"Errors                 : {total_errors}")

    finally:
        db.close()


if __name__ == "__main__":
    # Step 1: visualize detection on a handful of images first (quick sanity check)
    print("=== Step 1: Visual sanity check (first 5 images) ===")
    sample_paths = collect_image_paths(limit=5)
    for p in sample_paths:
        visualize_one(p)

    # Step 2: run the full pipeline against a small batch first
    print("\n=== Step 2: Small batch test (first 20 images) ===")
    run_batch_test(limit=20)

    # Step 3: uncomment below to run against everything once the small batch looks correct
    print("\n=== Step 3: Full batch ===")
    run_batch_test(limit=None)