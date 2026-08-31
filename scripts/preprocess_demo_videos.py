"""
Project Plexis - Demo Video Preprocessing Script
Runs YOLOv11 vehicle detector, fine-tuned plate detector, and OCR recognition
over camera_1.mp4 and camera_2.mp4 to generate precomputed frame-synced bounding boxes.
"""

import os
import sys
import json
import time
from pathlib import Path
import cv2
import numpy as np

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.config import BASE_DIR
from backend.anpr.detection import get_detector
from backend.anpr.ocr import get_ocr
from backend.anpr.validation import validate_plate, correct_positional_characters, majority_vote

DEMO_VIDEOS_DIR = BASE_DIR / "test_samples" / "demo_videos"
OUTPUT_DIR = DEMO_VIDEOS_DIR
STATIC_DIR = BASE_DIR / "backend" / "static" / "demo_detections"
STATIC_DIR.mkdir(parents=True, exist_ok=True)


def process_video(video_path: Path, output_json_path: Path, sample_interval: int = 3):
    print(f"\n==========================================")
    print(f"Processing Video: {video_path.name}")
    print(f"==========================================")

    if not video_path.exists():
        print(f"[ERROR] Video file not found at: {video_path}")
        return

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        print(f"[ERROR] Failed to open video: {video_path}")
        return

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    duration_sec = total_frames / fps

    print(f"Properties: {total_frames} frames, {fps:.1f} FPS, {width}x{height}, duration: {duration_sec:.1f}s")
    print(f"Sampling every {sample_interval} frames...")

    detector = get_detector()
    ocr_engine = get_ocr()

    frames_data = []
    frame_idx = 0
    start_time = time.time()
    last_print = time.time()

    # Track resolved plates to assist continuity
    recent_resolved_plate = None
    recent_resolved_conf = 0.0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame_idx += 1

        if frame_idx % sample_interval != 0 and frame_idx != 1:
            continue

        frame_time_sec = round((frame_idx - 1) / fps, 3)

        # Detect vehicles & plates
        det_res = detector.detect(frame)

        vehicle_boxes = []
        for v in det_res.vehicles:
            x1, y1, x2, y2 = v.bbox
            vehicle_boxes.append([
                int(x1), int(y1), int(x2), int(y2),
                str(v.vehicle_type),
                round(float(v.confidence), 2)
            ])

        plate_boxes = []
        plate_text_resolved = None
        ocr_conf = 0.0

        for p in det_res.plates:
            px1, py1, px2, py2 = p.bbox
            plate_boxes.append([
                int(px1), int(py1), int(px2), int(py2),
                round(float(p.confidence), 2)
            ])

            # If we have a plate crop, attempt OCR
            if p.crop is not None and p.crop.size > 0:
                try:
                    txt, conf = ocr_engine.recognize_single(p.crop)
                    if txt and conf > 0.3:
                        corrected = correct_positional_characters(txt)
                        is_valid, _ = validate_plate(corrected)
                        if is_valid or len(corrected) >= 6:
                            plate_text_resolved = corrected
                            ocr_conf = round(float(conf), 2)
                            recent_resolved_plate = corrected
                            recent_resolved_conf = ocr_conf
                except Exception:
                    pass

        # If plate box exists but OCR was fuzzy on this specific frame, carry forward recent plate in vicinity
        if plate_boxes and not plate_text_resolved and recent_resolved_plate:
            plate_text_resolved = recent_resolved_plate
            ocr_conf = recent_resolved_conf

        frames_data.append({
            "frame_idx": frame_idx,
            "frame_time_sec": frame_time_sec,
            "vehicle_boxes": vehicle_boxes,
            "plate_boxes": plate_boxes,
            "plate_text_if_resolved": plate_text_resolved,
            "ocr_conf": ocr_conf,
        })

        if time.time() - last_print > 3.0:
            progress = (frame_idx / total_frames) * 100
            elapsed = time.time() - start_time
            print(f"  Frame {frame_idx}/{total_frames} ({progress:.1f}%) — Elapsed: {elapsed:.1f}s")
            last_print = time.time()

    cap.release()
    total_elapsed = time.time() - start_time
    print(f"[OK] Completed in {total_elapsed:.1f}s ({len(frames_data)} sampled frames)")

    # Write output JSON
    payload = {
        "video_name": video_path.name,
        "total_frames": total_frames,
        "fps": fps,
        "width": width,
        "height": height,
        "duration_sec": round(duration_sec, 2),
        "sampled_interval": sample_interval,
        "frames": frames_data,
    }

    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f)
    print(f"[OK] Saved detection JSON to: {output_json_path}")

    # Also save to static folder for web serving
    static_dest = STATIC_DIR / output_json_path.name
    with open(static_dest, "w", encoding="utf-8") as f:
        json.dump(payload, f)
    print(f"[OK] Copied to static path: {static_dest}")


def main():
    print("==========================================")
    print("Project Plexis — Demo Video Preprocessor")
    print("==========================================")

    # 1. Camera 1 (30 FPS -> sample every 3 frames = 10 FPS detection rate)
    cam1_video = DEMO_VIDEOS_DIR / "camera_1.mp4"
    cam1_json = OUTPUT_DIR / "camera_1_detections.json"
    if cam1_video.exists():
        process_video(cam1_video, cam1_json, sample_interval=3)
    else:
        print(f"[WARN] camera_1.mp4 not found at {cam1_video}")

    # 2. Camera 2 (60 FPS -> sample every 6 frames = 10 FPS detection rate)
    cam2_video = DEMO_VIDEOS_DIR / "camera_2.mp4"
    cam2_json = OUTPUT_DIR / "camera_2_detections.json"
    if cam2_video.exists():
        process_video(cam2_video, cam2_json, sample_interval=6)
    else:
        print(f"[WARN] camera_2.mp4 not found at {cam2_video}")

    print("\n[OK] Video preprocessing completed successfully!")


if __name__ == "__main__":
    main()
