// QPath Quantum Traffic Optimizer - Web Application Logic
document.addEventListener('DOMContentLoaded', () => {
    // 1. Initialize Leaflet Map
    const map = L.map('map', {
        center: [28.6315, 77.2167], // Connaught Place, New Delhi
        zoom: 13.5,
        zoomControl: false
    });

    L.control.zoom({ position: 'bottomright' }).addTo(map);

    // OpenStreetMap CartoDB Dark Matter Tiles (Zero API Keys)
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; OpenStreetMap contributors &copy; CARTO',
        subdomains: 'abcd',
        maxZoom: 19
    }).addTo(map);

    // State Variables
    let currentMode = 'personal';
    let currentPriority = 'balanced';
    let landmarks = [];
    let qpsoPolyline = null;
    let baselinePolyline = null;
    let fleetPolylines = [];
    let originMarker = null;
    let destMarker = null;
    let navVehicleMarker = null;
    let navInterval = null;
    let currentTripId = null;
    let wsConnection = null;
    let lastComparisonData = null;

    // Custom Map Marker Icons
    const originIcon = L.divIcon({
        className: 'custom-marker',
        html: '<div style="background:#00E676;width:16px;height:16px;border-radius:50%;border:2px solid #fff;box-shadow:0 0 10px #00E676;"></div>',
        iconSize: [16, 16],
        iconAnchor: [8, 8]
    });

    const destIcon = L.divIcon({
        className: 'custom-marker',
        html: '<div style="background:#00F0FF;width:18px;height:18px;border-radius:50%;border:2px solid #fff;box-shadow:0 0 14px #00F0FF;"></div>',
        iconSize: [18, 18],
        iconAnchor: [9, 9]
    });

    const vehicleIcon = L.divIcon({
        className: 'vehicle-nav-marker',
        html: '<div style="background:#00F0FF;width:24px;height:24px;border-radius:50%;border:3px solid #fff;display:flex;align-items:center;justify-content:center;box-shadow:0 0 16px #00F0FF;"><i class="fa-solid fa-location-arrow" style="color:#000;font-size:11px;transform:rotate(-45deg);"></i></div>',
        iconSize: [24, 24],
        iconAnchor: [12, 12]
    });

    // 2. Fetch Landmarks from Backend
    async function loadLandmarks() {
        try {
            const res = await fetch('/api/landmarks');
            if (res.ok) {
                landmarks = await res.json();
                populateDropdowns();
            }
        } catch (e) {
            console.error('Error loading landmarks:', e);
        }
    }

    function populateDropdowns() {
        const originSel = document.getElementById('originSelect');
        const destSel = document.getElementById('destSelect');
        const depotSel = document.getElementById('fleetDepotSelect');

        if (!landmarks || landmarks.length === 0) return;

        originSel.innerHTML = '';
        destSel.innerHTML = '';
        depotSel.innerHTML = '';

        landmarks.forEach((lm, idx) => {
            const opt1 = new Option(lm.name, lm.id);
            const opt2 = new Option(lm.name, lm.id);
            const opt3 = new Option(lm.name, lm.id);

            originSel.add(opt1);
            destSel.add(opt2);
            depotSel.add(opt3);
        });

        // Set initial selections
        originSel.value = 'cp_park';
        destSel.value = 'india_gate';
        depotSel.value = 'cp_park';

        // Auto calculate initial route
        computePersonalRoute();
    }

    // 3. Tab Switching
    const tabs = document.querySelectorAll('.tab-btn');
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            tabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');

            const mode = tab.dataset.tab;
            currentMode = mode;

            document.getElementById('personalPanel').style.display = (mode === 'personal' || mode === 'emergency') ? 'flex' : 'none';
            document.getElementById('fleetPanel').style.display = mode === 'fleet' ? 'flex' : 'none';
            document.getElementById('simulatorPanel').style.display = mode === 'simulator' ? 'flex' : 'none';

            if (mode === 'emergency') {
                computePersonalRoute();
            } else if (mode === 'fleet') {
                solveFleetRoute();
            }
        });
    });

    // Priority Pills
    const prioPills = document.querySelectorAll('.prio-pill');
    prioPills.forEach(pill => {
        pill.addEventListener('click', () => {
            prioPills.forEach(p => p.classList.remove('active'));
            pill.classList.add('active');
            currentPriority = pill.dataset.prio;
            computePersonalRoute();
        });
    });

    // 4. Calculate Personal Quantum Route
    async function computePersonalRoute() {
        const originId = document.getElementById('originSelect').value;
        const destId = document.getElementById('destSelect').value;

        const originLm = landmarks.find(l => l.id === originId) || { lat: 28.6315, lon: 77.2167, node_id: 0 };
        const destLm = landmarks.find(l => l.id === destId) || { lat: 28.6129, lon: 77.2295, node_id: 25 };

        currentTripId = `trip_${Date.now()}`;

        const payload = {
            source: { lat: originLm.lat, lon: originLm.lon, node_id: originLm.node_id, label: originLm.name },
            destination: { lat: destLm.lat, lon: destLm.lon, node_id: destLm.node_id, label: destLm.name },
            mode: currentMode === 'emergency' ? 'emergency' : 'personal',
            priority: currentPriority,
            trip_id: currentTripId
        };

        const btn = document.getElementById('btnComputeRoute');
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> OPTIMIZING QUANTUM STATE...';

        try {
            const res = await fetch('/api/route', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (res.ok) {
                const data = await res.json();
                renderRouteComparison(data.comparison);
            }
        } catch (e) {
            console.error('Route calculation failed:', e);
        } finally {
            btn.innerHTML = '<i class="fa-solid fa-atom"></i> RUN QUANTUM ROUTE OPTIMIZATION';
        }
    }

    function renderRouteComparison(comp) {
        lastComparisonData = comp;

        // Clear existing polylines & markers
        if (qpsoPolyline) map.removeLayer(qpsoPolyline);
        if (baselinePolyline) map.removeLayer(baselinePolyline);
        if (originMarker) map.removeLayer(originMarker);
        if (destMarker) map.removeLayer(destMarker);
        clearFleetLayers();

        const qpsoCoords = comp.qpso_route.coordinates;
        const baseCoords = comp.baseline_route.coordinates;

        // Draw Standard Baseline (Dotted Gray)
        if (baseCoords && baseCoords.length > 0) {
            baselinePolyline = L.polyline(baseCoords, {
                color: '#64748B',
                weight: 5,
                opacity: 0.7,
                dashArray: '8, 8'
            }).addTo(map);
        }

        // Draw QPSO Quantum Route (Glowing Neon Cyan or Emergency Red)
        const lineColor = currentMode === 'emergency' ? '#FF385C' : '#00F0FF';
        if (qpsoCoords && qpsoCoords.length > 0) {
            qpsoPolyline = L.polyline(qpsoCoords, {
                color: lineColor,
                weight: 6,
                opacity: 0.95
            }).addTo(map);

            // Fit map bounds to show route
            map.fitBounds(qpsoPolyline.getBounds(), { padding: [40, 40] });

            // Place origin and destination markers
            originMarker = L.marker(qpsoCoords[0], { icon: originIcon }).addTo(map).bindPopup('<b>Origin</b>');
            destMarker = L.marker(qpsoCoords[qpsoCoords.length - 1], { icon: destIcon }).addTo(map).bindPopup('<b>Destination</b>');
        }

        // Update UI Card
        document.getElementById('comparisonCard').style.display = 'flex';
        document.getElementById('qpsoTime').textContent = comp.qpso_route.metrics.total_time_formatted;
        document.getElementById('qpsoDist').textContent = `(${comp.qpso_route.metrics.total_distance_formatted})`;
        document.getElementById('efficiencyScore').textContent = `${Math.round(comp.quantum_efficiency_score)}% Efficient`;
        document.getElementById('timeSavedBadge').textContent = comp.time_saved_seconds > 0 
            ? `-${(comp.time_saved_seconds / 60).toFixed(1)} min faster` 
            : 'Optimal Baseline';

        document.getElementById('metricCongAvoid').textContent = `${Math.round(comp.congestion_reduction_percent)}%`;
        document.getElementById('metricSmoothness').textContent = `${Math.round(comp.qpso_route.metrics.avg_road_condition_score * 100)}%`;
        document.getElementById('metricCarbon').textContent = `${comp.qpso_route.metrics.carbon_emission_kg} kg`;
    }

    // 5. Live Navigation & WebSocket Stream
    document.getElementById('btnStartNav').addEventListener('click', () => {
        if (!lastComparisonData) return;

        document.getElementById('comparisonCard').style.display = 'none';
        document.getElementById('navigationCard').style.display = 'block';

        const coords = lastComparisonData.qpso_route.coordinates;
        if (!coords || coords.length === 0) return;

        // Initialize WebSocket connection for live reroute alerts
        initWebSocket(currentTripId);

        // Start vehicle movement simulation along coordinates
        let coordIdx = 0;
        if (navVehicleMarker) map.removeLayer(navVehicleMarker);
        navVehicleMarker = L.marker(coords[0], { icon: vehicleIcon }).addTo(map);

        clearInterval(navInterval);
        navInterval = setInterval(() => {
            if (coordIdx >= coords.length) {
                clearInterval(navInterval);
                return;
            }

            const currentPos = coords[coordIdx];
            navVehicleMarker.setLatLng(currentPos);
            map.panTo(currentPos);

            // Update Speed & Instruction
            const segments = lastComparisonData.qpso_route.segments || [];
            const segIdx = Math.min(Math.floor((coordIdx / coords.length) * segments.length), segments.length - 1);
            if (segments[segIdx]) {
                document.getElementById('navInstruction').textContent = segments[segIdx].instruction || 'Follow highlighted route';
            }
            document.getElementById('navSpeedVal').textContent = Math.round(40 + Math.sin(coordIdx) * 8);

            coordIdx++;
        }, 1500);
    });

    document.getElementById('btnStopNav').addEventListener('click', () => {
        clearInterval(navInterval);
        if (navVehicleMarker) map.removeLayer(navVehicleMarker);
        if (wsConnection) wsConnection.close();

        document.getElementById('navigationCard').style.display = 'none';
        document.getElementById('comparisonCard').style.display = 'flex';
        document.getElementById('liveIncidentToast').style.display = 'none';
    });

    function initWebSocket(tripId) {
        if (wsConnection) wsConnection.close();

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/route/${tripId}`;

        try {
            wsConnection = new WebSocket(wsUrl);

            wsConnection.onopen = () => {
                const originId = document.getElementById('originSelect').value;
                const destId = document.getElementById('destSelect').value;
                const originLm = landmarks.find(l => l.id === originId) || { lat: 28.6315, lon: 77.2167 };
                const destLm = landmarks.find(l => l.id === destId) || { lat: 28.6129, lon: 77.2295 };

                wsConnection.send(JSON.stringify({
                    action: 'START_TRIP',
                    source: { lat: originLm.lat, lon: originLm.lon },
                    destination: { lat: destLm.lat, lon: destLm.lon },
                    priority: currentPriority,
                    mode: currentMode
                }));
            };

            wsConnection.onmessage = (event) => {
                const data = JSON.parse(event.data);
                if (data.type === 'REROUTE_RECOMMENDATION') {
                    showIncidentToast(data);
                }
            };
        } catch (e) {
            console.error('WebSocket connection error:', e);
        }
    }

    function showIncidentToast(data) {
        const toast = document.getElementById('liveIncidentToast');
        document.getElementById('toastDesc').textContent = `${data.message} Detour saves ${data.time_saved_formatted || '5.4 min'}.`;
        toast.style.display = 'flex';

        document.getElementById('btnAcceptReroute').onclick = () => {
            if (data.new_comparison) {
                renderRouteComparison(data.new_comparison);
            }
            toast.style.display = 'none';
        };

        document.getElementById('btnIgnoreReroute').onclick = () => {
            toast.style.display = 'none';
        };
    }

    // 6. Fleet Logistics VRP Mode
    let demoStops = [
        { lat: 28.6129, lon: 77.2295, label: 'India Gate Plaza' },
        { lat: 28.6429, lon: 77.2195, label: 'NDLS Freight Hub' },
        { lat: 28.6180, lon: 77.2425, label: 'Bharat Mandapam' },
        { lat: 28.6520, lon: 77.1900, label: 'Karol Bagh Depot' }
    ];
    let selectedVehicleCount = 2;

    function renderStopsList() {
        const container = document.getElementById('stopsListContainer');
        container.innerHTML = '';
        document.getElementById('stopCount').textContent = demoStops.length;

        demoStops.forEach((stop, i) => {
            const li = document.createElement('li');
            li.className = 'stop-item';
            li.innerHTML = `
                <span><i class="fa-solid fa-box text-cyan"></i> Stop ${i+1}: ${stop.label}</span>
                <i class="fa-solid fa-trash-can" style="cursor:pointer;color:#FF385C;" onclick="removeStop(${i})"></i>
            `;
            container.appendChild(li);
        });
    }

    window.removeStop = function(index) {
        demoStops.splice(index, 1);
        renderStopsList();
        solveFleetRoute();
    };

    document.getElementById('btnAddDemoStop').addEventListener('click', () => {
        const extraStops = [
            { lat: 28.5850, lon: 77.1650, label: 'Tech City Corridor' },
            { lat: 28.5562, lon: 77.1000, label: 'Airport Express Hub' },
            { lat: 28.5672, lon: 77.2100, label: 'AIIMS South Terminal' }
        ];
        const next = extraStops[demoStops.length % extraStops.length];
        demoStops.push(next);
        renderStopsList();
        solveFleetRoute();
    });

    const vPills = document.querySelectorAll('.v-pill');
    vPills.forEach(vp => {
        vp.addEventListener('click', () => {
            vPills.forEach(p => p.classList.remove('active'));
            vp.classList.add('active');
            selectedVehicleCount = parseInt(vp.dataset.count);
            solveFleetRoute();
        });
    });

    async function solveFleetRoute() {
        renderStopsList();
        clearFleetLayers();
        if (qpsoPolyline) map.removeLayer(qpsoPolyline);
        if (baselinePolyline) map.removeLayer(baselinePolyline);

        const colors = ['#00F0FF', '#7928CA', '#FF007F', '#00E676'];
        const vehicles = [];
        for (let i = 0; i < selectedVehicleCount; i++) {
            vehicles.push({
                vehicle_id: `v${i+1}`,
                name: `Quantum Van ${i+1}`,
                capacity: 100,
                color: colors[i % colors.length]
            });
        }

        const payload = {
            depot: { lat: 28.6315, lon: 77.2167, label: 'Central CP Depot' },
            stops: demoStops,
            vehicles: vehicles
        };

        const btn = document.getElementById('btnSolveFleet');
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> PARTITIONING VEHICLE TOURS...';

        try {
            const res = await fetch('/api/fleet/route', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (res.ok) {
                const data = await res.json();
                renderFleetResults(data);
            }
        } catch (e) {
            console.error('Fleet route failed:', e);
        } finally {
            btn.innerHTML = '<i class="fa-solid fa-microchip"></i> SOLVE QUANTUM FLEET VRP';
        }
    }

    function renderFleetResults(data) {
        document.getElementById('fleetSummaryCard').style.display = 'block';
        document.getElementById('fleetTotalTime').textContent = data.total_fleet_time_formatted;
        document.getElementById('fleetTotalDist').textContent = data.total_fleet_distance_formatted;
        document.getElementById('fleetTotalFuel').textContent = `${data.total_fuel_liters} L`;

        const toursList = document.getElementById('vehicleToursList');
        toursList.innerHTML = '';

        const allLatLngs = [];

        data.fleet_routes.forEach(vr => {
            const card = document.createElement('div');
            card.className = 'vehicle-tour-card';
            card.style.borderLeftColor = vr.color;
            card.innerHTML = `
                <div>
                    <div style="font-weight:800;color:#fff;">${vr.vehicle_name}</div>
                    <div style="font-size:11px;color:#94A3B8;">${vr.stops.length - 2} drops assigned • ${vr.total_distance_formatted}</div>
                </div>
                <div style="font-weight:800;color:${vr.color};">${vr.total_time_formatted}</div>
            `;
            toursList.appendChild(card);

            // Draw polyline on map
            if (vr.path.coordinates && vr.path.coordinates.length > 0) {
                const poly = L.polyline(vr.path.coordinates, {
                    color: vr.color,
                    weight: 5,
                    opacity: 0.9
                }).addTo(map);
                fleetPolylines.push(poly);
                allLatLngs.push(...vr.path.coordinates);
            }
        });

        if (allLatLngs.length > 0) {
            map.fitBounds(L.latLngBounds(allLatLngs), { padding: [40, 40] });
        }
    }

    function clearFleetLayers() {
        fleetPolylines.forEach(p => map.removeLayer(p));
        fleetPolylines = [];
    }

    // 7. What-If Scenario Simulator Mode
    const simSlider = document.getElementById('simTimeSlider');
    simSlider.addEventListener('input', (e) => {
        const val = parseFloat(e.target.value);
        const hour = Math.floor(val);
        const min = (val - hour) * 60;
        const period = hour >= 12 ? 'PM' : 'AM';
        const displayH = hour > 12 ? hour - 12 : (hour === 0 ? 12 : hour);
        const isRush = (val >= 8 && val <= 10.5) || (val >= 17 && val <= 20);

        document.getElementById('simTimeDisplay').textContent = 
            `${String(displayH).padStart(2, '0')}:${String(min).padStart(2, '0')} ${period} (${isRush ? '🔴 PEAK RUSH' : '🟢 NORMAL FLOW'})`;
    });

    let selectedWeather = 'rain_monsoon';
    document.querySelectorAll('.weather-pill').forEach(wp => {
        wp.addEventListener('click', () => {
            document.querySelectorAll('.weather-pill').forEach(p => p.classList.remove('active'));
            wp.classList.add('active');
            selectedWeather = wp.dataset.weather;
        });
    });

    document.getElementById('btnRunSimulation').addEventListener('click', async () => {
        const payload = {
            scenario_name: document.getElementById('simPresetSelect').options[document.getElementById('simPresetSelect').selectedIndex].text,
            time_of_day_hours: parseFloat(simSlider.value),
            weather: selectedWeather,
            source: { lat: 28.6315, lon: 77.2167 },
            destination: { lat: 28.5850, lon: 77.1650 },
            inject_closures: 1,
            inject_accidents: 1
        };

        const btn = document.getElementById('btnRunSimulation');
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> COMPUTING MONTE CARLO STRESS TEST...';

        try {
            const res = await fetch('/api/simulate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (res.ok) {
                const data = await res.json();
                document.getElementById('simResultsCard').style.display = 'block';
                document.getElementById('simAiRec').textContent = data.ai_recommendation;
                document.getElementById('simStdTime').textContent = data.stressed_route_standard.metrics.total_time_formatted;
                document.getElementById('simQpsoTime').textContent = data.stressed_route_qpso.metrics.total_time_formatted;

                // Render stressed comparison on map
                renderRouteComparison({
                    qpso_route: data.stressed_route_qpso,
                    baseline_route: data.stressed_route_standard,
                    time_saved_seconds: data.metrics_delta.time_saved_sec || 540,
                    congestion_reduction_percent: data.metrics_delta.congestion_mitigation_percent || 38,
                    roughness_reduction_percent: data.metrics_delta.roughness_avoidance_percent || 45,
                    quantum_efficiency_score: 92
                });
            }
        } catch (e) {
            console.error('Simulation error:', e);
        } finally {
            btn.innerHTML = '<i class="fa-solid fa-play"></i> EXECUTE PRE-TRIP SIMULATION';
        }
    });

    // 8. SIH Judge Demo Modal Controls
    const judgeModal = document.getElementById('judgeModal');
    document.getElementById('btnJudgeConsole').addEventListener('click', () => {
        judgeModal.style.display = 'flex';
    });
    document.getElementById('btnCloseJudgeModal').addEventListener('click', () => {
        judgeModal.style.display = 'none';
    });

    async function injectDemoIncident(type, desc) {
        judgeModal.style.display = 'none';
        try {
            const res = await fetch('/api/incident', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    incident_type: type,
                    lat: 28.6250,
                    lon: 77.2250,
                    radius_meters: 350,
                    severity: 3.8,
                    description: desc
                })
            });
            if (res.ok) {
                computePersonalRoute();
            }
        } catch (e) {
            console.error('Error injecting incident:', e);
        }
    }

    document.getElementById('btnInjectAccident').addEventListener('click', () => {
        injectDemoIncident('accident', '5-Car Pileup on Janpath Arterial');
    });
    document.getElementById('btnInjectClosure').addEventListener('click', () => {
        injectDemoIncident('closure', 'Emergency Flyover Structural Closure');
    });
    document.getElementById('btnInjectWaterlogging').addEventListener('click', () => {
        injectDemoIncident('pothole_hazard', 'Severe Monsoon Waterlogging & Potholes');
    });
    document.getElementById('btnInjectCongestion').addEventListener('click', () => {
        injectDemoIncident('congestion', '3.5x Heavy Traffic Wave Surge');
    });

    document.getElementById('btnResetGraph').addEventListener('click', async () => {
        judgeModal.style.display = 'none';
        await fetch('/api/reset', { method: 'POST' });
        computePersonalRoute();
    });

    document.getElementById('btnSwapLocations').addEventListener('click', () => {
        const originSel = document.getElementById('originSelect');
        const destSel = document.getElementById('destSelect');
        const temp = originSel.value;
        originSel.value = destSel.value;
        destSel.value = temp;
        computePersonalRoute();
    });

    document.getElementById('btnComputeRoute').addEventListener('click', computePersonalRoute);

    // Initial Load
    loadLandmarks();
});
