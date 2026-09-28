import math
import networkx as nx
from typing import List, Dict, Tuple, Optional, Any
from app.models.schemas import Coordinate, RouteSegment, MapLandmark, Incident, IncidentType
from app.config import settings

def haversine_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371000.0  # Earth radius in meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c

class GraphService:
    def __init__(self):
        self.graph = nx.DiGraph()
        self.landmarks: List[MapLandmark] = []
        self.incidents: Dict[str, Incident] = {}
        self.center_lat = settings.DEFAULT_LAT
        self.center_lon = settings.DEFAULT_LON
        self._initialize_graph()

    def _initialize_graph(self):
        """
        Builds a high-fidelity realistic urban road graph modeled after New Delhi Central Hub (Connaught Place,
        India Gate, Ring Road, Janpath, Barakhamba, Airport Expressway, and tech corridors).
        """
        self.graph.clear()
        
        # Center: Connaught Place (28.6315, 77.2167)
        c_lat = self.center_lat
        c_lon = self.center_lon
        
        # 1. Radial and Concentric Nodes for Connaught Place Core
        # Inner Circle (Radius ~250m, 8 radials)
        # Middle Circle (Radius ~500m)
        # Outer Circle (Radius ~800m)
        # Arterial spokes extending out 2-4 km
        
        node_id = 1
        inner_nodes = []
        middle_nodes = []
        outer_nodes = []
        
        spoke_names = [
            "Radial Janpath (South)", "Radial Barakhamba (East)", 
            "Radial Kasturba Gandhi (South-East)", "Radial Parliament St (South-West)",
            "Radial Baba Kharak Singh (West)", "Radial Chelmsford (North-West)",
            "Radial Minto Rd (North)", "Radial State Entry (North-East)"
        ]
        
        # Radial angles (8 compass sectors)
        angles = [3*math.pi/2, 0, 7*math.pi/4, 5*math.pi/4, math.pi, 3*math.pi/4, math.pi/2, math.pi/4]
        
        # Central Hub Center Plaza
        self.graph.add_node(0, lat=c_lat, lon=c_lon, label="CP Central Park", is_junction=True)
        
        # Create Inner Ring (radius ~0.0022 deg ≈ 240m)
        for i, ang in enumerate(angles):
            nid = node_id
            node_id += 1
            lat = c_lat + 0.0022 * math.sin(ang)
            lon = c_lon + 0.0024 * math.cos(ang)
            self.graph.add_node(nid, lat=lat, lon=lon, label=f"Inner Circle - Block {chr(65+i)}", is_junction=True)
            inner_nodes.append(nid)
            
        # Create Middle Ring (radius ~0.0045 deg ≈ 500m)
        for i, ang in enumerate(angles):
            nid = node_id
            node_id += 1
            lat = c_lat + 0.0045 * math.sin(ang)
            lon = c_lon + 0.0049 * math.cos(ang)
            self.graph.add_node(nid, lat=lat, lon=lon, label=f"Middle Circle - Radial {i+1}", is_junction=True)
            middle_nodes.append(nid)
            
        # Create Outer Ring / Connaught Circus (radius ~0.0075 deg ≈ 830m)
        for i, ang in enumerate(angles):
            nid = node_id
            node_id += 1
            lat = c_lat + 0.0075 * math.sin(ang)
            lon = c_lon + 0.0082 * math.cos(ang)
            self.graph.add_node(nid, lat=lat, lon=lon, label=f"Outer Connaught Circus {i+1}", is_junction=True)
            outer_nodes.append(nid)

        # Connect concentric circles
        # Inner Ring circular bidirectional edges
        for i in range(len(inner_nodes)):
            u = inner_nodes[i]
            v = inner_nodes[(i + 1) % len(inner_nodes)]
            self._add_bidirectional_road(u, v, speed_kph=35, name="Inner Circle Road", base_congestion=1.2, road_condition=0.92)

        # Middle Ring circular
        for i in range(len(middle_nodes)):
            u = middle_nodes[i]
            v = middle_nodes[(i + 1) % len(middle_nodes)]
            self._add_bidirectional_road(u, v, speed_kph=40, name="Middle Circle Avenue", base_congestion=1.4, road_condition=0.88)

        # Outer Ring circular
        for i in range(len(outer_nodes)):
            u = outer_nodes[i]
            v = outer_nodes[(i + 1) % len(outer_nodes)]
            self._add_bidirectional_road(u, v, speed_kph=45, name="Outer Connaught Circus", base_congestion=1.6, road_condition=0.85)

        # Connect Inner -> Middle -> Outer Radials
        for i in range(8):
            u_in = inner_nodes[i]
            u_mid = middle_nodes[i]
            u_out = outer_nodes[i]
            s_name = spoke_names[i]
            self._add_bidirectional_road(0, u_in, speed_kph=25, name="Central Park Access", base_congestion=1.1, road_condition=0.95)
            self._add_bidirectional_road(u_in, u_mid, speed_kph=40, name=s_name, base_congestion=1.5, road_condition=0.90)
            self._add_bidirectional_road(u_mid, u_out, speed_kph=45, name=s_name, base_congestion=1.7, road_condition=0.88)

        # 2. Major Urban Arteries & Outer Landmarks
        # Key Landmarks with coordinates
        landmarks_meta = [
            {"id": "cp_park", "name": "Connaught Place Central Hub", "category": "City Center", "lat": c_lat, "lon": c_lon, "node": 0},
            {"id": "india_gate", "name": "India Gate Memorial & Boulevard", "category": "Monument", "lat": 28.6129, "lon": 77.2295},
            {"id": "ndls_station", "name": "New Delhi Central Railway Station", "category": "Transit Hub", "lat": 28.6429, "lon": 77.2195},
            {"id": "pragati_maidan", "name": "Bharat Mandapam (Pragati Maidan)", "category": "Convention Center", "lat": 28.6180, "lon": 77.2425},
            {"id": "aiims_hospital", "name": "AIIMS Apex Trauma & Hospital", "category": "Emergency/Hospital", "lat": 28.5672, "lon": 77.2100},
            {"id": "cyber_tech_park", "name": "Quantum Tech City & IT Corridor", "category": "Business Park", "lat": 28.5850, "lon": 77.1650},
            {"id": "aerocity_hub", "name": "Indira Gandhi International Airport Hub", "category": "Airport / Logistics", "lat": 28.5562, "lon": 77.1000},
            {"id": "karol_bagh", "name": "Karol Bagh Commercial Hub", "category": "Market / Logistics", "lat": 28.6520, "lon": 77.1900},
            {"id": "ring_road_south", "name": "South Extension Ring Road", "category": "Arterial Highway", "lat": 28.5720, "lon": 77.2250},
            {"id": "delhi_gate", "name": "Delhi Gate Heritage Crossing", "category": "Junction", "lat": 28.6405, "lon": 77.2405},
        ]

        landmark_node_map = {0: 0}

        # Add Landmark nodes and intermediate grid junctions
        for lm in landmarks_meta:
            if "node" in lm:
                continue
            nid = node_id
            node_id += 1
            self.graph.add_node(nid, lat=lm["lat"], lon=lm["lon"], label=lm["name"], is_junction=True)
            landmark_node_map[lm["id"]] = nid

        # Grid Arteries & Interconnections
        # South Axis (Janpath -> Rajpath / India Gate -> AIIMS)
        ig_node = landmark_node_map["india_gate"]
        ndls_node = landmark_node_map["ndls_station"]
        pm_node = landmark_node_map["pragati_maidan"]
        aiims_node = landmark_node_map["aiims_hospital"]
        tech_node = landmark_node_map["cyber_tech_park"]
        aero_node = landmark_node_map["aerocity_hub"]
        kb_node = landmark_node_map["karol_bagh"]
        rr_node = landmark_node_map["ring_road_south"]
        dg_node = landmark_node_map["delhi_gate"]

        # Janpath Corridor: Outer Ring South (outer_nodes[0]) -> India Gate
        self._add_bidirectional_road(outer_nodes[0], ig_node, speed_kph=50, name="Janpath Boulevard", base_congestion=1.6, road_condition=0.92)
        # Barakhamba Corridor: Outer Ring East (outer_nodes[1]) -> Pragati Maidan
        self._add_bidirectional_road(outer_nodes[1], pm_node, speed_kph=55, name="Barakhamba Flyover Rd", base_congestion=1.5, road_condition=0.90)
        # Chelmsford North: Outer Ring NW (outer_nodes[5]) -> NDLS Station
        self._add_bidirectional_road(outer_nodes[5], ndls_node, speed_kph=40, name="Chelmsford Station Rd", base_congestion=2.2, road_condition=0.72)
        # Minto Rd: Outer Ring North (outer_nodes[6]) -> NDLS & Delhi Gate
        self._add_bidirectional_road(outer_nodes[6], ndls_node, speed_kph=35, name="Minto Underpass", base_congestion=2.5, road_condition=0.65)
        self._add_bidirectional_road(outer_nodes[6], dg_node, speed_kph=45, name="Deen Dayal Upadhyaya Marg", base_congestion=1.8, road_condition=0.82)
        # Parliament St / Baba Kharak Singh: Outer Ring SW (outer_nodes[3], outer_nodes[4]) -> Karol Bagh & Tech Corridor
        self._add_bidirectional_road(outer_nodes[4], kb_node, speed_kph=45, name="Pusa Road Link", base_congestion=1.9, road_condition=0.78)
        self._add_bidirectional_road(outer_nodes[3], tech_node, speed_kph=60, name="Shanti Path Diplomatic Expressway", base_congestion=1.1, road_condition=0.98)

        # Cross connections & bypasses
        self._add_bidirectional_road(ig_node, pm_node, speed_kph=55, name="Bhairon Marg", base_congestion=1.4, road_condition=0.90)
        self._add_bidirectional_road(ig_node, rr_node, speed_kph=55, name="Lodi Road Corridor", base_congestion=1.3, road_condition=0.94)
        self._add_bidirectional_road(rr_node, aiims_node, speed_kph=60, name="Mahatma Gandhi Ring Road", base_congestion=2.1, road_condition=0.88)
        self._add_bidirectional_road(aiims_node, tech_node, speed_kph=65, name="Vasant Kunj Expressway", base_congestion=1.2, road_condition=0.95)
        self._add_bidirectional_road(tech_node, aero_node, speed_kph=80, name="Aerocity Rapid Freeway", base_congestion=1.1, road_condition=0.99)
        self._add_bidirectional_road(kb_node, ndls_node, speed_kph=40, name="Desh Bandhu Gupta Road", base_congestion=2.4, road_condition=0.68)
        self._add_bidirectional_road(dg_node, pm_node, speed_kph=60, name="Mathura Road Expressway", base_congestion=1.7, road_condition=0.86)
        self._add_bidirectional_road(kb_node, tech_node, speed_kph=50, name="Ridge Road Bypass", base_congestion=1.2, road_condition=0.91)

        # Add 12 intermediate local grid junction nodes for dense alternative route paths
        extra_grid = [
            (c_lat + 0.012, c_lon - 0.010, "Patel Nagar Junction", 45, 1.4, 0.82),
            (c_lat + 0.015, c_lon + 0.012, "Civil Lines Avenue", 50, 1.2, 0.90),
            (c_lat - 0.014, c_lon + 0.016, "Khan Market Lane", 35, 1.8, 0.85),
            (c_lat - 0.018, c_lon - 0.014, "Chanakyapuri Green Avenue", 55, 1.0, 0.98),
            (c_lat - 0.025, c_lon + 0.005, "Jor Bagh Heritage Road", 40, 1.3, 0.92),
            (c_lat - 0.035, c_lon - 0.020, "Munirka Flyover Link", 60, 1.9, 0.84),
            (c_lat - 0.040, c_lon - 0.045, "Mahipalpur Bypass", 50, 2.3, 0.70),
            (c_lat + 0.008, c_lon + 0.028, "ITO Bridge & Vikas Marg", 55, 2.6, 0.75),
        ]

        grid_node_ids = []
        for lat, lon, label, spd, cong, cond in extra_grid:
            nid = node_id
            node_id += 1
            self.graph.add_node(nid, lat=lat, lon=lon, label=label, is_junction=True)
            grid_node_ids.append((nid, spd, cong, cond))

        # Interlink grid nodes with nearest landmark & outer ring nodes
        self._add_bidirectional_road(grid_node_ids[0][0], kb_node, speed_kph=45, name="Patel Link Rd", base_congestion=1.4, road_condition=0.82)
        self._add_bidirectional_road(grid_node_ids[0][0], outer_nodes[4], speed_kph=40, name="Link Rd Central", base_congestion=1.5, road_condition=0.85)
        self._add_bidirectional_road(grid_node_ids[1][0], ndls_node, speed_kph=50, name="Civil Lines Expressway", base_congestion=1.2, road_condition=0.90)
        self._add_bidirectional_road(grid_node_ids[1][0], dg_node, speed_kph=45, name="Ring Rd North", base_congestion=1.3, road_condition=0.88)
        self._add_bidirectional_road(grid_node_ids[2][0], ig_node, speed_kph=40, name="Pandara Road", base_congestion=1.7, road_condition=0.86)
        self._add_bidirectional_road(grid_node_ids[2][0], outer_nodes[2], speed_kph=45, name="KG Marg Extension", base_congestion=1.6, road_condition=0.90)
        self._add_bidirectional_road(grid_node_ids[3][0], outer_nodes[3], speed_kph=55, name="Panchsheel Marg", base_congestion=1.0, road_condition=0.98)
        self._add_bidirectional_road(grid_node_ids[3][0], tech_node, speed_kph=60, name="Nyaya Marg Corridor", base_congestion=1.1, road_condition=0.96)
        self._add_bidirectional_road(grid_node_ids[4][0], ig_node, speed_kph=45, name="Aurobindo Marg North", base_congestion=1.8, road_condition=0.89)
        self._add_bidirectional_road(grid_node_ids[4][0], rr_node, speed_kph=50, name="Aurobindo Marg South", base_congestion=2.0, road_condition=0.87)
        self._add_bidirectional_road(grid_node_ids[5][0], aiims_node, speed_kph=60, name="Africa Avenue", base_congestion=1.5, road_condition=0.91)
        self._add_bidirectional_road(grid_node_ids[5][0], tech_node, speed_kph=60, name="Nelson Mandela Marg", base_congestion=1.3, road_condition=0.93)
        self._add_bidirectional_road(grid_node_ids[6][0], tech_node, speed_kph=55, name="Vasant Kunj Arterial", base_congestion=1.8, road_condition=0.80)
        self._add_bidirectional_road(grid_node_ids[6][0], aero_node, speed_kph=70, name="Airport Northern Access", base_congestion=1.2, road_condition=0.95)
        self._add_bidirectional_road(grid_node_ids[7][0], dg_node, speed_kph=50, name="ITO Flyover East", base_congestion=2.5, road_condition=0.76)
        self._add_bidirectional_road(grid_node_ids[7][0], pm_node, speed_kph=55, name="Ring Rd Vikas Corridor", base_congestion=2.2, road_condition=0.80)

        # Store Landmarks
        self.landmarks = []
        for lm in landmarks_meta:
            nid = lm["node"] if "node" in lm else landmark_node_map[lm["id"]]
            self.landmarks.append(MapLandmark(
                id=lm["id"],
                name=lm["name"],
                category=lm["category"],
                lat=lm["lat"],
                lon=lm["lon"],
                node_id=nid
            ))

    def _add_bidirectional_road(self, u: int, v: int, speed_kph: float, name: str, base_congestion: float, road_condition: float):
        u_lat, u_lon = self.graph.nodes[u]["lat"], self.graph.nodes[u]["lon"]
        v_lat, v_lon = self.graph.nodes[v]["lat"], self.graph.nodes[v]["lon"]
        dist = haversine_meters(u_lat, u_lon, v_lat, v_lon)
        # Minimum distance safeguard
        dist = max(dist, 50.0)
        speed_mps = max(speed_kph * 1000.0 / 3600.0, 2.0)
        base_time = dist / speed_mps

        # Intermediate geometry (interpolated points for smooth map polylines)
        geom_forward = [[u_lat, u_lon], [(u_lat + v_lat) / 2.0, (u_lon + v_lon) / 2.0], [v_lat, v_lon]]
        geom_backward = [[v_lat, v_lon], [(u_lat + v_lat) / 2.0, (u_lon + v_lon) / 2.0], [u_lat, u_lon]]

        edge_data_f = {
            "length_meters": dist,
            "speed_kph": speed_kph,
            "base_time_seconds": base_time,
            "congestion_factor": base_congestion,
            "road_condition_score": road_condition,
            "is_closed": False,
            "name": name,
            "geometry": geom_forward
        }
        edge_data_b = {
            "length_meters": dist,
            "speed_kph": speed_kph,
            "base_time_seconds": base_time,
            "congestion_factor": base_congestion,
            "road_condition_score": road_condition,
            "is_closed": False,
            "name": name,
            "geometry": geom_backward
        }
        self.graph.add_edge(u, v, **edge_data_f)
        self.graph.add_edge(v, u, **edge_data_b)

    def get_nearest_node(self, lat: float, lon: float) -> int:
        best_node = None
        min_dist = float("inf")
        for n, data in self.graph.nodes(data=True):
            d = haversine_meters(lat, lon, data["lat"], data["lon"])
            if d < min_dist:
                min_dist = d
                best_node = n
        return best_node if best_node is not None else 0

    def apply_incident(self, incident: Incident) -> List[Tuple[int, int]]:
        """
        Applies incident effect to edges within incident radius or connected to incident coordinates.
        Returns list of affected edges (u, v).
        """
        self.incidents[incident.id] = incident
        affected_edges = []
        
        for u, v, data in self.graph.edges(data=True):
            u_lat, u_lon = self.graph.nodes[u]["lat"], self.graph.nodes[u]["lon"]
            v_lat, v_lon = self.graph.nodes[v]["lat"], self.graph.nodes[v]["lon"]
            mid_lat, mid_lon = (u_lat + v_lat) / 2.0, (u_lon + v_lon) / 2.0
            
            dist_u = haversine_meters(incident.lat, incident.lon, u_lat, u_lon)
            dist_mid = haversine_meters(incident.lat, incident.lon, mid_lat, mid_lon)
            dist_v = haversine_meters(incident.lat, incident.lon, v_lat, v_lon)
            
            min_dist = min(dist_u, dist_mid, dist_v)
            if min_dist <= incident.radius_meters or (u in incident.affected_nodes or v in incident.affected_nodes):
                affected_edges.append((u, v))
                if incident.incident_type == IncidentType.CLOSURE:
                    data["is_closed"] = True
                elif incident.incident_type == IncidentType.ACCIDENT:
                    data["congestion_factor"] = min(data["congestion_factor"] * incident.severity, 5.0)
                    data["road_condition_score"] = max(data["road_condition_score"] * 0.5, 0.1)
                elif incident.incident_type == IncidentType.CONGESTION:
                    data["congestion_factor"] = min(data["congestion_factor"] * incident.severity, 5.0)
                elif incident.incident_type == IncidentType.POTHOLE_HAZARD:
                    data["road_condition_score"] = max(data["road_condition_score"] * 0.4, 0.1)
                    data["congestion_factor"] = min(data["congestion_factor"] * 1.3, 4.0)

        return affected_edges

    def clear_incidents(self):
        self.incidents.clear()
        self._initialize_graph()

    def get_bounding_box(self) -> Dict[str, float]:
        lats = [d["lat"] for _, d in self.graph.nodes(data=True)]
        lons = [d["lon"] for _, d in self.graph.nodes(data=True)]
        return {
            "min_lat": min(lats),
            "max_lat": max(lats),
            "min_lon": min(lons),
            "max_lon": max(lons),
            "center_lat": self.center_lat,
            "center_lon": self.center_lon
        }

graph_service = GraphService()
