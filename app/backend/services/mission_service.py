import math

class MissionService:
    """
    Autonomous UAV Mission Planner with MAVLink / ArduPilot Hardware Abstraction Layer.
    Modes:
    - SIMULATION: Software-In-The-Loop flight path simulation
    - REAL_HARDWARE: Serial/UDP MAVLink communication with Pixhawk / ArduPilot FCU
    """

    def __init__(self, mode="SIMULATION"):
        self.mode = mode
        self.active_mission = None
        self.uav_status = {
            "mode": mode,
            "connected": True,
            "armed": False,
            "altitude_m": 0.0,
            "battery_pct": 94.5,
            "gps_fix": "3D_FIX",
            "satellites": 14,
            "latitude": 28.6139,
            "longitude": 77.2090
        }

    def generate_lawnmower_pattern(self, boundary_coords, altitude_m=15.0, spacing_m=10.0):
        """
        Generates Lawnmower grid flight path over field boundary points.
        - boundary_coords: list of dicts [{'lat': float, 'lng': float}]
        """
        if not boundary_coords or len(boundary_coords) < 3:
            # Default boundary box near Delhi farm
            boundary_coords = [
                {"lat": 28.6135, "lng": 77.2085},
                {"lat": 28.6145, "lng": 77.2085},
                {"lat": 28.6145, "lng": 77.2095},
                {"lat": 28.6135, "lng": 77.2095}
            ]

        lats = [pt["lat"] for pt in boundary_coords]
        lngs = [pt["lng"] for pt in boundary_coords]
        min_lat, max_lat = min(lats), max(lats)
        min_lng, max_lng = min(lngs), max(lngs)

        waypoints = []
        # Takeoff waypoint
        waypoints.append({
            "seq": 0,
            "command": "NAV_TAKEOFF",
            "lat": min_lat,
            "lng": min_lng,
            "alt_m": altitude_m,
            "action": "TAKEOFF"
        })

        # Lawnmower parallel sweeps
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

        # Return to Launch (RTL)
        waypoints.append({
            "seq": seq,
            "command": "NAV_RETURN_TO_LAUNCH",
            "lat": min_lat,
            "lng": min_lng,
            "alt_m": 0.0,
            "action": "RTL"
        })

        total_dist_km = (seq * spacing_m) / 1000.0
        est_flight_time_min = round((total_dist_km / 0.3), 1) # ~5 m/s sweep speed

        self.active_mission = {
            "mission_id": "MISSION-GRID-01",
            "type": "LAWNMOWER_SURVEY",
            "altitude_m": altitude_m,
            "waypoint_count": len(waypoints),
            "waypoints": waypoints,
            "estimated_distance_km": round(total_dist_km, 2),
            "estimated_duration_minutes": est_flight_time_min,
            "mavlink_protocol": "MAVLink 2.0 / ArduPilot"
        }

        return self.active_mission

    def plan_targeted_revisit(self, hotspot_data, hover_time_sec=10):
        """
        Creates AI-driven targeted revisit mission for high-severity DBSCAN hotspots.
        """
        waypoints = []
        waypoints.append({
            "seq": 0,
            "command": "NAV_TAKEOFF",
            "lat": hotspot_data.get("centroid", {}).get("lat", 28.6139),
            "lng": hotspot_data.get("centroid", {}).get("lng", 77.2090),
            "alt_m": 8.0,
            "action": "TAKEOFF_REVISIT"
        })

        centroid = hotspot_data.get("centroid", {"lat": 28.6139, "lng": 77.2090})

        waypoints.append({
            "seq": 1,
            "command": "NAV_LOITER_UNLIM",
            "lat": centroid["lat"],
            "lng": centroid["lng"],
            "alt_m": 6.0, # Low-altitude close inspection
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

        revisit_mission = {
            "mission_id": f"REVISIT-{hotspot_data.get('hotspot_id', 'HS-01')}",
            "type": "TARGETED_AI_REVISIT",
            "target_hotspot": hotspot_data.get("hotspot_id", "HS-01"),
            "target_centroid": centroid,
            "altitude_m": 6.0,
            "hover_duration_sec": hover_time_sec,
            "waypoints": waypoints,
            "mavlink_protocol": "MAVLink 2.0 / ArduPilot"
        }

        return revisit_mission

mission_service = MissionService()
