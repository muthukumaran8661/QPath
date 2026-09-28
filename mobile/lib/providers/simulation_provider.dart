import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/route_model.dart';
import '../models/simulation_model.dart';
import '../services/api_service.dart';
import 'route_provider.dart';

class SimulationState {
  final String scenarioName;
  final double timeOfDayHours;
  final String weather;
  final int injectClosures;
  final int injectAccidents;
  final bool isLoading;
  final String? errorMessage;
  final SimulationScenarioResponseModel? result;

  SimulationState({
    this.scenarioName = "Morning Monsoon Rush Hour",
    this.timeOfDayHours = 8.5,
    this.weather = "rain_monsoon",
    this.injectClosures = 1,
    this.injectAccidents = 1,
    this.isLoading = false,
    this.errorMessage,
    this.result,
  });

  SimulationState copyWith({
    String? scenarioName,
    double? timeOfDayHours,
    String? weather,
    int? injectClosures,
    int? injectAccidents,
    bool? isLoading,
    String? errorMessage,
    SimulationScenarioResponseModel? result,
  }) {
    return SimulationState(
      scenarioName: scenarioName ?? this.scenarioName,
      timeOfDayHours: timeOfDayHours ?? this.timeOfDayHours,
      weather: weather ?? this.weather,
      injectClosures: injectClosures ?? this.injectClosures,
      injectAccidents: injectAccidents ?? this.injectAccidents,
      isLoading: isLoading ?? this.isLoading,
      errorMessage: errorMessage,
      result: result ?? this.result,
    );
  }
}

class SimulationNotifier extends StateNotifier<SimulationState> {
  final ApiService _apiService;

  SimulationNotifier(this._apiService) : super(SimulationState());

  void setScenario(String name) => state = state.copyWith(scenarioName: name);
  void setTimeOfDay(double hours) => state = state.copyWith(timeOfDayHours: hours);
  void setWeather(String weather) => state = state.copyWith(weather: weather);
  void setClosures(int count) => state = state.copyWith(injectClosures: count);
  void setAccidents(int count) => state = state.copyWith(injectAccidents: count);

  Future<void> runSimulation(CoordinateModel source, CoordinateModel destination) async {
    state = state.copyWith(isLoading: true, errorMessage: null);

    final res = await _apiService.runWhatIfSimulation(
      scenarioName: state.scenarioName,
      timeOfDayHours: state.timeOfDayHours,
      weather: state.weather,
      source: source,
      destination: destination,
      injectClosures: state.injectClosures,
      injectAccidents: state.injectAccidents,
    );

    if (res != null) {
      state = state.copyWith(isLoading: false, result: res);
    } else {
      state = state.copyWith(
        isLoading: false,
        errorMessage: 'Simulation engine error. Please ensure backend is running.',
      );
    }
  }
}

final simulationProvider = StateNotifierProvider<SimulationNotifier, SimulationState>((ref) {
  final api = ref.watch(apiServiceProvider);
  return SimulationNotifier(api);
});
