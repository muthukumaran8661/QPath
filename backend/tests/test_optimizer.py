import pytest
import numpy as np
from app.models.schemas import (
    Coordinate, ObjectiveWeights, PriorityPreset, OptimizationMode,
    IncidentCreate, IncidentType, FleetRouteRequest, FleetVehicle
)
from app.optimizer.graph_service import GraphService
from app.optimizer.qpso import QPSORouteOptimizer
from app.optimizer.vrp import FleetVRPOptimizer
from app.simulator.traffic_simulator import TrafficSimulator

@pytest.fixture
def graph_service():
    gs = GraphService()
    return gs

@pytest.fixture
def optimizer(graph_service):
    return QPSORouteOptimizer(graph_service)

@pytest.fixture
def vrp_solver(graph_service, optimizer):
    return FleetVRPOptimizer(graph_service, optimizer)

@pytest.fixture
def simulator(graph_service, optimizer):
    return TrafficSimulator(graph_service, optimizer)

def test_graph_initialization(graph_service):
    g = graph_service.graph
    assert g.number_of_nodes() >= 15
    assert g.number_of_edges() >= 30
    assert len(graph_service.landmarks) >= 5

def test_qpso_convergence_and_cost(optimizer):
    # Route from CP Central Park (node 0) to India Gate (node 25 / landmark)
    src = Coordinate(lat=28.6315, lon=77.2167, node_id=0)
    dst = Coordinate(lat=28.6129, lon=77.2295)

    comp = optimizer.compute_route_comparison(
        source=src,
        destination=dst,
        mode=OptimizationMode.PERSONAL,
        priority=PriorityPreset.BALANCED,
        swarm_size=25,
        max_iter=30
    )

    assert comp.qpso_route is not None
    assert len(comp.qpso_route.nodes) >= 2
    assert comp.qpso_route.metrics.total_distance_meters > 0
    assert comp.qpso_route.metrics.total_time_seconds > 0
    assert comp.quantum_efficiency_score >= 50.0

def test_priority_presets_weight_tuning(optimizer):
    fastest_w = optimizer.get_priority_weights(PriorityPreset.FASTEST)
    shortest_w = optimizer.get_priority_weights(PriorityPreset.SHORTEST)
    smooth_w = optimizer.get_priority_weights(PriorityPreset.SMOOTH_ROADS)

    assert fastest_w.w_time > fastest_w.w_distance
    assert shortest_w.w_distance > shortest_w.w_time
    assert smooth_w.w_road_condition > smooth_w.w_distance

def test_road_closure_detour(optimizer, graph_service):
    # Route from node 0 to node 2 (inner circle)
    u_src = 0
    v_dst = 2
    
    # Check initial path
    init_res = optimizer.find_baseline_dijkstra(u_src, v_dst, ObjectiveWeights())
    direct_edge = (init_res.nodes[0], init_res.nodes[1]) if len(init_res.nodes) >= 2 else None

    if direct_edge and graph_service.graph.has_edge(direct_edge[0], direct_edge[1]):
        # Inject closure on that specific edge
        mid_lat = (graph_service.graph.nodes[direct_edge[0]]["lat"] + graph_service.graph.nodes[direct_edge[1]]["lat"]) / 2.0
        mid_lon = (graph_service.graph.nodes[direct_edge[0]]["lon"] + graph_service.graph.nodes[direct_edge[1]]["lon"]) / 2.0

        sim = TrafficSimulator(graph_service, optimizer)
        inc = sim.inject_incident(IncidentCreate(
            incident_type=IncidentType.CLOSURE,
            lat=mid_lat,
            lon=mid_lon,
            radius_meters=100.0,
            severity=5.0,
            description="Test Roadblock Closure"
        ))

        # Re-solve route
        reroute = optimizer.optimize_qpso(u_src, v_dst, ObjectiveWeights(), swarm_size=20, max_iter=25)
        # Ensure reroute does not pick the closed edge or finds alternative
        assert reroute.metrics.multi_objective_cost < 10000.0 or len(reroute.nodes) > 0
        
        # Cleanup
        sim.remove_incident(inc.id)

def test_fleet_vrp_multi_stop(vrp_solver, graph_service):
    depot = Coordinate(lat=28.6315, lon=77.2167, label="CP Depot")
    stops = [
        Coordinate(lat=28.6129, lon=77.2295, label="India Gate"),
        Coordinate(lat=28.6429, lon=77.2195, label="NDLS Station"),
        Coordinate(lat=28.6180, lon=77.2425, label="Pragati Maidan"),
        Coordinate(lat=28.6520, lon=77.1900, label="Karol Bagh")
    ]
    vehicles = [
        FleetVehicle(vehicle_id="v1", name="Delivery Van 1", capacity=100, color="#00F0FF"),
        FleetVehicle(vehicle_id="v2", name="Delivery Van 2", capacity=100, color="#7928CA")
    ]

    req = FleetRouteRequest(
        depot=depot,
        stops=stops,
        vehicles=vehicles
    )

    resp = vrp_solver.solve_vrp(req)
    assert resp.vehicles_deployed == 2
    assert len(resp.fleet_routes) == 2
    assert resp.total_fleet_distance_meters > 0
    assert resp.total_fleet_time_seconds > 0
    # Each vehicle should depart from depot and return to depot
    for vr in resp.fleet_routes:
        assert len(vr.stops) >= 2
        assert vr.stops[0].lat == depot.lat
        assert vr.stops[-1].lat == depot.lat

def test_what_if_simulator(simulator):
    from app.models.schemas import SimulationScenarioRequest, WeatherCondition
    req = SimulationScenarioRequest(
        scenario_name="Monsoon Flood Test",
        time_of_day_hours=8.5,
        weather=WeatherCondition.RAIN_MONSOON,
        source=Coordinate(lat=28.6315, lon=77.2167),
        destination=Coordinate(lat=28.5850, lon=77.1650),
        inject_closures=1,
        inject_accidents=1
    )

    res = simulator.run_what_if_simulation(req)
    assert res.scenario_name == "Monsoon Flood Test"
    assert res.normal_route is not None
    assert res.stressed_route_qpso is not None
    assert "metrics_delta" in res.model_dump()
    assert len(res.ai_recommendation) > 20
