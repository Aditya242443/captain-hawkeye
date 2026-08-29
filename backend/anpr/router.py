from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.database import get_db
from backend.anpr.models import Camera, Sighting
from backend.anpr.validation import validate_plate, correct_positional_characters

router = APIRouter(prefix="/api/anpr", tags=["ANPR"])


# ---------------------------------------------------------------------------
# Pydantic Schemas
# ---------------------------------------------------------------------------

class CameraResponse(BaseModel):
    camera_id: str
    location_name: Optional[str] = None
    gps_lat: float
    gps_lng: float

    class Config:
        orm_mode = True
        from_attributes = True


class CameraCreate(BaseModel):
    camera_id: str = Field(..., max_length=20, example="CAM_001")
    gps_lat: float = Field(..., example=28.6139)
    gps_lng: float = Field(..., example=77.2090)
    location_name: Optional[str] = Field(None, max_length=100, example="Connaught Place Outer Ring")


class SightingResponse(BaseModel):
    id: int
    plate_text: str
    camera_id: str
    timestamp: datetime
    gps_lat: float
    gps_lng: float
    confidence: float
    vehicle_type: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        orm_mode = True
        from_attributes = True


class PlateValidationRequest(BaseModel):
    plate_text: str = Field(..., example="DL01AB1234")


class PlateValidationResponse(BaseModel):
    input_text: str
    corrected_text: str
    is_valid: bool
    format_type: str


# ---------------------------------------------------------------------------
# API Routes
# ---------------------------------------------------------------------------

@router.get(
    "/cameras",
    response_model=List[CameraResponse],
    summary="Get all registered ANPR cameras",
    description="Returns all rows from the `cameras` table as a JSON list.",
)
def get_cameras(db: Session = Depends(get_db)):
    """
    Returns all cameras registered in the database:
    `[{camera_id, location_name, gps_lat, gps_lng}, ...]`
    """
    cameras = db.query(Camera).all()
    return cameras


@router.post(
    "/cameras",
    response_model=CameraResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register or update an ANPR camera",
)
def register_camera(camera_in: CameraCreate, db: Session = Depends(get_db)):
    """
    Registers a new camera or updates an existing camera by `camera_id`.
    """
    camera = db.query(Camera).filter(Camera.camera_id == camera_in.camera_id).first()
    if camera:
        camera.gps_lat = camera_in.gps_lat
        camera.gps_lng = camera_in.gps_lng
        camera.location_name = camera_in.location_name
    else:
        camera = Camera(
            camera_id=camera_in.camera_id,
            gps_lat=camera_in.gps_lat,
            gps_lng=camera_in.gps_lng,
            location_name=camera_in.location_name,
        )
        db.add(camera)

    db.commit()
    db.refresh(camera)
    return camera


@router.get(
    "/sightings/recent",
    response_model=List[SightingResponse],
    summary="Get recent vehicle sightings",
    description="Returns the most recent N vehicle sightings ordered by timestamp descending.",
)
def get_recent_sightings(
    limit: int = Query(20, ge=1, le=500, description="Maximum number of sightings to return"),
    plate: Optional[str] = Query(None, description="Optional filter by license plate string"),
    camera_id: Optional[str] = Query(None, description="Optional filter by camera ID"),
    db: Session = Depends(get_db),
):
    """
    Returns the most recent N sightings from `sightings` table:
    `[{id, plate_text, camera_id, timestamp, confidence, vehicle_type, gps_lat, gps_lng}, ...]`
    """
    query = db.query(Sighting)

    if plate:
        query = query.filter(Sighting.plate_text.ilike(f"%{plate.strip()}%"))
    if camera_id:
        query = query.filter(Sighting.camera_id == camera_id.strip())

    sightings = query.order_by(desc(Sighting.timestamp)).limit(limit).all()
    return sightings


@router.post(
    "/validate-plate",
    response_model=PlateValidationResponse,
    summary="Validate and correct a license plate string",
)
def validate_plate_endpoint(request: PlateValidationRequest):
    """
    Tests Indian license plate regex validation and positional OCR correction.
    """
    corrected = correct_positional_characters(request.plate_text)
    is_valid, fmt = validate_plate(corrected)
    return PlateValidationResponse(
        input_text=request.plate_text,
        corrected_text=corrected,
        is_valid=is_valid,
        format_type=fmt,
    )
