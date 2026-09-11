import math

class MissionService:
    """
    Autonomous UAV Mission Planner.
    Modes:
    - MISSION_SIMULATION: Generates waypoint objects for software simulation & UI display.
    - REAL_MAVLINK: Hardware serial/UDP connection to Pixhawk / ArduPilot FCU (requires pymavlink transport).
    """

    def __init__(self, mode="MISSION_SIMULATION"):
        self.mode = mode
        self.mavlink_transport_active = False # Set to True only when PyMAVLink serial port is open

    def generate_lawnmower_pattern(self, boundary_coords, altitude_m=15.0, spacing_m=10.0):
        """
        Generates Lawnmower grid flight path over field boundary points.
        Raises ValueError if boundary_coords is empty or missing.
        """
        if not boundary_coords or len(boundary_coords) < 3:
            raise ValueError("[MissionService] Field boundary coordinates are required for mission generation (minimum 3 GPS polygon vertices).")

        lats = [pt["lat"] for pt in boundary_coords]
        lngs = [pt["lng"] for pt in boundary_coords]
        min_lat, max_lat = min(lats), max(lats)
        min_lng, max_lng = min(lngs), max(lngs)

        waypoints = []
        waypoints.append({
            "seq": 0,
            "command": "NAV_TAKEOFF",
            "lat": min_lat,
            "lng": min_lng,
            "alt_m": altitude_m,
            "action": "TAKEOFF"
        })

        step_lat = (spacing_m / 111000.0)
        curr_lat = min_lat
        direction = 1
        seq = 1

        while curr_lat <= max_lat:
            start_lng = min_lng if direction == 1 else max_lng
            end_lng = max_lng if direction == 1 else min_lng

            waypoints.append({
                "seq": seq,
                "command": "NAV_WAYPOINT",
                "lat": round(curr_lat, 6),
                "lng": round(start_lng, 6),
                "alt_m": altitude_m,
                "action": "SCAN_SWEEP_START"
            })
            seq += 1

            waypoints.append({
                "seq": seq,
                "command": "NAV_WAYPOINT",
                "lat": round(curr_lat, 6),
                "lng": round(end_lng, 6),
                "alt_m": altitude_m,
                "action": "SCAN_SWEEP_END"
            })
            seq += 1

            curr_lat += step_lat
            direction *= -1

        waypoints.append({
            "seq": seq,
            "command": "NAV_RETURN_TO_LAUNCH",
            "lat": min_lat,
            "lng": min_lng,
            "alt_m": 0.0,
            "action": "RTL"
        })

        total_dist_km = (seq * spacing_m) / 1000.0
        est_flight_time_min = round((total_dist_km / 0.3), 1)

        mission_status = "REAL_MAVLINK_HARDWARE" if self.mavlink_transport_active else "SIMULATED_WAYPOINTS"

        return {
            "mission_id": "MISSION-GRID-01",
            "type": "LAWNMOWER_SURVEY",
            "execution_mode": mission_status,
            "mavlink_connection_status": "CONNECTED" if self.mavlink_transport_active else "NOT_CONNECTED (SIMULATION)",
            "altitude_m": altitude_m,
            "waypoint_count": len(waypoints),
            "waypoints": waypoints,
            "estimated_distance_km": round(total_dist_km, 2),
            "estimated_duration_minutes": est_flight_time_min
        }

    def plan_targeted_revisit(self, hotspot_data, hover_time_sec=10):
        """
        Creates AI-driven targeted revisit mission for high-severity DBSCAN hotspots.
        """
        centroid = hotspot_data.get("centroid")
        if not centroid or "lat" not in centroid or "lng" not in centroid:
            raise ValueError("[MissionService] Hotspot centroid coordinates (lat, lng) are required.")

        waypoints = []
        waypoints.append({
            "seq": 0,
            "command": "NAV_TAKEOFF",
            "lat": centroid["lat"],
            "lng": centroid["lng"],
            "alt_m": 8.0,
            "action": "TAKEOFF_REVISIT"
        })

        waypoints.append({
            "seq": 1,
            "command": "NAV_LOITER_UNLIM",
            "lat": centroid["lat"],
            "lng": centroid["lng"],
            "alt_m": 6.0,
            "hover_seconds": hover_time_sec,
            "action": "SPECTRAL_MULTISPECTRAL_CAPTURE"
        })

        waypoints.append({
            "seq": 2,
            "command": "NAV_RETURN_TO_LAUNCH",
            "lat": centroid["lat"],
            "lng": centroid["lng"],
            "alt_m": 0.0,
            "action": "RTL"
        })

        return {
            "mission_id": f"REVISIT-{hotspot_data.get('hotspot_id', 'HS-01')}",
            "type": "TARGETED_AI_REVISIT",
            "execution_mode": "SIMULATED_WAYPOINTS",
            "mavlink_connection_status": "NOT_CONNECTED (SIMULATION)",
            "target_hotspot": hotspot_data.get("hotspot_id", "HS-01"),
            "target_centroid": centroid,
            "altitude_m": 6.0,
            "hover_duration_sec": hover_time_sec,
            "waypoints": waypoints
        }

mission_service = MissionService()
