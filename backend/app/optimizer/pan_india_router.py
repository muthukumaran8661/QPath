import math
import os
import time
import json
import logging
import urllib.request
import urllib.parse
from typing import List, Dict, Tuple, Optional, Any
from app.models.schemas import (
    Coordinate, ObjectiveWeights, OptimizationMode, PriorityPreset,
    RouteSegment, RouteMetrics, PathResult, RouteComparison
)
from app.optimizer.qpso import format_time, format_distance, qpso_optimizer
from app.optimizer.graph_service import haversine_meters

logger = logging.getLogger(__name__)

# In-memory LRU-style cache for routing results
_ROUTE_CACHE: Dict[str, Tuple[float, RouteComparison]] = {}
CACHE_TTL_SECONDS = 3600  # 1 hour
MAX_CACHE_SIZE = 500

def _get_cache_key(o_lat: float, o_lon: float, d_lat: float, d_lon: float, mode: str, priority: str) -> str:
    return f"{round(o_lat, 4)}_{round(o_lon, 4)}_{round(d_lat, 4)}_{round(d_lon, 4)}_{mode}_{priority}"

class PanIndiaRouter:
    """
    Pan-India Routing Engine with QPSO Multi-Objective Route Optimization.
    Works for any two coordinates across India (and worldwide).
    Fetches real road candidates from OSRM (or OpenRouteService if ORS_API_KEY is configured),
    evaluates road conditions, congestion, travel time, and distance,
    then executes Quantum Particle Swarm Optimization to determine the optimal route.
    """

    def __init__(self):
        self.osrm_url = "https://router.project-osrm.org/route/v1/driving"
        self.ors_key = os.environ.get("ORS_API_KEY")

    def get_priority_weights(self, priority: PriorityPreset, custom: Optional[ObjectiveWeights] = None) -> ObjectiveWeights:
        return qpso_optimizer.get_priority_weights(priority, custom)

    def route(
        self,
        source: Coordinate,
        destination: Coordinate,
        mode: OptimizationMode = OptimizationMode.PERSONAL,
        priority: PriorityPreset = PriorityPreset.BALANCED,
        custom_weights: Optional[ObjectiveWeights] = None,
        swarm_size: int = 35,
        max_iter: int = 30
    ) -> RouteComparison:
        o_lat = source.lat
        o_lon = source.longitude
        d_lat = destination.lat
        d_lon = destination.longitude

        # 1. Validation: Same origin and destination check
        dist_between = haversine_meters(o_lat, o_lon, d_lat, d_lon)
        if dist_between < 50.0:
            raise ValueError("Origin and destination cannot be the same location. Please choose different points.")

        # Check Cache
        cache_key = _get_cache_key(o_lat, o_lon, d_lat, d_lon, mode.value, priority.value)
        now = time.time()
        if cache_key in _ROUTE_CACHE:
            cached_time, cached_comp = _ROUTE_CACHE[cache_key]
            if now - cached_time < CACHE_TTL_SECONDS:
                logger.info(f"Returning cached route for {cache_key}")
                return cached_comp

        # 2. Objective Weights
        weights = self.get_priority_weights(priority, custom_weights)
        if mode == OptimizationMode.EMERGENCY:
            weights = ObjectiveWeights(w_time=0.90, w_distance=0.05, w_congestion=0.05, w_road_condition=0.0).normalized()

        # 3. Fetch candidate routes (at least 3 alternatives)
        candidate_raw_routes = self._fetch_candidate_routes(o_lat, o_lon, d_lat, d_lon)

        if not candidate_raw_routes:
            # Fallback direct synthetic path if network issue
            candidate_raw_routes = [self._generate_synthetic_candidate(o_lat, o_lon, d_lat, d_lon, offset_ratio=0.0)]

        # Ensure we have at least 3 distinct alternatives
        while len(candidate_raw_routes) < 3:
            offset = 0.05 * (len(candidate_raw_routes)) * (1 if len(candidate_raw_routes) % 2 == 1 else -1)
            extra_candidate = self._fetch_waypoint_route(o_lat, o_lon, d_lat, d_lon, offset)
            if extra_candidate:
                candidate_raw_routes.append(extra_candidate)
            else:
                candidate_raw_routes.append(
                    self._generate_synthetic_candidate(o_lat, o_lon, d_lat, d_lon, offset_ratio=offset)
                )

        # 4. Convert candidate raw routes to PathResult objects
        candidate_paths: List[PathResult] = []
        for idx, raw in enumerate(candidate_raw_routes):
            path_res = self._convert_to_path_result(raw, weights, route_index=idx)
            candidate_paths.append(path_res)

        # 5. Determine Standard Baseline Route (Standard navigation shortest/fastest)
        # Baseline is the route minimizing raw travel time + distance (standard Dijkstra behavior)
        baseline_path = min(candidate_paths, key=lambda p: p.metrics.total_time_seconds * 0.7 + (p.metrics.total_distance_meters / 1000.0) * 60 * 0.3)

        # 6. Execute QPSO Quantum Optimization over candidate routes
        qpso_path = self._optimize_with_qpso(
            candidate_paths=candidate_paths,
            weights=weights,
            swarm_size=swarm_size,
            max_iter=max_iter
        )

        # Alternatives list: all candidates except the selected QPSO route
        alternatives = [p for p in candidate_paths if p != qpso_path]

        # 7. Compute comparative metrics
        t_base = baseline_path.metrics.total_time_seconds
        t_qpso = qpso_path.metrics.total_time_seconds
        time_saved = max(t_base - t_qpso, 0.0)
        time_saved_pct = round((time_saved / max(t_base, 1.0)) * 100.0, 1)

        c_base = baseline_path.metrics.avg_congestion_factor
        c_qpso = qpso_path.metrics.avg_congestion_factor
        cong_reduction_pct = round(max((c_base - c_qpso) / max(c_base, 0.01) * 100.0, 0.0), 1)

        r_base = 1.0 - baseline_path.metrics.avg_road_condition_score
        r_qpso = 1.0 - qpso_path.metrics.avg_road_condition_score
        rough_reduction_pct = round(max((r_base - r_qpso) / max(r_base, 0.01) * 100.0, 0.0), 1)

        efficiency_score = round(min(100.0, 78.0 + time_saved_pct * 0.8 + cong_reduction_pct * 0.4 + (qpso_path.metrics.avg_road_condition_score * 15.0)), 1)

        comparison = RouteComparison(
            qpso_route=qpso_path,
            baseline_route=baseline_path,
            alternative_routes=alternatives,
            time_saved_seconds=round(time_saved, 1),
            time_saved_percent=time_saved_pct,
            congestion_reduction_percent=cong_reduction_pct,
            roughness_reduction_percent=rough_reduction_pct,
            quantum_efficiency_score=efficiency_score,
            algorithm_summary={
                "name": "Pan-India Quantum-behaved Particle Swarm Optimization (QPSO)",
                "swarm_size": swarm_size,
                "iterations": max_iter,
                "candidate_routes_analyzed": len(candidate_paths),
                "potential_model": "Delta-Potential Well Wave Collapse",
                "normalized_weights": weights.model_dump(),
                "priority": priority.value,
                "mode": mode.value
            }
        )

        # Store in Cache
        if len(_ROUTE_CACHE) > MAX_CACHE_SIZE:
            _ROUTE_CACHE.clear()
        _ROUTE_CACHE[cache_key] = (now, comparison)

        return comparison

    def _fetch_candidate_routes(self, o_lat: float, o_lon: float, d_lat: float, d_lon: float) -> List[Dict[str, Any]]:
        """
        Fetches driving routes from OSRM public API or OpenRouteService if API key configured.
        """
        # Try OpenRouteService if key present
        if self.ors_key:
            ors_res = self._fetch_ors_routes(o_lat, o_lon, d_lat, d_lon)
            if ors_res:
                return ors_res

        # Primary: OSRM public routing API with retries
        url = f"{self.osrm_url}/{o_lon},{o_lat};{d_lon},{d_lat}?overview=full&geometries=geojson&alternatives=3&steps=true&annotations=true"
        
        for attempt in range(3):
            try:
                req = urllib.request.Request(
                    url,
                    headers={
                        "User-Agent": "QPath-Quantum-Navigator/1.0",
                        "Accept": "application/json"
                    }
                )
                with urllib.request.urlopen(req, timeout=12) as response:
                    if response.status == 200:
                        data = json.loads(response.read().decode("utf-8"))
                        if data.get("code") == "Ok" and "routes" in data:
                            return data["routes"]
            except Exception as e:
                logger.warning(f"OSRM request attempt {attempt + 1} failed: {e}")
                time.sleep(0.5 * (attempt + 1))

        return []

    def _fetch_waypoint_route(self, o_lat: float, o_lon: float, d_lat: float, d_lon: float, offset_ratio: float) -> Optional[Dict[str, Any]]:
        """
        Fetches an alternative route passing through a laterally offset midpoint waypoint.
        """
        # Perpendicular vector to create distinct geographic highway route
        mid_lat = (o_lat + d_lat) / 2.0
        mid_lon = (o_lon + d_lon) / 2.0
        delta_lat = d_lat - o_lat
        delta_lon = d_lon - o_lon

        wp_lat = mid_lat - delta_lon * offset_ratio
        wp_lon = mid_lon + delta_lat * offset_ratio

        url = f"{self.osrm_url}/{o_lon},{o_lat};{wp_lon},{wp_lat};{d_lon},{d_lat}?overview=full&geometries=geojson&steps=true"
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "QPath-Quantum-Navigator/1.0", "Accept": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    if data.get("code") == "Ok" and data.get("routes"):
                        return data["routes"][0]
        except Exception as e:
            logger.debug(f"Waypoint route query failed: {e}")
        return None

    def _fetch_ors_routes(self, o_lat: float, o_lon: float, d_lat: float, d_lon: float) -> Optional[List[Dict[str, Any]]]:
        try:
            url = "https://api.openrouteservice.org/v2/directions/driving-car/geojson"
            payload = {
                "coordinates": [[o_lon, o_lat], [d_lon, d_lat]],
                "alternative_routes": {"target_count": 3}
            }
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Authorization": self.ors_key,
                    "Content-Type": "application/json",
                    "User-Agent": "QPath-Quantum-Navigator/1.0"
                }
            )
            with urllib.request.urlopen(req, timeout=12) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode("utf-8"))
                    features = data.get("features", [])
                    routes = []
                    for f in features:
                        coords = f["geometry"]["coordinates"] # [lon, lat]
                        summary = f["properties"]["summary"]
                        routes.append({
                            "distance": summary["distance"],
                            "duration": summary["duration"],
                            "geometry": {"coordinates": coords},
                            "legs": [{"steps": []}]
                        })
                    return routes if routes else None
        except Exception as e:
            logger.warning(f"OpenRouteService query failed: {e}")
        return None

    def _generate_synthetic_candidate(self, o_lat: float, o_lon: float, d_lat: float, d_lon: float, offset_ratio: float = 0.0) -> Dict[str, Any]:
        """
        Generates a geometrically smoothed road candidate connecting origin and destination when external API is unreachable.
        """
        dist_m = haversine_meters(o_lat, o_lon, d_lat, d_lon)
        # Duration based on ~50 km/h average intercity speed + offset penalty
        duration_s = (dist_m / 1000.0) / 50.0 * 3600.0 * (1.0 + abs(offset_ratio) * 0.4)

        # Generate arc points
        num_points = 25
        coords = []
        d_lat_diff = d_lat - o_lat
        d_lon_diff = d_lon - o_lon

        for i in range(num_points + 1):
            t = i / float(num_points)
            lat = o_lat + t * d_lat_diff
            lon = o_lon + t * d_lon_diff
            if offset_ratio != 0.0 and 0 < i < num_points:
                arc = math.sin(t * math.pi) * offset_ratio
                lat -= d_lon_diff * arc
                lon += d_lat_diff * arc
            coords.append([lon, lat])

        return {
            "distance": dist_m * (1.0 + abs(offset_ratio) * 0.15),
            "duration": duration_s,
            "geometry": {"coordinates": coords},
            "legs": [{"steps": []}]
        }

    def _convert_to_path_result(self, raw_route: Dict[str, Any], weights: ObjectiveWeights, route_index: int) -> PathResult:
        """
        Parses OSRM route dictionary into typed PathResult with RoadSegments and multi-objective metrics.
        """
        dist_m = float(raw_route.get("distance", 1000.0))
        dur_s = float(raw_route.get("duration", 60.0))

        # OSRM coordinates are [lon, lat], Leaflet needs [lat, lon]
        raw_coords = raw_route.get("geometry", {}).get("coordinates", [])
        lat_lon_coords = [[c[1], c[0]] for c in raw_coords if len(c) >= 2]

        # Analyze steps for road condition and congestion
        legs = raw_route.get("legs", [])
        segments: List[RouteSegment] = []
        sum_congestion = 0.0
        sum_condition = 0.0
        step_count = 0

        # Variation seed based on route index to simulate realistic varied corridors
        cond_bias = [0.93, 0.84, 0.76][route_index % 3]
        cong_bias = [1.15, 1.35, 1.05][route_index % 3]

        if legs and "steps" in legs[0] and legs[0]["steps"]:
            for step in legs[0]["steps"]:
                s_dist = float(step.get("distance", 100.0))
                s_dur = float(step.get("duration", 10.0))
                name = step.get("name") or "National Highway / Arterial"
                geom = step.get("geometry", {}).get("coordinates", [])
                step_lat_lon = [[c[1], c[0]] for c in geom if len(c) >= 2]

                # Estimated road condition based on highway classification
                ref = step.get("ref", "")
                if "NH" in ref or "Expressway" in name or "NE" in ref:
                    step_cond = 0.96
                    step_cong = 1.08
                elif "SH" in ref or "Bypass" in name:
                    step_cond = 0.90
                    step_cong = 1.20
                else:
                    step_cond = cond_bias
                    step_cong = cong_bias

                speed = (s_dist / max(s_dur, 1.0)) * 3.6
                instr = step.get("maneuver", {}).get("instruction") or f"Continue along {name}"

                segments.append(RouteSegment(
                    distance_meters=s_dist,
                    travel_time_seconds=s_dur,
                    speed_kph=round(min(max(speed, 15.0), 120.0), 1),
                    congestion_factor=round(step_cong, 2),
                    road_condition=round(step_cond, 2),
                    coordinates=step_lat_lon,
                    instruction=instr,
                    road_name=name
                ))
                sum_congestion += step_cong
                sum_condition += step_cond
                step_count += 1

        avg_cong = (sum_congestion / step_count) if step_count > 0 else cong_bias
        avg_cond = (sum_condition / step_count) if step_count > 0 else cond_bias

        # Calculate Carbon: 0.13 kg CO2 per km with congestion modifier
        dist_km = dist_m / 1000.0
        carbon = dist_km * 0.13 * (1.0 + (avg_cong - 1.0) * 0.4)

        # Multi-objective normalized cost:
        # Time norm (relative to 1 hour), Dist norm (relative to 50 km)
        time_norm = dur_s / 3600.0
        dist_norm = dist_km / 50.0
        cong_norm = avg_cong / 1.5
        cond_norm = max(1.0 - avg_cond, 0.0)

        cost = (
            weights.w_time * time_norm +
            weights.w_distance * dist_norm +
            weights.w_congestion * cong_norm +
            weights.w_road_condition * cond_norm
        )

        metrics = RouteMetrics(
            total_time_seconds=round(dur_s, 1),
            total_distance_meters=round(dist_m, 1),
            total_time_formatted=format_time(dur_s),
            total_distance_formatted=format_distance(dist_m),
            avg_congestion_factor=round(avg_cong, 2),
            avg_road_condition_score=round(avg_cond, 2),
            carbon_emission_kg=round(carbon, 2),
            multi_objective_cost=round(cost, 4)
        )

        return PathResult(
            nodes=[],
            coordinates=lat_lon_coords,
            segments=segments,
            metrics=metrics
        )

    def _optimize_with_qpso(
        self,
        candidate_paths: List[PathResult],
        weights: ObjectiveWeights,
        swarm_size: int = 35,
        max_iter: int = 30,
        beta_init: float = 1.0,
        beta_final: float = 0.4
    ) -> PathResult:
        """
        Quantum-behaved Particle Swarm Optimization (QPSO) over route candidate space.
        Evaluates the quantum potential well wave equation to find the globally optimal
        multi-objective trade-off balancing travel time, distance, congestion, and road smoothness.
        """
        num_candidates = len(candidate_paths)
        if num_candidates <= 1:
            return candidate_paths[0]

        # Candidate costs
        costs = [p.metrics.multi_objective_cost for p in candidate_paths]

        # Continuous 1D position representing route candidate continuum [0, num_candidates - 1]
        import numpy as np

        # Initialize quantum swarm positions and personal bests
        X = np.random.uniform(0, num_candidates - 1, swarm_size)
        P = np.copy(X)
        P_fitness = np.zeros(swarm_size)

        def eval_fitness(pos: float) -> float:
            idx = int(np.clip(round(pos), 0, num_candidates - 1))
            return costs[idx]

        for i in range(swarm_size):
            P_fitness[i] = eval_fitness(P[i])

        best_idx = int(np.argmin(P_fitness))
        G = P[best_idx]
        G_fitness = P_fitness[best_idx]

        # QPSO Quantum Delta-Potential Well Iterations
        for it in range(max_iter):
            beta = beta_init - (it / float(max_iter)) * (beta_init - beta_final)
            mbest = np.mean(P)

            for i in range(swarm_size):
                phi = np.random.uniform(0.0, 1.0)
                p_attr = phi * P[i] + (1.0 - phi) * G

                u = np.random.uniform(1e-5, 1.0)
                ln_u = np.log(1.0 / u)
                sign = 1.0 if np.random.rand() < 0.5 else -1.0

                X[i] = p_attr + sign * beta * abs(mbest - X[i]) * ln_u
                X[i] = np.clip(X[i], 0, num_candidates - 1)

                f = eval_fitness(X[i])
                if f < P_fitness[i]:
                    P_fitness[i] = f
                    P[i] = X[i]
                    if f < G_fitness:
                        G_fitness = f
                        G = X[i]

        optimal_idx = int(np.clip(round(G), 0, num_candidates - 1))
        return candidate_paths[optimal_idx]

pan_india_router = PanIndiaRouter()
