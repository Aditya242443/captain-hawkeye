import math
from datetime import datetime, timedelta, timezone

# STEP 1: Fixed CAMERAS dictionary (Expanded to 10 cameras)
CAMERAS = {
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

VEHICLE_WEIGHTS = {
    "cycle": 0.5,
    "bike": 0.5,
    "car": 1.0,
    "bus": 3.0,
    "truck": 3.0,
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

def calculate_bearing_8point(lat1: float, lng1: float, lat2: float, lng2: float) -> str | None:
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

def parse_iso_utc(ts_str: str) -> datetime:
    """
    Parses ISO 8601 UTC timestamp string into a timezone-aware datetime object.
    """
    if ts_str.endswith("Z"):
        ts_str = ts_str[:-1] + "+00:00"
    return datetime.fromisoformat(ts_str).astimezone(timezone.utc)

def format_iso_utc(dt: datetime) -> str:
    """
    Formats a timezone-aware datetime object into ISO 8601 UTC string ending in 'Z'.
    """
    dt_utc = dt.astimezone(timezone.utc)
    return dt_utc.strftime("%Y-%m-%dT%H:%M:%SZ")

def clean_sightings(
    plate: str, 
    raw_sightings: list[dict], 
    confidence_threshold: float = 0.6, 
    dedupe_seconds: float = 5.0, 
    max_speed_kmh: float = 150.0
) -> list[dict]:
    """
    STEP 2: Data Cleaning Pipeline
    - Filters for plate (case-insensitive).
    - Drops sightings below confidence_threshold (0.6).
    - Deduplicates same-camera sightings within dedupe_seconds (5.0s).
    - Removes consecutive sightings implying speed > max_speed_kmh (150 km/h) as OCR misreads.
    - Returns chronologically sorted clean sightings.
    """
    target_plate = plate.strip().upper()

    # Filter by plate text and confidence threshold
    candidates = []
    for s in raw_sightings:
        if s.get("plate_text", "").strip().upper() == target_plate:
            if s.get("confidence", 0.0) >= confidence_threshold:
                if s.get("camera_id") in CAMERAS:
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

        # Check speed plausibility from last valid sighting
        cam_prev = CAMERAS[last_valid["camera_id"]]
        cam_curr = CAMERAS[s["camera_id"]]

        dist_km = haversine_km(
            cam_prev["gps_lat"], cam_prev["gps_lng"],
            cam_curr["gps_lat"], cam_curr["gps_lng"]
        )

        hours = dt_sec / 3600.0
        if hours > 0:
            implied_speed = dist_km / hours
            if implied_speed > max_speed_kmh:
                # Likely OCR misread teleporter jump, drop sighting
                continue

        cleaned.append(s)

    return cleaned

def enrich_sightings(cleaned_sightings: list[dict]) -> list[dict]:
    """
    STEP 3: Direction + Speed Enrichment (Includes vehicle_type & confidence)
    For each sighting after the first, computes:
    - direction_from_prev: 8-point compass bearing from prev camera to current camera
    - speed_from_prev_kmh: speed in km/h based on Haversine distance / time delta
    - vehicle_type & confidence preserved from raw sighting record
    First sighting always has direction_from_prev and speed_from_prev_kmh as null (None).
    """
    enriched = []

    for i, curr in enumerate(cleaned_sightings):
        cam_curr = CAMERAS[curr["camera_id"]]
        ts_z = format_iso_utc(curr["_parsed_dt"])

        if i == 0:
            direction_from_prev = None
            speed_from_prev_kmh = None
        else:
            prev = cleaned_sightings[i - 1]
            cam_prev = CAMERAS[prev["camera_id"]]

            dt_sec = (curr["_parsed_dt"] - prev["_parsed_dt"]).total_seconds()
            dist_km = haversine_km(
                cam_prev["gps_lat"], cam_prev["gps_lng"],
                cam_curr["gps_lat"], cam_curr["gps_lng"]
            )

            if dt_sec > 0:
                speed_from_prev_kmh = round(dist_km / (dt_sec / 3600.0), 1)
            else:
                speed_from_prev_kmh = 0.0

            direction_from_prev = calculate_bearing_8point(
                cam_prev["gps_lat"], cam_prev["gps_lng"],
                cam_curr["gps_lat"], cam_curr["gps_lng"]
            )

        enriched.append({
            "camera_id": curr["camera_id"],
            "location_name": cam_curr["location_name"],
            "gps_lat": cam_curr["gps_lat"],
            "gps_lng": cam_curr["gps_lng"],
            "timestamp": ts_z,
            "direction_from_prev": direction_from_prev,
            "speed_from_prev_kmh": speed_from_prev_kmh,
            "vehicle_type": curr.get("vehicle_type", "car"),
            "model": curr.get("model", "Unknown"),
            "color": curr.get("color", "Unknown"),
            "confidence": curr.get("confidence", 1.0)
        })

    return enriched

def _get_all_enriched_sightings(raw_sightings: list[dict]) -> list[dict]:
    """
    Helper to clean and enrich sightings for all plates in dataset.
    """
    plates = set(s.get("plate_text", "").strip().upper() for s in raw_sightings if s.get("plate_text"))
    all_enriched = []
    for p in plates:
        cleaned = clean_sightings(p, raw_sightings)
        enriched = enrich_sightings(cleaned)
        for item in enriched:
            all_enriched.append({
                **item,
                "_parsed_dt": parse_iso_utc(item["timestamp"])
            })
    return all_enriched

def compute_heatmap(
    raw_sightings: list[dict],
    start_time_str: str | None = None,
    end_time_str: str | None = None
) -> list[dict]:
    """
    STEP 5: GET /api/trajectory/heatmap
    Groups sightings in window by camera_id across all 10 cameras, weights vehicle_type,
    normalizes density_score to 0-1, evaluates is_congested, and calculates avg_speed_kmh per camera.
    """
    all_enriched = _get_all_enriched_sightings(raw_sightings)
    if not all_enriched:
        return []

    dataset_max_dt = max(item["_parsed_dt"] for item in all_enriched)

    if end_time_str:
        end_dt = parse_iso_utc(end_time_str)
    else:
        end_dt = dataset_max_dt

    if start_time_str:
        start_dt = parse_iso_utc(start_time_str)
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
        for cid in CAMERAS.keys()
    }

    for s in window_sightings:
        cid = s["camera_id"]
        if cid in cam_stats:
            cam_stats[cid]["sightings"].append(s)
            w = VEHICLE_WEIGHTS.get(s["vehicle_type"].lower(), 1.0)
            cam_stats[cid]["weighted_count"] += w
            if s["speed_from_prev_kmh"] is not None:
                cam_stats[cid]["speeds"].append(s["speed_from_prev_kmh"])

    max_weighted = max((stats["weighted_count"] for stats in cam_stats.values()), default=0.0)

    result = []
    for cid, info in CAMERAS.items():
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
            "location_name": info["location_name"],
            "gps_lat": info["gps_lat"],
            "gps_lng": info["gps_lng"],
            "vehicle_count": v_count,
            "density_score": density_score,
            "is_congested": is_congested,
            "avg_speed_kmh": avg_speed_kmh,
        })

    return result

def compute_congestion(raw_sightings: list[dict]) -> list[dict]:
    """
    STEP 6: GET /api/trajectory/congestion
    Reuses heatmap over a rolling 30-minute window across all 10 cameras, filters to is_congested: true.
    """
    all_enriched = _get_all_enriched_sightings(raw_sightings)
    if not all_enriched:
        return []

    end_dt = max(item["_parsed_dt"] for item in all_enriched)
    start_dt = end_dt - timedelta(minutes=30)

    window_sightings = [
        s for s in all_enriched if start_dt <= s["_parsed_dt"] <= end_dt
    ]

    cam_sightings = {cid: [] for cid in CAMERAS.keys()}
    for s in window_sightings:
        cid = s["camera_id"]
        if cid in cam_sightings:
            cam_sightings[cid].append(s)

    congested_list = []
    for cid, items in cam_sightings.items():
        v_count = len(items)
        if v_count >= CONGESTION_THRESHOLD:
            earliest_dt = min(item["_parsed_dt"] for item in items)
            congested_list.append({
                "camera_id": cid,
                "location_name": CAMERAS[cid]["location_name"],
                "vehicle_count": v_count,
                "since": format_iso_utc(earliest_dt)
            })

    return congested_list
