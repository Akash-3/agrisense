import 'package:flutter/material.dart';

/// Lightweight responsive layout utility class for AgriSense Mobile App.
/// Uses native Flutter MediaQuery and LayoutBuilder primitives without global scaling.
class ResponsiveLayoutHelper {
  const ResponsiveLayoutHelper._();

  /// Returns true if screen width is under 600dp (standard mobile phone layout).
  static bool isCompact(BuildContext context) {
    return MediaQuery.of(context).size.width < 600;
  }

  /// Returns true if screen width is 600dp or greater (tablet layout).
  static bool isTablet(BuildContext context) {
    return MediaQuery.of(context).size.width >= 600;
  }

  /// Returns true if device is in landscape orientation.
  static bool isLandscape(BuildContext context) {
    return MediaQuery.of(context).orientation == Orientation.landscape;
  }

  /// Resolves responsive grid cross axis count based on screen width.
  static int gridCrossAxisCount(
    BuildContext context, {
    int compact = 2,
    int tablet = 4,
    int landscape = 3,
  }) {
    if (isLandscape(context)) {
      return landscape;
    }
    return isTablet(context) ? tablet : compact;
  }

  /// Wraps child in a centered max-width constraint for clean tablet/landscape presentation.
  static Widget centeredConstrainedBox({
    required Widget child,
    double maxWidth = 600.0,
  }) {
    return Center(
      child: ConstrainedBox(
        constraints: BoxConstraints(maxWidth: maxWidth),
        child: child,
      ),
    );
  }
}
