import math
from typing import List, Dict, Tuple, Optional
from app.models.schemas import (
    Coordinate, FleetVehicle, FleetRouteRequest, FleetRouteResponse,
    VehicleRoute, PathResult, RouteSegment, RouteMetrics, ObjectiveWeights
)
from app.optimizer.graph_service import GraphService, haversine_meters
from app.optimizer.qpso import QPSORouteOptimizer, format_time, format_distance

class FleetVRPOptimizer:
    def __init__(self, graph_service: GraphService, qpso: QPSORouteOptimizer):
        self.gs = graph_service
        self.qpso = qpso

    def solve_vrp(self, request: FleetRouteRequest) -> FleetRouteResponse:
        depot = request.depot
        stops = request.stops
        vehicles = request.vehicles
        weights = request.weights or ObjectiveWeights()

        if not vehicles:
            vehicles = [FleetVehicle(vehicle_id="v1", name="Quantum Van Alpha", capacity=100, color="#00F0FF")]

        if not stops:
            # Return depot-only empty tours
            return FleetRouteResponse(
                fleet_routes=[],
                total_fleet_time_seconds=0,
                total_fleet_distance_meters=0,
                total_fleet_time_formatted="0 min",
                total_fleet_distance_formatted="0 km",
                total_fuel_liters=0.0,
                total_carbon_kg=0.0,
                vehicles_deployed=0
            )

        num_vehicles = len(vehicles)
        
        # 1. Cluster stops per vehicle (Spatial angular sector clustering from depot)
        stops_with_angle = []
        for s in stops:
            dy = s.lat - depot.lat
            dx = (s.lon - depot.lon) * math.cos(math.radians(depot.lat))
            angle = math.atan2(dy, dx)
            stops_with_angle.append((angle, s))
            
        stops_with_angle.sort(key=lambda x: x[0])
        sorted_stops = [s for _, s in stops_with_angle]

        # Partition stops evenly across available vehicles
        vehicle_stops: Dict[int, List[Coordinate]] = {i: [] for i in range(num_vehicles)}
        for idx, stop in enumerate(sorted_stops):
            v_idx = idx % num_vehicles
            vehicle_stops[v_idx].append(stop)

        # 2. For each vehicle, order stops using Nearest Neighbor + 2-Opt heuristic,
        # then build detailed QPSO road-level path for all legs
        vehicle_routes: List[VehicleRoute] = []
        total_time_all = 0.0
        total_dist_all = 0.0

        for v_idx, v in enumerate(vehicles):
            assigned = vehicle_stops[v_idx]
            if not assigned:
                continue

            # TSP Tour: Depot -> stop_1 -> stop_2 -> ... -> stop_k -> Depot
            ordered_tour = self._optimize_single_vehicle_tsp(depot, assigned)

            # Build detailed path across all legs
            all_nodes: List[int] = []
            all_coords: List[List[float]] = []
            all_segments: List[RouteSegment] = []
            v_total_dist = 0.0
            v_total_time = 0.0
            sum_cong = 0.0
            sum_cond = 0.0

            for leg_i in range(len(ordered_tour) - 1):
                from_coord = ordered_tour[leg_i]
                to_coord = ordered_tour[leg_i + 1]
                
                u_node = from_coord.node_id if from_coord.node_id is not None else self.gs.get_nearest_node(from_coord.lat, from_coord.lon)
                v_node = to_coord.node_id if to_coord.node_id is not None else self.gs.get_nearest_node(to_coord.lat, to_coord.lon)

                leg_path = self.qpso.optimize_qpso(
                    source_node=u_node,
                    dest_node=v_node,
                    weights=weights,
                    swarm_size=20,
                    max_iter=20
                )

                if leg_i > 0 and leg_path.nodes:
                    # Skip duplicate junction node at leg stitch
                    all_nodes.extend(leg_path.nodes[1:])
                    all_coords.extend(leg_path.coordinates[1:])
                else:
                    all_nodes.extend(leg_path.nodes)
                    all_coords.extend(leg_path.coordinates)

                all_segments.extend(leg_path.segments)
                v_total_dist += leg_path.metrics.total_distance_meters
                v_total_time += leg_path.metrics.total_time_seconds
                sum_cong += leg_path.metrics.avg_congestion_factor
                sum_cond += leg_path.metrics.avg_road_condition_score

            num_legs = max(len(ordered_tour) - 1, 1)
            v_avg_cong = sum_cong / num_legs
            v_avg_cond = sum_cond / num_legs
            km = v_total_dist / 1000.0
            v_carbon = km * 0.14 * (1.0 + (v_avg_cong - 1.0) * 0.35)

            v_metrics = RouteMetrics(
                total_time_seconds=v_total_time,
                total_distance_meters=v_total_dist,
                total_time_formatted=format_time(v_total_time),
                total_distance_formatted=format_distance(v_total_dist),
                avg_congestion_factor=round(v_avg_cong, 2),
                avg_road_condition_score=round(v_avg_cond, 2),
                carbon_emission_kg=round(v_carbon, 2),
                multi_objective_cost=round(v_total_time / 300.0 + v_total_dist / 3000.0, 4)
            )

            path_res = PathResult(
                nodes=all_nodes,
                coordinates=all_coords,
                segments=all_segments,
                metrics=v_metrics
            )

            vehicle_routes.append(VehicleRoute(
                vehicle_id=v.vehicle_id,
                vehicle_name=v.name,
                color=v.color,
                stops=ordered_tour,
                path=path_res,
                total_time_formatted=format_time(v_total_time),
                total_distance_formatted=format_distance(v_total_dist),
                assigned_capacity=len(assigned) * 15
            ))

            total_time_all += v_total_time
            total_dist_all += v_total_dist

        total_km = total_dist_all / 1000.0
        # Fuel estimate: 8.5 liters per 100km base delivery van + traffic factor
        total_fuel = (total_km / 100.0) * 8.5 * 1.15
        total_carbon = total_km * 0.14

        return FleetRouteResponse(
            fleet_routes=vehicle_routes,
            total_fleet_time_seconds=total_time_all,
            total_fleet_distance_meters=total_dist_all,
            total_fleet_time_formatted=format_time(total_time_all),
            total_fleet_distance_formatted=format_distance(total_dist_all),
            total_fuel_liters=round(total_fuel, 2),
            total_carbon_kg=round(total_carbon, 2),
            vehicles_deployed=len(vehicle_routes)
        )

    def _optimize_single_vehicle_tsp(self, depot: Coordinate, stops: List[Coordinate]) -> List[Coordinate]:
        """
        Orders stops for a single vehicle using Nearest-Neighbor + 2-opt tour improvement.
        """
        unvisited = list(stops)
        current = depot
        tour = [depot]

        while unvisited:
            best_idx = 0
            best_d = float("inf")
            for i, stop in enumerate(unvisited):
                d = haversine_meters(current.lat, current.lon, stop.lat, stop.lon)
                if d < best_d:
                    best_d = d
                    best_idx = i
            
            next_stop = unvisited.pop(best_idx)
            tour.append(next_stop)
            current = next_stop

        # Return to depot
        tour.append(depot)

        # 2-opt swap improvements on intermediate stops
        if len(tour) > 4:
            improved = True
            while improved:
                improved = False
                for i in range(1, len(tour) - 2):
                    for j in range(i + 1, len(tour) - 1):
                        d1 = haversine_meters(tour[i-1].lat, tour[i-1].lon, tour[i].lat, tour[i].lon) + \
                             haversine_meters(tour[j].lat, tour[j].lon, tour[j+1].lat, tour[j+1].lon)
                        d2 = haversine_meters(tour[i-1].lat, tour[i-1].lon, tour[j].lat, tour[j].lon) + \
                             haversine_meters(tour[i].lat, tour[i].lon, tour[j+1].lat, tour[j+1].lon)
                        if d2 < d1 - 1e-4:
                            tour[i:j+1] = reversed(tour[i:j+1])
                            improved = True

        return tour
