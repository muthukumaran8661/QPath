import 'package:latlong2/latlong.dart';
import 'route_model.dart';

class SimulationScenarioResponseModel {
  final String scenarioName;
  final String weather;
  final double timeOfDayHours;
  final PathResultModel normalRoute;
  final PathResultModel stressedRouteQpso;
  final PathResultModel stressedRouteStandard;
  final Map<String, dynamic> metricsDelta;
  final String aiRecommendation;

  SimulationScenarioResponseModel({
    required this.scenarioName,
    required this.weather,
    required this.timeOfDayHours,
    required this.normalRoute,
    required this.stressedRouteQpso,
    required this.stressedRouteStandard,
    required this.metricsDelta,
    required this.aiRecommendation,
  });

  factory SimulationScenarioResponseModel.fromJson(Map<String, dynamic> json) {
    return SimulationScenarioResponseModel(
      scenarioName: json['scenario_name'],
      weather: json['weather'],
      timeOfDayHours: (json['time_of_day_hours'] as num).toDouble(),
      normalRoute: PathResultModel.fromJson(json['normal_route']),
      stressedRouteQpso: PathResultModel.fromJson(json['stressed_route_qpso']),
      stressedRouteStandard: PathResultModel.fromJson(json['stressed_route_standard']),
      metricsDelta: json['metrics_delta'] as Map<String, dynamic>? ?? {},
      aiRecommendation: json['ai_recommendation'] ?? '',
    );
  }
}
