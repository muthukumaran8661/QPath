import math
import random
import numpy as np
import networkx as nx
from typing import List, Dict, Tuple, Optional, Any
from app.models.schemas import (
    Coordinate, ObjectiveWeights, OptimizationMode, PriorityPreset,
    RouteSegment, RouteMetrics, PathResult, RouteComparison
)
from app.optimizer.graph_service import graph_service, GraphService, haversine_meters

def format_time(seconds: float) -> str:
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    if mins >= 60:
        hrs = mins // 60
        rem_mins = mins % 60
        return f"{hrs} hr {rem_mins} min"
    return f"{mins} min {secs} sec" if mins < 5 else f"{mins} min"

def format_distance(meters: float) -> str:
    if meters >= 1000:
        return f"{meters / 1000.0:.1f} km"
    return f"{int(meters)} m"

class QPSORouteOptimizer:
    def __init__(self, graph_service: GraphService):
        self.gs = graph_service

    def get_priority_weights(self, priority: PriorityPreset, custom: Optional[ObjectiveWeights] = None) -> ObjectiveWeights:
        if custom:
            return custom.normalized()
        
        if priority == PriorityPreset.FASTEST:
            return ObjectiveWeights(w_time=0.65, w_distance=0.10, w_congestion=0.20, w_road_condition=0.05).normalized()
        elif priority == PriorityPreset.SHORTEST:
            return ObjectiveWeights(w_time=0.15, w_distance=0.70, w_congestion=0.10, w_road_condition=0.05).normalized()
        elif priority == PriorityPreset.LESS_CONGESTED:
            return ObjectiveWeights(w_time=0.25, w_distance=0.15, w_congestion=0.50, w_road_condition=0.10).normalized()
        elif priority == PriorityPreset.SMOOTH_ROADS:
            return ObjectiveWeights(w_time=0.20, w_distance=0.15, w_congestion=0.15, w_road_condition=0.50).normalized()
        else:  # BALANCED
            return ObjectiveWeights(w_time=0.40, w_distance=0.20, w_congestion=0.25, w_road_condition=0.15).normalized()

    def evaluate_path_metrics(self, path_nodes: List[int], weights: ObjectiveWeights) -> Tuple[RouteMetrics, List[RouteSegment]]:
        if not path_nodes or len(path_nodes) < 2:
            empty_metrics = RouteMetrics(
                total_time_seconds=0,
                total_distance_meters=0,
                total_time_formatted="0 min",
                total_distance_formatted="0 m",
                avg_congestion_factor=1.0,
                avg_road_condition_score=1.0,
                carbon_emission_kg=0.0,
                multi_objective_cost=float("inf")
            )
            return empty_metrics, []

        total_dist = 0.0
        total_time = 0.0
        sum_congestion = 0.0
        sum_road_cond = 0.0
        has_closed_road = False
        segments: List[RouteSegment] = []

        g = self.gs.graph

        for i in range(len(path_nodes) - 1):
            u = path_nodes[i]
            v = path_nodes[i+1]
            if not g.has_edge(u, v):
                # Penalty for nonexistent edge
                return RouteMetrics(
                    total_time_seconds=99999, total_distance_meters=99999,
                    total_time_formatted="N/A", total_distance_formatted="N/A",
                    avg_congestion_factor=5.0, avg_road_condition_score=0.1,
                    carbon_emission_kg=99.9, multi_objective_cost=float("inf")
                ), []
            
            data = g[u][v]
            dist = data.get("length_meters", 100.0)
            base_time = data.get("base_time_seconds", 10.0)
            cong = data.get("congestion_factor", 1.0)
            cond = data.get("road_condition_score", 0.9)
            closed = data.get("is_closed", False)
            speed = data.get("speed_kph", 40.0)
            geom = data.get("geometry", [[g.nodes[u]["lat"], g.nodes[u]["lon"]], [g.nodes[v]["lat"], g.nodes[v]["lon"]]])
            name = data.get("name", "Urban Link")

            if closed:
                has_closed_road = True

            actual_time = base_time * cong * (1.0 + (1.0 - cond) * 0.35)
            total_dist += dist
            total_time += actual_time
            sum_congestion += cong
            sum_road_cond += cond

            instr = f"Continue onto {name} for {format_distance(dist)}"
            segments.append(RouteSegment(
                u=u, v=v,
                distance_meters=dist,
                travel_time_seconds=actual_time,
                speed_kph=speed,
                congestion_factor=cong,
                road_condition=cond,
                is_closed=closed,
                coordinates=geom,
                instruction=instr,
                road_name=name
            ))

        n_edges = len(path_nodes) - 1
        avg_cong = sum_congestion / max(n_edges, 1)
        avg_cond = sum_road_cond / max(n_edges, 1)

        # Baseline carbon calculation: 0.13 kg CO2 per km, increased with traffic congestion delay
        km = total_dist / 1000.0
        carbon = km * 0.13 * (1.0 + (avg_cong - 1.0) * 0.45)

        # Multi-objective normalized cost function:
        # Cost = w_time*(time/300) + w_dist*(dist/3000) + w_cong*(avg_cong/2.0) + w_cond*(1.0 - avg_cond)
        time_norm = max(total_time / 300.0, 0.01)
        dist_norm = max(total_dist / 3000.0, 0.01)
        cong_norm = avg_cong / 2.0
        cond_norm = max(1.0 - avg_cond, 0.0)

        cost = (
            weights.w_time * time_norm +
            weights.w_distance * dist_norm +
            weights.w_congestion * cong_norm +
            weights.w_road_condition * cond_norm
        )

        if has_closed_road:
            cost += 10000.0  # Heavy barrier penalty for closed routes

        metrics = RouteMetrics(
            total_time_seconds=total_time,
            total_distance_meters=total_dist,
            total_time_formatted=format_time(total_time),
            total_distance_formatted=format_distance(total_dist),
            avg_congestion_factor=round(avg_cong, 2),
            avg_road_condition_score=round(avg_cond, 2),
            carbon_emission_kg=round(carbon, 2),
            multi_objective_cost=round(cost, 4)
        )
        return metrics, segments

    def find_baseline_dijkstra(self, source_node: int, dest_node: int, weights: ObjectiveWeights) -> PathResult:
        """
        Calculates standard baseline shortest path using standard distance weight (Dijkstra/A*),
        which standard navigation apps default to without quantum multi-objective balance.
        """
        g = self.gs.graph
        
        # Build weight function based strictly on static distance + base time
        def static_edge_weight(u, v, d):
            if d.get("is_closed", False):
                return 1e8
            return d.get("length_meters", 100.0)

        try:
            path = nx.shortest_path(g, source=source_node, target=dest_node, weight=static_edge_weight)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            # Fallback direct path or available
            path = [source_node, dest_node] if g.has_node(source_node) and g.has_node(dest_node) else []

        metrics, segments = self.evaluate_path_metrics(path, weights)
        coords = []
        for n in path:
            coords.append([g.nodes[n]["lat"], g.nodes[n]["lon"]])

        return PathResult(
            nodes=path,
            coordinates=coords,
            segments=segments,
            metrics=metrics
        )

    def optimize_qpso(
        self,
        source_node: int,
        dest_node: int,
        weights: ObjectiveWeights,
        swarm_size: int = 35,
        max_iter: int = 40,
        beta_init: float = 1.0,
        beta_final: float = 0.4
    ) -> PathResult:
        """
        Executes Quantum-behaved Particle Swarm Optimization (QPSO) with Delta-Potential well wave equation.
        Particles explore the graph potential landscape by perturbing objective edge priorities,
        tunneling through local minima to discover globally optimal congestion-free and pothole-free routes.
        """
        g = self.gs.graph
        edge_list = list(g.edges())
        num_edges = len(edge_list)
        if num_edges == 0:
            return self.find_baseline_dijkstra(source_node, dest_node, weights)

        # Baseline path as starting anchor
        baseline_res = self.find_baseline_dijkstra(source_node, dest_node, weights)
        best_path = baseline_res.nodes
        best_metrics, best_segments = self.evaluate_path_metrics(best_path, weights)
        best_cost = best_metrics.multi_objective_cost

        # Particle dimensions: Dimension per edge perturbation in [-1.5, 1.5]
        # Position X[i] encodes edge penalty multiplier
        X = np.random.uniform(-0.5, 0.5, (swarm_size, num_edges))
        P = np.copy(X)  # Personal best positions
        P_costs = np.full(swarm_size, float("inf"))
        P_paths = [[] for _ in range(swarm_size)]

        # Global best
        G = np.copy(X[0])
        G_cost = best_cost

        def decode_path(pos_vector: np.ndarray) -> List[int]:
            # Construct dynamic temporary weight dict
            temp_weights = {}
            for idx, (u, v) in enumerate(edge_list):
                d = g[u][v]
                if d.get("is_closed", False):
                    temp_weights[(u, v)] = 1e8
                    continue

                dist = d.get("length_meters", 100.0)
                base_time = d.get("base_time_seconds", 10.0)
                cong = d.get("congestion_factor", 1.0)
                cond = d.get("road_condition_score", 0.9)

                # Composite cost with quantum perturbation
                t_comp = base_time * cong
                r_comp = (1.0 - cond) * 50.0
                edge_cost = (
                    weights.w_time * t_comp +
                    weights.w_distance * (dist / 10.0) +
                    weights.w_congestion * (cong * 30.0) +
                    weights.w_road_condition * r_comp
                )

                # Quantum multiplier via exponential perturbation
                perturbation = math.exp(np.clip(pos_vector[idx], -2.0, 2.0))
                temp_weights[(u, v)] = max(edge_cost * perturbation, 0.1)

            def get_w(u, v, d):
                return temp_weights.get((u, v), d.get("length_meters", 100.0))

            try:
                p = nx.shortest_path(g, source=source_node, target=dest_node, weight=get_w)
                return p
            except (nx.NetworkXNoPath, nx.NodeNotFound):
                return best_path

        # Initialize Swarm evaluations
        for i in range(swarm_size):
            cand_path = decode_path(X[i])
            m, _ = self.evaluate_path_metrics(cand_path, weights)
            P_costs[i] = m.multi_objective_cost
            P_paths[i] = cand_path
            if m.multi_objective_cost < G_cost:
                G_cost = m.multi_objective_cost
                G = np.copy(X[i])
                best_path = cand_path
                best_metrics = m

        # QPSO Main Quantum Wave Iterations
        for it in range(max_iter):
            # Beta decay (Quantum tunneling contraction-expansion coefficient)
            beta = beta_init - (it / max_iter) * (beta_init - beta_final)

            # Calculate Mean Best Position (mbest) of the swarm
            mbest = np.mean(P, axis=0)

            for i in range(swarm_size):
                # Quantum Local Attractor: p_ij = phi * P_ij + (1 - phi) * G_j
                phi = np.random.uniform(0.0, 1.0, num_edges)
                p_attr = phi * P[i] + (1.0 - phi) * G

                # Quantum Delta Potential Well Position Update:
                # X_ij(t+1) = p_attr +- beta * |mbest - X_ij| * ln(1 / u)
                u_rand = np.random.uniform(1e-6, 1.0, num_edges)
                ln_u = np.log(1.0 / u_rand)
                sign_rand = np.where(np.random.rand(num_edges) < 0.5, 1.0, -1.0)
                
                X[i] = p_attr + sign_rand * beta * np.abs(mbest - X[i]) * ln_u

                # Evaluate new quantum state
                cand_path = decode_path(X[i])
                m, _ = self.evaluate_path_metrics(cand_path, weights)

                # Update Personal Best
                if m.multi_objective_cost < P_costs[i]:
                    P_costs[i] = m.multi_objective_cost
                    P[i] = np.copy(X[i])
                    P_paths[i] = cand_path

                    # Update Global Swarm Best
                    if m.multi_objective_cost < G_cost:
                        G_cost = m.multi_objective_cost
                        G = np.copy(X[i])
                        best_path = cand_path
                        best_metrics = m

        final_metrics, final_segments = self.evaluate_path_metrics(best_path, weights)
        coords = [[g.nodes[n]["lat"], g.nodes[n]["lon"]] for n in best_path]

        return PathResult(
            nodes=best_path,
            coordinates=coords,
            segments=final_segments,
            metrics=final_metrics
        )

    def compute_route_comparison(
        self,
        source: Coordinate,
        destination: Coordinate,
        mode: OptimizationMode = OptimizationMode.PERSONAL,
        priority: PriorityPreset = PriorityPreset.BALANCED,
        custom_weights: Optional[ObjectiveWeights] = None,
        swarm_size: int = 35,
        max_iter: int = 40
    ) -> RouteComparison:
        weights = self.get_priority_weights(priority, custom_weights)
        
        # Emergency Mode Priority Overrides
        if mode == OptimizationMode.EMERGENCY:
            weights = ObjectiveWeights(w_time=0.90, w_distance=0.05, w_congestion=0.05, w_road_condition=0.0).normalized()

        u_src = source.node_id if source.node_id is not None else self.gs.get_nearest_node(source.lat, source.lon)
        v_dst = destination.node_id if destination.node_id is not None else self.gs.get_nearest_node(destination.lat, destination.lon)

        # 1. Baseline Route (Standard Dijkstra)
        baseline_route = self.find_baseline_dijkstra(u_src, v_dst, weights)

        # 2. QPSO Multi-Objective Route
        qpso_route = self.optimize_qpso(
            source_node=u_src,
            dest_node=v_dst,
            weights=weights,
            swarm_size=swarm_size,
            max_iter=max_iter
        )

        # Metrics Delta Calculation
        t_base = baseline_route.metrics.total_time_seconds
        t_qpso = qpso_route.metrics.total_time_seconds
        time_saved = max(t_base - t_qpso, 0.0)
        time_saved_pct = round((time_saved / max(t_base, 1.0)) * 100.0, 1)

        c_base = baseline_route.metrics.avg_congestion_factor
        c_qpso = qpso_route.metrics.avg_congestion_factor
        cong_reduction_pct = round(max((c_base - c_qpso) / max(c_base, 0.01) * 100.0, 0.0), 1)

        r_base = 1.0 - baseline_route.metrics.avg_road_condition_score
        r_qpso = 1.0 - qpso_route.metrics.avg_road_condition_score
        rough_reduction_pct = round(max((r_base - r_qpso) / max(r_base, 0.01) * 100.0, 0.0), 1)

        efficiency_score = round(min(100.0, 75.0 + time_saved_pct * 0.8 + cong_reduction_pct * 0.5), 1)

        return RouteComparison(
            qpso_route=qpso_route,
            baseline_route=baseline_route,
            time_saved_seconds=round(time_saved, 1),
            time_saved_percent=time_saved_pct,
            congestion_reduction_percent=cong_reduction_pct,
            roughness_reduction_percent=rough_reduction_pct,
            quantum_efficiency_score=efficiency_score,
            algorithm_summary={
                "name": "Quantum-behaved Particle Swarm Optimization (QPSO)",
                "swarm_size": swarm_size,
                "iterations": max_iter,
                "potential_model": "Delta-Potential Well Wave Collapse",
                "normalized_weights": weights.model_dump()
            }
        )

qpso_optimizer = QPSORouteOptimizer(graph_service)
