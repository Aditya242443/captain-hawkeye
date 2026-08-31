import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Query, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.database import get_db
from backend.anpr.models import Camera, Sighting
from backend.trajectory.cleaning import (
    clean_sightings,
    enrich_sightings,
    compute_heatmap,
    compute_congestion,
    DEFAULT_CAMERAS,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/trajectory", tags=["Trajectory Reconstruction"])


def get_cameras_dict(db: Session) -> Dict[str, dict]:
    """
    Fetches all registered cameras from the database and returns a lookup dictionary.
    Falls back to DEFAULT_CAMERAS if the database table is empty.
    """
    try:
        camera_rows = db.query(Camera).all()
        if camera_rows:
            return {
                c.camera_id: {
                    "location_name": c.location_name or c.camera_id,
                    "gps_lat": float(c.gps_lat),
                    "gps_lng": float(c.gps_lng),
                }
                for c in camera_rows
            }
    except Exception as e:
        logger.warning("Could not fetch cameras from database: %s. Using default cameras.", e)

    return DEFAULT_CAMERAS


def sighting_to_dict(s: Sighting) -> dict:
    """Converts a Sighting ORM model to the dictionary shape expected by cleaning pipeline."""
    ts_str = s.timestamp.isoformat() if s.timestamp else ""
    if ts_str and not ts_str.endswith("Z") and "+" not in ts_str:
        ts_str += "Z"

    return {
        "id": s.id,
        "plate_text": s.plate_text,
        "camera_id": s.camera_id,
        "timestamp": ts_str,
        "confidence": float(s.confidence),
        "vehicle_type": s.vehicle_type or "car",
        "gps_lat": float(s.gps_lat),
        "gps_lng": float(s.gps_lng),
    }


def get_all_sightings_data(db: Session, plate: Optional[str] = None) -> List[dict]:
    """
    Queries sightings from the database and returns them as a list of dicts.
    """
    query = db.query(Sighting)
    if plate:
        query = query.filter(Sighting.plate_text.ilike(f"%{plate.strip()}%"))
    
    rows = query.order_by(Sighting.timestamp.asc()).all()
    return [sighting_to_dict(s) for s in rows]


@router.get("/heatmap", response_class=JSONResponse)
def get_traffic_heatmap(
    start_time: Optional[str] = Query(None, description="ISO 8601 UTC start datetime"),
    end_time: Optional[str] = Query(None, description="ISO 8601 UTC end datetime"),
    db: Session = Depends(get_db),
):
    """
    STEP 5: GET /api/trajectory/heatmap
    Computes camera density scores, congestion flags, and average speeds within a time window.
    Reads live sightings and cameras from the database.
    """
    try:
        cameras = get_cameras_dict(db)
        raw_sightings = get_all_sightings_data(db)
        heatmap_data = compute_heatmap(
            raw_sightings=raw_sightings,
            cameras=cameras,
            start_time_str=start_time,
            end_time_str=end_time,
        )
        return JSONResponse(status_code=200, content=heatmap_data)
    except Exception as e:
        logger.error("Heatmap computation failed: %s", e)
        return JSONResponse(
            status_code=500,
            content={
                "error": True,
                "message": f"Internal heatmap error: {str(e)}",
                "status_code": 500,
            },
        )


@router.get("/congestion", response_class=JSONResponse)
def get_traffic_congestion(db: Session = Depends(get_db)):
    """
    STEP 6: GET /api/trajectory/congestion
    Returns cameras currently experiencing congestion (rolling 30-min window).
    Reads live sightings and cameras from the database.
    """
    try:
        cameras = get_cameras_dict(db)
        raw_sightings = get_all_sightings_data(db)
        congestion_data = compute_congestion(raw_sightings=raw_sightings, cameras=cameras)
        return JSONResponse(status_code=200, content=congestion_data)
    except Exception as e:
        logger.error("Congestion computation failed: %s", e)
        return JSONResponse(
            status_code=500,
            content={
                "error": True,
                "message": f"Internal congestion error: {str(e)}",
                "status_code": 500,
            },
        )


@router.get("/{plate}")
def get_vehicle_trajectory(plate: str, db: Session = Depends(get_db)):
    """
    STEP 4: GET /api/trajectory/{plate}
    Reconstructs clean, enriched trajectory for a vehicle plate from live DB records.
    Returns HTTP 200 with found: false and sightings: [] when no match exists.
    """
    try:
        target_plate = plate.strip().upper()
        cameras = get_cameras_dict(db)
        raw_sightings = get_all_sightings_data(db, plate=target_plate)
        
        cleaned = clean_sightings(target_plate, raw_sightings, cameras=cameras)
        
        if not cleaned:
            return JSONResponse(
                status_code=200,
                content={
                    "plate": target_plate,
                    "found": False,
                    "sightings": [],
                },
            )

        enriched = enrich_sightings(cleaned, cameras=cameras)
        return JSONResponse(
            status_code=200,
            content={
                "plate": target_plate,
                "found": True,
                "sightings": enriched,
            },
        )
    except Exception as e:
        logger.error("Trajectory lookup failed for plate '%s': %s", plate, e)
        return JSONResponse(
            status_code=500,
            content={
                "error": True,
                "message": f"Internal trajectory error: {str(e)}",
                "status_code": 500,
            },
        )
