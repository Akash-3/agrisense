import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:math';
import 'dart:ui';

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/cupertino.dart';
import 'package:flutter/services.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
import 'package:geolocator/geolocator.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:image_picker/image_picker.dart';
import 'package:http/http.dart' as http;

import '../../config/app_config.dart';
import '../../models/telemetry_models.dart';
import '../../services/websocket_service.dart';
import '../../widgets/agri_logo_badge.dart';
import '../../widgets/app_drawer.dart';
import '../../widgets/farmer_avatar_widget.dart';
import '../../widgets/top_capsule_notification.dart';
import '../dashboard/farmer_dashboard.dart';
import '../drone/drone_flight_control_screen.dart';
import '../settings/settings_and_profile_screen.dart';

class FarmLayoutMapScreen extends StatefulWidget {
  const FarmLayoutMapScreen({super.key});

  @override
  State<FarmLayoutMapScreen> createState() => _FarmLayoutMapScreenState();
}

class _FarmLayoutMapScreenState extends State<FarmLayoutMapScreen> {
  final MapController _mapController = MapController();
  LatLng _currentGpsPos = const LatLng(19.1977, 84.7485);
  bool _isLocating = false;
  int _tileModeIndex = 0;

  final List<List<String>> _tileLayers = [
    [
      'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
      'https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Transportation/MapServer/tile/{z}/{y}/{x}',
      'https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}',
    ],
    [
      'https://tile.opentopomap.org/{z}/{x}/{y}.png',
    ],
    [
      'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
    ]
  ];

  final List<LatLng> _farmPolygon = [
    const LatLng(19.1985, 84.7475),
    const LatLng(19.1985, 84.7495),
    const LatLng(19.1965, 84.7495),
    const LatLng(19.1965, 84.7475),
  ];

  @override
  void initState() {
    super.initState();
    _fetchLiveGpsLocation();
  }

  Future<void> _fetchLiveGpsLocation() async {
    setState(() => _isLocating = true);
    try {
      LocationPermission permission = await Geolocator.checkPermission();
      if (permission == LocationPermission.denied) {
        permission = await Geolocator.requestPermission();
      }
      if (permission == LocationPermission.whileInUse || permission == LocationPermission.always) {
        Position pos = await Geolocator.getCurrentPosition(desiredAccuracy: LocationAccuracy.high);
        setState(() {
          _currentGpsPos = LatLng(pos.latitude, pos.longitude);
        });
        _mapController.move(_currentGpsPos, 16.5);
      }
    } catch (e) {
      // Fallback
    } finally {
      if (mounted) setState(() => _isLocating = false);
    }
  }

  double _calculatePolygonAreaAcres() {
    if (_farmPolygon.length < 3) return 0.0;
    double area = 0.0;
    int j = _farmPolygon.length - 1;
    for (int i = 0; i < _farmPolygon.length; i++) {
      final p1 = _farmPolygon[i];
      final p2 = _farmPolygon[j];
      area += (p2.longitude + p1.longitude) * (p2.latitude - p1.latitude);
      j = i;
    }
    double sqMeters = (area.abs() * 0.5) * 111319.5 * 111319.5 * cos(_currentGpsPos.latitude * pi / 180).abs();
    return sqMeters / 4046.86;
  }

  void _undoLastPoint() {
    if (_farmPolygon.isNotEmpty) {
      setState(() {
        _farmPolygon.removeLast();
      });
    }
  }

  void _clearPolygon() {
    setState(() {
      _farmPolygon.clear();
    });
  }

  @override
  Widget build(BuildContext context) {
    final areaAcres = _calculatePolygonAreaAcres();

    return Column(
      children: [
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
          color: const Color(0xFF0F172A),
          child: SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            physics: const BouncingScrollPhysics(),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('Google Hybrid Satellite Terrain', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 12, color: Colors.white)),
                    Text('Area: ${areaAcres.toStringAsFixed(1)} Acres (${_farmPolygon.length} Drag-Adjustable Corners)', style: const TextStyle(fontSize: 10, color: Color(0xFF34D399), fontWeight: FontWeight.bold)),
                  ],
                ),
                const SizedBox(width: 14),
                Row(
                  children: [
                    IconButton(
                      icon: const Icon(Icons.undo_rounded, color: Colors.amber, size: 20),
                      tooltip: 'Undo Corner',
                      onPressed: _undoLastPoint,
                    ),
                    IconButton(
                      icon: const Icon(Icons.delete_outline_rounded, color: Colors.redAccent, size: 20),
                      tooltip: 'Clear Polygon',
                      onPressed: _clearPolygon,
                    ),
                    IconButton(
                      icon: Icon(
                        _tileModeIndex == 0 ? Icons.satellite_alt : (_tileModeIndex == 1 ? Icons.terrain : Icons.map),
                        color: const Color(0xFF10B981),
                        size: 20,
                      ),
                      tooltip: 'Switch Map Layer',
                      onPressed: () {
                        setState(() {
                          _tileModeIndex = (_tileModeIndex + 1) % 3;
                        });
                      },
                    ),
                    const SizedBox(width: 4),
                    ElevatedButton.icon(
                      style: ElevatedButton.styleFrom(
                        backgroundColor: const Color(0xFF059669),
                        foregroundColor: Colors.white,
                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                      ),
                      onPressed: () {
                        ScaffoldMessenger.of(context).showSnackBar(
                          SnackBar(
                            behavior: SnackBarBehavior.floating,
                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(25)),
                            backgroundColor: const Color(0xFF059669),
                            content: Row(
                              children: [
                                const Icon(Icons.alt_route_rounded, color: Colors.white, size: 20),
                                const SizedBox(width: 10),
                                Expanded(child: Text('Autonomous Drone Flight Grid Generated for ${areaAcres.toStringAsFixed(1)} Acres!', style: const TextStyle(fontSize: 12, color: Colors.white))),
                              ],
                            ),
                          ),
                        );
                      },
                      icon: const Icon(Icons.alt_route_rounded, size: 14),
                      label: const Text('Plan Flight Grid', style: TextStyle(fontSize: 11)),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),

        Expanded(
          child: Stack(
            children: [
              FlutterMap(
                mapController: _mapController,
                options: MapOptions(
                  initialCenter: _currentGpsPos,
                  initialZoom: 16.5,
                  onTap: (pos, point) {
                    setState(() => _farmPolygon.add(point));
                  },
                ),
                children: [
                  for (String url in _tileLayers[_tileModeIndex])
                    TileLayer(
                      urlTemplate: url,
                      userAgentPackageName: 'com.agrisense.app',
                    ),
                  if (_farmPolygon.length >= 3)
                    PolygonLayer(
                      polygons: [
                        Polygon(
                          points: _farmPolygon,
                          color: const Color(0xFF10B981).withOpacity(0.3),
                          borderColor: const Color(0xFF10B981),
                          borderStrokeWidth: 3,
                          isFilled: true,
                        ),
                      ],
                    ),
                  if (_farmPolygon.length >= 2)
                    PolylineLayer(
                      polylines: [
                        Polyline(
                          points: _farmPolygon,
                          color: const Color(0xFF10B981),
                          strokeWidth: 3,
                        ),
                      ],
                    ),
                  MarkerLayer(
                    markers: [
                      Marker(
                        point: _currentGpsPos,
                        width: 44,
                        height: 44,
                        child: Container(
                          decoration: BoxDecoration(
                            color: const Color(0xFF10B981),
                            shape: BoxShape.circle,
                            border: Border.all(color: Colors.white, width: 3),
                            boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.3), blurRadius: 8)],
                          ),
                          child: const Icon(Icons.my_location, color: Colors.white, size: 22),
                        ),
                      ),

                      for (int i = 0; i < _farmPolygon.length; i++)
                        Marker(
                          point: _farmPolygon[i],
                          width: 44,
                          height: 44,
                          child: GestureDetector(
                            onPanUpdate: (details) {
                              final currentPixel = _mapController.camera.latLngToScreenPoint(_farmPolygon[i]);
                              final newPixel = Offset(currentPixel.x + details.delta.dx, currentPixel.y + details.delta.dy);
                              final newLatLng = _mapController.camera.pointToLatLng(Point(newPixel.dx, newPixel.dy));
                              setState(() {
                                _farmPolygon[i] = newLatLng;
                              });
                            },
                            child: Container(
                              decoration: BoxDecoration(
                                color: Colors.amber,
                                shape: BoxShape.circle,
                                border: Border.all(color: Colors.black, width: 2.5),
                                boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.4), blurRadius: 6)],
                              ),
                              child: Center(
                                child: Text(
                                  '${i + 1}',
                                  style: const TextStyle(color: Colors.black, fontSize: 13, fontWeight: FontWeight.bold),
                                ),
                              ),
                            ),
                          ),
                        ),
                    ],
                  ),
                ],
              ),
              Positioned(
                bottom: 16,
                right: 16,
                child: FloatingActionButton.small(
                  backgroundColor: Colors.white,
                  foregroundColor: const Color(0xFF059669),
                  onPressed: _fetchLiveGpsLocation,
                  child: _isLocating
                      ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2, color: Color(0xFF059669)))
                      : const Icon(Icons.gps_fixed),
                ),
              ),
              Positioned(
                top: 12,
                left: 12,
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                  decoration: BoxDecoration(
                    color: Colors.black87,
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Text(
                    _tileModeIndex == 0 ? 'Google Hybrid Satellite Terrain (Touch & Drag Markers to Adjust)' : (_tileModeIndex == 1 ? 'Topo Contour Map' : 'OpenStreetMap'),
                    style: const TextStyle(color: Colors.white, fontSize: 10, fontWeight: FontWeight.bold),
                  ),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

// ==================== 8. AUTONOMOUS DRONE CONTROL ====================
