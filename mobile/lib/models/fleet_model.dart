import 'package:flutter/material.dart';
import 'package:latlong2/latlong.dart';
import 'route_model.dart';

class FleetVehicleModel {
  final String vehicleId;
  final String name;
  final int capacity;
  final String colorHex;

  FleetVehicleModel({
    required this.vehicleId,
    required this.name,
    required this.capacity,
    required this.colorHex,
  });

  Color get color {
    try {
      String hex = colorHex.replaceAll('#', '');
      if (hex.length == 6) hex = 'FF$hex';
      return Color(int.parse(hex, radix: 16));
    } catch (_) {
      return Colors.cyan;
    }
  }

  Map<String, dynamic> toJson() => {
    'vehicle_id': vehicleId,
    'name': name,
    'capacity': capacity,
    'color': colorHex,
  };
}

class VehicleRouteModel {
  final String vehicleId;
  final String vehicleName;
  final String colorHex;
  final List<CoordinateModel> stops;
  final PathResultModel path;
  final String totalTimeFormatted;
  final String totalDistanceFormatted;
  final int assignedCapacity;

  VehicleRouteModel({
    required this.vehicleId,
    required this.vehicleName,
    required this.colorHex,
    required this.stops,
    required this.path,
    required this.totalTimeFormatted,
    required this.totalDistanceFormatted,
    required this.assignedCapacity,
  });

  factory VehicleRouteModel.fromJson(Map<String, dynamic> json) {
    var rawStops = json['stops'] as List<dynamic>? ?? [];
    List<CoordinateModel> stopsList = rawStops.map((s) => CoordinateModel.fromJson(s)).toList();

    return VehicleRouteModel(
      vehicleId: json['vehicle_id'],
      vehicleName: json['vehicle_name'],
      colorHex: json['color'] ?? '#00F0FF',
      stops: stopsList,
      path: PathResultModel.fromJson(json['path']),
      totalTimeFormatted: json['total_time_formatted'],
      totalDistanceFormatted: json['total_distance_formatted'],
      assignedCapacity: json['assigned_capacity'] ?? 0,
    );
  }
}

class FleetRouteResponseModel {
  final List<VehicleRouteModel> fleetRoutes;
  final double totalFleetTimeSeconds;
  final double totalFleetDistanceMeters;
  final String totalFleetTimeFormatted;
  final String totalFleetDistanceFormatted;
  final double totalFuelLiters;
  final double totalCarbonKg;
  final int vehiclesDeployed;

  FleetRouteResponseModel({
    required this.fleetRoutes,
    required this.totalFleetTimeSeconds,
    required this.totalFleetDistanceMeters,
    required this.totalFleetTimeFormatted,
    required this.totalFleetDistanceFormatted,
    required this.totalFuelLiters,
    required this.totalCarbonKg,
    required this.vehiclesDeployed,
  });

  factory FleetRouteResponseModel.fromJson(Map<String, dynamic> json) {
    var rawRoutes = json['fleet_routes'] as List<dynamic>? ?? [];
    List<VehicleRouteModel> routesList = rawRoutes.map((r) => VehicleRouteModel.fromJson(r)).toList();

    return FleetRouteResponseModel(
      fleetRoutes: routesList,
      totalFleetTimeSeconds: (json['total_fleet_time_seconds'] as num).toDouble(),
      totalFleetDistanceMeters: (json['total_fleet_distance_meters'] as num).toDouble(),
      totalFleetTimeFormatted: json['total_fleet_time_formatted'],
      totalFleetDistanceFormatted: json['total_fleet_distance_formatted'],
      totalFuelLiters: (json['total_fuel_liters'] as num).toDouble(),
      totalCarbonKg: (json['total_carbon_kg'] as num).toDouble(),
      vehiclesDeployed: json['vehicles_deployed'] ?? 0,
    );
  }
}
