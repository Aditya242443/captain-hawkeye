import os
from pathlib import Path
from dotenv import load_dotenv

# Base directory for the repository
BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env file from project root
env_path = BASE_DIR / ".env"
load_dotenv(dotenv_path=env_path)

# Database Configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:W1n2A6hxFjHU4i0B@db.xsobayjdrvnivokffphd.supabase.co:5432/postgres",
)

# AI / ML Model Weights Paths
PLATE_MODEL_PATH = os.getenv(
    "PLATE_MODEL_PATH",
    str(BASE_DIR / "backend" / "anpr" / "weights" / "best.pt"),
)
VEHICLE_MODEL_PATH = os.getenv("VEHICLE_MODEL_PATH", "yolo11n.pt")

# Vehicle classes from COCO to track (COCO class IDs: 2: car, 3: motorcycle, 5: bus, 7: truck)
COCO_VEHICLE_CLASS_IDS = [2, 3, 5, 7]
COCO_VEHICLE_CLASS_NAMES = {
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck",
}

# ANPR Pipeline Configurations
MAX_CANDIDATE_FRAMES_PER_TRACK = int(os.getenv("MAX_CANDIDATE_FRAMES_PER_TRACK", "3"))
TRACK_INACTIVE_MAX_FRAMES = int(os.getenv("TRACK_INACTIVE_MAX_FRAMES", "10"))
PLATE_DETECTION_CONFIDENCE = float(os.getenv("PLATE_DETECTION_CONFIDENCE", "0.25"))
VEHICLE_DETECTION_CONFIDENCE = float(os.getenv("VEHICLE_DETECTION_CONFIDENCE", "0.35"))
OCR_CONFIDENCE_THRESHOLD = float(os.getenv("OCR_CONFIDENCE_THRESHOLD", "0.40"))
