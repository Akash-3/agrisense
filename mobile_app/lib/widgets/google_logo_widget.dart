import 'dart:ui' as ui;

import 'package:flutter/material.dart';

class GoogleLogoWidget extends StatelessWidget {
  const GoogleLogoWidget({super.key});

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 20,
      height: 20,
      child: CustomPaint(painter: GoogleGPainter()),
    );
  }
}

class GoogleGPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final double cx = size.width / 2;
    final double cy = size.height / 2;
    final double r = size.width / 2;
    final Rect rect = Rect.fromCircle(center: Offset(cx, cy), radius: r);

    final Paint bluePaint = Paint()..color = const Color(0xFF4285F4)..style = PaintingStyle.fill;
    final Paint greenPaint = Paint()..color = const Color(0xFF34A853)..style = PaintingStyle.fill;
    final Paint yellowPaint = Paint()..color = const Color(0xFFFBBC05)..style = PaintingStyle.fill;
    final Paint redPaint = Paint()..color = const Color(0xFFEA4335)..style = PaintingStyle.fill;

    canvas.drawArc(rect, -0.6, 1.8, true, bluePaint);
    canvas.drawArc(rect, 1.2, 1.3, true, greenPaint);
    canvas.drawArc(rect, 2.5, 1.0, true, yellowPaint);
    canvas.drawArc(rect, 3.5, 1.4, true, redPaint);

    final Paint whitePaint = Paint()..color = Colors.white..style = PaintingStyle.fill;
    canvas.drawCircle(Offset(cx, cy), r * 0.55, whitePaint);

    final ui.Path path = ui.Path();
    path.moveTo(cx, cy - (r * 0.22));
    path.lineTo(cx + (r * 0.95), cy - (r * 0.22));
    path.lineTo(cx + (r * 0.95), cy + (r * 0.22));
    path.lineTo(cx, cy + (r * 0.22));
    path.close();
    canvas.drawPath(path, bluePaint);
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}

