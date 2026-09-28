import pytest
from starlette.testclient import TestClient
from app.main import app

@pytest.fixture
def client():
    return TestClient(app)

def test_health_endpoints(client):
    r1 = client.get("/")
    assert r1.status_code == 200

    r2 = client.get("/health")
    assert r2.status_code == 200
    assert r2.json()["quantum_engine"] == "active"

def test_graph_info_and_landmarks(client):
    r = client.get("/api/city/graph-info")
    assert r.status_code == 200
    data = r.json()
    assert data["nodes_count"] > 10
    assert data["edges_count"] > 20

    r_lm = client.get("/api/landmarks")
    assert r_lm.status_code == 200
    assert len(r_lm.json()) >= 5

def test_post_route_endpoint(client):
    payload = {
        "source": {"lat": 28.6315, "lon": 77.2167, "label": "CP"},
        "destination": {"lat": 28.6129, "lon": 77.2295, "label": "India Gate"},
        "mode": "personal",
        "priority": "fastest"
    }
    r = client.post("/api/route", json=payload)
    assert r.status_code == 200
    res = r.json()
    assert "trip_id" in res
    assert "comparison" in res
    assert res["comparison"]["qpso_route"]["metrics"]["total_time_seconds"] > 0

def test_post_fleet_route_endpoint(client):
    payload = {
        "depot": {"lat": 28.6315, "lon": 77.2167, "label": "Depot"},
        "stops": [
            {"lat": 28.6129, "lon": 77.2295, "label": "Stop A"},
            {"lat": 28.6429, "lon": 77.2195, "label": "Stop B"}
        ],
        "vehicles": [
            {"vehicle_id": "v1", "name": "Fleet Alpha", "capacity": 50, "color": "#00F0FF"}
        ]
    }
    r = client.post("/api/fleet/route", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data["vehicles_deployed"] == 1
    assert len(data["fleet_routes"]) == 1

def test_incident_lifecycle(client):
    # 1. Create incident
    inc_payload = {
        "incident_type": "accident",
        "lat": 28.6315,
        "lon": 77.2167,
        "radius_meters": 250,
        "severity": 3.0,
        "description": "Jammed intersection"
    }
    r_create = client.post("/api/incident", json=inc_payload)
    assert r_create.status_code == 200
    inc_id = r_create.json()["id"]

    # 2. List incidents
    r_list = client.get("/api/incidents")
    assert r_list.status_code == 200
    assert any(i["id"] == inc_id for i in r_list.json())

    # 3. Delete incident
    r_del = client.delete(f"/api/incident/{inc_id}")
    assert r_del.status_code == 200

    # 4. Reset
    r_rst = client.post("/api/reset")
    assert r_rst.status_code == 200
