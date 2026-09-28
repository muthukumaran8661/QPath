import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
import '../core/constants.dart';
import '../models/route_model.dart';
import '../providers/route_provider.dart';
import '../widgets/route_comparison_card.dart';
import '../widgets/judge_demo_panel.dart';
import '../widgets/turn_by_turn_banner.dart';
import 'simulator_screen.dart';
import 'fleet_screen.dart';

class HomeMapScreen extends ConsumerStatefulWidget {
  const HomeMapScreen({Key? key}) : super(key: key);

  @override
  ConsumerState<HomeMapScreen> createState() => _HomeMapScreenState();
}

class _HomeMapScreenState extends ConsumerState<HomeMapScreen> {
  final MapController _mapController = MapController();
  List<Map<String, dynamic>> _landmarks = [];

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(routeProvider.notifier).computeRoute();
      _loadLandmarks();
    });
  }

  Future<void> _loadLandmarks() async {
    final api = ref.read(apiServiceProvider);
    final list = await api.getLandmarks();
    if (mounted) {
      setState(() {
        _landmarks = list;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final routeState = ref.watch(routeProvider);
    final routeNotifier = ref.read(routeProvider.notifier);

    // Construct Map Markers
    List<Marker> markers = [];

    // 1. Source Marker
    markers.add(
      Marker(
        point: routeState.source.toLatLng(),
        width: 40,
        height: 40,
        child: const Icon(Icons.location_on, color: AppColors.success, size: 36),
      ),
    );

    // 2. Destination Marker
    markers.add(
      Marker(
        point: routeState.destination.toLatLng(),
        width: 40,
        height: 40,
        child: const Icon(Icons.location_on, color: AppColors.quantumCyan, size: 38),
      ),
    );

    // 3. Simulated Vehicle Position Marker
    if (routeState.isNavigating && routeState.currentLocation != null) {
      markers.add(
        Marker(
          point: routeState.currentLocation!,
          width: 32,
          height: 32,
          child: Container(
            decoration: BoxDecoration(
              color: AppColors.quantumCyan,
              shape: BoxShape.circle,
              border: Border.all(color: Colors.white, width: 2.5),
              boxShadow: [
                BoxShadow(
                  color: AppColors.quantumCyan.withOpacity(0.6),
                  blurRadius: 12,
                  spreadRadius: 3,
                ),
              ],
            ),
            child: const Icon(Icons.navigation, color: Colors.black, size: 16),
          ),
        ),
      );
    }

    // Polylines
    List<Polyline> polylines = [];
    if (routeState.comparison != null) {
      // Baseline Standard Route (Gray)
      final baseCoords = routeState.comparison!.baselineRoute.coordinates;
      if (baseCoords.isNotEmpty) {
        polylines.add(
          Polyline(
            points: baseCoords,
            strokeWidth: 4.5,
            color: AppColors.standardRoute.withOpacity(0.6),
          ),
        );
      }

      // QPSO Quantum Route (Neon Cyan / Purple Glow)
      final qpsoCoords = routeState.comparison!.qpsoRoute.coordinates;
      if (qpsoCoords.isNotEmpty) {
        polylines.add(
          Polyline(
            points: qpsoCoords,
            strokeWidth: 6.0,
            color: routeState.mode == 'emergency' ? AppColors.emergencyRoute : AppColors.quantumCyan,
          ),
        );
      }
    }

    return Scaffold(
      backgroundColor: AppColors.backgroundDark,
      body: Stack(
        children: [
          // 1. OpenStreetMap Tile Layer
          FlutterMap(
            mapController: _mapController,
            options: MapOptions(
              initialCenter: const LatLng(AppConstants.defaultLat, AppConstants.defaultLon),
              initialZoom: AppConstants.defaultZoom,
              onTap: (_, latlng) {
                // Tap to set destination easily
                if (!routeState.isNavigating) {
                  routeNotifier.setDestination(CoordinateModel(
                    lat: latlng.latitude,
                    lon: latlng.longitude,
                    label: 'Tapped Destination',
                  ));
                  routeNotifier.computeRoute();
                }
              },
            ),
            children: [
              TileLayer(
                urlTemplate: AppConstants.osmTileUrl,
                userAgentPackageName: 'com.infinitycore.optimizer',
              ),
              PolylineLayer(polylines: polylines),
              MarkerLayer(markers: markers),
            ],
          ),

          // 2. Top Bar & Mode Selector
          SafeArea(
            child: Column(
              children: [
                if (routeState.isNavigating)
                  const TurnByTurnBanner()
                else ...[
                  _buildTopControlCard(routeState, routeNotifier),
                  _buildPriorityPillBar(routeState, routeNotifier),
                ],
              ],
            ),
          ),

          // 3. Floating Action Buttons (Judge Demo, What-If Simulator, Fleet)
          if (!routeState.isNavigating)
            Positioned(
              right: 16,
              bottom: routeState.comparison != null ? 310 : 30,
              child: Column(
                children: [
                  // SIH Special Judge Demo Console Trigger
                  FloatingActionButton.small(
                    heroTag: 'judge_demo_fab',
                    backgroundColor: AppColors.quantumPurple,
                    foregroundColor: Colors.white,
                    onPressed: () {
                      showModalBottomSheet(
                        context: context,
                        backgroundColor: Colors.transparent,
                        builder: (_) => const JudgeDemoPanel(),
                      );
                    },
                    tooltip: 'SIH Judge Demo Console',
                    child: const Icon(Icons.bolt, size: 20),
                  ),
                  const SizedBox(height: 10),

                  // What-If Simulator Screen Trigger
                  FloatingActionButton.small(
                    heroTag: 'simulator_fab',
                    backgroundColor: AppColors.surfaceElevated,
                    foregroundColor: AppColors.quantumCyan,
                    onPressed: () {
                      Navigator.push(
                        context,
                        MaterialPageRoute(builder: (_) => const SimulatorScreen()),
                      );
                    },
                    tooltip: 'What-If Traffic Simulator',
                    child: const Icon(Icons.science_rounded, size: 20),
                  ),
                  const SizedBox(height: 10),

                  // Fleet VRP Mode Trigger
                  FloatingActionButton.small(
                    heroTag: 'fleet_fab',
                    backgroundColor: AppColors.surfaceElevated,
                    foregroundColor: Colors.amberAccent,
                    onPressed: () {
                      Navigator.push(
                        context,
                        MaterialPageRoute(builder: (_) => const FleetScreen()),
                      );
                    },
                    tooltip: 'Fleet Logistics VRP',
                    child: const Icon(Icons.local_shipping_rounded, size: 20),
                  ),
                  const SizedBox(height: 10),

                  // Center Map View
                  FloatingActionButton.small(
                    heroTag: 'center_fab',
                    backgroundColor: AppColors.surfaceElevated,
                    foregroundColor: Colors.white,
                    onPressed: () {
                      _mapController.move(
                        const LatLng(AppConstants.defaultLat, AppConstants.defaultLon),
                        AppConstants.defaultZoom,
                      );
                    },
                    child: const Icon(Icons.my_location, size: 18),
                  ),
                ],
              ),
            ),

          // 4. Loading Indicator
          if (routeState.isLoading)
            Positioned.fill(
              child: Container(
                color: Colors.black38,
                child: const Center(
                  child: CircularProgressIndicator(color: AppColors.quantumCyan),
                ),
              ),
            ),

          // 5. Bottom Route Comparison Card
          if (!routeState.isNavigating && routeState.comparison != null)
            Positioned(
              left: 0,
              right: 0,
              bottom: 0,
              child: RouteComparisonCard(
                comparison: routeState.comparison!,
                onStartNavigation: () {
                  routeNotifier.startLiveNavigation();
                },
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildTopControlCard(RouteState routeState, RouteNotifier routeNotifier) {
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppColors.surfaceDark.withOpacity(0.95),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.white12),
        boxShadow: const [
          BoxShadow(color: Colors.black45, blurRadius: 10, offset: Offset(0, 4)),
        ],
      ),
      child: Column(
        children: [
          // Mode Tabs (Personal / Fleet / Emergency Corridor)
          Row(
            children: [
              _ModeTab(
                label: 'Personal',
                icon: Icons.directions_car,
                isSelected: routeState.mode == 'personal',
                onTap: () => routeNotifier.setMode('personal'),
              ),
              const SizedBox(width: 8),
              _ModeTab(
                label: 'Fleet VRP',
                icon: Icons.local_shipping,
                isSelected: routeState.mode == 'fleet',
                onTap: () {
                  Navigator.push(
                    context,
                    MaterialPageRoute(builder: (_) => const FleetScreen()),
                  );
                },
              ),
              const SizedBox(width: 8),
              _ModeTab(
                label: 'Emergency Cor.',
                icon: Icons.emergency,
                isSelected: routeState.mode == 'emergency',
                isEmergency: true,
                onTap: () => routeNotifier.setMode('emergency'),
              ),
            ],
          ),
          const Divider(color: Colors.white12, height: 16),

          // Origin & Destination Preset Pickers
          Row(
            children: [
              const Column(
                children: [
                  Icon(Icons.radio_button_checked, color: AppColors.success, size: 16),
                  SizedBox(height: 10),
                  Icon(Icons.location_on, color: AppColors.quantumCyan, size: 18),
                ],
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  children: [
                    _LandmarkDropdown(
                      label: 'Origin',
                      selectedLabel: routeState.source.label ?? 'CP Central Hub',
                      landmarks: _landmarks,
                      onSelect: (lm) {
                        routeNotifier.setSource(CoordinateModel(
                          lat: (lm['lat'] as num).toDouble(),
                          lon: (lm['lon'] as num).toDouble(),
                          label: lm['name'],
                          nodeId: lm['node_id'],
                        ));
                        routeNotifier.computeRoute();
                      },
                    ),
                    const SizedBox(height: 6),
                    _LandmarkDropdown(
                      label: 'Destination',
                      selectedLabel: routeState.destination.label ?? 'India Gate Boulevard',
                      landmarks: _landmarks,
                      onSelect: (lm) {
                        routeNotifier.setDestination(CoordinateModel(
                          lat: (lm['lat'] as num).toDouble(),
                          lon: (lm['lon'] as num).toDouble(),
                          label: lm['name'],
                          nodeId: lm['node_id'],
                        ));
                        routeNotifier.computeRoute();
                      },
                    ),
                  ],
                ),
              ),
              IconButton(
                icon: const Icon(Icons.swap_vert_rounded, color: AppColors.quantumCyan),
                onPressed: () => routeNotifier.swapLocations(),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildPriorityPillBar(RouteState routeState, RouteNotifier routeNotifier) {
    final priorities = [
      {'id': 'balanced', 'label': '⚡ Balanced', 'desc': 'Quantum Best'},
      {'id': 'fastest', 'label': '⏱️ Fastest', 'desc': 'Min Time'},
      {'id': 'less_congested', 'label': '🚦 Zero Traffic', 'desc': 'Avoid Jams'},
      {'id': 'smooth_roads', 'label': '🛣️ Smooth', 'desc': 'Pothole-free'},
      {'id': 'shortest', 'label': '📍 Shortest', 'desc': 'Min Dist'},
    ];

    return SizedBox(
      height: 38,
      child: ListView.separated(
        padding: const EdgeInsets.symmetric(horizontal: 16),
        scrollDirection: Axis.horizontal,
        itemCount: priorities.length,
        separatorBuilder: (_, __) => const SizedBox(width: 8),
        itemBuilder: (context, i) {
          final p = priorities[i];
          final isSelected = routeState.priority == p['id'];

          return InkWell(
            onTap: () => routeNotifier.setPriority(p['id']!),
            borderRadius: BorderRadius.circular(20),
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              decoration: BoxDecoration(
                color: isSelected ? AppColors.quantumCyan : AppColors.surfaceElevated,
                borderRadius: BorderRadius.circular(20),
                border: Border.all(
                  color: isSelected ? AppColors.quantumCyan : Colors.white12,
                ),
              ),
              child: Text(
                p['label']!,
                style: TextStyle(
                  color: isSelected ? Colors.black : Colors.white,
                  fontSize: 12,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
          );
        },
      ),
    );
  }
}

class _ModeTab extends StatelessWidget {
  final String label;
  final IconData icon;
  final bool isSelected;
  final bool isEmergency;
  final VoidCallback onTap;

  const _ModeTab({
    required this.label,
    required this.icon,
    required this.isSelected,
    this.isEmergency = false,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    Color activeColor = isEmergency ? AppColors.emergencyRoute : AppColors.quantumCyan;

    return Expanded(
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(10),
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 8),
          decoration: BoxDecoration(
            color: isSelected ? activeColor.withOpacity(0.18) : Colors.transparent,
            borderRadius: BorderRadius.circular(10),
            border: Border.all(
              color: isSelected ? activeColor : Colors.white12,
            ),
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(icon, size: 16, color: isSelected ? activeColor : AppColors.textSecondary),
              const SizedBox(width: 6),
              Text(
                label,
                style: TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w700,
                  color: isSelected ? Colors.white : AppColors.textSecondary,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _LandmarkDropdown extends StatelessWidget {
  final String label;
  final String selectedLabel;
  final List<Map<String, dynamic>> landmarks;
  final Function(Map<String, dynamic>) onSelect;

  const _LandmarkDropdown({
    required this.label,
    required this.selectedLabel,
    required this.landmarks,
    required this.onSelect,
  });

  @override
  Widget build(BuildContext context) {
    return PopupMenuButton<Map<String, dynamic>>(
      onSelected: onSelect,
      color: AppColors.surfaceElevated,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      itemBuilder: (context) {
        return landmarks.map((lm) {
          return PopupMenuItem<Map<String, dynamic>>(
            value: lm,
            child: Row(
              children: [
                const Icon(Icons.place_outlined, color: AppColors.quantumCyan, size: 18),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    lm['name'] ?? '',
                    style: const TextStyle(fontSize: 13, color: Colors.white),
                  ),
                ),
              ],
            ),
          );
        }).toList();
      },
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
        decoration: BoxDecoration(
          color: AppColors.surfaceElevated,
          borderRadius: BorderRadius.circular(8),
        ),
        child: Row(
          children: [
            Expanded(
              child: Text(
                selectedLabel,
                style: const TextStyle(fontSize: 13, color: Colors.white, fontWeight: FontWeight.w600),
                overflow: TextOverflow.ellipsis,
              ),
            ),
            const Icon(Icons.arrow_drop_down, color: AppColors.textSecondary, size: 18),
          ],
        ),
      ),
    );
  }
}
