import json
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, Any, Optional
from app.models.schemas import Coordinate, OptimizationMode, PriorityPreset, IncidentCreate, IncidentType
from app.optimizer.graph_service import graph_service
from app.optimizer.qpso import qpso_optimizer
from app.api.routes import traffic_simulator

ws_router = APIRouter()

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.trip_states: Dict[str, Dict[str, Any]] = {}

    async def connect(self, trip_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[trip_id] = websocket
        self.trip_states[trip_id] = {
            "source": None,
            "destination": None,
            "current_coord": None,
            "priority": PriorityPreset.BALANCED,
            "mode": OptimizationMode.PERSONAL,
            "current_route": None
        }

        # Register callback with simulator to auto-reroute on incident
        def on_incident(event_data):
            asyncio.create_task(self.handle_incident_event(trip_id, event_data))

        traffic_simulator.register_trip(trip_id, on_incident)

    def disconnect(self, trip_id: str):
        if trip_id in self.active_connections:
            del self.active_connections[trip_id]
        if trip_id in self.trip_states:
            del self.trip_states[trip_id]
        traffic_simulator.unregister_trip(trip_id)

    async def send_json(self, trip_id: str, data: Dict[str, Any]):
        if trip_id in self.active_connections:
            try:
                await self.active_connections[trip_id].send_text(json.dumps(data))
            except Exception as e:
                print(f"Error sending to {trip_id}: {e}")

    async def handle_incident_event(self, trip_id: str, event_data: Dict[str, Any]):
        state = self.trip_states.get(trip_id)
        if not state or not state.get("destination"):
            return

        cur_coord = state.get("current_coord") or state.get("source")
        dst_coord = state.get("destination")
        priority = state.get("priority", PriorityPreset.BALANCED)
        mode = state.get("mode", OptimizationMode.PERSONAL)

        if not cur_coord or not dst_coord:
            return

        # Re-solve route using QPSO
        comp = qpso_optimizer.compute_route_comparison(
            source=cur_coord,
            destination=dst_coord,
            mode=mode,
            priority=priority,
            swarm_size=30,
            max_iter=30
        )

        old_route = state.get("current_route")
        time_saved = 0.0
        if old_route and old_route.metrics:
            time_saved = max(old_route.metrics.total_time_seconds - comp.qpso_route.metrics.total_time_seconds, 0.0)

        alert_msg = f"Incident Alert ahead! QPath Quantum Reroute detected ({comp.time_saved_percent}% efficiency gain)."

        await self.send_json(trip_id, {
            "type": "REROUTE_RECOMMENDATION",
            "message": alert_msg,
            "incident": event_data.get("incident"),
            "time_saved_seconds": comp.time_saved_seconds,
            "time_saved_formatted": f"{int(comp.time_saved_seconds // 60)} min {int(comp.time_saved_seconds % 60)} sec",
            "new_comparison": comp.model_dump()
        })

manager = ConnectionManager()

@ws_router.websocket("/ws/route/{trip_id}")
async def route_websocket_endpoint(websocket: WebSocket, trip_id: str):
    await manager.connect(trip_id, websocket)
    try:
        # Send initial confirmation
        await manager.send_json(trip_id, {
            "type": "CONNECTED",
            "trip_id": trip_id,
            "status": "Quantum Stream Active"
        })

        while True:
            raw_text = await websocket.receive_text()
            try:
                data = json.loads(raw_text)
            except Exception:
                continue

            action = data.get("action", "")

            if action == "START_TRIP":
                src = Coordinate(**data["source"])
                dst = Coordinate(**data["destination"])
                prio = PriorityPreset(data.get("priority", "balanced"))
                mode = OptimizationMode(data.get("mode", "personal"))

                manager.trip_states[trip_id]["source"] = src
                manager.trip_states[trip_id]["destination"] = dst
                manager.trip_states[trip_id]["current_coord"] = src
                manager.trip_states[trip_id]["priority"] = prio
                manager.trip_states[trip_id]["mode"] = mode

                comp = qpso_optimizer.compute_route_comparison(
                    source=src, destination=dst, mode=mode, priority=prio
                )
                manager.trip_states[trip_id]["current_route"] = comp.qpso_route

                await manager.send_json(trip_id, {
                    "type": "INITIAL_ROUTE",
                    "comparison": comp.model_dump()
                })

            elif action == "UPDATE_POSITION":
                lat = float(data.get("lat", 0.0))
                lon = float(data.get("lon", 0.0))
                cur_coord = Coordinate(lat=lat, lon=lon)
                manager.trip_states[trip_id]["current_coord"] = cur_coord

                await manager.send_json(trip_id, {
                    "type": "POSITION_ACK",
                    "lat": lat,
                    "lon": lon
                })

            elif action == "TRIGGER_DEMO_INCIDENT":
                # Judge demo trigger: injects incident at current or midpoint location
                inc_type = IncidentType(data.get("incident_type", "accident"))
                lat = float(data.get("lat", graph_service.center_lat + 0.005))
                lon = float(data.get("lon", graph_service.center_lon + 0.005))
                desc = data.get("description", "Judge Demo Injected Incident")

                inc = traffic_simulator.inject_incident(IncidentCreate(
                    incident_type=inc_type,
                    lat=lat,
                    lon=lon,
                    radius_meters=400,
                    severity=3.5,
                    description=desc
                ))

                await manager.send_json(trip_id, {
                    "type": "DEMO_INCIDENT_INJECTED",
                    "incident": inc.model_dump()
                })

            elif action == "ACCEPT_REROUTE":
                new_comp_data = data.get("new_comparison")
                if new_comp_data and "qpso_route" in new_comp_data:
                    from app.models.schemas import PathResult
                    manager.trip_states[trip_id]["current_route"] = PathResult(**new_comp_data["qpso_route"])

                await manager.send_json(trip_id, {
                    "type": "REROUTE_CONFIRMED",
                    "status": "New Quantum Route Activated"
                })

    except WebSocketDisconnect:
        manager.disconnect(trip_id)
    except Exception as e:
        manager.disconnect(trip_id)
