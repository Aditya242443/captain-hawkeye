"""
Project Plexis (Captain Hawkeye) - ANPR Module
"""

# Lazy / safe exports to allow submodules (e.g. validation) to be imported cleanly
def __getattr__(name):
    if name in ("Camera", "Sighting"):
        from backend.anpr.models import Camera, Sighting
        return locals()[name]
    elif name in ("VehiclePlateDetector", "detect_vehicles_and_plates"):
        from backend.anpr.detection import VehiclePlateDetector, detect_vehicles_and_plates
        return locals()[name]
    elif name in ("VehicleTracker", "TrackedVehicle", "calculate_quality_score", "calculate_sharpness"):
        from backend.anpr.tracking import VehicleTracker, TrackedVehicle, calculate_quality_score, calculate_sharpness
        return locals()[name]
    elif name == "PlateOCR":
        from backend.anpr.ocr import PlateOCR
        return PlateOCR
    elif name in (
        "validate_plate",
        "correct_positional_characters",
        "majority_vote",
        "is_valid_standard",
        "is_valid_bh",
        "is_valid_relaxed",
    ):
        import backend.anpr.validation as val
        return getattr(val, name)
    elif name in ("ANPRPipeline", "CameraConfig"):
        from backend.anpr.pipeline import ANPRPipeline, CameraConfig
        return locals()[name]
    elif name == "anpr_router":
        from backend.anpr.router import router as anpr_router
        return anpr_router
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "Camera",
    "Sighting",
    "VehiclePlateDetector",
    "detect_vehicles_and_plates",
    "VehicleTracker",
    "TrackedVehicle",
    "calculate_quality_score",
    "calculate_sharpness",
    "PlateOCR",
    "validate_plate",
    "correct_positional_characters",
    "majority_vote",
    "is_valid_standard",
    "is_valid_bh",
    "is_valid_relaxed",
    "ANPRPipeline",
    "CameraConfig",
    "anpr_router",
]
