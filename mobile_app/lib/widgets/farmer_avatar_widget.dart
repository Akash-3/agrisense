import 'package:flutter/material.dart';

// ==================== SHARED DYNAMIC FARMER AVATAR WIDGET ====================
class FarmerAvatarWidget extends StatelessWidget {
  final int avatarId;
  final String name;
  final double radius;
  final Color backgroundColor;

  const FarmerAvatarWidget({
    super.key,
    required this.avatarId,
    required this.name,
    this.radius = 20,
    this.backgroundColor = const Color(0xFF0F172A),
  });

  IconData _getAvatarIcon(int id) {
    switch (id) {
      case 1:
        return Icons.face;
      case 2:
        return Icons.person;
      case 3:
        return Icons.agriculture;
      case 4:
        return Icons.nature_people;
      case 5:
        return Icons.account_circle;
      case 6:
        return Icons.local_florist_rounded; // Lily Floral Avatar
      default:
        return Icons.person;
    }
  }

  @override
  Widget build(BuildContext context) {
    return CircleAvatar(
      radius: radius,
      backgroundColor: backgroundColor,
      child: Icon(
        _getAvatarIcon(avatarId),
        color: Colors.white,
        size: radius * 1.1,
      ),
    );
  }
}

// ==================== ATTRACTIVE SWIPEABLE TOP FLOATING CAPSULE NOTIFICATION ====================
