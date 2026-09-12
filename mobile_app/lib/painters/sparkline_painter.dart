import 'dart:math';
import 'dart:ui' as ui;

import 'package:flutter/material.dart';

class SparklinePainter extends CustomPainter {
  final List<double> data;
  final Color color;

  SparklinePainter({required this.data, required this.color});

  @override
  void paint(Canvas canvas, Size size) {
    if (data.length < 2) return;
    final paint = Paint()
      ..color = color
      ..strokeWidth = 2.2
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round;

    final path = ui.Path();
    final double dx = size.width / (data.length - 1);
    final double minVal = data.reduce(min);
    final double maxVal = data.reduce(max);
    final double range = (maxVal - minVal) == 0 ? 1.0 : (maxVal - minVal);

    for (int i = 0; i < data.length; i++) {
      final x = i * dx;
      final y = size.height - ((data[i] - minVal) / range) * (size.height * 0.7) - (size.height * 0.15);
      if (i == 0) {
        path.moveTo(x, y);
      } else {
        path.lineTo(x, y);
      }
    }
    canvas.drawPath(path, paint);
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => true;
}
