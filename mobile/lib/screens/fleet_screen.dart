import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
import '../core/constants.dart';
import '../models/route_model.dart';
import '../providers/fleet_provider.dart';

class FleetScreen extends ConsumerStatefulWidget {
  const FleetScreen({Key? key}) : super(key: key);

  @override
  ConsumerState<FleetScreen> createState() => _FleetScreenState();
}

class _FleetScreenState extends ConsumerState<FleetScreen> {
  final MapController _mapController = MapController();

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(fleetProvider.notifier).optimizeFleet();
    });
  }

  @override
  Widget build(BuildContext context) {
    final fleetState = ref.watch(fleetProvider);
    final fleetNotifier = ref.read(fleetProvider.notifier);

    // Build Polylines & Markers for each vehicle tour
    List<Polyline> polylines = [];
    List<Marker> markers = [];

    // Depot Marker
    markers.add(
      Marker(
        point: fleetState.depot.toLatLng(),
        width: 44,
        height: 44,
        child: Container(
          decoration: BoxDecoration(
            color: Colors.amber,
            shape: BoxShape.circle,
            border: Border.all(color: Colors.black, width: 2),
            boxShadow: const [BoxShadow(color: Colors.amber, blurRadius: 10)],
          ),
          child: const Icon(Icons.warehouse_rounded, color: Colors.black, size: 22),
        ),
      ),
    );

    if (fleetState.result != null) {
      for (var vr in fleetState.result!.fleetRoutes) {
        Color vColor = vr.colorHex.isNotEmpty
            ? Color(int.parse(vr.colorHex.replaceAll('#', 'FF'), radix: 16))
            : AppColors.quantumCyan;

        // Add vehicle path polyline
        if (vr.path.coordinates.isNotEmpty) {
          polylines.add(
            Polyline(
              points: vr.path.coordinates,
              strokeWidth: 5.0,
              color: vColor,
            ),
          );
        }

        // Add stop markers
        for (int i = 1; i < vr.stops.length - 1; i++) {
          final stop = vr.stops[i];
          markers.add(
            Marker(
              point: stop.toLatLng(),
              width: 32,
              height: 32,
              child: Container(
                decoration: BoxDecoration(
                  color: vColor,
                  shape: BoxShape.circle,
                  border: Border.all(color: Colors.white, width: 2),
                ),
                child: Center(
                  child: Text(
                    '$i',
                    style: const TextStyle(color: Colors.black, fontWeight: FontWeight.w900, fontSize: 13),
                  ),
                ),
              ),
            ),
          );
        }
      }
    }

    return Scaffold(
      backgroundColor: AppColors.backgroundDark,
      appBar: AppBar(
        title: const Text('Quantum Fleet Logistics VRP'),
        backgroundColor: AppColors.surfaceDark,
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh, color: AppColors.quantumCyan),
            onPressed: () => fleetNotifier.optimizeFleet(),
          ),
        ],
      ),
      body: Column(
        children: [
          // 1. Map Section
          Expanded(
            flex: 5,
            child: Stack(
              children: [
                FlutterMap(
                  mapController: _mapController,
                  options: MapOptions(
                    initialCenter: fleetState.depot.toLatLng(),
                    initialZoom: 12.8,
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
                if (fleetState.isLoading)
                  Positioned.fill(
                    child: Container(
                      color: Colors.black45,
                      child: const Center(child: CircularProgressIndicator(color: AppColors.quantumCyan)),
                    ),
                  ),
              ],
            ),
          ),

          // 2. Control & Fleet Metrics Section
          Expanded(
            flex: 5,
            child: Container(
              padding: const EdgeInsets.all(16),
              decoration: const BoxDecoration(
                color: AppColors.surfaceDark,
                borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
              ),
              child: SingleChildScrollView(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Vehicle Count Selector
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        const Text(
                          'Active Fleet Vehicles:',
                          style: TextStyle(fontWeight: FontWeight.w700, fontSize: 14, color: Colors.white),
                        ),
                        Row(
                          children: [1, 2, 3, 4].map((cnt) {
                            final isSel = fleetState.vehicles.length == cnt;
                            return Padding(
                              padding: const EdgeInsets.only(left: 6),
                              child: ChoiceChip(
                                label: Text('$cnt'),
                                selected: isSel,
                                selectedColor: AppColors.quantumCyan,
                                onSelected: (_) => fleetNotifier.setVehicleCount(cnt),
                                labelStyle: TextStyle(
                                  color: isSel ? Colors.black : Colors.white,
                                  fontWeight: FontWeight.w800,
                                ),
                              ),
                            );
                          }).toList(),
                        ),
                      ],
                    ),
                    const SizedBox(height: 14),

                    // Fleet Totals Summary
                    if (fleetState.result != null) ...[
                      Container(
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: AppColors.surfaceElevated,
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(color: Colors.white12),
                        ),
                        child: Row(
                          children: [
                            Expanded(
                              child: _FleetStatTile(
                                label: 'Fleet Time',
                                val: fleetState.result!.totalFleetTimeFormatted,
                                icon: Icons.timer,
                              ),
                            ),
                            Container(width: 1, height: 32, color: Colors.white12),
                            Expanded(
                              child: _FleetStatTile(
                                label: 'Distance',
                                val: fleetState.result!.totalFleetDistanceFormatted,
                                icon: Icons.route,
                              ),
                            ),
                            Container(width: 1, height: 32, color: Colors.white12),
                            Expanded(
                              child: _FleetStatTile(
                                label: 'Fuel Est.',
                                val: '${fleetState.result!.totalFuelLiters} L',
                                icon: Icons.local_gas_station,
                              ),
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(height: 16),

                      // Per-Vehicle Breakdown List
                      const Text(
                        'Optimized Delivery Tours',
                        style: TextStyle(fontSize: 14, fontWeight: FontWeight.w800, color: Colors.white),
                      ),
                      const SizedBox(height: 8),
                      ...fleetState.result!.fleetRoutes.map((vr) {
                        Color vColor = vr.colorHex.isNotEmpty
                            ? Color(int.parse(vr.colorHex.replaceAll('#', 'FF'), radix: 16))
                            : AppColors.quantumCyan;

                        return Container(
                          margin: const EdgeInsets.only(bottom: 8),
                          padding: const EdgeInsets.all(10),
                          decoration: BoxDecoration(
                            color: AppColors.surfaceElevated,
                            borderRadius: BorderRadius.circular(10),
                            border: Border.all(color: vColor.withOpacity(0.4)),
                          ),
                          child: Row(
                            children: [
                              Container(width: 12, height: 12, decoration: BoxDecoration(color: vColor, shape: BoxShape.circle)),
                              const SizedBox(width: 10),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(vr.vehicleName, style: const TextStyle(fontWeight: FontWeight.w700, color: Colors.white, fontSize: 13)),
                                    Text('${vr.stops.length - 2} drops assigned • ${vr.totalDistanceFormatted}', style: const TextStyle(fontSize: 11, color: AppColors.textSecondary)),
                                  ],
                                ),
                              ),
                              Text(vr.totalTimeFormatted, style: TextStyle(color: vColor, fontWeight: FontWeight.w800, fontSize: 13)),
                            ],
                          ),
                        );
                      }).toList(),
                    ],
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _FleetStatTile extends StatelessWidget {
  final String label;
  final String val;
  final IconData icon;

  const _FleetStatTile({
    required this.label,
    required this.val,
    required this.icon,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Icon(icon, color: AppColors.quantumCyan, size: 16),
        const SizedBox(height: 2),
        Text(val, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 14, color: Colors.white)),
        Text(label, style: const TextStyle(fontSize: 10, color: AppColors.textSecondary)),
      ],
    );
  }
}
