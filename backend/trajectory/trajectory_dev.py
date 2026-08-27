from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from trajectory_router import router as trajectory_router
import os

app = FastAPI(
    title="Captain Hawkeye — Vehicle Trajectory & Traffic Analytics API",
    description="SIH 2026 PS 26127 Backend Router for license plate trajectory reconstruction and heatmap analytics.",
    version="1.0.0"
)

# Enable CORS for all origins (Frontend Leaflet dashboard integration)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global internal error handler adhering to contract
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "error": True,
            "message": f"Internal server error: {str(exc)}",
            "status_code": 500
        }
    )

# Mount trajectory router
app.include_router(trajectory_router)

# Serve Leaflet.js preview dashboard
@app.get("/preview.html")
@app.get("/preview")
async def serve_preview():
    preview_path = os.path.join(os.path.dirname(__file__), "preview.html")
    return FileResponse(preview_path, media_type="text/html")

@app.get("/")
async def root():
    return {
        "system": "Captain Hawkeye — Vehicle Trajectory API",
        "status": "online",
        "endpoints": [
            "/api/trajectory/{plate}",
            "/api/trajectory/heatmap",
            "/api/trajectory/congestion",
            "/preview.html"
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
