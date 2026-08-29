import json
import os
from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from cleaning import (
    clean_sightings,
    enrich_sightings,
    compute_heatmap,
    compute_congestion,
)

router = APIRouter(prefix="/api/trajectory", tags=["Trajectory Reconstruction"])

# Path to mock sightings fixture
FIXTURE_PATH = os.path.join(os.path.dirname(__file__), "sightings.json")

def load_sightings() -> list[dict]:
    """
    Helper to load raw sightings fixture dynamically from sightings.json.
    """
    if not os.path.exists(FIXTURE_PATH):
        return []
    with open(FIXTURE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

@router.get("/heatmap", response_class=JSONResponse)
async def get_traffic_heatmap(
    start_time: str | None = Query(None, description="ISO 8601 UTC start datetime"),
    end_time: str | None = Query(None, description="ISO 8601 UTC end datetime")
):
    """
    STEP 5: GET /api/trajectory/heatmap
    Computes camera density scores, congestion flags, and average speeds within a time window.
    """
    try:
        raw_sightings = load_sightings()
        heatmap_data = compute_heatmap(
            raw_sightings=raw_sightings,
            start_time_str=start_time,
            end_time_str=end_time
        )
        return JSONResponse(status_code=200, content=heatmap_data)
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "error": True,
                "message": f"Internal heatmap error: {str(e)}",
                "status_code": 500
            }
        )

@router.get("/congestion", response_class=JSONResponse)
async def get_traffic_congestion():
    """
    STEP 6: GET /api/trajectory/congestion
    Returns cameras currently experiencing congestion (rolling 30-min window).
    """
    try:
        raw_sightings = load_sightings()
        congestion_data = compute_congestion(raw_sightings=raw_sightings)
        return JSONResponse(status_code=200, content=congestion_data)
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "error": True,
                "message": f"Internal congestion error: {str(e)}",
                "status_code": 500
            }
        )

@router.get("/{plate}")
async def get_vehicle_trajectory(plate: str):
    """
    STEP 4: GET /api/trajectory/{plate}
    Reconstructs clean, enriched trajectory for a vehicle plate.
    Returns HTTP 200 with found: false and sightings: [] when no match exists.
    """
    try:
        raw_sightings = load_sightings()
        cleaned = clean_sightings(plate, raw_sightings)
        
        if not cleaned:
            return JSONResponse(
                status_code=200,
                content={
                    "plate": plate.upper(),
                    "found": False,
                    "sightings": []
                }
            )

        enriched = enrich_sightings(cleaned)
        return JSONResponse(
            status_code=200,
            content={
                "plate": plate.upper(),
                "found": True,
                "sightings": enriched
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "error": True,
                "message": f"Internal trajectory error: {str(e)}",
                "status_code": 500
            }
        )
