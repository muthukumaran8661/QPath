// QPath Quantum Traffic Optimizer - Web Application Logic
document.addEventListener('DOMContentLoaded', () => {
    // 1. Initialize Leaflet Map
    const map = L.map('map', {
        center: [28.6315, 77.2167], // Default: New Delhi Center
        zoom: 12,
        zoomControl: false
    });

    L.control.zoom({ position: 'bottomright' }).addTo(map);

    // Standard OpenStreetMap Tiles (Zero API Keys Required)
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank">OpenStreetMap</a> contributors'
    }).addTo(map);

    // State Variables
    let currentMode = 'personal';
    let currentPriority = 'balanced';
    let landmarks = [];
    let qpsoPolyline = null;
    let baselinePolyline = null;
    let alternativePolylines = [];
    let fleetPolylines = [];
    let originMarker = null;
    let destMarker = null;
    let navVehicleMarker = null;
    let navInterval = null;
    let currentTripId = null;
    let wsConnection = null;
    let lastComparisonData = null;

    // Pan-India Coordinates State
    let originCoords = { lat: 28.6315, lon: 77.2167, label: 'Connaught Place, New Delhi' };
    let destCoords = { lat: 28.6129, lon: 77.2295, label: 'India Gate, New Delhi' };
    let emgOriginCoords = { lat: 28.5672, lon: 77.2100, label: 'AIIMS Trauma Center, New Delhi' };
    let emgDestCoords = { lat: 28.6129, lon: 77.2295, label: 'India Gate, New Delhi' };
    const geocodeCache = new Map();

    // Custom Map Marker Icons
    const originIcon = L.divIcon({
        className: 'custom-marker',
        html: '<div style="background:#00E676;width:18px;height:18px;border-radius:50%;border:2px solid #fff;box-shadow:0 0 12px #00E676;cursor:grab;"></div>',
        iconSize: [18, 18],
        iconAnchor: [9, 9]
    });

    const destIcon = L.divIcon({
        className: 'custom-marker',
        html: '<div style="background:#00F0FF;width:18px;height:18px;border-radius:50%;border:2px solid #fff;box-shadow:0 0 14px #00F0FF;cursor:grab;"></div>',
        iconSize: [18, 18],
        iconAnchor: [9, 9]
    });

    const vehicleIcon = L.divIcon({
        className: 'vehicle-nav-marker',
        html: '<div style="background:#00F0FF;width:24px;height:24px;border-radius:50%;border:3px solid #fff;display:flex;align-items:center;justify-content:center;box-shadow:0 0 16px #00F0FF;"><i class="fa-solid fa-location-arrow" style="color:#000;font-size:11px;transform:rotate(-45deg);"></i></div>',
        iconSize: [24, 24],
        iconAnchor: [12, 12]
    });

    // 2. Geocoding Service (Photon with India Bias & Nominatim Fallback)
    async function searchPlaces(query) {
        if (!query || query.trim().length < 2) return [];
        const cleanQuery = query.trim();
        const cacheKey = cleanQuery.toLowerCase();
        if (geocodeCache.has(cacheKey)) {
            return geocodeCache.get(cacheKey);
        }

        let results = [];
        // 1. Try Photon (free, biased to India via center coordinates)
        try {
            const photonUrl = `https://photon.komoot.io/api/?q=${encodeURIComponent(cleanQuery)}&limit=5&lang=en&lat=20.5937&lon=78.9629`;
            const resp = await fetch(photonUrl);
            if (resp.ok) {
                const data = await resp.json();
                if (data.features && data.features.length > 0) {
                    results = data.features.map(f => {
                        const p = f.properties;
                        const name = p.name || p.city || p.street || cleanQuery;
                        const areaParts = [p.district, p.city, p.state, p.country].filter(Boolean);
                        const uniqueArea = [...new Set(areaParts)].filter(part => part !== name).join(', ');
                        return {
                            name: name,
                            area: uniqueArea || 'India',
                            lat: f.geometry.coordinates[1],
                            lon: f.geometry.coordinates[0]
                        };
                    });
                }
            }
        } catch (e) {
            console.warn('Photon geocoding notice:', e);
        }

        // 2. Fallback to Nominatim if Photon returns no results
        if (results.length === 0) {
            try {
                const nomUrl = `https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(cleanQuery)}&format=json&limit=5&countrycodes=in&addressdetails=1`;
                const resp = await fetch(nomUrl, { headers: { 'Accept': 'application/json' } });
                if (resp.ok) {
                    const data = await resp.json();
                    results = data.map(item => ({
                        name: item.name || item.display_name.split(',')[0],
                        area: item.display_name.split(',').slice(1, 4).join(',').trim() || 'India',
                        lat: parseFloat(item.lat),
                        lon: parseFloat(item.lon)
                    }));
                }
            } catch (e) {
                console.warn('Nominatim fallback notice:', e);
            }
        }

        geocodeCache.set(cacheKey, results);
        return results;
    }

    async function reverseGeocode(lat, lon) {
        const cacheKey = `rev_${lat.toFixed(4)}_${lon.toFixed(4)}`;
        if (geocodeCache.has(cacheKey)) return geocodeCache.get(cacheKey);

        try {
            const url = `https://nominatim.openstreetmap.org/reverse?lat=${lat}&lon=${lon}&format=json`;
            const resp = await fetch(url, { headers: { 'Accept': 'application/json' } });
            if (resp.ok) {
                const data = await resp.json();
                const name = data.name || (data.address ? (data.address.suburb || data.address.city || data.address.town || data.address.road) : null) || `${lat.toFixed(4)}, ${lon.toFixed(4)}`;
                geocodeCache.set(cacheKey, name);
                return name;
            }
        } catch (e) {
            console.warn('Reverse geocode error:', e);
        }
        return `${lat.toFixed(4)}, ${lon.toFixed(4)}`;
    }

    // 3. Autocomplete Setup Helper
    function setupAutocomplete(inputId, dropdownId, clearBtnId, onSelect) {
        const input = document.getElementById(inputId);
        const dropdown = document.getElementById(dropdownId);
        const clearBtn = clearBtnId ? document.getElementById(clearBtnId) : null;
        if (!input || !dropdown) return;

        let debounceTimer = null;

        input.addEventListener('input', () => {
            const val = input.value;
            if (clearBtn) clearBtn.style.display = val.length > 0 ? 'block' : 'none';

            clearTimeout(debounceTimer);
            if (val.trim().length < 2) {
                dropdown.style.display = 'none';
                dropdown.innerHTML = '';
                return;
            }

            debounceTimer = setTimeout(async () => {
                dropdown.innerHTML = '<div style="padding:8px 10px;font-size:11px;color:#94a3b8;"><i class="fa-solid fa-spinner fa-spin"></i> Searching locations in India...</div>';
                dropdown.style.display = 'block';

                const suggestions = await searchPlaces(val);
                if (suggestions.length === 0) {
                    dropdown.innerHTML = '<div style="padding:8px 10px;font-size:11px;color:#94a3b8;">No locations found. Press enter or click map.</div>';
                    return;
                }

                dropdown.innerHTML = '';
                suggestions.forEach(s => {
                    const item = document.createElement('div');
                    item.className = 'suggestion-item';
                    item.innerHTML = `
                        <div class="suggestion-title">${s.name}</div>
                        <div class="suggestion-area">${s.area}</div>
                    `;
                    item.addEventListener('click', () => {
                        input.value = s.name;
                        dropdown.style.display = 'none';
                        if (clearBtn) clearBtn.style.display = 'block';
                        onSelect(s);
                    });
                    dropdown.appendChild(item);
                });
            }, 300);
        });

        if (clearBtn) {
            clearBtn.addEventListener('click', () => {
                input.value = '';
                clearBtn.style.display = 'none';
                dropdown.style.display = 'none';
                input.focus();
            });
        }

        document.addEventListener('click', (e) => {
            if (!input.contains(e.target) && !dropdown.contains(e.target)) {
                dropdown.style.display = 'none';
            }
        });
    }

    // Initialize Autocomplete for Personal Commute
    setupAutocomplete('originInput', 'originSuggestions', 'btnClearOrigin', (item) => {
        originCoords = { lat: item.lat, lon: item.lon, label: item.name };
        computePersonalRoute();
    });

    setupAutocomplete('destInput', 'destSuggestions', 'btnClearDest', (item) => {
        destCoords = { lat: item.lat, lon: item.lon, label: item.name };
        computePersonalRoute();
    });

    // Initialize Autocomplete for Emergency Panel
    setupAutocomplete('emgOriginInput', 'emgOriginSuggestions', null, (item) => {
        emgOriginCoords = { lat: item.lat, lon: item.lon, label: item.name };
    });

    setupAutocomplete('emgDestInput', 'emgDestSuggestions', null, (item) => {
        emgDestCoords = { lat: item.lat, lon: item.lon, label: item.name };
    });

    // "Use My Current Location" (Browser Geolocation)
    const btnUseLocation = document.getElementById('btnUseCurrentLocation');
    if (btnUseLocation) {
        btnUseLocation.addEventListener('click', () => {
            if (!navigator.geolocation) {
                alert('Geolocation is not supported by your browser.');
                return;
            }
            btnUseLocation.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Locating...';
            navigator.geolocation.getCurrentPosition(
                async (position) => {
                    const lat = position.coords.latitude;
                    const lon = position.coords.longitude;
                    const placeName = await reverseGeocode(lat, lon);
                    originCoords = { lat, lon, label: placeName };
                    document.getElementById('originInput').value = placeName;
                    const clearOrigin = document.getElementById('btnClearOrigin');
                    if (clearOrigin) clearOrigin.style.display = 'block';
                    btnUseLocation.innerHTML = '<i class="fa-solid fa-location-crosshairs"></i> My Location';
                    computePersonalRoute();
                },
                (err) => {
                    console.warn('Geolocation error:', err);
                    btnUseLocation.innerHTML = '<i class="fa-solid fa-location-crosshairs"></i> My Location';
                    alert('Unable to retrieve your current location. Please allow location permissions in your browser.');
                },
                { enableHighAccuracy: true, timeout: 8000 }
            );
        });
    }

    // Popular Quick-Picks Pills
    document.querySelectorAll('.quick-pick-pill').forEach(pill => {
        pill.addEventListener('click', () => {
            const city = pill.dataset.city;
            const lat = parseFloat(pill.dataset.lat);
            const lon = parseFloat(pill.dataset.lon);

            // Set destination to selected quick city
            destCoords = { lat, lon, label: city };
            document.getElementById('destInput').value = city;
            const clearDest = document.getElementById('btnClearDest');
            if (clearDest) clearDest.style.display = 'block';
            computePersonalRoute();
        });
    });

    // Swap Locations (Origin <-> Destination)
    document.getElementById('btnSwapLocations')?.addEventListener('click', () => {
        const originInput = document.getElementById('originInput');
        const destInput = document.getElementById('destInput');

        // Swap coordinates
        const tempCoords = { ...originCoords };
        originCoords = { ...destCoords };
        destCoords = tempCoords;

        // Swap input text
        const tempVal = originInput.value;
        originInput.value = destInput.value;
        destInput.value = tempVal;

        computePersonalRoute();
    });

    // Interactive Map Click Handler: Set Origin or Destination
    map.on('click', async (e) => {
        const lat = e.latlng.lat;
        const lon = e.latlng.lng;
        const placeName = await reverseGeocode(lat, lon);

        // Calculate distance to current origin and dest
        const distToOrigin = Math.hypot(lat - originCoords.lat, lon - originCoords.lon);
        const distToDest = Math.hypot(lat - destCoords.lat, lon - destCoords.lon);

        if (distToOrigin < distToDest) {
            // Closer to origin -> update origin
            originCoords = { lat, lon, label: placeName };
            document.getElementById('originInput').value = placeName;
        } else {
            // Closer to dest -> update dest
            destCoords = { lat, lon, label: placeName };
            document.getElementById('destInput').value = placeName;
        }
        computePersonalRoute();
    });

    // 4. Tab Switching
    const tabs = document.querySelectorAll('.tab-btn');
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            tabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');

            const mode = tab.dataset.tab;
            currentMode = mode;

            // Hide all panels first
            document.getElementById('personalPanel').style.display = 'none';
            document.getElementById('fleetPanel').style.display = 'none';
            document.getElementById('simulatorPanel').style.display = 'none';
            document.getElementById('emergencyPanel').style.display = 'none';

            // Show the relevant panel
            if (mode === 'personal') {
                document.getElementById('personalPanel').style.display = 'flex';
                computePersonalRoute();
            } else if (mode === 'fleet') {
                document.getElementById('fleetPanel').style.display = 'flex';
                solveFleetRoute();
            } else if (mode === 'simulator') {
                document.getElementById('simulatorPanel').style.display = 'flex';
            } else if (mode === 'emergency') {
                document.getElementById('emergencyPanel').style.display = 'flex';
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

    // 5. Calculate Pan-India Quantum Route
    async function computePersonalRoute() {
        if (!originCoords || !destCoords) return;

        currentTripId = `trip_${Date.now()}`;

        const payload = {
            origin: { lat: originCoords.lat, lon: originCoords.lon, label: originCoords.label },
            destination: { lat: destCoords.lat, lon: destCoords.lon, label: destCoords.label },
            mode: currentMode === 'emergency' ? 'emergency' : 'personal',
            priority: currentPriority,
            trip_id: currentTripId
        };

        const btn = document.getElementById('btnComputeRoute');
        if (btn) btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> OPTIMIZING QUANTUM ROUTE...';

        try {
            const res = await fetch('/api/route', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (res.ok) {
                const data = await res.json();
                renderRouteComparison(data.comparison);
            } else {
                const errData = await res.json();
                alert(errData.detail || 'Routing failed. Please choose different locations.');
            }
        } catch (e) {
            console.error('Route calculation failed:', e);
        } finally {
            if (btn) btn.innerHTML = '<i class="fa-solid fa-atom"></i> RUN QUANTUM ROUTE OPTIMIZATION';
        }
    }

    function renderRouteComparison(comp) {
        lastComparisonData = comp;

        // Clear existing polylines & markers
        if (qpsoPolyline) map.removeLayer(qpsoPolyline);
        if (baselinePolyline) map.removeLayer(baselinePolyline);
        alternativePolylines.forEach(p => map.removeLayer(p));
        alternativePolylines = [];
        if (originMarker) map.removeLayer(originMarker);
        if (destMarker) map.removeLayer(destMarker);
        clearFleetLayers();

        const qpsoCoords = comp.qpso_route.coordinates;
        const baseCoords = comp.baseline_route.coordinates;
        const alternatives = comp.alternative_routes || [];

        // 1. Draw Alternative Candidate Routes in faint slate grey
        alternatives.forEach(alt => {
            if (alt.coordinates && alt.coordinates.length > 0) {
                const poly = L.polyline(alt.coordinates, {
                    color: '#475569',
                    weight: 4,
                    opacity: 0.45
                }).addTo(map);
                alternativePolylines.push(poly);
            }
        });

        // 2. Draw Standard Baseline Route (Dotted Slate Gray)
        if (baseCoords && baseCoords.length > 0) {
            baselinePolyline = L.polyline(baseCoords, {
                color: '#64748B',
                weight: 5,
                opacity: 0.7,
                dashArray: '8, 8'
            }).addTo(map);
        }

        // 3. Draw QPSO Quantum Route (Glowing Neon Cyan or Emergency Red)
        const lineColor = currentMode === 'emergency' ? '#FF385C' : '#00F0FF';
        if (qpsoCoords && qpsoCoords.length > 0) {
            qpsoPolyline = L.polyline(qpsoCoords, {
                color: lineColor,
                weight: 6,
                opacity: 0.95
            }).addTo(map);

            // Auto-zoom map bounds to fit route
            map.fitBounds(qpsoPolyline.getBounds(), { padding: [40, 40] });

            // Place draggable Origin and Destination markers
            const startPt = qpsoCoords[0];
            const endPt = qpsoCoords[qpsoCoords.length - 1];

            originMarker = L.marker(startPt, { icon: originIcon, draggable: true }).addTo(map)
                .bindPopup(`<b>Origin:</b> ${originCoords.label || 'Origin'}<br><small>Drag marker to adjust</small>`);

            destMarker = L.marker(endPt, { icon: destIcon, draggable: true }).addTo(map)
                .bindPopup(`<b>Destination:</b> ${destCoords.label || 'Destination'}<br><small>Drag marker to adjust</small>`);

            // Marker Drag Events
            originMarker.on('dragend', async (e) => {
                const pos = e.target.getLatLng();
                originCoords.lat = pos.lat;
                originCoords.lon = pos.lng;
                const name = await reverseGeocode(pos.lat, pos.lng);
                originCoords.label = name;
                document.getElementById('originInput').value = name;
                computePersonalRoute();
            });

            destMarker.on('dragend', async (e) => {
                const pos = e.target.getLatLng();
                destCoords.lat = pos.lat;
                destCoords.lon = pos.lng;
                const name = await reverseGeocode(pos.lat, pos.lng);
                destCoords.label = name;
                document.getElementById('destInput').value = name;
                computePersonalRoute();
            });
        }

        // Update UI Comparison Metrics Card
        const compCard = document.getElementById('comparisonCard');
        if (compCard) {
            compCard.style.display = 'flex';
            document.getElementById('qpsoTime').textContent = comp.qpso_route.metrics.total_time_formatted;
            document.getElementById('qpsoDist').textContent = `(${comp.qpso_route.metrics.total_distance_formatted})`;
            document.getElementById('efficiencyScore').textContent = `${Math.round(comp.quantum_efficiency_score)}% Score`;
            document.getElementById('timeSavedBadge').textContent = comp.time_saved_seconds > 0 
                ? `-${(comp.time_saved_seconds / 60).toFixed(1)} min faster` 
                : 'Optimal Multi-Objective';

            document.getElementById('metricCongAvoid').textContent = `${Math.round(comp.congestion_reduction_percent)}%`;
            document.getElementById('metricSmoothness').textContent = `${Math.round(comp.qpso_route.metrics.avg_road_condition_score * 100)}%`;
            document.getElementById('metricCarbon').textContent = `${comp.qpso_route.metrics.carbon_emission_kg} kg`;
        }
    }

    // 6. Live Navigation & WebSocket Stream
    document.getElementById('btnStartNav')?.addEventListener('click', () => {
        if (!lastComparisonData) return;

        document.getElementById('comparisonCard').style.display = 'none';
        document.getElementById('navigationCard').style.display = 'block';

        const coords = lastComparisonData.qpso_route.coordinates;
        if (!coords || coords.length === 0) return;

        // Initialize WebSocket connection for live reroute alerts
        initWebSocket(currentTripId);

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

            const segments = lastComparisonData.qpso_route.segments || [];
            const segIdx = Math.min(Math.floor((coordIdx / coords.length) * segments.length), segments.length - 1);
            if (segments[segIdx]) {
                document.getElementById('navInstruction').textContent = segments[segIdx].instruction || 'Follow highlighted route';
            }
            document.getElementById('navSpeedVal').textContent = Math.round(40 + Math.sin(coordIdx) * 8);

            coordIdx++;
        }, 1500);
    });

    document.getElementById('btnStopNav')?.addEventListener('click', () => {
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
                wsConnection.send(JSON.stringify({
                    action: 'START_TRIP',
                    source: { lat: originCoords.lat, lon: originCoords.lon },
                    destination: { lat: destCoords.lat, lon: destCoords.lon },
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

    // 7. Fleet Logistics VRP Mode
    let demoStops = [
        { lat: 28.6129, lon: 77.2295, label: 'India Gate Plaza' },
        { lat: 28.6429, lon: 77.2195, label: 'NDLS Freight Hub' },
        { lat: 28.6180, lon: 77.2425, label: 'Bharat Mandapam' },
        { lat: 28.6520, lon: 77.1900, label: 'Karol Bagh Depot' }
    ];
    let selectedVehicleCount = 2;

    function renderStopsList() {
        const container = document.getElementById('stopsListContainer');
        if (!container) return;
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

    document.getElementById('btnAddDemoStop')?.addEventListener('click', () => {
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
        alternativePolylines.forEach(p => map.removeLayer(p));

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
        if (btn) btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> PARTITIONING VEHICLE TOURS...';

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
            if (btn) btn.innerHTML = '<i class="fa-solid fa-microchip"></i> SOLVE QUANTUM FLEET VRP';
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

    // 8. What-If Scenario Simulator Mode
    const simSlider = document.getElementById('simTimeSlider');
    if (simSlider) {
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
    }

    let selectedWeather = 'rain_monsoon';
    document.querySelectorAll('.weather-pill').forEach(wp => {
        wp.addEventListener('click', () => {
            document.querySelectorAll('.weather-pill').forEach(p => p.classList.remove('active'));
            wp.classList.add('active');
            selectedWeather = wp.dataset.weather;
        });
    });

    document.getElementById('btnRunSimulation')?.addEventListener('click', async () => {
        const payload = {
            scenario_name: document.getElementById('simPresetSelect').options[document.getElementById('simPresetSelect').selectedIndex].text,
            time_of_day_hours: parseFloat(simSlider.value),
            weather: selectedWeather,
            source: { lat: originCoords.lat, lon: originCoords.lon },
            destination: { lat: destCoords.lat, lon: destCoords.lon },
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

    // 9. Incident Console Modal Controls
    const judgeModal = document.getElementById('judgeModal');
    document.getElementById('btnJudgeConsole')?.addEventListener('click', () => {
        judgeModal.style.display = 'flex';
    });
    document.getElementById('btnCloseJudgeModal')?.addEventListener('click', () => {
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
                    lat: originCoords.lat + 0.005,
                    lon: originCoords.lon + 0.005,
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

    document.getElementById('btnInjectAccident')?.addEventListener('click', () => {
        injectDemoIncident('accident', '5-Car Pileup on Janpath Arterial');
    });
    document.getElementById('btnInjectClosure')?.addEventListener('click', () => {
        injectDemoIncident('closure', 'Emergency Flyover Structural Closure');
    });
    document.getElementById('btnInjectWaterlogging')?.addEventListener('click', () => {
        injectDemoIncident('pothole_hazard', 'Severe Monsoon Waterlogging & Potholes');
    });
    document.getElementById('btnInjectCongestion')?.addEventListener('click', () => {
        injectDemoIncident('congestion', '3.5x Heavy Traffic Wave Surge');
    });

    document.getElementById('btnResetGraph')?.addEventListener('click', async () => {
        judgeModal.style.display = 'none';
        await fetch('/api/reset', { method: 'POST' });
        computePersonalRoute();
    });

    document.getElementById('btnComputeRoute')?.addEventListener('click', computePersonalRoute);

    // 10. Emergency Green Corridor Logic
    let emgVehicleType = 'ambulance';
    document.querySelectorAll('.emg-type-pill').forEach(pill => {
        pill.addEventListener('click', () => {
            document.querySelectorAll('.emg-type-pill').forEach(p => p.classList.remove('active'));
            pill.classList.add('active');
            emgVehicleType = pill.dataset.emgtype;
        });
    });

    document.getElementById('btnSwapEmg')?.addEventListener('click', () => {
        const oInput = document.getElementById('emgOriginInput');
        const dInput = document.getElementById('emgDestInput');
        const tempCoords = { ...emgOriginCoords };
        emgOriginCoords = { ...emgDestCoords };
        emgDestCoords = tempCoords;

        const tempVal = oInput.value;
        oInput.value = dInput.value;
        dInput.value = tempVal;
    });

    document.getElementById('btnComputeEmg')?.addEventListener('click', async () => {
        const btn = document.getElementById('btnComputeEmg');
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> COMPUTING EMERGENCY CORRIDOR...';
        btn.style.background = 'rgba(255,56,92,0.4)';

        const payload = {
            origin: { lat: emgOriginCoords.lat, lon: emgOriginCoords.lon, label: emgOriginCoords.label },
            destination: { lat: emgDestCoords.lat, lon: emgDestCoords.lon, label: emgDestCoords.label },
            mode: 'emergency',
            priority: 'fastest',
            trip_id: `emg_${Date.now()}`
        };

        try {
            const res = await fetch('/api/route', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (res.ok) {
                const data = await res.json();
                const comp = data.comparison;

                // Draw emergency route on map (bright pulsing red)
                if (qpsoPolyline) map.removeLayer(qpsoPolyline);
                if (baselinePolyline) map.removeLayer(baselinePolyline);
                alternativePolylines.forEach(p => map.removeLayer(p));
                clearFleetLayers();

                const coords = comp.qpso_route.coordinates;
                if (coords && coords.length > 0) {
                    qpsoPolyline = L.polyline(coords, {
                        color: '#FF385C',
                        weight: 7,
                        opacity: 1.0
                    }).addTo(map);
                    map.fitBounds(qpsoPolyline.getBounds(), { padding: [40, 40] });

                    if (originMarker) map.removeLayer(originMarker);
                    if (destMarker) map.removeLayer(destMarker);
                    originMarker = L.marker(coords[0], { icon: originIcon }).addTo(map).bindPopup('<b>Dispatch Point</b>');
                    destMarker = L.marker(coords[coords.length - 1], { icon: destIcon }).addTo(map).bindPopup('<b>Incident Location</b>');
                }

                document.getElementById('emgComparisonCard').style.display = 'flex';
                document.getElementById('emgTime').textContent = comp.qpso_route.metrics.total_time_formatted;
                document.getElementById('emgDist').textContent = `(${comp.qpso_route.metrics.total_distance_formatted})`;
                document.getElementById('emgEfficiency').textContent = `ETA: ${comp.qpso_route.metrics.total_time_formatted}`;
                const saved = comp.time_saved_seconds > 0 ? `-${(comp.time_saved_seconds / 60).toFixed(1)} min faster` : 'Optimal Corridor';
                document.getElementById('emgSavedBadge').textContent = saved;
                document.getElementById('emgSignals').textContent = Math.floor(3 + Math.random() * 4);
                document.getElementById('emgCleared').textContent = `${(comp.qpso_route.metrics.total_distance_meters / 1000.0 * 0.4).toFixed(1)} km`;
                document.getElementById('emgETA').textContent = comp.qpso_route.metrics.total_time_formatted;
            }
        } catch (e) {
            console.error('Emergency corridor error:', e);
        } finally {
            btn.innerHTML = '<i class="fa-solid fa-siren-on"></i> ACTIVATE GREEN CORRIDOR';
            btn.style.background = '';
        }
    });

    // Initial Load: Compute route between default locations (CP to India Gate)
    computePersonalRoute();
});
