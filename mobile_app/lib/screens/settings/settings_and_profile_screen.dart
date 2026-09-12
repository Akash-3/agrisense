import 'package:flutter/material.dart';
import '../../widgets/farmer_avatar_widget.dart';
import '../../config/app_config.dart';

class SettingsAndProfileScreen extends StatefulWidget {
  final Map<String, dynamic> farmer;
  final List<Map<String, dynamic>> farms;
  final int selectedIdx;
  final String appVersion;
  final Function(int) onSelectFarm;
  final Function(String, double, String) onAddFarm;
  final VoidCallback onLogout;
  final VoidCallback onEditProfile;
  final VoidCallback onCheckUpdate;

  const SettingsAndProfileScreen({
    super.key,
    required this.farmer,
    required this.farms,
    required this.selectedIdx,
    required this.appVersion,
    required this.onSelectFarm,
    required this.onAddFarm,
    required this.onLogout,
    required this.onEditProfile,
    required this.onCheckUpdate,
  });

  @override
  State<SettingsAndProfileScreen> createState() => _SettingsAndProfileScreenState();
}

class _SettingsAndProfileScreenState extends State<SettingsAndProfileScreen> {
  bool _useCelsius = true;
  bool _autoSync = true;
  bool _pushAlerts = true;

  void _showAddFarmDialog(BuildContext context) {
    final nameCtrl = TextEditingController();
    final acresCtrl = TextEditingController(text: "20");
    final cropCtrl = TextEditingController(text: "Wheat & Paddy");

    showDialog(
      context: context,
      builder: (ctx) {
        return AlertDialog(
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
          title: const Text('Add New Farm Field', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: nameCtrl,
                textCapitalization: TextCapitalization.words,
                decoration: const InputDecoration(labelText: 'Farm Name (e.g. South Paddy Field)'),
              ),
              const SizedBox(height: 8),
              TextField(
                controller: acresCtrl,
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(labelText: 'Farm Area (Acres)'),
              ),
              const SizedBox(height: 8),
              TextField(
                controller: cropCtrl,
                textCapitalization: TextCapitalization.words,
                decoration: const InputDecoration(labelText: 'Crop Types'),
              ),
            ],
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Cancel')),
            ElevatedButton(
              style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF059669), foregroundColor: Colors.white),
              onPressed: () {
                final name = nameCtrl.text.trim();
                final acres = double.tryParse(acresCtrl.text) ?? 10.0;
                final crop = cropCtrl.text.trim();
                if (name.isNotEmpty) {
                  widget.onAddFarm(name, acres, crop);
                  Navigator.pop(ctx);
                }
              },
              child: const Text('Add Field'),
            ),
          ],
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final activeFarm = widget.farms[widget.selectedIdx];

    return SingleChildScrollView(
      physics: const AlwaysScrollableScrollPhysics(),
      padding: const EdgeInsets.all(16.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // 1. ACCOUNT PROFILE CARD
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(16),
              boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.04), blurRadius: 8)],
            ),
            child: Row(
              children: [
                FarmerAvatarWidget(avatarId: widget.farmer['avatar_id'] ?? 1, name: widget.farmer['full_name'] ?? 'Farmer', radius: 28),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(widget.farmer['full_name'] ?? 'Farmer Account', style: const TextStyle(fontSize: 17, fontWeight: FontWeight.bold, color: Color(0xFF0F172A))),
                      Text(widget.farmer['phone_or_email'] ?? '', style: const TextStyle(fontSize: 11, color: Color(0xFF64748B))),
                      const SizedBox(height: 4),
                      Text('Active Field: ${activeFarm['farm_name']} (${activeFarm['farm_acres']} Acres)', style: const TextStyle(fontSize: 10, color: Color(0xFF059669), fontWeight: FontWeight.bold)),
                    ],
                  ),
                ),
                InkWell(
                  onTap: widget.onEditProfile,
                  borderRadius: BorderRadius.circular(10),
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                    decoration: BoxDecoration(
                      color: const Color(0xFF059669).withOpacity(0.1),
                      borderRadius: BorderRadius.circular(10),
                      border: Border.all(color: const Color(0xFF059669).withOpacity(0.3)),
                    ),
                    child: Row(
                      children: const [
                        Icon(Icons.edit_outlined, size: 14, color: Color(0xFF059669)),
                        SizedBox(width: 4),
                        Text('Edit', style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: Color(0xFF059669))),
                      ],
                    ),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 20),

          // 2. FARM MANAGEMENT CATALOG
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text('Farm Fields Catalog', style: TextStyle(fontSize: 15, fontWeight: FontWeight.bold, color: Color(0xFF0F172A))),
              ElevatedButton.icon(
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF059669),
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                ),
                onPressed: () => _showAddFarmDialog(context),
                icon: const Icon(Icons.add, size: 16),
                label: const Text('Add Field', style: TextStyle(fontSize: 11)),
              ),
            ],
          ),
          const SizedBox(height: 8),

          for (int i = 0; i < widget.farms.length; i++)
            Container(
              margin: const EdgeInsets.only(bottom: 8),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: i == widget.selectedIdx ? const Color(0xFF059669) : Colors.transparent, width: 2),
                boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.03), blurRadius: 6)],
              ),
              child: ListTile(
                leading: Icon(Icons.landscape, color: i == widget.selectedIdx ? const Color(0xFF059669) : Colors.grey),
                title: Text(widget.farms[i]['farm_name'], style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
                subtitle: Text('${widget.farms[i]['farm_acres']} Acres • ${widget.farms[i]['crop_type'] ?? 'Wheat & Paddy'}', style: const TextStyle(fontSize: 11, color: Colors.grey)),
                trailing: Icon(i == widget.selectedIdx ? Icons.check_circle : Icons.circle_outlined, color: const Color(0xFF059669)),
                onTap: () => widget.onSelectFarm(i),
              ),
            ),
          const SizedBox(height: 20),

          // 3. APPLICATION & SOFTWARE UPDATES
          const Text('Software & System Info', style: TextStyle(fontSize: 15, fontWeight: FontWeight.bold, color: Color(0xFF0F172A))),
          const SizedBox(height: 8),

          Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(14),
              boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.03), blurRadius: 6)],
            ),
            child: Row(
              children: [
                const Icon(Icons.system_update_rounded, color: Color(0xFF059669), size: 24),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('AgriSense v${widget.appVersion}', style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: Color(0xFF0F172A))),
                      const Text('Build 2026.09 (Release Edition)', style: TextStyle(fontSize: 10, color: Colors.grey)),
                    ],
                  ),
                ),
                ElevatedButton(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFF059669),
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                  ),
                  onPressed: widget.onCheckUpdate,
                  child: const Text('Check Updates', style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold)),
                ),
              ],
            ),
          ),
          const SizedBox(height: 20),

          // 4. APP PREFERENCES & TOGGLES
          const Text('Preferences & Configuration', style: TextStyle(fontSize: 15, fontWeight: FontWeight.bold, color: Color(0xFF0F172A))),
          const SizedBox(height: 8),

          Container(
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(14),
              boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.03), blurRadius: 6)],
            ),
            child: Column(
              children: [
                SwitchListTile(
                  secondary: const Icon(Icons.thermostat, color: Color(0xFF059669)),
                  title: const Text('Temperature Unit (°C / °F)', style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold)),
                  subtitle: Text(_useCelsius ? 'Celsius (°C)' : 'Fahrenheit (°F)', style: const TextStyle(fontSize: 11, color: Colors.grey)),
                  value: _useCelsius,
                  activeColor: const Color(0xFF059669),
                  onChanged: (val) => setState(() => _useCelsius = val),
                ),
                const Divider(height: 1),
                SwitchListTile(
                  secondary: const Icon(Icons.sync_rounded, color: Color(0xFF059669)),
                  title: const Text('Real-Time Data Sync', style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold)),
                  subtitle: const Text('Automated telemetry stream updates', style: TextStyle(fontSize: 11, color: Colors.grey)),
                  value: _autoSync,
                  activeColor: const Color(0xFF059669),
                  onChanged: (val) => setState(() => _autoSync = val),
                ),
                const Divider(height: 1),
                SwitchListTile(
                  secondary: const Icon(Icons.notifications_active_rounded, color: Color(0xFF059669)),
                  title: const Text('Crop Alert Notifications', style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold)),
                  subtitle: const Text('Receive immediate pathogen and weather warnings', style: TextStyle(fontSize: 11, color: Colors.grey)),
                  value: _pushAlerts,
                  activeColor: const Color(0xFF059669),
                  onChanged: (val) => setState(() => _pushAlerts = val),
                ),
              ],
            ),
          ),
          const SizedBox(height: 24),

          // 5. ACCOUNT LOGOUT BUTTON
          SizedBox(
            width: double.infinity,
            height: 48,
            child: OutlinedButton.icon(
              style: OutlinedButton.styleFrom(
                foregroundColor: Colors.redAccent,
                side: const BorderSide(color: Colors.redAccent),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
              ),
              onPressed: widget.onLogout,
              icon: const Icon(Icons.logout),
              label: const Text('Sign Out of Account', style: TextStyle(fontWeight: FontWeight.bold)),
            ),
          ),
        ],
      ),
    );
  }
}
