import 'package:flutter/material.dart';

import '../../models/telemetry_models.dart';

class DroneFlightControlScreen extends StatelessWidget {
  final TelemetryPacket? packet;
  final bool isConnected;

  const DroneFlightControlScreen({super.key, required this.packet, required this.isConnected});

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      physics: const AlwaysScrollableScrollPhysics(),
      padding: const EdgeInsets.all(16.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(16),
              boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.04), blurRadius: 8)],
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('Autonomous Drone Control Station', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Color(0xFF0F172A))),
                const SizedBox(height: 14),
                Row(
                  children: [
                    _metric('Battery', '88%', Icons.battery_charging_full, Colors.green),
                    _metric('Altitude', '15.0 m', Icons.height, Colors.cyan[700]!),
                    _metric('Flight Speed', '4.2 m/s', Icons.speed, Colors.amber[800]!),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: 20),
          SizedBox(
            width: double.infinity,
            height: 50,
            child: ElevatedButton.icon(
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0xFF059669),
                foregroundColor: Colors.white,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
              ),
              onPressed: () {
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(
                    behavior: SnackBarBehavior.floating,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(25)),
                    backgroundColor: const Color(0xFF059669),
                    content: Row(
                      children: const [
                        Icon(Icons.flight_takeoff_rounded, color: Colors.white, size: 20),
                        SizedBox(width: 10),
                        Expanded(child: Text('Autonomous Scan Mission Dispatched!', style: TextStyle(fontSize: 12, color: Colors.white))),
                      ],
                    ),
                  ),
                );
              },
              icon: const Icon(Icons.flight_takeoff_rounded),
              label: const Text('Start Autonomous Scan Mission', style: TextStyle(fontSize: 15, fontWeight: FontWeight.bold)),
            ),
          ),
        ],
      ),
    );
  }

  Widget _metric(String title, String val, IconData icon, Color color) {
    return Expanded(
      child: Column(
        children: [
          Icon(icon, color: color, size: 22),
          const SizedBox(height: 4),
          Text(title, style: const TextStyle(fontSize: 10, color: Color(0xFF64748B))),
          Text(val, style: const TextStyle(fontSize: 14, fontWeight: FontWeight.bold, color: Color(0xFF0F172A))),
        ],
      ),
    );
  }
}

// ==================== 9. UNIFIED ENTERPRISE "SETTINGS & PROFILE" HUB ====================
