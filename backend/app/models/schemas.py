from pydantic import BaseModel, Field, model_validator
from typing import List, Optional, Dict, Any, Union
from enum import Enum
import time

class OptimizationMode(str, Enum):
    PERSONAL = "personal"
    FLEET = "fleet"
    EMERGENCY = "emergency"

class PriorityPreset(str, Enum):
    FASTEST = "fastest"
    SHORTEST = "shortest"
    LESS_CONGESTED = "less_congested"
    SMOOTH_ROADS = "smooth_roads"
    BALANCED = "balanced"

class IncidentType(str, Enum):
    CONGESTION = "congestion"
    ACCIDENT = "accident"
    CLOSURE = "closure"
    POTHOLE_HAZARD = "pothole_hazard"

class WeatherCondition(str, Enum):
    CLEAR = "clear"
    RAIN_MONSOON = "rain_monsoon"
    FOG = "fog"
    STORM = "storm"

class ObjectiveWeights(BaseModel):
    w_time: float = Field(default=0.40, ge=0.0, le=1.0, description="Weight for Travel Time")
    w_distance: float = Field(default=0.20, ge=0.0, le=1.0, description="Weight for Physical Distance")
    w_congestion: float = Field(default=0.25, ge=0.0, le=1.0, description="Weight for Congestion Avoidance")
    w_road_condition: float = Field(default=0.15, ge=0.0, le=1.0, description="Weight for Road Smoothness/Condition")

    def normalized(self) -> "ObjectiveWeights":
        total = self.w_time + self.w_distance + self.w_congestion + self.w_road_condition
        if total == 0:
            return ObjectiveWeights(w_time=0.4, w_distance=0.2, w_congestion=0.25, w_road_condition=0.15)
        return ObjectiveWeights(
            w_time=self.w_time / total,
            w_distance=self.w_distance / total,
            w_congestion=self.w_congestion / total,
            w_road_condition=self.w_road_condition / total
        )

class Coordinate(BaseModel):
    lat: float
    lon: Optional[float] = None
    lng: Optional[float] = None
    label: Optional[str] = None
    node_id: Optional[int] = None

    @model_validator(mode="before")
    @classmethod
    def check_coordinates(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "lng" in data and "lon" not in data:
                data["lon"] = data["lng"]
            elif "lon" in data and "lng" not in data:
                data["lng"] = data["lon"]
        return data

    @property
    def longitude(self) -> float:
        return self.lon if self.lon is not None else (self.lng or 0.0)

class RouteSegment(BaseModel):
    u: int = 0
    v: int = 0
    distance_meters: float
    travel_time_seconds: float
    speed_kph: float = 40.0
    congestion_factor: float = 1.0
    road_condition: float = 0.9
    is_closed: bool = False
    coordinates: List[List[float]] = []  # [[lat, lon], ...]
    instruction: Optional[str] = None
    road_name: Optional[str] = None

class RouteMetrics(BaseModel):
    total_time_seconds: float
    total_distance_meters: float
    total_time_formatted: str
    total_distance_formatted: str
    avg_congestion_factor: float
    avg_road_condition_score: float
    carbon_emission_kg: float
    multi_objective_cost: float

class PathResult(BaseModel):
    nodes: List[int] = []
    coordinates: List[List[float]]  # [[lat, lon], ...]
    segments: List[RouteSegment] = []
    metrics: RouteMetrics

class RouteComparison(BaseModel):
    qpso_route: PathResult
    baseline_route: PathResult
    alternative_routes: List[PathResult] = []
    time_saved_seconds: float
    time_saved_percent: float
    congestion_reduction_percent: float
    roughness_reduction_percent: float
    quantum_efficiency_score: float
    algorithm_summary: Dict[str, Any]

class RouteRequest(BaseModel):
    source: Optional[Coordinate] = None
    origin: Optional[Coordinate] = None
    destination: Coordinate
    mode: OptimizationMode = OptimizationMode.PERSONAL
    priority: PriorityPreset = PriorityPreset.BALANCED
    custom_weights: Optional[ObjectiveWeights] = None
    trip_id: Optional[str] = None
    swarm_size: int = 35
    max_iterations: int = 45

    @model_validator(mode="before")
    @classmethod
    def check_origin_source(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Map origin to source if source missing
            if "origin" in data and "source" not in data:
                data["source"] = data["origin"]
            elif "source" in data and "origin" not in data:
                data["origin"] = data["source"]
            # Handle string priority like "Smooth Road", "Fastest", etc.
            if "priority" in data and isinstance(data["priority"], str):
                p_str = data["priority"].strip().lower().replace(" ", "_")
                if "smooth" in p_str:
                    data["priority"] = PriorityPreset.SMOOTH_ROADS
                elif "fast" in p_str:
                    data["priority"] = PriorityPreset.FASTEST
                elif "short" in p_str:
                    data["priority"] = PriorityPreset.SHORTEST
                elif "congest" in p_str:
                    data["priority"] = PriorityPreset.LESS_CONGESTED
                else:
                    data["priority"] = PriorityPreset.BALANCED
        return data

class RouteResponse(BaseModel):
    trip_id: str
    mode: OptimizationMode
    priority: PriorityPreset
    weights: ObjectiveWeights
    comparison: RouteComparison
    timestamp: float = Field(default_factory=time.time)

# Fleet VRP Models
class FleetVehicle(BaseModel):
    vehicle_id: str
    name: str
    capacity: int = 100
    color: str = "#00F0FF"

class FleetRouteRequest(BaseModel):
    depot: Coordinate
    stops: List[Coordinate]
    vehicles: List[FleetVehicle]
    weights: Optional[ObjectiveWeights] = None
    mode: OptimizationMode = OptimizationMode.FLEET

class VehicleRoute(BaseModel):
    vehicle_id: str
    vehicle_name: str
    color: str
    stops: List[Coordinate]
    path: PathResult
    total_time_formatted: str
    total_distance_formatted: str
    assigned_capacity: int

class FleetRouteResponse(BaseModel):
    fleet_routes: List[VehicleRoute]
    total_fleet_time_seconds: float
    total_fleet_distance_meters: float
    total_fleet_time_formatted: str
    total_fleet_distance_formatted: str
    total_fuel_liters: float
    total_carbon_kg: float
    vehicles_deployed: int

# Incident Models
class IncidentCreate(BaseModel):
    incident_type: IncidentType
    lat: float
    lon: float
    radius_meters: float = 300.0
    severity: float = Field(default=2.5, ge=1.0, le=5.0, description="Multiplier for congestion or closure")
    duration_minutes: int = 30
    description: str = "Simulated Incident"

class Incident(BaseModel):
    id: str
    incident_type: IncidentType
    lat: float
    lon: float
    affected_nodes: List[int]
    radius_meters: float
    severity: float
    duration_minutes: int
    description: str
    created_at: float
    active: bool = True

# What-If Simulation
class SimulationScenarioRequest(BaseModel):
    scenario_name: str = "Morning Monsoon Rush Hour"
    time_of_day_hours: float = 8.5  # 8:30 AM
    weather: WeatherCondition = WeatherCondition.RAIN_MONSOON
    source: Coordinate
    destination: Coordinate
    inject_closures: int = 2
    inject_accidents: int = 2
    global_congestion_multiplier: float = 1.8

class SimulationScenarioResponse(BaseModel):
    scenario_name: str
    weather: WeatherCondition
    time_of_day_hours: float
    normal_route: PathResult
    stressed_route_qpso: PathResult
    stressed_route_standard: PathResult
    metrics_delta: Dict[str, Any]
    active_incidents_injected: List[Incident]
    ai_recommendation: str

# Graph Node / Landmark
class MapLandmark(BaseModel):
    id: str
    name: str
    category: str
    lat: float
    lon: float
    node_id: int
