import math
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any

# Default 10 Camera Locations across Jabalpur (Used as fallback/reference)
DEFAULT_CAMERAS: Dict[str, dict] = {
    "CAM_01": {"location_name": "MG Road Junction",   "gps_lat": 23.1815, "gps_lng": 79.9864},
    "CAM_02": {"location_name": "Wright Town Circle", "gps_lat": 23.1900, "gps_lng": 79.9950},
    "CAM_03": {"location_name": "Napier Town",        "gps_lat": 23.1706, "gps_lng": 79.9422},
    "CAM_04": {"location_name": "Madan Mahal",         "gps_lat": 23.1489, "gps_lng": 79.9247},
    "CAM_05": {"location_name": "Ranjhi",              "gps_lat": 23.2245, "gps_lng": 80.0134},
    "CAM_06": {"location_name": "Adhartal",            "gps_lat": 23.2100, "gps_lng": 79.9350},
    "CAM_07": {"location_name": "Bhedaghat",           "gps_lat": 23.1320, "gps_lng": 79.8010},
    "CAM_08": {"location_name": "Marhatal",            "gps_lat": 23.1600, "gps_lng": 79.9400},
    "CAM_09": {"location_name": "Damoh Naka",          "gps_lat": 23.1900, "gps_lng": 79.9200},
    "CAM_10": {"location_name": "Sadar",               "gps_lat": 23.1800, "gps_lng": 79.9500},
}

# Backward compatibility alias
CAMERAS = DEFAULT_CAMERAS

VEHICLE_WEIGHTS = {
    "cycle": 0.5,
    "bike": 0.5,
    "motorcycle": 0.5,
    "car": 1.0,
    "bus": 3.0,
    "truck": 3.0,
    "vehicle": 1.0,
}

CONGESTION_THRESHOLD = 8  # Tunable raw vehicle count threshold for congestion


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """
    Computes the Haversine distance in kilometers between two GPS coordinates.
    """
    R = 6371.0  # Earth's mean radius in kilometers
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lng2 - lng1)

    a = (math.sin(delta_phi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2)
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c


def calculate_bearing_8point(lat1: float, lng1: float, lat2: float, lng2: float) -> Optional[str]:
    """
    Calculates the 8-point compass direction (N/NE/E/SE/S/SW/W/NW) 
    from (lat1, lng1) to (lat2, lng2).
    """
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_lng = math.radians(lng2 - lng1)

    if abs(lat1 - lat2) < 1e-7 and abs(lng1 - lng2) < 1e-7:
        return None

    y = math.sin(delta_lng) * math.cos(phi2)
    x = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(delta_lng)

    bearing_deg = (math.degrees(math.atan2(y, x)) + 360.0) % 360.0

    compass_points = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    index = int((bearing_deg + 22.5) // 45.0) % 8
    return compass_points[index]


def parse_iso_utc(ts_input: Any) -> datetime:
    """
    Parses datetime or ISO 8601 UTC timestamp string into a timezone-aware datetime object.
    """
    if isinstance(ts_input, datetime):
        if ts_input.tzinfo is None:
            return ts_input.replace(tzinfo=timezone.utc)
        return ts_input.astimezone(timezone.utc)

    ts_str = str(ts_input).strip()
    if ts_str.endswith("Z"):
        ts_str = ts_str[:-1] + "+00:00"
    return datetime.fromisoformat(ts_str).astimezone(timezone.utc)


def format_iso_utc(dt: datetime) -> str:
    """
    Formats a timezone-aware datetime object into ISO 8601 UTC string ending in 'Z'.
    """
    dt_utc = dt.astimezone(timezone.utc)
    return dt_utc.strftime("%Y-%m-%dT%H:%M:%SZ")


def _resolve_cameras(cameras: Optional[Dict[str, dict]] = None) -> Dict[str, dict]:
    """Helper to ensure camera mapping is available."""
    if cameras and len(cameras) > 0:
        return cameras
    return DEFAULT_CAMERAS


def clean_sightings(
    plate: str, 
    raw_sightings: List[dict],
    cameras: Optional[Dict[str, dict]] = None,
    confidence_threshold: float = 0.6, 
    dedupe_seconds: float = 5.0, 
    max_speed_kmh: float = 150.0
) -> List[dict]:
    """
    STEP 2: Data Cleaning Pipeline
    - Filters for plate (case-insensitive).
    - Drops sightings below confidence_threshold (0.6).
    - Deduplicates same-camera sightings within dedupe_seconds (5.0s).
    - Removes consecutive sightings implying speed > max_speed_kmh (150 km/h) as OCR misreads.
    - Returns chronologically sorted clean sightings.
    """
    active_cameras = _resolve_cameras(cameras)
    target_plate = plate.strip().upper()

    # Filter by plate text and confidence threshold
    candidates = []
    for s in raw_sightings:
        s_plate = str(s.get("plate_text", "")).strip().upper()
        if s_plate == target_plate:
            conf = float(s.get("confidence", 0.0))
            if conf >= confidence_threshold:
                cam_id = s.get("camera_id")
                # Accept sighting if camera is in registered cameras or has GPS coordinates
                if cam_id in active_cameras or (s.get("gps_lat") and s.get("gps_lng")):
                    parsed_dt = parse_iso_utc(s["timestamp"])
                    candidates.append({
                        **s,
                        "_parsed_dt": parsed_dt
                    })

    # Sort chronologically by timestamp
    candidates.sort(key=lambda s: s["_parsed_dt"])

    # Deduplicate and speed check loop against last valid accepted sighting
    cleaned = []
    for s in candidates:
        if not cleaned:
            cleaned.append(s)
            continue

        last_valid = cleaned[-1]
        dt_sec = (s["_parsed_dt"] - last_valid["_parsed_dt"]).total_seconds()

        # Check same-camera near-duplicate (< 5 seconds)
        if s["camera_id"] == last_valid["camera_id"] and dt_sec < dedupe_seconds:
            continue

        # Coordinates for speed plausibility
        lat_prev = last_valid.get("gps_lat")
        lng_prev = last_valid.get("gps_lng")
        if (lat_prev is None or lng_prev is None) and last_valid["camera_id"] in active_cameras:
            lat_prev = active_cameras[last_valid["camera_id"]]["gps_lat"]
            lng_prev = active_cameras[last_valid["camera_id"]]["gps_lng"]

        lat_curr = s.get("gps_lat")
        lng_curr = s.get("gps_lng")
        if (lat_curr is None or lng_curr is None) and s["camera_id"] in active_cameras:
            lat_curr = active_cameras[s["camera_id"]]["gps_lat"]
            lng_curr = active_cameras[s["camera_id"]]["gps_lng"]

        if lat_prev is not None and lng_prev is not None and lat_curr is not None and lng_curr is not None:
            dist_km = haversine_km(lat_prev, lng_prev, lat_curr, lng_curr)
            hours = dt_sec / 3600.0
            if hours > 0:
                implied_speed = dist_km / hours
                if implied_speed > max_speed_kmh:
                    # Likely OCR misread teleporter jump, drop sighting
                    continue

        cleaned.append(s)

    return cleaned


def enrich_sightings(
    cleaned_sightings: List[dict],
    cameras: Optional[Dict[str, dict]] = None,
) -> List[dict]:
    """
    STEP 3: Direction + Speed Enrichment (Includes vehicle_type & confidence)
    For each sighting after the first, computes:
    - direction_from_prev: 8-point compass bearing from prev camera to current camera
    - speed_from_prev_kmh: speed in km/h based on Haversine distance / time delta
    - vehicle_type & confidence preserved from raw sighting record
    First sighting always has direction_from_prev and speed_from_prev_kmh as null (None).
    """
    active_cameras = _resolve_cameras(cameras)
    enriched = []

    for i, curr in enumerate(cleaned_sightings):
        cid_curr = curr["camera_id"]
        cam_info = active_cameras.get(cid_curr, {})
        loc_name = curr.get("location_name") or cam_info.get("location_name", cid_curr)
        lat_curr = curr.get("gps_lat", cam_info.get("gps_lat", 0.0))
        lng_curr = curr.get("gps_lng", cam_info.get("gps_lng", 0.0))

        ts_z = format_iso_utc(curr["_parsed_dt"])

        if i == 0:
            direction_from_prev = None
            speed_from_prev_kmh = None
        else:
            prev = cleaned_sightings[i - 1]
            cid_prev = prev["camera_id"]
            cam_prev_info = active_cameras.get(cid_prev, {})
            lat_prev = prev.get("gps_lat", cam_prev_info.get("gps_lat", 0.0))
            lng_prev = prev.get("gps_lng", cam_prev_info.get("gps_lng", 0.0))

            dt_sec = (curr["_parsed_dt"] - prev["_parsed_dt"]).total_seconds()
            dist_km = haversine_km(lat_prev, lng_prev, lat_curr, lng_curr)

            if dt_sec > 0:
                speed_from_prev_kmh = round(dist_km / (dt_sec / 3600.0), 1)
            else:
                speed_from_prev_kmh = 0.0

            direction_from_prev = calculate_bearing_8point(
                lat_prev, lng_prev,
                lat_curr, lng_curr
            )

        enriched.append({
            "camera_id": cid_curr,
            "location_name": loc_name,
            "gps_lat": lat_curr,
            "gps_lng": lng_curr,
            "timestamp": ts_z,
            "direction_from_prev": direction_from_prev,
            "speed_from_prev_kmh": speed_from_prev_kmh,
            "vehicle_type": curr.get("vehicle_type", "car"),
            "model": curr.get("model", "Unknown"),
            "color": curr.get("color", "Unknown"),
            "confidence": float(curr.get("confidence", 1.0))
        })

    return enriched


def _get_all_enriched_sightings(
    raw_sightings: List[dict],
    cameras: Optional[Dict[str, dict]] = None,
) -> List[dict]:
    """
    Helper to clean and enrich sightings for all plates in dataset.
    """
    active_cameras = _resolve_cameras(cameras)
    plates = set(str(s.get("plate_text", "")).strip().upper() for s in raw_sightings if s.get("plate_text"))
    all_enriched = []
    for p in plates:
        cleaned = clean_sightings(p, raw_sightings, cameras=active_cameras)
        enriched = enrich_sightings(cleaned, cameras=active_cameras)
        for item in enriched:
            all_enriched.append({
                **item,
                "_parsed_dt": parse_iso_utc(item["timestamp"])
            })
    return all_enriched


def compute_heatmap(
    raw_sightings: List[dict],
    cameras: Optional[Dict[str, dict]] = None,
    start_time_str: Optional[str] = None,
    end_time_str: Optional[str] = None
) -> List[dict]:
    """
    STEP 5: GET /api/trajectory/heatmap
    Groups sightings in window by camera_id across all cameras, weights vehicle_type,
    normalizes density_score to 0-1, evaluates is_congested, and calculates avg_speed_kmh per camera.
    """
    active_cameras = _resolve_cameras(cameras)
    all_enriched = _get_all_enriched_sightings(raw_sightings, cameras=active_cameras)
    
    if not all_enriched:
        # Return base camera list with 0 density if no sightings
        return [
            {
                "camera_id": cid,
                "location_name": info.get("location_name", cid),
                "gps_lat": info.get("gps_lat", 0.0),
                "gps_lng": info.get("gps_lng", 0.0),
                "vehicle_count": 0,
                "density_score": 0.0,
                "is_congested": False,
                "avg_speed_kmh": 0.0,
            }
            for cid, info in active_cameras.items()
        ]

    dataset_max_dt = max(item["_parsed_dt"] for item in all_enriched)

    if end_time_str:
        try:
            end_dt = parse_iso_utc(end_time_str)
        except Exception:
            end_dt = dataset_max_dt
    else:
        end_dt = dataset_max_dt

    if start_time_str:
        try:
            start_dt = parse_iso_utc(start_time_str)
        except Exception:
            start_dt = end_dt - timedelta(hours=2)
    else:
        start_dt = end_dt - timedelta(hours=2)

    if not any(start_dt <= s["_parsed_dt"] <= end_dt for s in all_enriched):
        end_dt = dataset_max_dt
        start_dt = end_dt - timedelta(hours=2)

    window_sightings = [
        s for s in all_enriched if start_dt <= s["_parsed_dt"] <= end_dt
    ]

    cam_stats = {
        cid: {"sightings": [], "weighted_count": 0.0, "speeds": []}
        for cid in active_cameras.keys()
    }

    for s in window_sightings:
        cid = s["camera_id"]
        if cid in cam_stats:
            cam_stats[cid]["sightings"].append(s)
            w = VEHICLE_WEIGHTS.get(str(s.get("vehicle_type", "")).lower(), 1.0)
            cam_stats[cid]["weighted_count"] += w
            if s.get("speed_from_prev_kmh") is not None:
                cam_stats[cid]["speeds"].append(s["speed_from_prev_kmh"])

    max_weighted = max((stats["weighted_count"] for stats in cam_stats.values()), default=0.0)

    result = []
    for cid, info in active_cameras.items():
        stats = cam_stats[cid]
        v_count = len(stats["sightings"])
        
        if max_weighted > 0:
            density_score = round(stats["weighted_count"] / max_weighted, 2)
        else:
            density_score = 0.0

        is_congested = v_count >= CONGESTION_THRESHOLD

        speeds = stats["speeds"]
        if speeds:
            avg_speed_kmh = round(sum(speeds) / len(speeds), 1)
        else:
            avg_speed_kmh = 0.0

        result.append({
            "camera_id": cid,
            "location_name": info.get("location_name", cid),
            "gps_lat": info.get("gps_lat", 0.0),
            "gps_lng": info.get("gps_lng", 0.0),
            "vehicle_count": v_count,
            "density_score": density_score,
            "is_congested": is_congested,
            "avg_speed_kmh": avg_speed_kmh,
        })

    return result


def compute_congestion(
    raw_sightings: List[dict],
    cameras: Optional[Dict[str, dict]] = None,
) -> List[dict]:
    """
    STEP 6: GET /api/trajectory/congestion
    Reuses heatmap over a rolling 30-minute window across all cameras, filters to is_congested: true.
    """
    active_cameras = _resolve_cameras(cameras)
    all_enriched = _get_all_enriched_sightings(raw_sightings, cameras=active_cameras)
    if not all_enriched:
        return []

    end_dt = max(item["_parsed_dt"] for item in all_enriched)
    start_dt = end_dt - timedelta(minutes=30)

    window_sightings = [
        s for s in all_enriched if start_dt <= s["_parsed_dt"] <= end_dt
    ]

    cam_sightings = {cid: [] for cid in active_cameras.keys()}
    for s in window_sightings:
        cid = s["camera_id"]
        if cid in cam_sightings:
            cam_sightings[cid].append(s)

    congested_list = []
    for cid, items in cam_sightings.items():
        v_count = len(items)
        if v_count >= CONGESTION_THRESHOLD:
            earliest_dt = min(item["_parsed_dt"] for item in items)
            cam_info = active_cameras.get(cid, {})
            congested_list.append({
                "camera_id": cid,
                "location_name": cam_info.get("location_name", cid),
                "vehicle_count": v_count,
                "since": format_iso_utc(earliest_dt)
            })

    return congested_list
