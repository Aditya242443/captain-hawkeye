import os
import logging
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict, Any
import numpy as np
from ultralytics import YOLO

from backend.config import (
    PLATE_MODEL_PATH,
    VEHICLE_MODEL_PATH,
    COCO_VEHICLE_CLASS_IDS,
    COCO_VEHICLE_CLASS_NAMES,
    PLATE_DETECTION_CONFIDENCE,
    VEHICLE_DETECTION_CONFIDENCE,
)

logger = logging.getLogger(__name__)


@dataclass
class VehicleDetection:
    """Bounding box, confidence, and type for a detected vehicle."""
    bbox: Tuple[int, int, int, int]  # (x1, y1, x2, y2)
    confidence: float
    vehicle_type: str
    class_id: int


@dataclass
class PlateDetection:
    """Bounding box, confidence, and image crop for a detected license plate."""
    bbox: Tuple[int, int, int, int]  # (x1, y1, x2, y2)
    confidence: float
    crop: Optional[np.ndarray] = None


@dataclass
class DetectionResult:
    """Combined detection results for vehicles and plates in a single frame."""
    vehicles: List[VehicleDetection]
    plates: List[PlateDetection]


class VehiclePlateDetector:
    """
    Detector handling both vehicle detection (via pretrained YOLOv11)
    and license plate detection (via fine-tuned YOLOv11 plate detector).
    """

    def __init__(
        self,
        plate_model_path: str = PLATE_MODEL_PATH,
        vehicle_model_path: str = VEHICLE_MODEL_PATH,
        lazy_load: bool = False,
    ):
        self.plate_model_path = plate_model_path
        self.vehicle_model_path = vehicle_model_path
        self.plate_model: Optional[YOLO] = None
        self.vehicle_model: Optional[YOLO] = None

        if not lazy_load:
            self.load_models()

    def load_models(self):
        """Loads or initialises the YOLO models."""
        try:
            logger.info("Loading vehicle detection model: %s", self.vehicle_model_path)
            self.vehicle_model = YOLO(self.vehicle_model_path)
        except Exception as e:
            logger.warning("Could not load vehicle model '%s': %s", self.vehicle_model_path, e)
            self.vehicle_model = None

        try:
            if os.path.exists(self.plate_model_path):
                logger.info("Loading fine-tuned plate detection model: %s", self.plate_model_path)
                self.plate_model = YOLO(self.plate_model_path)
            else:
                logger.warning(
                    "Plate model path '%s' does not exist on disk. Using vehicle detector as fallback if needed.",
                    self.plate_model_path,
                )
                self.plate_model = None
        except Exception as e:
            logger.warning("Could not load plate model '%s': %s", self.plate_model_path, e)
            self.plate_model = None

    def detect_vehicles(
        self,
        frame: np.ndarray,
        conf_threshold: float = VEHICLE_DETECTION_CONFIDENCE,
    ) -> List[VehicleDetection]:
        """
        Detects vehicles in the frame filtered to relevant COCO vehicle classes:
        car, motorcycle, bus, truck.
        """
        if self.vehicle_model is None:
            self.load_models()
        if self.vehicle_model is None:
            return []

        results = self.vehicle_model.predict(
            source=frame,
            classes=COCO_VEHICLE_CLASS_IDS,
            conf=conf_threshold,
            verbose=False,
        )

        detections: List[VehicleDetection] = []
        for result in results:
            boxes = result.boxes
            if boxes is None:
                continue
            for box in boxes:
                xyxy = box.xyxy[0].cpu().numpy().astype(int)
                conf = float(box.conf[0].cpu().numpy())
                cls_id = int(box.cls[0].cpu().numpy())
                vehicle_type = COCO_VEHICLE_CLASS_NAMES.get(cls_id, "vehicle")

                detections.append(
                    VehicleDetection(
                        bbox=(int(xyxy[0]), int(xyxy[1]), int(xyxy[2]), int(xyxy[3])),
                        confidence=conf,
                        vehicle_type=vehicle_type,
                        class_id=cls_id,
                    )
                )

        return detections

    def detect_plates(
        self,
        frame: np.ndarray,
        conf_threshold: float = PLATE_DETECTION_CONFIDENCE,
    ) -> List[PlateDetection]:
        """
        Detects license plates in the frame using the fine-tuned YOLO model.
        Extracts cropped plate images.
        """
        if self.plate_model is None:
            self.load_models()
        if self.plate_model is None:
            return []

        results = self.plate_model.predict(
            source=frame,
            conf=conf_threshold,
            verbose=False,
        )

        detections: List[PlateDetection] = []
        h, w = frame.shape[:2]

        for result in results:
            boxes = result.boxes
            if boxes is None:
                continue
            for box in boxes:
                xyxy = box.xyxy[0].cpu().numpy().astype(int)
                conf = float(box.conf[0].cpu().numpy())

                x1, y1, x2, y2 = max(0, xyxy[0]), max(0, xyxy[1]), min(w, xyxy[2]), min(h, xyxy[3])
                if x2 > x1 and y2 > y1:
                    crop = frame[y1:y2, x1:x2].copy()
                else:
                    crop = None

                detections.append(
                    PlateDetection(
                        bbox=(x1, y1, x2, y2),
                        confidence=conf,
                        crop=crop,
                    )
                )

        return detections

    def detect(
        self,
        frame: np.ndarray,
        vehicle_conf: float = VEHICLE_DETECTION_CONFIDENCE,
        plate_conf: float = PLATE_DETECTION_CONFIDENCE,
    ) -> DetectionResult:
        """
        Detects both vehicles and license plates from a single frame.
        """
        vehicles = self.detect_vehicles(frame, conf_threshold=vehicle_conf)
        plates = self.detect_plates(frame, conf_threshold=plate_conf)
        return DetectionResult(vehicles=vehicles, plates=plates)


# Global singleton detector instance (can be reused across pipelines)
_global_detector: Optional[VehiclePlateDetector] = None


def get_detector() -> VehiclePlateDetector:
    """Returns or lazily creates a singleton detector instance."""
    global _global_detector
    if _global_detector is None:
        _global_detector = VehiclePlateDetector(lazy_load=False)
    return _global_detector


def detect_vehicles_and_plates(
    frame: np.ndarray,
    detector: Optional[VehiclePlateDetector] = None,
    vehicle_conf: float = VEHICLE_DETECTION_CONFIDENCE,
    plate_conf: float = PLATE_DETECTION_CONFIDENCE,
) -> Tuple[List[VehicleDetection], List[PlateDetection]]:
    """
    Convenience function that takes a video frame and returns both vehicle bounding boxes
    (with class label for vehicle_type) and plate bounding boxes.
    """
    det = detector or get_detector()
    res = det.detect(frame, vehicle_conf=vehicle_conf, plate_conf=plate_conf)
    return res.vehicles, res.plates
