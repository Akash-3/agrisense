import 'package:flutter/material.dart';

class AgriSenseLogoBadge extends StatelessWidget {
  final double size;
  final double borderRadius;

  const AgriSenseLogoBadge({super.key, this.size = 64, this.borderRadius = 18});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        color: const Color(0xFF0F172A),
        borderRadius: BorderRadius.circular(borderRadius),
        boxShadow: [
          BoxShadow(
            color: const Color(0xFF10B981).withOpacity(0.35),
            blurRadius: size * 0.25,
            spreadRadius: 2,
          )
        ],
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(borderRadius),
        child: Image.asset(
          'assets/images/agrisense_logo.png',
          width: size,
          height: size,
          fit: BoxFit.cover,
          errorBuilder: (ctx, err, stack) {
            return Container(
              color: const Color(0xFF059669),
              child: const Icon(Icons.agriculture_rounded, color: Colors.white, size: 36),
            );
          },
        ),
      ),
    );
  }
}
