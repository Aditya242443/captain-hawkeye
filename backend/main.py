import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.anpr.router import router as anpr_router
from backend.trajectory.router import router as trajectory_router
from backend.database import Base, engine
from backend.config import BASE_DIR

# Initialize database schema (creates tables if they do not exist)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Project Plexis (Captain Hawkeye) API",
    description="City-Wide AI Engine for Multi-Camera ANPR Trajectory Tracking and Urban Traffic Analytics — SIH 2026",
    version="1.0.0",
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# ROUTER MOUNTS
# =============================================================================

# 1. ANPR Module (Automatic Number Plate Recognition)
app.include_router(anpr_router)

# 2. Trajectory Module (Trajectory Reconstruction, Heatmap & Congestion)
app.include_router(trajectory_router)


# =============================================================================
# STATIC ASSETS & DEMO VIDEOS
# =============================================================================

# Demo videos directory
demo_videos_dir = BASE_DIR / "test_samples" / "demo_videos"
if demo_videos_dir.exists():
    app.mount("/static/videos", StaticFiles(directory=str(demo_videos_dir)), name="demo_videos")

# Consolidated frontend directory
frontend_dir = BASE_DIR / "frontend"
if frontend_dir.exists():
    app.mount("/app", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")


# =============================================================================
# ROOT & HEALTH CHECK
# =============================================================================

@app.get("/", tags=["System"])
def root():
    # If frontend index.html exists, serve it at root
    frontend_index = BASE_DIR / "frontend" / "index.html"
    if frontend_index.exists():
        return FileResponse(str(frontend_index))

    return {
        "project": "Project Plexis (Captain Hawkeye)",
        "team": "Sovereigns (SIH 2026)",
        "status": "operational",
        "endpoints": {
            "docs": "/docs",
            "anpr_cameras": "/api/anpr/cameras",
            "anpr_sightings_recent": "/api/anpr/sightings/recent",
            "anpr_validate_plate": "/api/anpr/validate-plate",
            "anpr_demo_detections": "/api/anpr/demo-detections/{camera_id}",
            "trajectory_lookup": "/api/trajectory/{plate}",
            "trajectory_heatmap": "/api/trajectory/heatmap",
            "trajectory_congestion": "/api/trajectory/congestion",
            "app_ui": "/app/",
        },
    }


@app.get("/health", tags=["System"])
def health_check():
    return {
        "status": "healthy",
        "modules": {
            "anpr": "operational",
            "trajectory": "operational",
        }
    }
