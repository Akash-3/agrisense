import 'package:flutter/material.dart';
import '../../services/auth_service.dart';

class DeviceManagementScreen extends StatefulWidget {
  final int farmId;
  final String farmName;

  const DeviceManagementScreen({
    super.key,
    required this.farmId,
    required this.farmName,
  });

  @override
  State<DeviceManagementScreen> createState() => _DeviceManagementScreenState();
}

class _DeviceManagementScreenState extends State<DeviceManagementScreen> {
  final _authService = AuthService();
  bool _isLoading = true;
  List<dynamic> _zones = [];
  List<dynamic> _devices = [];

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  Future<void> _loadData() async {
    setState(() => _isLoading = true);
    try {
      final zones = await _authService.getZones(widget.farmId);
      final devices = await _authService.getDevices(widget.farmId);
      setState(() {
        _zones = zones;
        _devices = devices;
        _isLoading = false;
      });
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to load devices: $e')),
        );
        setState(() => _isLoading = false);
      }
    }
  }

  void _showAssignModal(int zoneId, String zoneName) {
    final controller = TextEditingController();
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Assign Device'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Target Zone: $zoneName', style: const TextStyle(fontWeight: FontWeight.bold)),
            const SizedBox(height: 12),
            TextField(
              controller: controller,
              decoration: const InputDecoration(
                labelText: 'Device ID',
                hintText: 'e.g. ESP32_MULTI_NODE_01',
                border: OutlineInputBorder(),
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () async {
              final deviceId = controller.text.trim();
              if (deviceId.isEmpty) return;
              Navigator.pop(ctx);
              await _assignDevice(deviceId, zoneId);
            },
            child: const Text('Provision'),
          ),
        ],
      ),
    );
  }

  Future<void> _assignDevice(String deviceId, int zoneId) async {
    setState(() => _isLoading = true);
    try {
      await _authService.assignDevice(deviceId, zoneId);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Device assigned successfully!')),
        );
      }
      await _loadData();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error assigning device: $e')),
        );
        setState(() => _isLoading = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Hardware Provisioning'),
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _zones.isEmpty
              ? const Center(child: Text('No zones found for this farm.'))
              : ListView.builder(
                  padding: const EdgeInsets.all(16),
                  itemCount: _zones.length,
                  itemBuilder: (context, index) {
                    final zone = _zones[index];
                    final zoneDevices = _devices.where((d) => d['zone_id'] == zone['id']).toList();

                    return Card(
                      margin: const EdgeInsets.only(bottom: 16),
                      child: Padding(
                        padding: const EdgeInsets.all(16.0),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              mainAxisAlignment: MainAxisAlignment.spaceBetween,
                              children: [
                                Expanded(
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      Text(
                                        zone['zone_name'],
                                        style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
                                      ),
                                      Text('${zone['acres']} Acres', style: const TextStyle(color: Colors.grey)),
                                    ],
                                  ),
                                ),
                                ElevatedButton.icon(
                                  onPressed: () => _showAssignModal(zone['id'], zone['zone_name']),
                                  icon: const Icon(Icons.add, size: 16),
                                  label: const Text('Assign'),
                                ),
                              ],
                            ),
                            const Divider(),
                            if (zoneDevices.isEmpty)
                              const Padding(
                                padding: EdgeInsets.all(8.0),
                                child: Text('No devices assigned', style: TextStyle(color: Colors.grey, fontStyle: FontStyle.italic)),
                              )
                            else
                              ...zoneDevices.map((d) => ListTile(
                                leading: const Icon(Icons.memory, color: Colors.green),
                                title: Text(d['device_id'], style: const TextStyle(fontWeight: FontWeight.bold)),
                                subtitle: Text('Type: ${d['device_type']}'),
                                trailing: const Chip(label: Text('Assigned'), backgroundColor: Colors.greenAccent),
                              )),
                          ],
                        ),
                      ),
                    );
                  },
                ),
    );
  }
}
