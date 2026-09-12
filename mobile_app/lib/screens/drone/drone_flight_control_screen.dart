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
              boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.04), blurRadius: 8)],
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('Autonomous Drone Control Station (Demo)', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Color(0xFF0F172A))),
                const SizedBox(height: 14),
                Row(
                  children: [
                    _metric('Battery', 'N/A', Icons.battery_unknown, Colors.grey),
                    _metric('Altitude', 'N/A', Icons.height, Colors.grey),
                    _metric('Flight Speed', 'N/A', Icons.speed, Colors.grey),
                  ],
                ),
                const SizedBox(height: 8),
                const Center(
                  child: Text('Hardware not connected. Feature unavailable.', style: TextStyle(fontSize: 12, color: Colors.orange, fontWeight: FontWeight.bold)),
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
                backgroundColor: Colors.grey,
                foregroundColor: Colors.white,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
              ),
              onPressed: () {
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(
                    behavior: SnackBarBehavior.floating,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(25)),
                    backgroundColor: Colors.orange,
                    content: Row(
                      children: const [
                        Icon(Icons.warning_amber_rounded, color: Colors.white, size: 20),
                        SizedBox(width: 10),
                        Expanded(child: Text('Demo Mode: Hardware unavailable.', style: TextStyle(fontSize: 12, color: Colors.white))),
                      ],
                    ),
                  ),
                );
              },
              icon: const Icon(Icons.flight_takeoff_rounded),
              label: const Text('Start Autonomous Scan (Demo)', style: TextStyle(fontSize: 15, fontWeight: FontWeight.bold)),
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
