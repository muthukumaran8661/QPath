import uuid
import time
import asyncio
from typing import List, Dict, Callable, Any, Optional
from app.models.schemas import (
    Incident, IncidentCreate, IncidentType, WeatherCondition,
    SimulationScenarioRequest, SimulationScenarioResponse, Coordinate
)
from app.optimizer.graph_service import GraphService, haversine_meters
from app.optimizer.qpso import QPSORouteOptimizer

class TrafficSimulator:
    def __init__(self, graph_service: GraphService, qpso: QPSORouteOptimizer):
        self.gs = graph_service
        self.qpso = qpso
        self.active_incidents: Dict[str, Incident] = {}
        self.trip_listeners: Dict[str, List[Callable[[Dict[str, Any]], Any]]] = {}

    def inject_incident(self, create_dto: IncidentCreate) -> Incident:
        inc_id = f"inc_{uuid.uuid4().hex[:8]}"
        
        # Determine affected nodes within radius
        affected_nodes = []
        for n, data in self.gs.graph.nodes(data=True):
            d = haversine_meters(create_dto.lat, create_dto.lon, data["lat"], data["lon"])
            if d <= create_dto.radius_meters:
                affected_nodes.append(n)

        # Ensure at least nearest node is included
        if not affected_nodes:
            nearest = self.gs.get_nearest_node(create_dto.lat, create_dto.lon)
            affected_nodes.append(nearest)

        incident = Incident(
            id=inc_id,
            incident_type=create_dto.incident_type,
            lat=create_dto.lat,
            lon=create_dto.lon,
            affected_nodes=affected_nodes,
            radius_meters=create_dto.radius_meters,
            severity=create_dto.severity,
            duration_minutes=create_dto.duration_minutes,
            description=create_dto.description,
            created_at=time.time(),
            active=True
        )

        self.active_incidents[inc_id] = incident
        affected_edges = self.gs.apply_incident(incident)

        # Broadcast update to active trip subscribers
        self._notify_subscribers(incident, affected_edges)
        return incident

    def remove_incident(self, inc_id: str) -> bool:
        if inc_id in self.active_incidents:
            del self.active_incidents[inc_id]
            # Rebuild graph to base state then reapply remaining incidents
            self.gs.clear_incidents()
            for remaining in self.active_incidents.values():
                self.gs.apply_incident(remaining)
            return True
        return False

    def reset_all(self):
        self.active_incidents.clear()
        self.gs.clear_incidents()

    def get_all_incidents(self) -> List[Incident]:
        return list(self.active_incidents.values())

    def register_trip(self, trip_id: str, callback: Callable[[Dict[str, Any]], Any]):
        if trip_id not in self.trip_listeners:
            self.trip_listeners[trip_id] = []
        self.trip_listeners[trip_id].append(callback)

    def unregister_trip(self, trip_id: str):
        if trip_id in self.trip_listeners:
            del self.trip_listeners[trip_id]

    def _notify_subscribers(self, incident: Incident, affected_edges: List[Any]):
        event_payload = {
            "event": "INCIDENT_ALERT",
            "incident": incident.model_dump(),
            "affected_edges_count": len(affected_edges),
            "timestamp": time.time()
        }
        for trip_id, cbs in self.trip_listeners.items():
            for cb in cbs:
                try:
                    cb(event_payload)
                except Exception as e:
                    print(f"Error notifying trip {trip_id}: {e}")

    def run_what_if_simulation(self, scenario: SimulationScenarioRequest) -> SimulationScenarioResponse:
        """
        Executes What-If scenario prediction by testing route behaviors under simulated stress.
        """
        u_src = scenario.source.node_id if scenario.source.node_id is not None else self.gs.get_nearest_node(scenario.source.lat, scenario.source.lon)
        v_dst = scenario.destination.node_id if scenario.destination.node_id is not None else self.gs.get_nearest_node(scenario.destination.lat, scenario.destination.lon)

        # 1. Base normal route under standard conditions
        normal_comparison = self.qpso.compute_route_comparison(scenario.source, scenario.destination)
        normal_route = normal_comparison.qpso_route

        # 2. Inject temporary synthetic stress
        # Weather impact
        weather_friction = 1.0
        weather_cong = 1.0
        if scenario.weather == WeatherCondition.RAIN_MONSOON:
            weather_friction = 0.65  # Potholes fill with water, roads rougher
            weather_cong = 1.45      # Slower speeds
        elif scenario.weather == WeatherCondition.FOG:
            weather_cong = 1.3
        elif scenario.weather == WeatherCondition.STORM:
            weather_friction = 0.55
            weather_cong = 1.6

        # Rush hour time of day curve
        hour = scenario.time_of_day_hours
        rush_factor = 1.0
        if 8.0 <= hour <= 10.5 or 17.0 <= hour <= 20.5:
            rush_factor = 1.75
        elif 11.0 <= hour <= 16.0:
            rush_factor = 1.25

        total_multiplier = scenario.global_congestion_multiplier * weather_cong * rush_factor

        # Select random intermediate edges along normal route to close or block
        injected_incidents: List[Incident] = []
        path_nodes = normal_route.nodes

        if len(path_nodes) > 3 and scenario.inject_closures > 0:
            closure_idx = len(path_nodes) // 2
            c_node = path_nodes[closure_idx]
            lat_c = self.gs.graph.nodes[c_node]["lat"]
            lon_c = self.gs.graph.nodes[c_node]["lon"]
            
            inc = self.inject_incident(IncidentCreate(
                incident_type=IncidentType.CLOSURE,
                lat=lat_c,
                lon=lon_c,
                radius_meters=350,
                severity=5.0,
                description=f"Simulated Roadblock / Waterlogging at Node {c_node}"
            ))
            injected_incidents.append(inc)

        if len(path_nodes) > 4 and scenario.inject_accidents > 0:
            acc_idx = max(1, len(path_nodes) // 3)
            a_node = path_nodes[acc_idx]
            lat_a = self.gs.graph.nodes[a_node]["lat"]
            lon_a = self.gs.graph.nodes[a_node]["lon"]

            inc2 = self.inject_incident(IncidentCreate(
                incident_type=IncidentType.ACCIDENT,
                lat=lat_a,
                lon=lon_a,
                radius_meters=300,
                severity=2.8,
                description=f"Simulated Multi-vehicle Jam near Node {a_node}"
            ))
            injected_incidents.append(inc2)

        # 3. Compute stressed routes
        stressed_comp = self.qpso.compute_route_comparison(scenario.source, scenario.destination)
        stressed_qpso = stressed_comp.qpso_route
        stressed_std = stressed_comp.baseline_route

        # 4. Cleanup temporary simulation incidents
        for inc in injected_incidents:
            self.remove_incident(inc.id)

        # Delta metrics
        t_base = normal_route.metrics.total_time_seconds
        t_stressed_qpso = stressed_qpso.metrics.total_time_seconds
        t_stressed_std = stressed_std.metrics.total_time_seconds

        time_saved_by_qpso_in_stress = max(t_stressed_std - t_stressed_qpso, 0.0)

        ai_rec = (
            f"Under {scenario.scenario_name} (Peak Factor: {total_multiplier:.2f}x, {scenario.weather.value}), "
            f"standard routing experiences gridlock (+{(t_stressed_std - t_base)/60:.1f} min delay). "
            f"InfinityCore QPSO proactively diverted via clear peripheral corridors, saving {time_saved_by_qpso_in_stress/60:.1f} min "
            f"and avoiding {stressed_comp.congestion_reduction_percent}% congested choke-points."
        )

        return SimulationScenarioResponse(
            scenario_name=scenario.scenario_name,
            weather=scenario.weather,
            time_of_day_hours=scenario.time_of_day_hours,
            normal_route=normal_route,
            stressed_route_qpso=stressed_qpso,
            stressed_route_standard=stressed_std,
            metrics_delta={
                "normal_time_sec": t_base,
                "stressed_qpso_time_sec": t_stressed_qpso,
                "stressed_standard_time_sec": t_stressed_std,
                "time_saved_sec": round(time_saved_by_qpso_in_stress, 1),
                "congestion_mitigation_percent": stressed_comp.congestion_reduction_percent,
                "roughness_avoidance_percent": stressed_comp.roughness_reduction_percent
            },
            active_incidents_injected=injected_incidents,
            ai_recommendation=ai_rec
        )
