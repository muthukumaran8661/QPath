import 'package:latlong2/latlong.dart';

class CoordinateModel {
  final double lat;
  final double lon;
  final String? label;
  final int? nodeId;

  CoordinateModel({
    required this.lat,
    required this.lon,
    this.label,
    this.nodeId,
  });

  LatLng toLatLng() => LatLng(lat, lon);

  factory CoordinateModel.fromJson(Map<String, dynamic> json) {
    return CoordinateModel(
      lat: (json['lat'] as num).toDouble(),
      lon: (json['lon'] as num).toDouble(),
      label: json['label'] as String?,
      nodeId: json['node_id'] as int?,
    );
  }

  Map<String, dynamic> toJson() => {
    'lat': lat,
    'lon': lon,
    'label': label,
    if (nodeId != null) 'node_id': nodeId,
  };
}

class RouteMetricsModel {
  final double totalTimeSeconds;
  final double totalDistanceMeters;
  final String totalTimeFormatted;
  final String totalDistanceFormatted;
  final double avgCongestionFactor;
  final double avgRoadConditionScore;
  final double carbonEmissionKg;
  final double multiObjectiveCost;

  RouteMetricsModel({
    required this.totalTimeSeconds,
    required this.totalDistanceMeters,
    required this.totalTimeFormatted,
    required this.totalDistanceFormatted,
    required this.avgCongestionFactor,
    required this.avgRoadConditionScore,
    required this.carbonEmissionKg,
    required this.multiObjectiveCost,
  });

  factory RouteMetricsModel.fromJson(Map<String, dynamic> json) {
    return RouteMetricsModel(
      totalTimeSeconds: (json['total_time_seconds'] as num).toDouble(),
      totalDistanceMeters: (json['total_distance_meters'] as num).toDouble(),
      totalTimeFormatted: json['total_time_formatted'] ?? '0 min',
      totalDistanceFormatted: json['total_distance_formatted'] ?? '0 m',
      avgCongestionFactor: (json['avg_congestion_factor'] as num).toDouble(),
      avgRoadConditionScore: (json['avg_road_condition_score'] as num).toDouble(),
      carbonEmissionKg: (json['carbon_emission_kg'] as num).toDouble(),
      multiObjectiveCost: (json['multi_objective_cost'] as num).toDouble(),
    );
  }
}

class RouteSegmentModel {
  final int u;
  final int v;
  final double distanceMeters;
  final double travelTimeSeconds;
  final double speedKph;
  final double congestionFactor;
  final double roadCondition;
  final bool isClosed;
  final List<LatLng> coordinates;
  final String? instruction;
  final String? roadName;

  RouteSegmentModel({
    required this.u,
    required this.v,
    required this.distanceMeters,
    required this.travelTimeSeconds,
    required this.speedKph,
    required this.congestionFactor,
    required this.roadCondition,
    required this.isClosed,
    required this.coordinates,
    this.instruction,
    this.roadName,
  });

  factory RouteSegmentModel.fromJson(Map<String, dynamic> json) {
    var rawCoords = json['coordinates'] as List<dynamic>? ?? [];
    List<LatLng> coords = rawCoords.map((c) {
      var arr = c as List<dynamic>;
      return LatLng((arr[0] as num).toDouble(), (arr[1] as num).toDouble());
    }).toList();

    return RouteSegmentModel(
      u: json['u'] ?? 0,
      v: json['v'] ?? 0,
      distanceMeters: (json['distance_meters'] as num).toDouble(),
      travelTimeSeconds: (json['travel_time_seconds'] as num).toDouble(),
      speedKph: (json['speed_kph'] as num).toDouble(),
      congestionFactor: (json['congestion_factor'] as num).toDouble(),
      roadCondition: (json['road_condition'] as num).toDouble(),
      isClosed: json['is_closed'] ?? false,
      coordinates: coords,
      instruction: json['instruction'] as String?,
      roadName: json['road_name'] as String?,
    );
  }
}

class PathResultModel {
  final List<int> nodes;
  final List<LatLng> coordinates;
  final List<RouteSegmentModel> segments;
  final RouteMetricsModel metrics;

  PathResultModel({
    required this.nodes,
    required this.coordinates,
    required this.segments,
    required this.metrics,
  });

  factory PathResultModel.fromJson(Map<String, dynamic> json) {
    var rawCoords = json['coordinates'] as List<dynamic>? ?? [];
    List<LatLng> coords = rawCoords.map((c) {
      var arr = c as List<dynamic>;
      return LatLng((arr[0] as num).toDouble(), (arr[1] as num).toDouble());
    }).toList();

    var rawSegs = json['segments'] as List<dynamic>? ?? [];
    List<RouteSegmentModel> segs = rawSegs.map((s) => RouteSegmentModel.fromJson(s)).toList();

    return PathResultModel(
      nodes: (json['nodes'] as List<dynamic>? ?? []).map((e) => e as int).toList(),
      coordinates: coords,
      segments: segs,
      metrics: RouteMetricsModel.fromJson(json['metrics']),
    );
  }
}

class RouteComparisonModel {
  final PathResultModel qpsoRoute;
  final PathResultModel baselineRoute;
  final double timeSavedSeconds;
  final double timeSavedPercent;
  final double congestionReductionPercent;
  final double roughnessReductionPercent;
  final double quantumEfficiencyScore;

  RouteComparisonModel({
    required this.qpsoRoute,
    required this.baselineRoute,
    required this.timeSavedSeconds,
    required this.timeSavedPercent,
    required this.congestionReductionPercent,
    required this.roughnessReductionPercent,
    required this.quantumEfficiencyScore,
  });

  factory RouteComparisonModel.fromJson(Map<String, dynamic> json) {
    return RouteComparisonModel(
      qpsoRoute: PathResultModel.fromJson(json['qpso_route']),
      baselineRoute: PathResultModel.fromJson(json['baseline_route']),
      timeSavedSeconds: (json['time_saved_seconds'] as num).toDouble(),
      timeSavedPercent: (json['time_saved_percent'] as num).toDouble(),
      congestionReductionPercent: (json['congestion_reduction_percent'] as num).toDouble(),
      roughnessReductionPercent: (json['roughness_reduction_percent'] as num).toDouble(),
      quantumEfficiencyScore: (json['quantum_efficiency_score'] as num).toDouble(),
    );
  }
}

class RouteResponseModel {
  final String tripId;
  final String mode;
  final String priority;
  final RouteComparisonModel comparison;

  RouteResponseModel({
    required this.tripId,
    required this.mode,
    required this.priority,
    required this.comparison,
  });

  factory RouteResponseModel.fromJson(Map<String, dynamic> json) {
    return RouteResponseModel(
      tripId: json['trip_id'],
      mode: json['mode'],
      priority: json['priority'],
      comparison: RouteComparisonModel.fromJson(json['comparison']),
    );
  }
}
