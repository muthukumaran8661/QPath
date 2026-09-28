import 'dart:async';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:latlong2/latlong.dart';
import '../models/route_model.dart';
import '../services/api_service.dart';
import '../services/websocket_service.dart';

final apiServiceProvider = Provider<ApiService>((ref) => ApiService());

class RouteState {
  final CoordinateModel source;
  final CoordinateModel destination;
  final String mode; // personal, fleet, emergency
  final String priority; // fastest, shortest, less_congested, smooth_roads, balanced
  final bool isLoading;
  final String? errorMessage;
  final RouteComparisonModel? comparison;
  final String? tripId;
  
  // Dynamic WebSocket Alert Banner
  final bool hasRerouteAlert;
  final String? rerouteMessage;
  final double? rerouteTimeSavedSeconds;
  final Map<String, dynamic>? pendingNewComparison;

  // Live Navigation State
  final bool isNavigating;
  final LatLng? currentLocation;
  final int currentSegmentIndex;
  final double currentSpeedKph;
  final String? currentInstruction;

  RouteState({
    required this.source,
    required this.destination,
    this.mode = 'personal',
    this.priority = 'balanced',
    this.isLoading = false,
    this.errorMessage,
    this.comparison,
    this.tripId,
    this.hasRerouteAlert = false,
    this.rerouteMessage,
    this.rerouteTimeSavedSeconds,
    this.pendingNewComparison,
    this.isNavigating = false,
    this.currentLocation,
    this.currentSegmentIndex = 0,
    this.currentSpeedKph = 0.0,
    this.currentInstruction,
  });

  RouteState copyWith({
    CoordinateModel? source,
    CoordinateModel? destination,
    String? mode,
    String? priority,
    bool? isLoading,
    String? errorMessage,
    RouteComparisonModel? comparison,
    String? tripId,
    bool? hasRerouteAlert,
    String? rerouteMessage,
    double? rerouteTimeSavedSeconds,
    Map<String, dynamic>? pendingNewComparison,
    bool? isNavigating,
    LatLng? currentLocation,
    int? currentSegmentIndex,
    double? currentSpeedKph,
    String? currentInstruction,
  }) {
    return RouteState(
      source: source ?? this.source,
      destination: destination ?? this.destination,
      mode: mode ?? this.mode,
      priority: priority ?? this.priority,
      isLoading: isLoading ?? this.isLoading,
      errorMessage: errorMessage,
      comparison: comparison ?? this.comparison,
      tripId: tripId ?? this.tripId,
      hasRerouteAlert: hasRerouteAlert ?? this.hasRerouteAlert,
      rerouteMessage: rerouteMessage ?? this.rerouteMessage,
      rerouteTimeSavedSeconds: rerouteTimeSavedSeconds ?? this.rerouteTimeSavedSeconds,
      pendingNewComparison: pendingNewComparison ?? this.pendingNewComparison,
      isNavigating: isNavigating ?? this.isNavigating,
      currentLocation: currentLocation ?? this.currentLocation,
      currentSegmentIndex: currentSegmentIndex ?? this.currentSegmentIndex,
      currentSpeedKph: currentSpeedKph ?? this.currentSpeedKph,
      currentInstruction: currentInstruction ?? this.currentInstruction,
    );
  }
}

class RouteNotifier extends StateNotifier<RouteState> {
  final ApiService _apiService;
  WebSocketService? _wsService;
  Timer? _navSimulationTimer;

  RouteNotifier(this._apiService)
      : super(RouteState(
          source: CoordinateModel(lat: 28.6315, lon: 77.2167, label: "CP Central Hub", nodeId: 0),
          destination: CoordinateModel(lat: 28.6129, lon: 77.2295, label: "India Gate Boulevard", nodeId: 25),
        ));

  void setSource(CoordinateModel src) {
    state = state.copyWith(source: src);
  }

  void setDestination(CoordinateModel dst) {
    state = state.copyWith(destination: dst);
  }

  void setMode(String mode) {
    state = state.copyWith(mode: mode);
    computeRoute();
  }

  void setPriority(String priority) {
    state = state.copyWith(priority: priority);
    computeRoute();
  }

  void swapLocations() {
    final oldSrc = state.source;
    final oldDst = state.destination;
    state = state.copyWith(source: oldDst, destination: oldSrc);
    computeRoute();
  }

  Future<void> computeRoute() async {
    state = state.copyWith(isLoading: true, errorMessage: null);

    final res = await _apiService.computeRoute(
      source: state.source,
      destination: state.destination,
      mode: state.mode,
      priority: state.priority,
    );

    if (res != null) {
      state = state.copyWith(
        isLoading: false,
        comparison: res.comparison,
        tripId: res.tripId,
        currentLocation: state.source.toLatLng(),
      );
    } else {
      state = state.copyWith(
        isLoading: false,
        errorMessage: 'Failed to reach QPath Quantum Engine. Check backend connection.',
      );
    }
  }

  void startLiveNavigation() {
    if (state.comparison == null) return;
    
    final tId = state.tripId ?? 'trip_demo_${DateTime.now().millisecondsSinceEpoch}';
    state = state.copyWith(
      isNavigating: true,
      tripId: tId,
      currentSegmentIndex: 0,
      currentLocation: state.source.toLatLng(),
      currentSpeedKph: 45.0,
      currentInstruction: state.comparison!.qpsoRoute.segments.isNotEmpty
          ? state.comparison!.qpsoRoute.segments.first.instruction
          : 'Proceed towards destination',
    );

    // Initialize WebSocket for live rerouting stream
    _wsService?.disconnect();
    _wsService = WebSocketService(
      tripId: tId,
      onMessageReceived: _handleWebSocketMessage,
    );
    _wsService!.connect();
    _wsService!.startTrip(
      source: state.source,
      destination: state.destination,
      priority: state.priority,
      mode: state.mode,
    );

    // Start simulated vehicle movement along coordinates
    _startMovementSimulation();
  }

  void _startMovementSimulation() {
    _navSimulationTimer?.cancel();
    final coords = state.comparison?.qpsoRoute.coordinates ?? [];
    if (coords.isEmpty) return;

    int coordIdx = 0;
    _navSimulationTimer = Timer.periodic(const Duration(milliseconds: 1200), (timer) {
      if (!state.isNavigating || coordIdx >= coords.length) {
        timer.cancel();
        return;
      }

      final nextPos = coords[coordIdx];
      coordIdx++;

      // Update segment instructions if advanced
      final segments = state.comparison?.qpsoRoute.segments ?? [];
      int segIdx = (coordIdx * segments.length ~/ coords.length).clamp(0, segments.length - 1);
      String instr = segments.isNotEmpty ? (segments[segIdx].instruction ?? 'Follow highlighted path') : 'Proceed';

      state = state.copyWith(
        currentLocation: nextPos,
        currentSegmentIndex: segIdx,
        currentSpeedKph: 38.0 + (coordIdx % 4) * 4.0,
        currentInstruction: instr,
      );

      _wsService?.updatePosition(nextPos.latitude, nextPos.longitude);
    });
  }

  void _handleWebSocketMessage(Map<String, dynamic> data) {
    final type = data['type'];
    if (type == 'REROUTE_RECOMMENDATION') {
      final msg = data['message'] ?? 'Incident alert detected on current route!';
      final timeSaved = (data['time_saved_seconds'] as num?)?.toDouble() ?? 0.0;
      final newComp = data['new_comparison'] as Map<String, dynamic>?;

      state = state.copyWith(
        hasRerouteAlert: true,
        rerouteMessage: msg,
        rerouteTimeSavedSeconds: timeSaved,
        pendingNewComparison: newComp,
      );
    }
  }

  void acceptReroute() {
    if (state.pendingNewComparison != null) {
      try {
        final newComp = RouteComparisonModel.fromJson(state.pendingNewComparison!);
        state = state.copyWith(
          comparison: newComp,
          hasRerouteAlert: false,
          rerouteMessage: null,
          pendingNewComparison: null,
        );
        _wsService?.acceptReroute(state.pendingNewComparison ?? {});
      } catch (e) {
        print('Error accepting reroute: $e');
      }
    }
  }

  void ignoreReroute() {
    state = state.copyWith(
      hasRerouteAlert: false,
      rerouteMessage: null,
      pendingNewComparison: null,
    );
  }

  Future<void> triggerDemoIncident(String type) async {
    final cur = state.currentLocation ?? state.source.toLatLng();
    await _apiService.injectIncident(
      type: type,
      lat: cur.latitude + 0.003,
      lon: cur.longitude + 0.003,
      severity: 3.8,
      description: 'SIH Judge Demo Injected $type',
    );
  }

  void stopNavigation() {
    _navSimulationTimer?.cancel();
    _wsService?.disconnect();
    state = state.copyWith(
      isNavigating: false,
      hasRerouteAlert: false,
    );
  }

  @override
  void dispose() {
    _navSimulationTimer?.cancel();
    _wsService?.disconnect();
    super.dispose();
  }
}

final routeProvider = StateNotifierProvider<RouteNotifier, RouteState>((ref) {
  final api = ref.watch(apiServiceProvider);
  return RouteNotifier(api);
});
