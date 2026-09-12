class Formatters {
  const Formatters._();

  static String capitalizeWords(String value) {
    return value
        .trim()
        .split(RegExp(r'\s+'))
        .where((word) => word.isNotEmpty)
        .map(
          (word) => word.length == 1
              ? word.toUpperCase()
              : '${word[0].toUpperCase()}${word.substring(1).toLowerCase()}',
        )
        .join(' ');
  }

  static String formatAcres(double acres) {
    if (!acres.isFinite) return '—';
    if (acres == acres.roundToDouble()) {
      return acres.toStringAsFixed(0);
    }
    return acres.toStringAsFixed(2);
  }

  static double celsiusToFahrenheit(double celsius) {
    return (celsius * 9 / 5) + 32;
  }

  static double fahrenheitToCelsius(double fahrenheit) {
    return (fahrenheit - 32) * 5 / 9;
  }

  static String temperature(
    double celsius, {
    required bool useFahrenheit,
    int decimals = 1,
  }) {
    final value = useFahrenheit
        ? celsiusToFahrenheit(celsius)
        : celsius;

    return '${value.toStringAsFixed(decimals)}°${useFahrenheit ? 'F' : 'C'}';
  }

  static String percentage(double value, {int decimals = 1}) {
    if (!value.isFinite) return '—';
    return '${value.toStringAsFixed(decimals)}%';
  }
}
