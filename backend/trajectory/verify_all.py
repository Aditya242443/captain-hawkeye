"""
Verification script for all 5 requirements from the user's request.
Run: python verify_all.py
"""
import urllib.request, json

BASE = "http://127.0.0.1:8000/api/trajectory"
PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"

def check(condition, msg):
    print(f"  [{PASS if condition else FAIL}] {msg}")
    return condition

print("\n====== Captain Hawkeye — Requirement Verification ======\n")

# ─── REQ 1: Overlapping marker offset logic (frontend-only, verified via API data) ─────────────────
print("REQ 1 — Overlapping Pin Offset (CAM_01 revisit by MP20EF9012)")
r1 = json.loads(urllib.request.urlopen(f"{BASE}/MP20EF9012").read())
sightings = r1["sightings"]
cam_ids = [s["camera_id"] for s in sightings]
cam01_visits = cam_ids.count("CAM_01")
check(r1["found"], "MP20EF9012 found=true")
check(len(sightings) == 5, f"5 sightings returned (got {len(sightings)})")
check(cam01_visits == 2, f"CAM_01 appears exactly twice (got {cam01_visits})")
check("vehicle_type" in sightings[0], "vehicle_type field present in sightings")
check("confidence" in sightings[0], "confidence field present in sightings")

# ─── REQ 2: 10 Cameras in heatmap response ───────────────────────────────────────────────────────
print("\nREQ 2 — 10 Cameras in Heatmap Response")
r2 = json.loads(urllib.request.urlopen(f"{BASE}/heatmap").read())
cam_ids_hm = [c["camera_id"] for c in r2]
new_cams = ["CAM_07", "CAM_08", "CAM_09", "CAM_10"]
check(len(r2) == 10, f"Heatmap returns 10 camera entries (got {len(r2)})")
for nc in new_cams:
    check(nc in cam_ids_hm, f"New camera {nc} present in heatmap")
check(all("location_name" in c for c in r2), "location_name field present in all heatmap entries")

# ─── REQ 3: Permanent labels (frontend-only; confirmed by location_name in API) ─────────────────
print("\nREQ 3 — Permanent Camera Labels (verified via location_name in heatmap API)")
for c in r2:
    check(bool(c.get("location_name")), f"{c['camera_id']} has non-empty location_name: '{c.get('location_name')}'")

# ─── REQ 4: MP20JK7890 trajectory through new cameras ────────────────────────────────────────────
print("\nREQ 4 — Vehicle Info Card Data (MP20JK7890 new cameras route)")
r4 = json.loads(urllib.request.urlopen(f"{BASE}/MP20JK7890").read())
s4 = r4["sightings"]
cams_in_route = [s["camera_id"] for s in s4]
check(r4["found"], "MP20JK7890 found=true")
check(len(s4) == 5, f"5 sightings for MP20JK7890 (got {len(s4)})")
check("CAM_07" in cams_in_route, "CAM_07 (Bhedaghat) in route")
check("CAM_08" in cams_in_route, "CAM_08 (Marhatal) in route")
check("CAM_09" in cams_in_route, "CAM_09 (Damoh Naka) in route")
check("CAM_10" in cams_in_route, "CAM_10 (Sadar) in route")
check(s4[0].get("vehicle_type") == "car", f"vehicle_type=car (got '{s4[0].get('vehicle_type')}')")

# ─── REQ 5: Enrichment fields shape ─────────────────────────────────────────────────────────────
print("\nREQ 5 — Trajectory Enrichment Shape (direction, speed, first/last null, model, color)")
r5 = json.loads(urllib.request.urlopen(f"{BASE}/MP20AB1234").read())
s5 = r5["sightings"]
check(s5[0]["direction_from_prev"] is None, "First sighting direction_from_prev=null")
check(s5[0]["speed_from_prev_kmh"] is None, "First sighting speed_from_prev_kmh=null")
check(s5[1]["direction_from_prev"] is not None, f"2nd sighting has direction (got '{s5[1]['direction_from_prev']}')")
check(s5[1]["speed_from_prev_kmh"] is not None, f"2nd sighting has speed (got {s5[1]['speed_from_prev_kmh']} km/h)")
check("model" in s5[0] and s5[0]["model"] == "Swift", f"Simulated model present and consistent (got '{s5[0].get('model')}')")
check("color" in s5[0] and s5[0]["color"] == "Silver", f"Simulated color present and consistent (got '{s5[0].get('color')}')")

# ─── Congestion endpoint ─────────────────────────────────────────────────────────────────────────
print("\nCongestion Endpoint Health")
r_cong = json.loads(urllib.request.urlopen(f"{BASE}/congestion").read())
check(isinstance(r_cong, list), "Congestion returns a list")
if r_cong:
    check("camera_id" in r_cong[0] and "location_name" in r_cong[0] and "since" in r_cong[0],
          "Congestion entry has camera_id, location_name, since fields")

print("\n========================================================\n")
