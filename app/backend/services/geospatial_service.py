import numpy as np
from sklearn.cluster import DBSCAN

class GeospatialService:
    """
    Real Spatial Hotspot Detection & Bounding Polygon Engine using DBSCAN.
    Clusters stress telemetry across field GPS coordinates and calculates exact affected field area ($m^2$).
    """

    def cluster_hotspots(self, telemetry_points, eps_meters=20.0, min_samples=2):
        """
        Clusters spatial telemetry nodes into stress hotspots.
        - telemetry_points: list of dicts with keys 'lat', 'lng', 'severity', 'node_id', 'condition'
        """
        if not telemetry_points:
            return {"hotspots": [], "total_affected_area_m2": 0.0, "total_hotspots": 0}

        coords = []
        high_stress_indices = []

        for idx, pt in enumerate(telemetry_points):
            # Only cluster points with noticeable stress severity (> 25.0)
            if pt.get("severity", 0.0) >= 25.0:
                coords.append([pt["lat"], pt["lng"]])
                high_stress_indices.append(idx)

        if not coords:
            return {"hotspots": [], "total_affected_area_m2": 0.0, "total_hotspots": 0}

        coords_arr = np.array(coords)

        # Convert lat/lng degrees approx to meters (1 deg lat ~ 111,000 meters)
        coords_meters = np.zeros_like(coords_arr)
        coords_meters[:, 0] = coords_arr[:, 0] * 111000.0
        coords_meters[:, 1] = coords_arr[:, 1] * 111000.0 * np.cos(np.radians(coords_arr[:, 0].mean()))

        db = DBSCAN(eps=eps_meters, min_samples=min_samples).fit(coords_meters)
        labels = db.labels_

        unique_labels = set(labels)
        hotspots = []
        total_area = 0.0

        for cluster_id in unique_labels:
            if cluster_id == -1:
                continue # Skip noise points

            cluster_mask = (labels == cluster_id)
            cluster_pts_latlng = coords_arr[cluster_mask]
            cluster_pts_meters = coords_meters[cluster_mask]

            centroid_lat = float(np.mean(cluster_pts_latlng[:, 0]))
            centroid_lng = float(np.mean(cluster_pts_latlng[:, 1]))

            # Estimate area using bounding polygon box in meters
            min_x, max_x = np.min(cluster_pts_meters[:, 0]), np.max(cluster_pts_meters[:, 0])
            min_y, max_y = np.min(cluster_pts_meters[:, 1]), np.max(cluster_pts_meters[:, 1])

            dx = max(10.0, max_x - min_x) # Minimum 10m width
            dy = max(10.0, max_y - min_y) # Minimum 10m length
            area_m2 = float(dx * dy)
            total_area += area_m2

            # Collect affected nodes
            affected_nodes = [telemetry_points[high_stress_indices[i]]["node_id"] for i, is_in in enumerate(cluster_mask) if is_in]
            severities = [telemetry_points[high_stress_indices[i]]["severity"] for i, is_in in enumerate(cluster_mask) if is_in]
            avg_sev = float(np.mean(severities))

            hotspots.append({
                "hotspot_id": f"HS-DB-{cluster_id + 1:02d}",
                "centroid": {"lat": round(centroid_lat, 6), "lng": round(centroid_lng, 6)},
                "affected_nodes": affected_nodes,
                "node_count": len(affected_nodes),
                "avg_severity": round(avg_sev, 2),
                "area_m2": round(area_m2, 2),
                "polygon_bounds": [
                    {"lat": round(centroid_lat + (dy/222000.0), 6), "lng": round(centroid_lng - (dx/222000.0), 6)},
                    {"lat": round(centroid_lat + (dy/222000.0), 6), "lng": round(centroid_lng + (dx/222000.0), 6)},
                    {"lat": round(centroid_lat - (dy/222000.0), 6), "lng": round(centroid_lng + (dx/222000.0), 6)},
                    {"lat": round(centroid_lat - (dy/222000.0), 6), "lng": round(centroid_lng - (dx/222000.0), 6)}
                ]
            })

        return {
            "hotspots": hotspots,
            "total_affected_area_m2": round(total_area, 2),
            "total_hotspots": len(hotspots),
            "algorithm": "DBSCAN (Density-Based Spatial Clustering of Applications with Noise)"
        }

geospatial_service = GeospatialService()
