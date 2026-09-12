import 'dart:ui' as ui;

import 'package:flutter/material.dart';

import 'package:flutter/material.dart';

class OrganicLeafPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = const Color(0xFFD1FAE5).withOpacity(0.45)
      ..style = PaintingStyle.fill;

    final path = ui.Path();
    path.moveTo(0, size.height);
    path.quadraticBezierTo(size.width * 0.3, size.height * 0.3, size.width * 0.65, size.height * 0.55);
    path.quadraticBezierTo(size.width * 0.85, size.height * 0.7, size.width, size.height);
    path.close();
    canvas.drawPath(path, paint);

    final leafPaint = Paint()
      ..color = const Color(0xFF059669).withOpacity(0.22)
      ..style = PaintingStyle.fill;

    final leafPath = ui.Path();
    leafPath.moveTo(12, size.height - 8);
    leafPath.quadraticBezierTo(32, size.height - 40, 18, size.height - 55);
    leafPath.quadraticBezierTo(4, size.height - 40, 12, size.height - 8);
    canvas.drawPath(leafPath, leafPaint);
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}

// ==================== 5. PROFESSIONAL MODERN DESIGN SYSTEM DRAWER ====================
