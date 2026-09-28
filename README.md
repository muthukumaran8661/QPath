# InfinityCore – Adaptive Quantum-Inspired Traffic Route Optimizer
**Smart India Hackathon (SIH) 2026 Grand Finale MVP**

[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688.svg?style=flat&logo=fastapi)](https://fastapi.tiangolo.com)
[![Flutter](https://img.shields.io/badge/Mobile-Flutter%203-02569B.svg?style=flat&logo=flutter)](https://flutter.dev)
[![QPSO Optimizer](https://img.shields.io/badge/Engine-Quantum--behaved%20PSO-00F0FF.svg)](https://numpy.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 🌟 Executive Overview
**InfinityCore** is an enterprise-grade, quantum-inspired multi-objective traffic navigation and fleet logistics optimization platform. Built specifically for Smart India Hackathon 2026, it replaces static single-metric routing (distance/time) with an adaptive **Delta-Potential Quantum-behaved Particle Swarm Optimization (QPSO)** engine.

### Key Capabilities
1. **Multi-Objective Quantum Routing**: Simultaneously optimizes **Travel Time**, **Physical Distance**, **Real-time Congestion**, and **Road Quality / Pothole Avoidance** ($w_1 \cdot T + w_2 \cdot D + w_3 \cdot C + w_4 \cdot R$).
2. **Live Dynamic Re-Routing (WebSocket Stream)**: Detects accidents and roadblocks downstream and pushes instantaneous detours to drivers with quantified time savings.
3. **Multi-Stop Fleet Dispatch (Capacitated VRP)**: Multi-vehicle delivery partitioner with TSP 2-opt clustering and QPSO street routing.
4. **Emergency Green Corridor**: Zero-latency priority override mode for ambulances and first responders.
5. **What-If Scenario Simulator**: Pre-trip stress tester simulating monsoon floods, peak rush-hour bottlenecks, and sudden highway closures.
6. **SIH Judge Demo Console**: Interactive in-app console for judges to inject incidents and observe real-time reroutes live.

---

## 📐 Mathematical Formulation of QPSO
In Quantum-behaved PSO, particles move without deterministic velocity, governed by a wave function collapsed inside a delta potential well:

- **Mean Best Position ($mbest$):**
  $$mbest = \frac{1}{M} \sum_{i=1}^{M} P_{i}$$
  where $P_i$ is personal historical best and $M$ is swarm size.
- **Local Quantum Attractor ($p_{ij}$):**
  $$p_{ij} = \phi \cdot P_{ij} + (1 - \phi) \cdot G_j, \quad \phi \sim U(0, 1)$$
- **Delta Potential Position Update:**
  $$X_{ij}(t+1) = p_{ij} \pm \beta(t) \cdot |mbest_j - X_{ij}(t)| \cdot \ln(1 / u), \quad u \sim U(0, 1)$$
  with adaptive quantum tunneling coefficient $\beta(t) = \beta_{\text{initial}} - \frac{t}{T_{\max}} (\beta_{\text{initial}} - \beta_{\text{final}})$.

---

## 🏗️ Architecture & Technology Stack

```
infinitycore/
├── backend/                  # Python FastAPI Backend & Quantum Engine
│   ├── app/
│   │   ├── api/              # REST Endpoints & WebSocket Router
│   │   ├── optimizer/        # QPSO Pure NumPy Engine & Fleet VRP Solver
│   │   ├── simulator/        # Dynamic Incident Engine & What-If Simulator
│   │   ├── models/           # Pydantic v2 Schemas & DTOs
│   │   ├── config.py         # App Configuration
│   │   └── main.py           # FastAPI Entry Point
│   ├── tests/                # Pytest Unit Test Suite (11 passing tests)
│   ├── Dockerfile            # Container definition
│   └── requirements.txt      # Python dependencies
├── mobile/                   # Flutter Mobile App (Android / Web / iOS)
│   ├── lib/
│   │   ├── core/             # Theme & Tokens (Material 3 Cyber Neon)
│   │   ├── models/           # Dart Data Models
│   │   ├── services/         # REST ApiService & WebSocket Live Stream
│   │   ├── providers/        # Riverpod State Notifiers
│   │   ├── screens/          # Home Map, Simulator, Fleet Screens
│   │   ├── widgets/          # Comparison Card, Judge Panel, Turn Banner
│   │   └── main.dart         # Flutter Entrypoint
│   └── pubspec.yaml          # Flutter dependencies
└── docker-compose.yml        # 1-Command Startup
```

---

## 🚀 Quick Start Guide

### 1. Run Backend with Python
```bash
# From workspace root:
cd backend

# Install dependencies
pip install -r requirements.txt

# Run Unit Tests
python -m pytest backend/tests/ -v

# Start FastAPI Server (Swagger docs at http://127.0.0.1:8000/docs)
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Run Backend with Docker
```bash
docker-compose up --build
```

### 3. Run Mobile App (Flutter)
```bash
cd mobile
flutter pub get
flutter run
```

---

## 📡 REST & WebSocket API Documentation

| Endpoint | Method | Description |
|---|---|---|
| `/api/route` | `POST` | Calculates QPSO multi-objective route and Dijkstra baseline comparison |
| `/api/fleet/route` | `POST` | Solves multi-vehicle, multi-stop fleet VRP with color-coded tours |
| `/api/simulate` | `POST` | Pre-trip What-If stress test (weather, rush hour, closures) |
| `/api/incident` | `POST` | Injects live incident (congestion spike, accident, closure) |
| `/api/incidents` | `GET` | Lists all active graph incidents |
| `/api/reset` | `POST` | Resets graph to pristine base state |
| `/api/landmarks` | `GET` | Returns preset urban landmarks (CP, India Gate, Station, etc.) |
| `/ws/route/{trip_id}` | `WS` | Real-time bi-directional stream for live position tracking & instant reroute pushes |

---

## 🎤 SIH 2026 3-Minute Live Judge Demo Script

1. **The Hook (0:00 - 0:45)**:
   - *"Current GPS tools optimize solely for distance or delayed traffic data. InfinityCore introduces Quantum-behaved Particle Swarm Optimization to discover hidden clear corridors while balancing road roughness, emissions, and congestion."*
2. **Personal Route & Quantum Comparison (0:45 - 1:30)**:
   - Select Origin (*CP Central Hub*) and Destination (*India Gate*).
   - Show the **Quantum Comparison Card**: 18% time saved, 35% traffic avoided, smooth pothole-free route.
3. **Live Re-Routing & Judge Console (1:30 - 2:15)**:
   - Tap **"Start Quantum Navigation"**. The vehicle begins simulated travel.
   - Tap the **Purple Bolt Icon** to open the **SIH Judge Demo Console**.
   - Tap **"Inject Accident"**.
   - Watch the animated alert banner appear immediately via WebSocket: *"Incident Ahead! Quantum detour saves 6.4 min [ACCEPT DETOUR]"*.
   - Tap Accept, and observe the polyline instantly adapt to bypass the roadblock.
4. **Fleet VRP & What-If Simulator (2:15 - 3:00)**:
   - Switch to **Fleet VRP Mode**: show multi-drop logistics divided across 2 color-coded delivery vans.
   - Open **What-If Simulator**: drag the slider to 8:30 AM Monsoon Rain to show predictive traffic stress testing before traveling.
