import json
import random
from datetime import datetime, timedelta, timezone

# 10 Camera Locations across Jabalpur
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

VEHICLE_TYPES = ["car", "truck", "bike", "bus", "cycle"]

# SIMULATED vehicle attributes — placeholder for the detection module's future classifier output, not real recognition.
VEHICLE_PROFILES = {
    "car": {
        "models": ["Swift", "i20", "WagonR", "City"],
        "colors": ["White", "Silver", "Red", "Black"]
    },
    "bike": {
        "models": ["Activa", "Pulsar", "Splendor"],
        "colors": ["Black", "Red", "Blue"]
    },
    "bus": {
        "models": ["Volvo 9400", "Tata Starbus", "Ashok Leyland Viking"],
        "colors": ["Yellow", "Red", "Blue"]
    },
    "truck": {
        "models": ["Tata Prima", "Ashok Leyland 2820", "Eicher Pro"],
        "colors": ["Red", "Blue", "White"]
    },
    "cycle": {
        "models": ["Hero Sprint", "Firefox Target", "Atlas Ultimate"],
        "colors": ["Black", "Red", "Blue"]
    }
}

def generate_mock_sightings():
    random.seed(42)  # Reproducible dataset
    
    # Base timestamp set to today 10:00:00 UTC
    now_utc = datetime(2026, 8, 26, 12, 0, 0, tzinfo=timezone.utc)
    start_time = now_utc - timedelta(hours=2) # 10:00:00 UTC

    sightings = []

    # Map to ensure consistency of simulated vehicle model and color per plate across all sightings
    plate_attributes = {
        "MP20AB1234": {"model": "Swift", "color": "Silver"},
        "MP20CB5678": {"model": "Pulsar", "color": "Black"},
        "MP20EF9012": {"model": "Volvo 9400", "color": "Red"},
        "MP20GH3456": {"model": "Tata Prima", "color": "Blue"},
        "MP20JK7890": {"model": "City", "color": "White"},
    }

    def get_plate_profile(plate_text: str, v_type: str):
        if plate_text not in plate_attributes:
            profile = VEHICLE_PROFILES.get(v_type, VEHICLE_PROFILES["car"])
            model = random.choice(profile["models"])
            color = random.choice(profile["colors"])
            plate_attributes[plate_text] = {"model": model, "color": color}
        return plate_attributes[plate_text]

    # Target Plate 1: MP20AB1234 (Car) — 6 stops + noise
    p1_attr = get_plate_profile("MP20AB1234", "car")
    p1_route = [
        ("CAM_04", 0, 0.95),      # 10:00:00 (Madan Mahal)
        ("CAM_03", 10, 0.92),     # 10:10:00 (Napier Town)
        ("CAM_01", 20, 0.96),     # 10:20:00 (MG Road Junction)
        ("CAM_02", 35, 0.94),     # 10:35:00 (Wright Town Circle)
        ("CAM_06", 50, 0.91),     # 10:50:00 (Adhartal)
        ("CAM_05", 70, 0.97),     # 11:10:00 (Ranjhi)
    ]
    for cam, mins, conf in p1_route:
        ts = start_time + timedelta(minutes=mins)
        sightings.append({
            "plate_text": "MP20AB1234",
            "camera_id": cam,
            "timestamp": ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "confidence": conf,
            "vehicle_type": "car",
            "model": p1_attr["model"],
            "color": p1_attr["color"]
        })

    # Noise for MP20AB1234 to test cleaning pipeline:
    # Noise A: Low confidence sighting (< 0.6)
    sightings.append({
        "plate_text": "MP20AB1234",
        "camera_id": "CAM_01",
        "timestamp": (start_time + timedelta(minutes=15)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "confidence": 0.45,
        "vehicle_type": "car",
        "model": p1_attr["model"],
        "color": p1_attr["color"]
    })
    # Noise B: Same-camera duplicate within 3s (< 5s window)
    sightings.append({
        "plate_text": "MP20AB1234",
        "camera_id": "CAM_01",
        "timestamp": (start_time + timedelta(minutes=20, seconds=3)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "confidence": 0.96,
        "vehicle_type": "car",
        "model": p1_attr["model"],
        "color": p1_attr["color"]
    })
    # Noise C: Teleporter speed jump (> 150 km/h misread)
    sightings.append({
        "plate_text": "MP20AB1234",
        "camera_id": "CAM_05",
        "timestamp": (start_time + timedelta(minutes=21)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "confidence": 0.88,
        "vehicle_type": "car",
        "model": p1_attr["model"],
        "color": p1_attr["color"]
    })

    # Target Plate 2: MP20CB5678 (Bike) — 5 stops
    p2_attr = get_plate_profile("MP20CB5678", "bike")
    p2_route = [
        ("CAM_01", 5, 0.93),
        ("CAM_02", 18, 0.95),
        ("CAM_03", 30, 0.89),
        ("CAM_04", 45, 0.94),
        ("CAM_06", 65, 0.96),
    ]
    for cam, mins, conf in p2_route:
        ts = start_time + timedelta(minutes=mins)
        sightings.append({
            "plate_text": "MP20CB5678",
            "camera_id": cam,
            "timestamp": ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "confidence": conf,
            "vehicle_type": "bike",
            "model": p2_attr["model"],
            "color": p2_attr["color"]
        })

    # Target Plate 3: MP20EF9012 (Bus) — 5 stops (revisits CAM_01)
    p3_attr = get_plate_profile("MP20EF9012", "bus")
    p3_route = [
        ("CAM_06", 5, 0.97),
        ("CAM_01", 25, 0.94),
        ("CAM_02", 35, 0.91),
        ("CAM_05", 55, 0.96),
        ("CAM_01", 75, 0.93),  # 2nd visit to CAM_01!
    ]
    for cam, mins, conf in p3_route:
        ts = start_time + timedelta(minutes=mins)
        sightings.append({
            "plate_text": "MP20EF9012",
            "camera_id": cam,
            "timestamp": ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "confidence": conf,
            "vehicle_type": "bus",
            "model": p3_attr["model"],
            "color": p3_attr["color"]
        })

    # Target Plate 4: MP20GH3456 (Truck) — 4 stops
    p4_attr = get_plate_profile("MP20GH3456", "truck")
    p4_route = [
        ("CAM_05", 10, 0.92),
        ("CAM_01", 30, 0.95),
        ("CAM_02", 50, 0.90),
        ("CAM_04", 80, 0.94),
    ]
    for cam, mins, conf in p4_route:
        ts = start_time + timedelta(minutes=mins)
        sightings.append({
            "plate_text": "MP20GH3456",
            "camera_id": cam,
            "timestamp": ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "confidence": conf,
            "vehicle_type": "truck",
            "model": p4_attr["model"],
            "color": p4_attr["color"]
        })

    # Target Plate 5: MP20JK7890 (Car) — Passes through 4 new cameras (CAM_07, CAM_08, CAM_10, CAM_09)
    p5_attr = get_plate_profile("MP20JK7890", "car")
    p5_route = [
        ("CAM_07", 12, 0.96),  # Bhedaghat
        ("CAM_08", 28, 0.93),  # Marhatal
        ("CAM_10", 42, 0.95),  # Sadar
        ("CAM_09", 58, 0.91),  # Damoh Naka
        ("CAM_06", 78, 0.97),  # Adhartal
    ]
    for cam, mins, conf in p5_route:
        ts = start_time + timedelta(minutes=mins)
        sightings.append({
            "plate_text": "MP20JK7890",
            "camera_id": cam,
            "timestamp": ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "confidence": conf,
            "vehicle_type": "car",
            "model": p5_attr["model"],
            "color": p5_attr["color"]
        })

    # Background random traffic block (~130 sightings across all 10 cameras)
    cam_keys = list(CAMERAS.keys())
    state_codes = ["MP20", "MP09", "MP04", "MH12", "DL01"]
    
    for i in range(130):
        code = random.choice(state_codes)
        letters = "".join(random.choices("ABCDEFGHJKLMNPQRSTUVWXYZ", k=2))
        digits = f"{random.randint(1000, 9999)}"
        plate = f"{code}{letters}{digits}"
        
        cam = random.choice(cam_keys)
        mins = random.randint(0, 118)
        secs = random.randint(0, 59)
        ts = start_time + timedelta(minutes=mins, seconds=secs)
        conf = round(random.uniform(0.65, 0.99), 2)
        v_type = random.choice(VEHICLE_TYPES)

        bg_attr = get_plate_profile(plate, v_type)

        sightings.append({
            "plate_text": plate,
            "camera_id": cam,
            "timestamp": ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "confidence": conf,
            "vehicle_type": v_type,
            "model": bg_attr["model"],
            "color": bg_attr["color"]
        })

    # Sort sightings chronologically
    sightings.sort(key=lambda s: s["timestamp"])

    with open("sightings.json", "w", encoding="utf-8") as f:
        json.dump(sightings, f, indent=2)

    print(f"Successfully generated {len(sightings)} mock sightings across 10 cameras!")

if __name__ == "__main__":
    generate_mock_sightings()

