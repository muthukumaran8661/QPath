import 'dart:convert';
import 'package:http/http.dart' as http;
import '../core/constants.dart';
import '../models/route_model.dart';
import '../models/fleet_model.dart';
import '../models/simulation_model.dart';

class ApiService {
  final String baseUrl;

  ApiService({this.baseUrl = AppConstants.defaultBaseUrl});

  Future<List<Map<String, dynamic>>> getLandmarks() async {
    try {
      final response = await http.get(Uri.parse('$baseUrl/landmarks'));
      if (response.statusCode == 200) {
        List<dynamic> list = jsonDecode(response.body);
        return list.map((e) => e as Map<String, dynamic>).toList();
      }
      return [];
    } catch (e) {
      print('Error fetching landmarks: $e');
      return [];
    }
  }

  Future<RouteResponseModel?> computeRoute({
    required CoordinateModel source,
    required CoordinateModel destination,
    String mode = 'personal',
    String priority = 'balanced',
    Map<String, double>? customWeights,
    String? tripId,
  }) async {
    try {
      final body = {
        'source': source.toJson(),
        'destination': destination.toJson(),
        'mode': mode,
        'priority': priority,
        if (customWeights != null) 'custom_weights': customWeights,
        if (tripId != null) 'trip_id': tripId,
      };

      final response = await http.post(
        Uri.parse('$baseUrl/route'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode(body),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        return RouteResponseModel.fromJson(data);
      } else {
        print('Route calculation error: ${response.body}');
        return null;
      }
    } catch (e) {
      print('Network error computing route: $e');
      return null;
    }
  }

  Future<FleetRouteResponseModel?> computeFleetRoute({
    required CoordinateModel depot,
    required List<CoordinateModel> stops,
    required List<FleetVehicleModel> vehicles,
  }) async {
    try {
      final body = {
        'depot': depot.toJson(),
        'stops': stops.map((s) => s.toJson()).toList(),
        'vehicles': vehicles.map((v) => v.toJson()).toList(),
        'mode': 'fleet',
      };

      final response = await http.post(
        Uri.parse('$baseUrl/fleet/route'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode(body),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        return FleetRouteResponseModel.fromJson(data);
      }
      return null;
    } catch (e) {
      print('Error computing fleet route: $e');
      return null;
    }
  }

  Future<SimulationScenarioResponseModel?> runWhatIfSimulation({
    required String scenarioName,
    required double timeOfDayHours,
    required String weather,
    required CoordinateModel source,
    required CoordinateModel destination,
    int injectClosures = 1,
    int injectAccidents = 1,
  }) async {
    try {
      final body = {
        'scenario_name': scenarioName,
        'time_of_day_hours': timeOfDayHours,
        'weather': weather,
        'source': source.toJson(),
        'destination': destination.toJson(),
        'inject_closures': injectClosures,
        'inject_accidents': injectAccidents,
      };

      final response = await http.post(
        Uri.parse('$baseUrl/simulate'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode(body),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        return SimulationScenarioResponseModel.fromJson(data);
      }
      return null;
    } catch (e) {
      print('Error running simulation: $e');
      return null;
    }
  }

  Future<bool> injectIncident({
    required String type,
    required double lat,
    required double lon,
    double severity = 3.0,
    String description = 'Judge Demo Incident',
  }) async {
    try {
      final body = {
        'incident_type': type,
        'lat': lat,
        'lon': lon,
        'radius_meters': 350.0,
        'severity': severity,
        'duration_minutes': 30,
        'description': description,
      };

      final response = await http.post(
        Uri.parse('$baseUrl/incident'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode(body),
      );

      return response.statusCode == 200;
    } catch (e) {
      print('Error injecting incident: $e');
      return false;
    }
  }

  Future<bool> resetIncidents() async {
    try {
      final response = await http.post(Uri.parse('$baseUrl/reset'));
      return response.statusCode == 200;
    } catch (e) {
      return false;
    }
  }
}
