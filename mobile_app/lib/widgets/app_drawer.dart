import 'package:flutter/material.dart';
import '../painters/organic_leaf_painter.dart';
import 'farmer_avatar_widget.dart';

class AppDrawer extends StatelessWidget {
  final Map<String, dynamic> farmer;
  final List<Map<String, dynamic>> farms;
  final int selectedIdx;
  final VoidCallback onLogout;
  final VoidCallback onEditProfile;
  final VoidCallback? onOpenCropAiScanner;
  final Function(int) onSelectScreen;

  const AppDrawer({
    super.key,
    required this.farmer,
    required this.farms,
    required this.selectedIdx,
    required this.onLogout,
    required this.onEditProfile,
    this.onOpenCropAiScanner,
    required this.onSelectScreen,
  });

  Widget _buildNavItem({
    required BuildContext context,
    required String title,
    required String subtitle,
    required IconData icon,
    required bool isSelected,
    required VoidCallback onTap,
    bool isDestructive = false,
  }) {
    final Color cardBg = isDestructive
        ? const Color(0xFFFEF2F2)
        : (isSelected ? const Color(0xFFECFDF5) : Colors.white);

    final Color borderColor = isDestructive
        ? const Color(0xFFFCA5A5)
        : (isSelected ? const Color(0xFFA7F3D0) : const Color(0xFFF1F5F9));

    final Color iconBg = isDestructive
        ? const Color(0xFFFEE2E2)
        : (isSelected ? const Color(0xFFD1FAE5) : const Color(0xFFF1F5F9));

    final Color iconColor = isDestructive
        ? const Color(0xFFDC2626)
        : (isSelected ? const Color(0xFF059669) : const Color(0xFF047857));

    final Color titleColor = isDestructive
        ? const Color(0xFFB91C1C)
        : (isSelected ? const Color(0xFF064E3B) : const Color(0xFF0F172A));

    final Color subtitleColor = isDestructive
        ? const Color(0xFFEF4444)
        : const Color(0xFF64748B);

    final Color chevronColor = isDestructive
        ? const Color(0xFFEF4444)
        : (isSelected ? const Color(0xFF059669) : const Color(0xFF94A3B8));

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 5),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(20),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
          decoration: BoxDecoration(
            color: cardBg,
            borderRadius: BorderRadius.circular(20),
            border: Border.all(color: borderColor, width: 1.2),
            boxShadow: isSelected || isDestructive
                ? []
                : [
                    BoxShadow(
                      color: Colors.black.withValues(alpha: 0.03),
                      blurRadius: 10,
                      offset: const Offset(0, 3),
                    )
                  ],
          ),
          child: Row(
            children: [
              Container(
                width: 44,
                height: 44,
                decoration: BoxDecoration(
                  color: iconBg,
                  borderRadius: BorderRadius.circular(14),
                ),
                child: Icon(icon, color: iconColor, size: 22),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      title,
                      style: TextStyle(
                        color: titleColor,
                        fontWeight: FontWeight.w700,
                        fontSize: 14.5,
                        letterSpacing: -0.2,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      subtitle,
                      style: TextStyle(
                        color: subtitleColor,
                        fontSize: 11.5,
                        fontWeight: FontWeight.w400,
                      ),
                    ),
                  ],
                ),
              ),
              Icon(Icons.chevron_right_rounded, color: chevronColor, size: 20),
            ],
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final active = farms.isNotEmpty && selectedIdx < farms.length
        ? farms[selectedIdx]
        : {'farm_name': 'Main Farm', 'farm_acres': 15.0};

    final String name = farmer['full_name'] ?? 'Akash Satapathy';
    final String farmName = active['farm_name'] ?? 'Main Farm';
    final double acres = (active['farm_acres'] ?? 15.0).toDouble();

    return Drawer(
      backgroundColor: const Color(0xFFF8FAFC),
      child: SafeArea(
        top: false,
        child: Column(
          children: [
            // HEADER CARD
            Container(
              width: double.infinity,
              padding: const EdgeInsets.fromLTRB(20, 52, 20, 24),
              decoration: const BoxDecoration(
                gradient: LinearGradient(
                  colors: [Color(0xFF064E3B), Color(0xFF022C22)],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                ),
                borderRadius: BorderRadius.vertical(bottom: Radius.circular(32)),
              ),
              child: Stack(
                children: [
                  Positioned(
                    top: -10,
                    right: -10,
                    child: Opacity(
                      opacity: 0.12,
                      child: Icon(Icons.airplanemode_active_rounded, size: 85, color: Colors.white),
                    ),
                  ),
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Stack(
                        children: [
                          Container(
                            decoration: BoxDecoration(
                              shape: BoxShape.circle,
                              border: Border.all(color: Colors.white.withValues(alpha: 0.9), width: 2.5),
                            ),
                            child: FarmerAvatarWidget(
                              avatarId: farmer['avatar_id'] ?? 1,
                              name: name,
                              radius: 34,
                            ),
                          ),
                          Positioned(
                            bottom: 2,
                            right: 2,
                            child: Container(
                              width: 14,
                              height: 14,
                              decoration: BoxDecoration(
                                color: const Color(0xFF22C55E),
                                shape: BoxShape.circle,
                                border: Border.all(color: const Color(0xFF064E3B), width: 2),
                              ),
                            ),
                          )
                        ],
                      ),
                      const SizedBox(height: 14),
                      Text(
                        name,
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 20,
                          fontWeight: FontWeight.bold,
                          letterSpacing: -0.4,
                        ),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        '$farmName (${acres.toStringAsFixed(1)} Acres)',
                        style: const TextStyle(
                          color: Color(0xFFA7F3D0),
                          fontSize: 13,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                      const SizedBox(height: 16),
                      // Technology Capsule Pill
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                        decoration: BoxDecoration(
                          color: Colors.white.withValues(alpha: 0.1),
                          borderRadius: BorderRadius.circular(16),
                          border: Border.all(color: Colors.white.withValues(alpha: 0.2)),
                        ),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Container(
                              padding: const EdgeInsets.all(6),
                              decoration: BoxDecoration(
                                color: const Color(0xFF059669),
                                borderRadius: BorderRadius.circular(10),
                              ),
                              child: const Icon(Icons.eco_rounded, color: Colors.white, size: 16),
                            ),
                            const SizedBox(width: 10),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: const [
                                  Text(
                                    'Farming Smarter',
                                    style: TextStyle(
                                      color: Colors.white,
                                      fontSize: 12.5,
                                      fontWeight: FontWeight.bold,
                                    ),
                                  ),
                                  Text(
                                    'With Technology',
                                    style: TextStyle(
                                      color: Color(0xFFA7F3D0),
                                      fontSize: 10.5,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                            const Icon(Icons.chevron_right_rounded, color: Color(0xFFA7F3D0), size: 18),
                          ],
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(height: 12),
            // NAVIGATION ITEMS LIST
            Expanded(
              child: ListView(
                padding: EdgeInsets.zero,
                children: [
                  _buildNavItem(
                    context: context,
                    title: 'Dashboard & Analytics',
                    subtitle: 'Overview of your farm data',
                    icon: Icons.grid_view_rounded,
                    isSelected: selectedIdx == 0,
                    onTap: () {
                      onSelectScreen(0);
                    },
                  ),
                  _buildNavItem(
                    context: context,
                    title: 'Satellite Terrain Map',
                    subtitle: 'View and analyze your fields',
                    icon: Icons.map_rounded,
                    isSelected: selectedIdx == 1,
                    onTap: () {
                      onSelectScreen(1);
                    },
                  ),
                  _buildNavItem(
                    context: context,
                    title: 'Autonomous Drone Station',
                    subtitle: 'Control and monitor drones',
                    icon: Icons.flight_takeoff_rounded,
                    isSelected: selectedIdx == 2,
                    onTap: () {
                      onSelectScreen(2);
                    },
                  ),
                  _buildNavItem(
                    context: context,
                    title: 'Live Crop AI Health Scan',
                    subtitle: 'Snap photo for instant AI diagnosis',
                    icon: Icons.center_focus_strong_rounded,
                    isSelected: false,
                    onTap: () {
                      Navigator.pop(context);
                      if (onOpenCropAiScanner != null) {
                        onOpenCropAiScanner!();
                      }
                    },
                  ),
                  _buildNavItem(
                    context: context,
                    title: 'Settings',
                    subtitle: 'App preferences & system setup',
                    icon: Icons.settings_rounded,
                    isSelected: selectedIdx == 3,
                    onTap: () {
                      onSelectScreen(3);
                    },
                  ),
                  _buildNavItem(
                    context: context,
                    title: 'Edit Profile & Account',
                    subtitle: 'Manage your personal information',
                    icon: Icons.person_rounded,
                    isSelected: false,
                    onTap: () {
                      Navigator.pop(context);
                      onEditProfile();
                    },
                  ),
                  const SizedBox(height: 12),
                  const Padding(
                    padding: EdgeInsets.symmetric(horizontal: 20),
                    child: Divider(color: Color(0xFFE2E8F0), height: 1),
                  ),
                  const SizedBox(height: 12),
                  _buildNavItem(
                    context: context,
                    title: 'Sign Out',
                    subtitle: 'See you again soon!',
                    icon: Icons.logout_rounded,
                    isSelected: false,
                    isDestructive: true,
                    onTap: () {
                      Navigator.pop(context);
                      onLogout();
                    },
                  ),
                ],
              ),
            ),
            // FOOTER WITH ORGANIC VECTOR
            Container(
              height: 60,
              padding: const EdgeInsets.symmetric(horizontal: 20),
              child: CustomPaint(
                painter: OrganicLeafPainter(),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  crossAxisAlignment: CrossAxisAlignment.center,
                  children: [
                    Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: const [
                        Text(
                          'GROW  •  MONITOR  •  SUSTAIN',
                          style: TextStyle(
                            color: Color(0xFF64748B),
                            fontSize: 9.5,
                            fontWeight: FontWeight.bold,
                            letterSpacing: 0.5,
                          ),
                        ),
                        SizedBox(height: 2),
                        Text(
                          'v1.4.0',
                          style: TextStyle(
                            color: Color(0xFF94A3B8),
                            fontSize: 11,
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                      ],
                    ),
                    Row(
                      children: const [
                        Icon(Icons.eco_rounded, color: Color(0xFF047857), size: 14),
                        SizedBox(width: 4),
                        Text(
                          'A Greener\nTomorrow',
                          textAlign: TextAlign.end,
                          style: TextStyle(
                            color: Color(0xFF047857),
                            fontSize: 10,
                            fontWeight: FontWeight.bold,
                            height: 1.1,
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ==================== SPARKLINE WAVE PAINTER ====================
