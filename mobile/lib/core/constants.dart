import 'package:flutter/material.dart';

class AppConstants {
  static const String appName = 'QPath';
  static const String appTagline = 'Quantum-Inspired Route Optimizer';
  
  // Default Backend URLs (10.0.2.2 for Android Emulator, localhost for Web/Desktop)
  static const String defaultBaseUrl = 'http://127.0.0.1:8000/api';
  static const String defaultWsUrl = 'ws://127.0.0.1:8000/ws/route';
  
  // Default Map Coordinates (New Delhi Connaught Place)
  static const double defaultLat = 28.6315;
  static const double defaultLon = 77.2167;
  static const double defaultZoom = 13.5;
  
  // OpenStreetMap Tile URL (Free, Zero API keys required)
  static const String osmTileUrl = 'https://tile.openstreetmap.org/{z}/{x}/{y}.png';
}

class AppColors {
  static const Color backgroundDark = Color(0xFF090D16);
  static const Color surfaceDark = Color(0xFF131B2E);
  static const Color surfaceElevated = Color(0xFF1B2640);
  static const Color surfaceCard = Color(0xFF172138);

  static const Color quantumCyan = Color(0xFF00F0FF);
  static const Color quantumPurple = Color(0xFF8A2BE2);
  static const Color quantumMagenta = Color(0xFFFF007F);
  
  static const Color standardRoute = Color(0xFF718096);
  static const Color qpsoRoute = Color(0xFF00F0FF);
  static const Color emergencyRoute = Color(0xFFFF3366);
  
  static const Color textPrimary = Color(0xFFF1F5F9);
  static const Color textSecondary = Color(0xFF94A3B8);
  static const Color textMuted = Color(0xFF64748B);

  static const Color success = Color(0xFF00E676);
  static const Color warning = Color(0xFFFFB800);
  static const Color error = Color(0xFFFF385C);
}
