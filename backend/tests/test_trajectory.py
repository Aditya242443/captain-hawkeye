"""
Project Plexis — Trajectory & API Integration Tests
Tests trajectory cleaning, enrichment, heatmap computation, congestion logic,
and live FastAPI unified backend endpoints.
"""

import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.main import app
from backend.trajectory.cleaning import (
    haversine_km,
    calculate_bearing_8point,
    clean_sightings,
    enrich_sightings,
    compute_heatmap,
    compute_congestion,
    DEFAULT_CAMERAS,
)

client = TestClient(app)


# =============================================================================
# 1. Trajectory Mathematical & Cleaning Unit Tests
# =============================================================================

def test_haversine_known_distance():
    # Distance between Jabalpur MG Road (CAM_01) and Wright Town (CAM_02)
    # CAM_01: (23.1815, 79.9864), CAM_02: (23.1900, 79.9950)
    dist = haversine_km(23.1815, 79.9864, 23.1900, 79.9950)
    assert 1.0 < dist < 1.8, f"Expected ~1.28km, got {dist}"


def test_calculate_bearing_8point():
    # North movement
    assert calculate_bearing_8point(23.1000, 79.9000, 23.2000, 79.9000) == "N"
    # East movement
    assert calculate_bearing_8point(23.1000, 79.9000, 23.1000, 80.0000) == "E"
    # South movement
    assert calculate_bearing_8point(23.2000, 79.9000, 23.1000, 79.9000) == "S"
    # West movement
    assert calculate_bearing_8point(23.1000, 80.0000, 23.1000, 79.9000) == "W"


def test_clean_sightings_filters_low_confidence_and_noise():
    raw = [
        # Valid high confidence
        {"plate_text": "MP20AB1234", "camera_id": "CAM_01", "timestamp": "2026-08-30T10:00:00Z", "confidence": 0.95, "vehicle_type": "car", "gps_lat": 23.1815, "gps_lng": 79.9864},
        # Low confidence (< 0.6) - should be dropped
        {"plate_text": "MP20AB1234", "camera_id": "CAM_02", "timestamp": "2026-08-30T10:02:00Z", "confidence": 0.45, "vehicle_type": "car", "gps_lat": 23.1900, "gps_lng": 79.9950},
        # Near-duplicate on same camera within 2s - should be deduplicated
        {"plate_text": "MP20AB1234", "camera_id": "CAM_01", "timestamp": "2026-08-30T10:00:02Z", "confidence": 0.92, "vehicle_type": "car", "gps_lat": 23.1815, "gps_lng": 79.9864},
        # Valid second checkpoint
        {"plate_text": "MP20AB1234", "camera_id": "CAM_02", "timestamp": "2026-08-30T10:10:00Z", "confidence": 0.94, "vehicle_type": "car", "gps_lat": 23.1900, "gps_lng": 79.9950},
    ]

    cleaned = clean_sightings("MP20AB1234", raw, cameras=DEFAULT_CAMERAS)
    assert len(cleaned) == 2
    assert cleaned[0]["camera_id"] == "CAM_01"
    assert cleaned[1]["camera_id"] == "CAM_02"


def test_enrich_sightings():
    cleaned = [
        {"plate_text": "MP20AB1234", "camera_id": "CAM_01", "timestamp": "2026-08-30T10:00:00Z", "confidence": 0.95, "vehicle_type": "car", "gps_lat": 23.1815, "gps_lng": 79.9864, "_parsed_dt": datetime(2026, 8, 30, 10, 0, 0, tzinfo=timezone.utc)},
        {"plate_text": "MP20AB1234", "camera_id": "CAM_02", "timestamp": "2026-08-30T10:10:00Z", "confidence": 0.94, "vehicle_type": "car", "gps_lat": 23.1900, "gps_lng": 79.9950, "_parsed_dt": datetime(2026, 8, 30, 10, 10, 0, tzinfo=timezone.utc)},
    ]

    enriched = enrich_sightings(cleaned, cameras=DEFAULT_CAMERAS)
    assert len(enriched) == 2
    # First stop has null prev bearing & speed
    assert enriched[0]["direction_from_prev"] is None
    assert enriched[0]["speed_from_prev_kmh"] is None
    # Second stop has computed speed & bearing
    assert enriched[1]["direction_from_prev"] is not None
    assert enriched[1]["speed_from_prev_kmh"] is not None
    assert enriched[1]["speed_from_prev_kmh"] > 0


# =============================================================================
# 2. FastAPI Backend Endpoint Integration Tests
# =============================================================================

def test_health_check_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["modules"]["anpr"] == "operational"
    assert data["modules"]["trajectory"] == "operational"


def test_get_cameras_endpoint():
    response = client.get("/api/anpr/cameras")
    assert response.status_code == 200
    cameras = response.json()
    assert len(cameras) >= 10
    camera_ids = [c["camera_id"] for c in cameras]
    assert "CAM_01" in camera_ids
    assert "CAM_02" in camera_ids


def test_get_recent_sightings_endpoint():
    response = client.get("/api/anpr/sightings/recent?limit=10")
    assert response.status_code == 200
    sightings = response.json()
    assert isinstance(sightings, list)
    if len(sightings) > 0:
        s = sightings[0]
        assert "plate_text" in s
        assert "camera_id" in s
        assert "confidence" in s


def test_trajectory_lookup_known_plate():
    response = client.get("/api/trajectory/MP20AB1234")
    assert response.status_code == 200
    data = response.json()
    assert data["plate"] == "MP20AB1234"
    assert data["found"] is True
    assert len(data["sightings"]) >= 2
    first_stop = data["sightings"][0]
    assert "location_name" in first_stop
    assert "gps_lat" in first_stop


def test_trajectory_lookup_unknown_plate():
    response = client.get("/api/trajectory/UNKNOWN99999")
    assert response.status_code == 200
    data = response.json()
    assert data["plate"] == "UNKNOWN99999"
    assert data["found"] is False
    assert data["sightings"] == []


def test_heatmap_endpoint():
    response = client.get("/api/trajectory/heatmap")
    assert response.status_code == 200
    heatmap = response.json()
    assert isinstance(heatmap, list)
    assert len(heatmap) >= 10
    for node in heatmap:
        assert "camera_id" in node
        assert "density_score" in node
        assert "vehicle_count" in node
        assert "is_congested" in node


def test_congestion_endpoint():
    response = client.get("/api/trajectory/congestion")
    assert response.status_code == 200
    congestion = response.json()
    assert isinstance(congestion, list)
    for c in congestion:
        assert "camera_id" in c
        assert "location_name" in c
        assert "vehicle_count" in c
        assert "since" in c


def test_validate_plate_endpoint():
    response = client.post("/api/anpr/validate-plate", json={"plate_text": "DLOIAB1234"})
    assert response.status_code == 200
    data = response.json()
    assert data["input_text"] == "DLOIAB1234"
    assert data["corrected_text"] == "DL01AB1234"
    assert data["is_valid"] is True
    assert data["format_type"] == "standard"
