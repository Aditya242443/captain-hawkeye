import os
import logging
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Callable
from dataclasses import dataclass
import cv2
import numpy as np
from sqlalchemy.orm import Session

from backend.config import (
    PLATE_DETECTION_CONFIDENCE,
    VEHICLE_DETECTION_CONFIDENCE,
    MAX_CANDIDATE_FRAMES_PER_TRACK,
)
from backend.anpr.models import Camera, Sighting
from backend.anpr.detection import VehiclePlateDetector, get_detector
from backend.anpr.tracking import VehicleTracker, TrackedVehicle
from backend.anpr.ocr import PlateOCR, get_ocr
from backend.anpr.validation import majority_vote, validate_plate

logger = logging.getLogger(__name__)


@dataclass
class CameraConfig:
    """Configuration representing a physical camera feed identity."""
    camera_id: str
    gps_lat: float
    gps_lng: float
    location_name: Optional[str] = None


class ANPRPipeline:
    """
    End-to-end ANPR Pipeline orchestrating:
    1. Vehicle detection & ByteTrack tracking
    2. License plate detection within vehicles
    3. Sharpness & quality scoring in a rolling candidate buffer
    4. PaddleOCR recognition on top quality frames
    5. Positional character correction & multi-frame majority voting
    6. Database insertion into Supabase / PostgreSQL 'sightings' table
    """

    def __init__(
        self,
        camera_config: CameraConfig,
        detector: Optional[VehiclePlateDetector] = None,
        tracker: Optional[VehicleTracker] = None,
        ocr_engine: Optional[PlateOCR] = None,
        min_sighting_confidence: float = 0.35,
    ):
        self.camera_config = camera_config
        self.detector = detector or get_detector()
        self.tracker = tracker or VehicleTracker(max_buffer_size=MAX_CANDIDATE_FRAMES_PER_TRACK)
        self.ocr_engine = ocr_engine or get_ocr()
        self.min_sighting_confidence = min_sighting_confidence
        self.frame_count = 0

    def ensure_camera_registered(self, db: Session) -> Camera:
        """
        Ensures the camera record exists in the 'cameras' table
        to satisfy foreign key constraints for sightings.
        """
        camera = db.query(Camera).filter(Camera.camera_id == self.camera_config.camera_id).first()
        if not camera:
            logger.info("Registering camera '%s' in database.", self.camera_config.camera_id)
            camera = Camera(
                camera_id=self.camera_config.camera_id,
                gps_lat=self.camera_config.gps_lat,
                gps_lng=self.camera_config.gps_lng,
                location_name=self.camera_config.location_name,
            )
            db.add(camera)
            db.commit()
            db.refresh(camera)
        return camera

    def resolve_track_to_sighting(
        self,
        track: TrackedVehicle,
        db: Session,
    ) -> Optional[Sighting]:
        """
        Runs OCR on candidate plate frames for a tracked vehicle,
        applies validation and majority voting, and persists sighting to the database.
        """
        if track.processed_for_sighting:
            return None

        if not track.best_plates:
            logger.debug("Track ID %d has no candidate plate frames.", track.track_id)
            return None

        # Extract crops from candidate frames
        candidate_crops = [item.crop for item in track.best_plates if item.crop is not None]
        if not candidate_crops:
            return None

        # Run OCR on the top candidate frames
        ocr_candidates = self.ocr_engine.recognize(candidate_crops)

        # Run majority voting and positional correction
        plate_text, ocr_conf = majority_vote(ocr_candidates)

        if not plate_text or ocr_conf < self.min_sighting_confidence:
            logger.debug(
                "Track ID %d OCR discarded (text='%s', conf=%.2f)",
                track.track_id, plate_text, ocr_conf
            )
            return None

        is_valid, fmt = validate_plate(plate_text)
        logger.info(
            "Track ID %d resolved -> Plate: '%s' (Format: %s, Conf: %.2f, Type: %s)",
            track.track_id, plate_text, fmt, ocr_conf, track.vehicle_type
        )

        # Combine detection confidence and OCR confidence
        det_conf = max(item.detection_confidence for item in track.best_plates)
        combined_conf = float((det_conf * 0.4) + (ocr_conf * 0.6))

        # Persist sighting to PostgreSQL database
        sighting_time = track.last_seen_time or datetime.now(timezone.utc)
        sighting = Sighting(
            plate_text=plate_text,
            camera_id=self.camera_config.camera_id,
            timestamp=sighting_time,
            gps_lat=self.camera_config.gps_lat,
            gps_lng=self.camera_config.gps_lng,
            confidence=round(combined_conf, 4),
            vehicle_type=track.vehicle_type,
        )

        try:
            self.ensure_camera_registered(db)
            db.add(sighting)
            db.commit()
            db.refresh(sighting)
            track.processed_for_sighting = True
            logger.info("Saved sighting ID %d for plate '%s'", sighting.id, plate_text)
            return sighting
        except Exception as e:
            db.rollback()
            logger.error("Failed to save sighting to database: %s", e)
            return None

    def process_frame(
        self,
        frame: np.ndarray,
        timestamp: Optional[datetime] = None,
        db: Optional[Session] = None,
    ) -> List[Sighting]:
        """
        Processes a single video frame through the full ANPR pipeline.

        Returns:
        - List of newly committed Sighting records (if any tracks resolved this frame)
        """
        if frame is None or frame.size == 0:
            return []

        self.frame_count += 1
        current_time = timestamp or datetime.now(timezone.utc)

        # Step 1: Detect vehicles and plates
        result = self.detector.detect(
            frame,
            vehicle_conf=VEHICLE_DETECTION_CONFIDENCE,
            plate_conf=PLATE_DETECTION_CONFIDENCE,
        )
        vehicles, plates = result.vehicles, result.plates

        # Step 2: Track vehicles
        # Format vehicle detections for tracker
        # In simple single-frame / tracker mode, assign IDs or use ByteTrack
        tracked_veh_input = []
        for i, veh in enumerate(vehicles):
            tracked_veh_input.append({
                "track_id": getattr(veh, "track_id", i + 1),
                "bbox": veh.bbox,
                "vehicle_type": veh.vehicle_type,
            })

        # Step 3: Update tracking and rolling quality buffer
        self.tracker.update_tracks(
            tracked_vehicles=tracked_veh_input,
            detected_plates=plates,
            timestamp=current_time,
            frame_idx=self.frame_count,
        )

        # Step 4: Process tracks that exited or completed
        sightings: List[Sighting] = []
        if db is not None:
            exited_tracks = self.tracker.get_and_clear_exited_tracks()
            for track in exited_tracks:
                s = self.resolve_track_to_sighting(track, db)
                if s:
                    sightings.append(s)

        return sightings

    def flush_and_resolve_all(self, db: Session) -> List[Sighting]:
        """
        Flushes all active and pending tracks at the end of video/stream processing.
        """
        all_tracks = self.tracker.flush_all_tracks()
        sightings: List[Sighting] = []
        for track in all_tracks:
            s = self.resolve_track_to_sighting(track, db)
            if s:
                sightings.append(s)
        return sightings

    def process_video_file(
        self,
        video_path: str,
        db: Session,
        frame_interval: int = 1,
        callback: Optional[Callable[[int, List[Sighting]], None]] = None,
    ) -> List[Sighting]:
        """
        Processes a full video file, extracting sightings and logging them to the DB.
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise RuntimeError(f"Could not open video file: {video_path}")

        all_sightings: List[Sighting] = []
        frame_idx = 0

        try:
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break

                frame_idx += 1
                if frame_idx % frame_interval != 0:
                    continue

                new_sightings = self.process_frame(frame, db=db)
                if new_sightings:
                    all_sightings.extend(new_sightings)
                    if callback:
                        callback(frame_idx, new_sightings)

            # Flush remaining tracks
            final_sightings = self.flush_and_resolve_all(db)
            all_sightings.extend(final_sightings)

        finally:
            cap.release()

        return all_sightings
