-- =============================================================================
-- Project Plexis (Captain Hawkeye) - Database Schema
-- Shared PostgreSQL / Supabase Schema for ANPR, Trajectory, and Alerts Modules
-- =============================================================================

CREATE TABLE IF NOT EXISTS cameras (
    camera_id VARCHAR(20) PRIMARY KEY,
    gps_lat FLOAT NOT NULL,
    gps_lng FLOAT NOT NULL,
    location_name VARCHAR(100)
);

CREATE TABLE IF NOT EXISTS sightings (
    id SERIAL PRIMARY KEY,
    plate_text VARCHAR(15) NOT NULL,
    camera_id VARCHAR(20) NOT NULL REFERENCES cameras(camera_id),
    timestamp TIMESTAMP NOT NULL,
    gps_lat FLOAT NOT NULL,
    gps_lng FLOAT NOT NULL,
    confidence FLOAT NOT NULL,
    vehicle_type VARCHAR(20),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sightings_plate ON sightings(plate_text);
CREATE INDEX IF NOT EXISTS idx_sightings_camera_time ON sightings(camera_id, timestamp);
