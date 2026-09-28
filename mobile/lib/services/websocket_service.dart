import 'dart:async';
import 'dart:convert';
import 'package:web_socket_channel/web_socket_channel.dart';
import '../core/constants.dart';
import '../models/route_model.dart';

class WebSocketService {
  WebSocketChannel? _channel;
  final String tripId;
  final Function(Map<String, dynamic>) onMessageReceived;
  bool isConnected = false;

  WebSocketService({
    required this.tripId,
    required this.onMessageReceived,
  });

  void connect({String baseUrl = AppConstants.defaultWsUrl}) {
    try {
      final uri = Uri.parse('$baseUrl/$tripId');
      _channel = WebSocketChannel.connect(uri);
      isConnected = true;

      _channel!.stream.listen(
        (message) {
          try {
            final data = jsonDecode(message);
            onMessageReceived(data);
          } catch (e) {
            print('Error parsing ws msg: $e');
          }
        },
        onDone: () {
          isConnected = false;
          print('WebSocket closed for trip $tripId');
        },
        onError: (error) {
          isConnected = false;
          print('WebSocket error: $error');
        },
      );
    } catch (e) {
      isConnected = false;
      print('WebSocket connection exception: $e');
    }
  }

  void startTrip({
    required CoordinateModel source,
    required CoordinateModel destination,
    String priority = 'balanced',
    String mode = 'personal',
  }) {
    _send({
      'action': 'START_TRIP',
      'source': source.toJson(),
      'destination': destination.toJson(),
      'priority': priority,
      'mode': mode,
    });
  }

  void updatePosition(double lat, double lon) {
    _send({
      'action': 'UPDATE_POSITION',
      'lat': lat,
      'lon': lon,
    });
  }

  void triggerDemoIncident({
    required String incidentType,
    required double lat,
    required double lon,
    String description = 'Judge Demo Incident',
  }) {
    _send({
      'action': 'TRIGGER_DEMO_INCIDENT',
      'incident_type': incidentType,
      'lat': lat,
      'lon': lon,
      'description': description,
    });
  }

  void acceptReroute(Map<String, dynamic> newComparison) {
    _send({
      'action': 'ACCEPT_REROUTE',
      'new_comparison': newComparison,
    });
  }

  void _send(Map<String, dynamic> data) {
    if (_channel != null && isConnected) {
      _channel!.sink.add(jsonEncode(data));
    }
  }

  void disconnect() {
    _channel?.sink.close();
    isConnected = false;
  }
}
