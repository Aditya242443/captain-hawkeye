"""
Project Plexis (Captain Hawkeye) - Database Seeding Script
Populates the Supabase PostgreSQL database with:
1. 10 Jabalpur ANPR Camera Nodes
2. Realistic multi-camera vehicle sighting trajectories
3. Congestion clusters for traffic analytics
"""

import sys
import random
from pathlib import Path
from datetime import datetime, timedelta, timezone

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.database import Base, engine, SessionLocal
from backend.anpr.models import Camera, Sighting

CAMERAS_DATA = [
    {"camera_id": "CAM_01", "location_name": "MG Road Junction",   "gps_lat": 23.1815, "gps_lng": 79.9864},
    {"camera_id": "CAM_02", "location_name": "Wright Town Circle", "gps_lat": 23.1900, "gps_lng": 79.9950},
    {"camera_id": "CAM_03", "location_name": "Napier Town",        "gps_lat": 23.1706, "gps_lng": 79.9422},
    {"camera_id": "CAM_04", "location_name": "Madan Mahal",         "gps_lat": 23.1489, "gps_lng": 79.9247},
    {"camera_id": "CAM_05", "location_name": "Ranjhi",              "gps_lat": 23.2245, "gps_lng": 80.0134},
    {"camera_id": "CAM_06", "location_name": "Adhartal",            "gps_lat": 23.2100, "gps_lng": 79.9350},
    {"camera_id": "CAM_07", "location_name": "Bhedaghat",           "gps_lat": 23.1320, "gps_lng": 79.8010},
    {"camera_id": "CAM_08", "location_name": "Marhatal",            "gps_lat": 23.1600, "gps_lng": 79.9400},
    {"camera_id": "CAM_09", "location_name": "Damoh Naka",          "gps_lat": 23.1900, "gps_lng": 79.9200},
    {"camera_id": "CAM_10", "location_name": "Sadar",               "gps_lat": 23.1800, "gps_lng": 79.9500},
]


def seed_database():
    print("=== Initializing Project Plexis Database Schema ===")
    Base.metadata.create_all(bind=engine)
    print("[OK] Schema initialized successfully.")

    db = SessionLocal()
    try:
        print("\n=== Seeding 10 Jabalpur ANPR Cameras ===")
        cam_map = {}
        for c_data in CAMERAS_DATA:
            cam = db.query(Camera).filter(Camera.camera_id == c_data["camera_id"]).first()
            if not cam:
                cam = Camera(**c_data)
                db.add(cam)
                print(f"  + Registered {c_data['camera_id']} ({c_data['location_name']})")
            else:
                cam.location_name = c_data["location_name"]
                cam.gps_lat = c_data["gps_lat"]
                cam.gps_lng = c_data["gps_lng"]
                print(f"  * Updated {c_data['camera_id']} ({c_data['location_name']})")
            cam_map[c_data["camera_id"]] = c_data

        db.commit()

        # Seed Vehicle Sightings
        print("\n=== Seeding Vehicle Trajectories & Sighting History ===")
        now = datetime.now(timezone.utc)
        random.seed(42)

        # Predefined rich trajectories
        trajectories = [
            {
                "plate": "MP20AB1234",
                "vehicle_type": "car",
                "route": [
                    ("CAM_04", 65, 0.95),  # Madan Mahal 65 min ago
                    ("CAM_03", 52, 0.92),  # Napier Town 52 min ago
                    ("CAM_01", 38, 0.96),  # MG Road 38 min ago
                    ("CAM_02", 24, 0.94),  # Wright Town 24 min ago
                    ("CAM_06", 14, 0.91),  # Adhartal 14 min ago
                    ("CAM_05", 4,  0.97),  # Ranjhi 4 min ago
                ]
            },
            {
                "plate": "MP20CB5678",
                "vehicle_type": "motorcycle",
                "route": [
                    ("CAM_07", 75, 0.89),  # Bhedaghat
                    ("CAM_04", 45, 0.93),  # Madan Mahal
                    ("CAM_08", 28, 0.91),  # Marhatal
                    ("CAM_10", 12, 0.95),  # Sadar
                ]
            },
            {
                "plate": "MP20EF9012",
                "vehicle_type": "bus",
                "route": [
                    ("CAM_09", 55, 0.94),  # Damoh Naka
                    ("CAM_06", 40, 0.92),  # Adhartal
                    ("CAM_02", 22, 0.96),  # Wright Town
                    ("CAM_01", 8,  0.95),  # MG Road
                ]
            },
            {
                "plate": "MP20GH3456",
                "vehicle_type": "truck",
                "route": [
                    ("CAM_05", 60, 0.91),  # Ranjhi
                    ("CAM_01", 35, 0.88),  # MG Road
                    ("CAM_02", 18, 0.93),  # Wright Town
                    ("CAM_08", 5,  0.92),  # Marhatal
                ]
            },
            {
                "plate": "DL01AB1234",
                "vehicle_type": "car",
                "route": [
                    ("CAM_03", 50, 0.96),
                    ("CAM_10", 30, 0.94),
                    ("CAM_01", 10, 0.98),
                ]
            },
            {
                "plate": "MH12A1234",
                "vehicle_type": "car",
                "route": [
                    ("CAM_04", 42, 0.93),
                    ("CAM_08", 25, 0.90),
                    ("CAM_02", 6,  0.95),
                ]
            },
            {
                "plate": "22BH1234AA",
                "vehicle_type": "car",
                "route": [
                    ("CAM_09", 35, 0.92),
                    ("CAM_01", 15, 0.95),
                    ("CAM_02", 2,  0.97),
                ]
            }
        ]

        sightings_to_add = []

        # Add structured trajectories
        for traj in trajectories:
            plate = traj["plate"]
            v_type = traj["vehicle_type"]
            for cid, mins_ago, conf in traj["route"]:
                ts = now - timedelta(minutes=mins_ago)
                cam_info = cam_map[cid]
                sightings_to_add.append(
                    Sighting(
                        plate_text=plate,
                        camera_id=cid,
                        timestamp=ts,
                        gps_lat=cam_info["gps_lat"],
                        gps_lng=cam_info["gps_lng"],
                        confidence=conf,
                        vehicle_type=v_type,
                    )
                )

        # Add background traffic to create realistic density & congestion clusters (especially at CAM_01 and CAM_02)
        bg_plates = [
            ("MP20ZA1111", "car"), ("MP20ZB2222", "car"), ("MP20ZC3333", "motorcycle"),
            ("MP20ZD4444", "bus"), ("MP20ZE5555", "truck"), ("MP20ZF6666", "car"),
            ("MP20ZG7777", "car"), ("MP20ZH8888", "motorcycle"), ("MP20ZJ9999", "car"),
            ("MP20ZK1010", "car"), ("MP20ZL2020", "car"), ("MP20ZM3030", "bus"),
            ("HR26DQ5555", "car"), ("UP32AZ0001", "car"), ("KA05MJ9999", "car"),
        ]

        # Heavy cluster on CAM_01 (MG Road) and CAM_02 (Wright Town) in last 25 minutes
        for i, (bg_plate, bg_type) in enumerate(bg_plates):
            # CAM_01 recent sightings (creates congestion)
            ts1 = now - timedelta(minutes=random.randint(2, 25))
            cam1 = cam_map["CAM_01"]
            sightings_to_add.append(
                Sighting(
                    plate_text=bg_plate,
                    camera_id="CAM_01",
                    timestamp=ts1,
                    gps_lat=cam1["gps_lat"],
                    gps_lng=cam1["gps_lng"],
                    confidence=round(random.uniform(0.85, 0.99), 2),
                    vehicle_type=bg_type,
                )
            )

            # CAM_02 recent sightings (creates congestion)
            ts2 = now - timedelta(minutes=random.randint(1, 28))
            cam2 = cam_map["CAM_02"]
            sightings_to_add.append(
                Sighting(
                    plate_text=f"{bg_plate[:7]}{i}X",
                    camera_id="CAM_02",
                    timestamp=ts2,
                    gps_lat=cam2["gps_lat"],
                    gps_lng=cam2["gps_lng"],
                    confidence=round(random.uniform(0.80, 0.98), 2),
                    vehicle_type=bg_type,
                )
            )

            # Random distribution across other cameras
            other_cam_id = f"CAM_{random.randint(3, 10):02d}"
            cam_other = cam_map[other_cam_id]
            ts3 = now - timedelta(minutes=random.randint(10, 110))
            sightings_to_add.append(
                Sighting(
                    plate_text=f"MP20R{random.randint(1000, 9999)}",
                    camera_id=other_cam_id,
                    timestamp=ts3,
                    gps_lat=cam_other["gps_lat"],
                    gps_lng=cam_other["gps_lng"],
                    confidence=round(random.uniform(0.78, 0.97), 2),
                    vehicle_type=random.choice(["car", "motorcycle", "bus", "truck"]),
                )
            )

        db.add_all(sightings_to_add)
        db.commit()
        print(f"[OK] Successfully seeded {len(sightings_to_add)} live sightings across 10 cameras.")
        print("[OK] Database ready for Project Plexis demo!\n")

    except Exception as e:
        db.rollback()
        print(f"[ERROR] Database seeding error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
