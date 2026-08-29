from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.anpr.router import router as anpr_router
from backend.database import Base, engine

# Initialize database schema (creates tables if they do not exist)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Plexis (Captain Hawkeye) API",
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

# 1. ANPR Module (Automatic Number Plate Recognition) - Sole writer to sightings/cameras
app.include_router(anpr_router)

# 2. Trajectory Module - Read-only consumer of sightings
# NOTE: Trajectory tracking and heatmap router will be mounted here by Aditya Raj
# Example mount when ready:
# from backend.trajectory.router import router as trajectory_router
# app.include_router(trajectory_router, prefix="/api/trajectory", tags=["Trajectory"])

# 3. Alerts Module - Read-only consumer of sightings
# NOTE: Real-time alerting router will be mounted here by Aditya Pandey
# Example mount when ready:
# from backend.alerts.router import router as alerts_router
# app.include_router(alerts_router, prefix="/api/alerts", tags=["Alerts"])


# =============================================================================
# ROOT & HEALTH CHECK
# =============================================================================

@app.get("/", tags=["System"])
def root():
    return {
        "project": "Plexis (Captain Hawkeye)",
        "module": "ANPR & Core Backend",
        "status": "operational",
        "endpoints": {
            "docs": "/docs",
            "anpr_cameras": "/api/anpr/cameras",
            "anpr_sightings_recent": "/api/anpr/sightings/recent",
        },
    }


@app.get("/health", tags=["System"])
def health_check():
    return {"status": "healthy"}
