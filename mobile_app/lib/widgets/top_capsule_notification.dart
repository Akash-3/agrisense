import 'package:flutter/material.dart';

class TopCapsuleNotification extends StatelessWidget {
  final String title;
  final String message;
  final IconData icon;
  final Color backgroundColor;
  final Color textColor;
  final VoidCallback onDismiss;

  const TopCapsuleNotification({
    super.key,
    required this.title,
    required this.message,
    this.icon = Icons.notifications_active_rounded,
    this.backgroundColor = const Color(0xFF0F172A),
    this.textColor = Colors.white,
    required this.onDismiss,
  });

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        child: Dismissible(
          key: UniqueKey(),
          direction: DismissDirection.horizontal,
          onDismissed: (_) => onDismiss(),
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            decoration: BoxDecoration(
              color: backgroundColor,
              borderRadius: BorderRadius.circular(30),
              boxShadow: [
                BoxShadow(
                  color: backgroundColor.withValues(alpha: 0.35),
                  blurRadius: 16,
                  offset: const Offset(0, 6),
                ),
              ],
              border: Border.all(color: Colors.white24, width: 1),
            ),
            child: Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(8),
                  decoration: const BoxDecoration(
                    color: Color(0xFF059669),
                    shape: BoxShape.circle,
                  ),
                  child: Icon(icon, color: Colors.white, size: 18),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        title,
                        style: TextStyle(
                          color: textColor,
                          fontWeight: FontWeight.w900,
                          fontSize: 13,
                        ),
                      ),
                      Text(
                        message,
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(
                          color: textColor.withValues(alpha: 0.85),
                          fontSize: 11,
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: 8),
                InkWell(
                  onTap: onDismiss,
                  borderRadius: BorderRadius.circular(20),
                  child: const Padding(
                    padding: EdgeInsets.all(4.0),
                    child: Icon(Icons.close_rounded, color: Colors.white60, size: 18),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

// ==================== GOOGLE & MICROSOFT LOGO WIDGETS ====================
