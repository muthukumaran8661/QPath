import uuid
from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import List, Dict, Any
from app.models.schemas import (
    RouteRequest, RouteResponse,
    FleetRouteRequest, FleetRouteResponse,
    SimulationScenarioRequest, SimulationScenarioResponse,
    IncidentCreate, Incident, MapLandmark
)
from app.optimizer.graph_service import graph_service, haversine_meters
from app.optimizer.qpso import qpso_optimizer
from app.optimizer.pan_india_router import pan_india_router
from app.optimizer.vrp import FleetVRPOptimizer
from app.simulator.traffic_simulator import TrafficSimulator

router = APIRouter()

vrp_optimizer = FleetVRPOptimizer(graph_service, qpso_optimizer)
traffic_simulator = TrafficSimulator(graph_service, qpso_optimizer)

@router.post("/route", response_model=RouteResponse, summary="Compute Quantum Multi-Objective Route")
async def compute_route(request: RouteRequest):
    src = request.source or request.origin
    dst = request.destination
    if not src or not dst:
        raise HTTPException(status_code=400, detail="Both origin/source and destination are required.")

    # Validation: Same location check
    src_lon = src.longitude
    dst_lon = dst.longitude
    dist_m = haversine_meters(src.lat, src_lon, dst.lat, dst_lon)
    if dist_m < 50.0:
        raise HTTPException(
            status_code=400,
            detail="Origin and destination cannot be the same location. Please choose distinct locations."
        )

    trip_id = request.trip_id or f"trip_{uuid.uuid4().hex[:8]}"

    try:
        comparison = pan_india_router.route(
            source=src,
            destination=dst,
            mode=request.mode,
            priority=request.priority,
            custom_weights=request.custom_weights,
            swarm_size=request.swarm_size,
            max_iter=request.max_iterations
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        # Fallback to internal synthetic graph optimizer if external routing encounters error
        try:
            comparison = qpso_optimizer.compute_route_comparison(
                source=src,
                destination=dst,
                mode=request.mode,
                priority=request.priority,
                custom_weights=request.custom_weights,
                swarm_size=request.swarm_size,
                max_iter=request.max_iterations
            )
        except Exception:
            raise HTTPException(
                status_code=502,
                detail=f"Routing service temporarily unavailable. Please retry. Error: {str(e)}"
            )

    weights = qpso_optimizer.get_priority_weights(request.priority, request.custom_weights)
    
    return RouteResponse(
        trip_id=trip_id,
        mode=request.mode,
        priority=request.priority,
        weights=weights,
        comparison=comparison
    )

@router.post("/fleet/route", response_model=FleetRouteResponse, summary="Solve Fleet Multi-Stop VRP")
async def compute_fleet_route(request: FleetRouteRequest):
    return vrp_optimizer.solve_vrp(request)

@router.post("/simulate", response_model=SimulationScenarioResponse, summary="What-If Traffic Scenario Simulator")
async def simulate_scenario(request: SimulationScenarioRequest):
    return traffic_simulator.run_what_if_simulation(request)

@router.post("/incident", response_model=Incident, summary="Inject Live Traffic Incident")
async def inject_incident(request: IncidentCreate):
    return traffic_simulator.inject_incident(request)

@router.get("/incidents", response_model=List[Incident], summary="List Active Traffic Incidents")
async def list_incidents():
    return traffic_simulator.get_all_incidents()

@router.delete("/incident/{incident_id}", summary="Remove Incident")
async def delete_incident(incident_id: str):
    removed = traffic_simulator.remove_incident(incident_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Incident not found")
    return {"status": "success", "message": f"Incident {incident_id} resolved"}

@router.post("/reset", summary="Reset All Incidents to Base State")
async def reset_graph():
    traffic_simulator.reset_all()
    return {"status": "success", "message": "Graph restored to pristine base state"}

@router.get("/landmarks", response_model=List[MapLandmark], summary="Get Preset Urban Landmarks")
async def get_landmarks():
    return graph_service.landmarks

@router.get("/city/graph-info", summary="Get Road Graph Statistics and Topology Meta")
async def get_graph_info():
    g = graph_service.graph
    bbox = graph_service.get_bounding_box()
    return {
        "city": "New Delhi Central Hub",
        "nodes_count": g.number_of_nodes(),
        "edges_count": g.number_of_edges(),
        "bounding_box": bbox,
        "active_incidents_count": len(traffic_simulator.get_all_incidents()),
        "landmarks_count": len(graph_service.landmarks)
    }
