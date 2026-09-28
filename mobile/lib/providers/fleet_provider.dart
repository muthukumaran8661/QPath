import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/route_model.dart';
import '../models/fleet_model.dart';
import '../services/api_service.dart';
import 'route_provider.dart';

class FleetState {
  final CoordinateModel depot;
  final List<CoordinateModel> stops;
  final List<FleetVehicleModel> vehicles;
  final bool isLoading;
  final String? errorMessage;
  final FleetRouteResponseModel? result;

  FleetState({
    required this.depot,
    required this.stops,
    required this.vehicles,
    this.isLoading = false,
    this.errorMessage,
    this.result,
  });

  FleetState copyWith({
    CoordinateModel? depot,
    List<CoordinateModel>? stops,
    List<FleetVehicleModel>? vehicles,
    bool? isLoading,
    String? errorMessage,
    FleetRouteResponseModel? result,
  }) {
    return FleetState(
      depot: depot ?? this.depot,
      stops: stops ?? this.stops,
      vehicles: vehicles ?? this.vehicles,
      isLoading: isLoading ?? this.isLoading,
      errorMessage: errorMessage,
      result: result ?? this.result,
    );
  }
}

class FleetNotifier extends StateNotifier<FleetState> {
  final ApiService _apiService;

  FleetNotifier(this._apiService)
      : super(FleetState(
          depot: CoordinateModel(lat: 28.6315, lon: 77.2167, label: "Central CP Logistics Depot", nodeId: 0),
          stops: [
            CoordinateModel(lat: 28.6129, lon: 77.2295, label: "Stop 1: India Gate Plaza", nodeId: 25),
            CoordinateModel(lat: 28.6429, lon: 77.2195, label: "Stop 2: NDLS Hub", nodeId: 26),
            CoordinateModel(lat: 28.6180, lon: 77.2425, label: "Stop 3: Bharat Mandapam", nodeId: 27),
            CoordinateModel(lat: 28.6520, lon: 77.1900, label: "Stop 4: Karol Bagh Logistics", nodeId: 31),
          ],
          vehicles: [
            FleetVehicleModel(vehicleId: "v1", name: "Quantum Van Alpha", capacity: 100, colorHex: "#00F0FF"),
            FleetVehicleModel(vehicleId: "v2", name: "Quantum Van Beta", capacity: 100, colorHex: "#7928CA"),
          ],
        ));

  void addStop(CoordinateModel stop) {
    final updated = List<CoordinateModel>.from(state.stops)..add(stop);
    state = state.copyWith(stops: updated);
    optimizeFleet();
  }

  void removeStop(int index) {
    final updated = List<CoordinateModel>.from(state.stops)..removeAt(index);
    state = state.copyWith(stops: updated);
    optimizeFleet();
  }

  void setVehicleCount(int count) {
    final colors = ["#00F0FF", "#7928CA", "#FF007F", "#00E676", "#FFB800"];
    final vehicles = List.generate(count, (i) {
      return FleetVehicleModel(
        vehicleId: "v${i + 1}",
        name: "Quantum Dispatch ${i + 1}",
        capacity: 100,
        colorHex: colors[i % colors.length],
      );
    });
    state = state.copyWith(vehicles: vehicles);
    optimizeFleet();
  }

  Future<void> optimizeFleet() async {
    state = state.copyWith(isLoading: true, errorMessage: null);

    final res = await _apiService.computeFleetRoute(
      depot: state.depot,
      stops: state.stops,
      vehicles: state.vehicles,
    );

    if (res != null) {
      state = state.copyWith(isLoading: false, result: res);
    } else {
      state = state.copyWith(
        isLoading: false,
        errorMessage: 'Fleet optimization error. Check backend connection.',
      );
    }
  }
}

final fleetProvider = StateNotifierProvider<FleetNotifier, FleetState>((ref) {
  final api = ref.watch(apiServiceProvider);
  return FleetNotifier(api);
});
