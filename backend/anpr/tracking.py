import logging
import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Tuple, Optional, Dict, Any
import cv2
import numpy as np

from backend.config import (
    MAX_CANDIDATE_FRAMES_PER_TRACK,
    TRACK_INACTIVE_MAX_FRAMES,
    COCO_VEHICLE_CLASS_NAMES,
)
from backend.anpr.detection import VehicleDetection, PlateDetection

logger = logging.getLogger(__name__)


def calculate_sharpness(image: np.ndarray) -> float:
    """
    Calculates image sharpness using OpenCV Laplacian variance.
    Higher values correspond to crisper, less blurry edges.
    """
    if image is None or image.size == 0:
        return 0.0
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def calculate_quality_score(
    crop: np.ndarray,
    bbox: Tuple[int, int, int, int],
    confidence: float,
) -> float:
    """
    Computes a composite quality score for a cropped license plate frame:
    - Laplacian variance (sharpness)
    - Plate bounding box size / resolution
    - Plate detection confidence

    Returns a score where higher is better.
    """
    if crop is None or crop.size == 0:
        return 0.0

    sharpness = calculate_sharpness(crop)
    x1, y1, x2, y2 = bbox
    area = max(0, x2 - x1) * max(0, y2 - y1)

    # Normalized component weights
    # Sharpness: typical values 20 (blurry) to 600+ (sharp) -> mapped to [0, 1]
    sharpness_norm = min(sharpness / 400.0, 1.0)
    # Area: typical plate crop 2000px to 30000px -> mapped to [0, 1]
    size_norm = min(math.sqrt(max(1, area)) / 150.0, 1.0)
    # Confidence: [0.0, 1.0]
    conf_norm = min(max(confidence, 0.0), 1.0)

    # Composite weighted score (0.0 to 1.0)
    composite_score = (sharpness_norm * 0.45) + (size_norm * 0.25) + (conf_norm * 0.30)
    return composite_score


@dataclass
class CandidatePlateFrame:
    """Stores a cropped candidate plate image along with quality score metadata."""
    crop: np.ndarray
    quality_score: float
    detection_confidence: float
    sharpness: float
    bbox: Tuple[int, int, int, int]
    timestamp: datetime


@dataclass
class TrackedVehicle:
    """
    Represents a vehicle tracked across multiple frames with its best plate candidates.
    """
    track_id: int
    vehicle_type: str
    bbox: Tuple[int, int, int, int]
    first_seen: datetime
    last_seen_frame: int
    last_seen_time: datetime
    frame_count: int = 1
    processed_for_sighting: bool = False
    best_plates: List[CandidatePlateFrame] = field(default_factory=list)

    def add_candidate_plate(
        self,
        crop: np.ndarray,
        bbox: Tuple[int, int, int, int],
        confidence: float,
        timestamp: datetime,
        max_buffer_size: int = MAX_CANDIDATE_FRAMES_PER_TRACK,
    ):
        """
        Adds a candidate plate crop to the vehicle's rolling buffer if it qualifies
        among the top scoring frames.
        """
        if crop is None or crop.size == 0:
            return

        sharpness = calculate_sharpness(crop)
        score = calculate_quality_score(crop, bbox, confidence)

        candidate = CandidatePlateFrame(
            crop=crop,
            quality_score=score,
            detection_confidence=confidence,
            sharpness=sharpness,
            bbox=bbox,
            timestamp=timestamp,
        )

        self.best_plates.append(candidate)
        # Keep buffer sorted by quality_score descending
        self.best_plates.sort(key=lambda c: c.quality_score, reverse=True)
        if len(self.best_plates) > max_buffer_size:
            self.best_plates = self.best_plates[:max_buffer_size]


class VehicleTracker:
    """
    Multi-vehicle tracking manager. Maintains tracked vehicle state,
    associates detected plates to vehicles, and updates quality buffers.
    """

    def __init__(
        self,
        max_buffer_size: int = MAX_CANDIDATE_FRAMES_PER_TRACK,
        inactive_threshold: int = TRACK_INACTIVE_MAX_FRAMES,
    ):
        self.max_buffer_size = max_buffer_size
        self.inactive_threshold = inactive_threshold
        self.active_tracks: Dict[int, TrackedVehicle] = {}
        self.completed_tracks: List[TrackedVehicle] = []
        self.current_frame_idx: int = 0

    def is_box_inside(
        self,
        inner_box: Tuple[int, int, int, int],
        outer_box: Tuple[int, int, int, int],
        tolerance: float = 0.2,
    ) -> bool:
        """
        Checks whether the center or substantial portion of inner_box (plate)
        lies within outer_box (vehicle).
        """
        px1, py1, px2, py2 = inner_box
        vx1, vy1, vx2, vy2 = outer_box

        pcx = (px1 + px2) / 2.0
        pcy = (py1 + py2) / 2.0

        # Expand outer box slightly by tolerance
        vw = vx2 - vx1
        vh = vy2 - vy1
        exp_vx1 = vx1 - tolerance * vw
        exp_vy1 = vy1 - tolerance * vh
        exp_vx2 = vx2 + tolerance * vw
        exp_vy2 = vy2 + tolerance * vh

        return exp_vx1 <= pcx <= exp_vx2 and exp_vy1 <= pcy <= exp_vy2

    def update_tracks(
        self,
        tracked_vehicles: List[Dict[str, Any]],
        detected_plates: List[PlateDetection],
        timestamp: datetime,
        frame_idx: Optional[int] = None,
    ) -> List[TrackedVehicle]:
        """
        Updates tracked vehicles for the current frame.

        Parameters:
        - tracked_vehicles: List of dicts with keys: {'track_id': int, 'bbox': (x1,y1,x2,y2), 'vehicle_type': str}
        - detected_plates: List of PlateDetection objects detected in this frame
        - timestamp: Current frame timestamp
        - frame_idx: Optional frame counter

        Returns:
        - List of active TrackedVehicle objects in current frame
        """
        if frame_idx is not None:
            self.current_frame_idx = frame_idx
        else:
            self.current_frame_idx += 1

        current_track_ids = set()

        for veh_data in tracked_vehicles:
            tid = veh_data["track_id"]
            bbox = veh_data["bbox"]
            vtype = veh_data.get("vehicle_type", "vehicle")
            current_track_ids.add(tid)

            if tid in self.active_tracks:
                track = self.active_tracks[tid]
                track.bbox = bbox
                track.vehicle_type = vtype
                track.last_seen_frame = self.current_frame_idx
                track.last_seen_time = timestamp
                track.frame_count += 1
            else:
                track = TrackedVehicle(
                    track_id=tid,
                    vehicle_type=vtype,
                    bbox=bbox,
                    first_seen=timestamp,
                    last_seen_frame=self.current_frame_idx,
                    last_seen_time=timestamp,
                    frame_count=1,
                )
                self.active_tracks[tid] = track

            # Match detected plates to this vehicle track
            for plate in detected_plates:
                if self.is_box_inside(plate.bbox, bbox):
                    if plate.crop is not None:
                        track.add_candidate_plate(
                            crop=plate.crop,
                            bbox=plate.bbox,
                            confidence=plate.confidence,
                            timestamp=timestamp,
                            max_buffer_size=self.max_buffer_size,
                        )

        # Check for inactive tracks that have exited the frame
        exited_track_ids = []
        for tid, track in list(self.active_tracks.items()):
            if self.current_frame_idx - track.last_seen_frame >= self.inactive_threshold:
                exited_track_ids.append(tid)
                self.completed_tracks.append(track)

        for tid in exited_track_ids:
            del self.active_tracks[tid]

        return list(self.active_tracks.values())

    def get_and_clear_exited_tracks(self) -> List[TrackedVehicle]:
        """Returns all completed/exited tracks ready for final ANPR resolution and clears them."""
        exited = self.completed_tracks
        self.completed_tracks = []
        return exited

    def flush_all_tracks(self) -> List[TrackedVehicle]:
        """Flushes all remaining active and completed tracks (e.g. at end of stream/video)."""
        all_tracks = list(self.active_tracks.values()) + self.completed_tracks
        self.active_tracks.clear()
        self.completed_tracks.clear()
        return all_tracks
