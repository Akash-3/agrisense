class Validators {
  const Validators._();

  static String? requiredText(String? value, {String field = 'Field'}) {
    if (value == null || value.trim().isEmpty) {
      return '$field is required.';
    }
    return null;
  }

  static String? emailOrPhone(String? value) {
    final required = requiredText(value, field: 'Email or phone');
    if (required != null) return required;

    final input = value!.trim();

    final email = RegExp(
      r'^[^@\s]+@[^@\s]+\.[^@\s]+$',
      caseSensitive: false,
    );

    final phone = RegExp(r'^\+?[0-9]{10,15}$');

    if (!email.hasMatch(input) && !phone.hasMatch(input)) {
      return 'Enter a valid email address or phone number.';
    }

    return null;
  }

  static String? password(String? value) {
    if (value == null || value.isEmpty) {
      return 'Password is required.';
    }
    if (value.length < 8) {
      return 'Password must contain at least 8 characters.';
    }
    return null;
  }

  static String? confirmPassword(String? value, String password) {
    if (value == null || value.isEmpty) {
      return 'Please confirm your password.';
    }
    if (value != password) {
      return 'Passwords do not match.';
    }
    return null;
  }

  static String? otp(String? value) {
    if (value == null || value.trim().isEmpty) {
      return 'OTP is required.';
    }
    if (!RegExp(r'^\d{6}$').hasMatch(value.trim())) {
      return 'OTP must be exactly 6 digits.';
    }
    return null;
  }

  static String? acreage(double? acres) {
    if (acres == null || !acres.isFinite) {
      return 'Farm acreage is required.';
    }
    if (acres <= 0) {
      return 'Farm acreage must be greater than 0.';
    }
    if (acres > 100000) {
      return 'Farm acreage is unrealistically large.';
    }
    return null;
  }

  static String? age(int? age) {
    if (age == null) return null;
    if (age < 13 || age > 120) {
      return 'Enter a valid age.';
    }
    return null;
  }
}
