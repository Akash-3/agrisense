import unittest
from app.backend.services.geospatial_service import geospatial_service

class TestGeospatialDBSCAN(unittest.TestCase):
    def test_clustering_and_area(self):
        sample_nodes = [
            {"node_id": "NODE-01", "lat": 28.6139, "lng": 77.2090, "severity": 65.0},
            {"node_id": "NODE-02", "lat": 28.6140, "lng": 77.2091, "severity": 70.0},
            {"node_id": "NODE-03", "lat": 28.6138, "lng": 77.2089, "severity": 62.0},
            {"node_id": "NODE-04", "lat": 28.6160, "lng": 77.2110, "severity": 10.0} # Low stress (filtered)
        ]

        res = geospatial_service.cluster_hotspots(sample_nodes, eps_meters=25.0, min_samples=2)

        self.assertIn("hotspots", res)
        self.assertGreater(res["total_hotspots"], 0)
        self.assertGreater(res["total_affected_area_m2"], 0.0)

if __name__ == "__main__":
    unittest.main()
