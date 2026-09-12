import 'dart:convert';
import 'dart:math';

import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:http/http.dart' as http;
import 'package:latlong2/latlong.dart';

import '../../config/app_config.dart';

class FarmSetupWizardScreen extends StatefulWidget {
  final String fullName;
  final String emailOrPhone;
  final String gender;
  final int age;
  final int avatarId;
  final String password;
  final String otpCode;
  final Function(Map<String, dynamic>) onSetupComplete;

  const FarmSetupWizardScreen({
    super.key,
    required this.fullName,
    required this.emailOrPhone,
    required this.gender,
    required this.age,
    required this.avatarId,
    required this.password,
    required this.otpCode,
    required this.onSetupComplete,
  });

  @override
  State<FarmSetupWizardScreen> createState() => _FarmSetupWizardScreenState();
}

class _FarmSetupWizardScreenState extends State<FarmSetupWizardScreen> {
  final _farmNameController = TextEditingController();
  String _cropType = 'Wheat & Paddy';
  final List<LatLng> _polygonPoints = [];
  bool _isLoading = false;

  @override
  void dispose() {
    _farmNameController.dispose();
    super.dispose();
  }

  double _computePolygonAcres(List<LatLng> points) {
    if (points.length < 3) return 0.0;

    const double radius = 6371000.0;
    double area = 0.0;

    for (int i = 0; i < points.length; i++) {
      final int j = (i + 1) % points.length;
      final double lat1 = points[i].latitude * (pi / 180.0);
      final double lon1 = points[i].longitude * (pi / 180.0);
      final double lat2 = points[j].latitude * (pi / 180.0);
      final double lon2 = points[j].longitude * (pi / 180.0);
      area += (lon2 - lon1) * (2.0 + sin(lat1) + sin(lat2));
    }

    area = (area * radius * radius / 2.0).abs();
    return double.parse((area / 4046.86).toStringAsFixed(2));
  }

  double get _calculatedAcres => _computePolygonAcres(_polygonPoints);

  void _showMessage(String message, {bool error = true}) {
    if (!mounted) return;
    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(
        SnackBar(
          content: Text(message),
          backgroundColor: error ? Colors.redAccent : const Color(0xFF059669),
        ),
      );
  }

  Future<void> _completeRegistration() async {
    if (_isLoading) return;

    final farmName = _farmNameController.text.trim();
    final acres = _calculatedAcres;

    if (farmName.isEmpty) {
      _showMessage('Please enter your farm or field name.');
      return;
    }
    if (_polygonPoints.length < 3 || acres <= 0) {
      _showMessage('Please mark at least 3 boundary points so the farm area can be calculated.');
      return;
    }

    setState(() => _isLoading = true);

    try {
      await AppConfig.resolveActiveHost();

      final payload = <String, dynamic>{
        'full_name': widget.fullName.trim(),
        'phone_or_email': widget.emailOrPhone.trim(),
        'farm_name': farmName,
        'farm_acres': acres,
        'password': widget.password,
        'gender': widget.gender,
        'age': widget.age,
        'avatar_id': widget.avatarId,
        'crop_type': _cropType,
        'otp_code': widget.otpCode.trim(),
      };

      final response = await http
          .post(
            Uri.parse('${AppConfig.backendHttpUrl}/api/v1/auth/register'),
            headers: {'Content-Type': 'application/json'},
            body: jsonEncode(payload),
          )
          .timeout(const Duration(seconds: 12));

      Map<String, dynamic> data = {};
      try {
        final decoded = jsonDecode(response.body);
        if (decoded is Map<String, dynamic>) {
          data = decoded;
        }
      } catch (_) {
        // Handled by the status-code branch below.
      }

      if (response.statusCode < 200 || response.statusCode >= 300) {
        final detail = data['detail']?.toString();
        _showMessage(
          detail != null && detail.isNotEmpty
              ? detail
              : 'Registration failed. Please try again.',
        );
        return;
      }

      if (data['status'] != 'success') {
        final message = data['detail']?.toString() ?? data['message']?.toString();
        _showMessage(
          message != null && message.isNotEmpty
              ? message
              : 'Registration was not completed by the server.',
        );
        return;
      }

      final farmerId = data['farmer_id'];
      if (farmerId == null) {
        _showMessage('Registration succeeded but the server did not return a farmer ID.');
        return;
      }

      final returnedFarm = data['farm'];
      final farm = returnedFarm is Map<String, dynamic>
          ? returnedFarm
          : <String, dynamic>{
              'farm_name': farmName,
              'farm_acres': acres,
              'crop_type': _cropType,
            };

      if (!mounted) return;
      widget.onSetupComplete({
        'id': farmerId,
        'full_name': widget.fullName,
        'phone_or_email': widget.emailOrPhone,
        'gender': widget.gender,
        'age': widget.age,
        'avatar_id': widget.avatarId,
        'farms': [farm],
      });
    } on http.ClientException {
      _showMessage('Unable to contact the registration service. Please check your connection and try again.');
    } catch (_) {
      _showMessage('Registration could not be completed. Please try again.');
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final acres = _calculatedAcres;

    return Scaffold(
      backgroundColor: const Color(0xFFF8FAFC),
      appBar: AppBar(
        backgroundColor: const Color(0xFF0F172A),
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Welcome, ${widget.fullName}',
              style: const TextStyle(fontSize: 15, fontWeight: FontWeight.bold, color: Colors.white),
            ),
            const Text(
              'Farm & Field Configuration',
              style: TextStyle(fontSize: 11, color: Color(0xFF10B981)),
            ),
          ],
        ),
        actions: const [],
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(18),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(14),
                  boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.04), blurRadius: 8)],
                ),
                child: const Row(
                  children: [
                    Icon(Icons.check_circle, color: Color(0xFF059669), size: 18),
                    SizedBox(width: 8),
                    Text('Account Verified', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: Color(0xFF059669))),
                    Spacer(),
                    Icon(Icons.arrow_forward_ios_rounded, color: Colors.grey, size: 12),
                    Spacer(),
                    Icon(Icons.landscape_rounded, color: Color(0xFF059669), size: 18),
                    SizedBox(width: 8),
                    Text('Farm Setup', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: Color(0xFF0F172A))),
                  ],
                ),
              ),
              const SizedBox(height: 16),
              TextField(
                controller: _farmNameController,
                enabled: !_isLoading,
                textCapitalization: TextCapitalization.words,
                decoration: InputDecoration(
                  labelText: 'Farm / Field Name',
                  hintText: 'e.g. Green Valley Farm',
                  prefixIcon: const Icon(Icons.landscape_outlined, color: Color(0xFF059669)),
                  filled: true,
                  fillColor: Colors.white,
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(14),
                    borderSide: const BorderSide(color: Color(0xFFE2E8F0)),
                  ),
                ),
              ),
              const SizedBox(height: 14),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 4),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(color: const Color(0xFFE2E8F0)),
                ),
                child: DropdownButtonHideUnderline(
                  child: DropdownButton<String>(
                    value: _cropType,
                    isExpanded: true,
                    style: const TextStyle(color: Color(0xFF0F172A), fontSize: 13, fontWeight: FontWeight.bold),
                    onChanged: _isLoading ? null : (val) => setState(() => _cropType = val ?? _cropType),
                    items: const [
                      'Wheat & Paddy',
                      'Corn & Maize',
                      'Cotton',
                      'Sugarcane',
                      'Organic Vegetables',
                      'Fruit Orchard',
                      'Pulses & Oilseeds',
                    ].map((c) => DropdownMenuItem(value: c, child: Text(c))).toList(),
                  ),
                ),
              ),
              const SizedBox(height: 16),
              Container(
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(16),
                  boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.04), blurRadius: 8)],
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        const Text('Calculated Farm Boundary:', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: Color(0xFF059669))),
                        Text(
                          '${acres.toStringAsFixed(2)} Acres',
                          style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w900, color: Color(0xFF0F172A)),
                        ),
                      ],
                    ),
                    const SizedBox(height: 6),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        const Expanded(
                          child: Text('Tap the map to mark at least 3 boundary points:', style: TextStyle(fontSize: 11, color: Colors.grey)),
                        if (_polygonPoints.isNotEmpty)
                          GestureDetector(
                            onTap: _isLoading ? null : () => setState(() => _polygonPoints.clear()),
                            child: const Text('Clear Pins', style: TextStyle(fontSize: 11, color: Colors.redAccent, fontWeight: FontWeight.bold)),
                          ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    SizedBox(
                      height: 220,
                      child: ClipRRect(
                        borderRadius: BorderRadius.circular(14),
                        child: FlutterMap(
                          options: MapOptions(
                            initialCenter: const LatLng(20.2961, 85.8245),
                            initialZoom: 15.0,
                            onTap: _isLoading ? null : (_, point) => setState(() => _polygonPoints.add(point)),
                          ),
                          children: [
                            TileLayer(
                              urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
                              userAgentPackageName: 'com.agrisense.app',
                            ),
                            if (_polygonPoints.length >= 3)
                              PolygonLayer(
                                polygons: [
                                  Polygon(
                                    points: _polygonPoints,
                                    color: const Color(0xFF10B981).withValues(alpha: 0.35),
                                    borderColor: const Color(0xFF059669),
                                    borderStrokeWidth: 2,
                                  ),
                                ],
                              ),
                            MarkerLayer(
                              markers: _polygonPoints
                                  .map(
                                    (pt) => Marker(
                                      point: pt,
                                      width: 22,
                                      height: 22,
                                      child: const Icon(Icons.location_on_rounded, color: Color(0xFF059669), size: 20),
                                    ),
                                  )
                                  .toList(),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 20),
              SizedBox(
                width: double.infinity,
                height: 50,
                child: ElevatedButton(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFF059669),
                    foregroundColor: Colors.white,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                  ),
                  onPressed: _isLoading ? null : _completeRegistration,
                  child: _isLoading
                      ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                      : const Text('Complete Setup & Launch Platform', style: TextStyle(fontSize: 15, fontWeight: FontWeight.bold)),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
