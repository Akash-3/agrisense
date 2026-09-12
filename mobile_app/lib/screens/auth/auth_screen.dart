import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:http/http.dart' as http;

import '../../config/app_config.dart';
import '../../widgets/agri_logo_badge.dart';
import '../../widgets/google_logo_widget.dart';
import '../../widgets/microsoft_logo_widget.dart';
import 'farm_setup_wizard_screen.dart';

class AuthScreen extends StatefulWidget {
  final Function(Map<String, dynamic>) onLoginSuccess;
  const AuthScreen({super.key, required this.onLoginSuccess});

  @override
  State<AuthScreen> createState() => _AuthScreenState();
}

class _AuthScreenState extends State<AuthScreen> with SingleTickerProviderStateMixin {
  late TabController _tabController;
  final _loginIdController = TextEditingController();
  final _loginPassController = TextEditingController();

  final _regNameController = TextEditingController();
  final _regIdController = TextEditingController();
  final _regFarmNameController = TextEditingController(text: "Green Valley Farm");
  final _regAcresController = TextEditingController(text: "15.0");
  final _regPassController = TextEditingController();

  bool _obscureLoginPass = true;
  bool _obscureRegPass = true;
  bool _obscureRegConfirmPass = true;

  String? _regGender;
  int _regAge = 32;
  int _regAvatarId = 1;
  String _regCropType = "Wheat & Paddy";

  final _regConfirmPassController = TextEditingController();

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
  }

  @override
  void dispose() {
    _tabController.dispose();
    _loginIdController.dispose();
    _loginPassController.dispose();
    _regNameController.dispose();
    _regIdController.dispose();
    _regFarmNameController.dispose();
    _regAcresController.dispose();
    _regPassController.dispose();
    _regConfirmPassController.dispose();
    super.dispose();
  }

  Future<void> _submitLogin() async {
    final id = _loginIdController.text.trim();
    final pass = _loginPassController.text.trim();
    if (id.isEmpty || pass.isEmpty) {
      _showMsg('Please enter your registered email/mobile and password.');
      return;
    }

    setState(() => _isLoading = true);
    await AppConfig.resolveActiveHost();

    try {
      final res = await http.post(
        Uri.parse('${AppConfig.backendHttpUrl}/api/v1/auth/login'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'phone_or_email': id, 'password': pass}),
      ).timeout(const Duration(seconds: 12));

      Map<String, dynamic> data = <String, dynamic>{};
      try {
        final decoded = jsonDecode(res.body);
        if (decoded is Map<String, dynamic>) {
          data = decoded;
        }
      } catch (_) {}

      if (res.statusCode == 200 &&
          data['status'] == 'success' &&
          data['farmer'] is Map<String, dynamic>) {
        if (!mounted) return;
        widget.onLoginSuccess(data['farmer'] as Map<String, dynamic>);
        return;
      }

      _showMsg(
        data['detail']?.toString() ??
            data['message']?.toString() ??
            'Invalid email/mobile or password.',
      );
    } catch (_) {
      _showMsg('Unable to reach the authentication service. Please check your internet connection and try again.');
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  void _submitSSOLogin(String provider) {
    final name = provider == 'google' ? 'Google' : 'Microsoft';
    _showMsg(
      '$name sign-in is not configured for this release. Please use email/mobile and password.',
      isError: false,
    );
  }


  void _showForgotPasswordDialog() {
    final emailController = TextEditingController(text: _loginIdController.text);

    showDialog(
      context: context,
      builder: (ctx) {
        return AlertDialog(
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
          title: Row(
            children: const [
              Icon(Icons.lock_reset_rounded, color: Color(0xFF059669)),
              SizedBox(width: 10),
              Text('Reset Account Password', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
            ],
          ),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text('Enter your registered Email or Mobile Number to receive a 6-digit verification code.', style: TextStyle(fontSize: 12, color: Colors.grey)),
              const SizedBox(height: 14),
              TextField(
                controller: emailController,
                decoration: InputDecoration(
                  labelText: 'Registered Mobile or Email',
                  prefixIcon: const Icon(Icons.email_outlined, color: Color(0xFF059669)),
                  filled: true,
                  fillColor: const Color(0xFFF1F5F9),
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
                ),
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(ctx),
              child: const Text('Cancel', style: TextStyle(color: Colors.grey)),
            ),
            ElevatedButton(
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0xFF059669),
                foregroundColor: Colors.white,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
              ),
              onPressed: () async {
                final id = emailController.text.trim();
                if (id.isEmpty) {
                  _showMsg('Please enter your registered email or mobile.');
                  return;
                }
                Navigator.pop(ctx);
                _sendForgotPasswordOTP(id);
              },
              child: const Text('Send Reset OTP', style: TextStyle(fontWeight: FontWeight.bold)),
            ),
          ],
        );
      },
    ).whenComplete(emailController.dispose);
  }

  Future<void> _sendForgotPasswordOTP(String recipient) async {
    final id = recipient.trim();

    if (id.isEmpty) {
      _showMsg('Please enter your registered email or mobile.');
      return;
    }

    setState(() => _isLoading = true);

    try {
      await AppConfig.resolveActiveHost();

      final res = await http
          .post(
            Uri.parse(
              '${AppConfig.backendHttpUrl}/api/v1/auth/forgot-password/send-otp',
            ),
            headers: const {'Content-Type': 'application/json'},
            body: jsonEncode({'phone_or_email': id}),
          )
          .timeout(const Duration(seconds: 8));

      Map<String, dynamic> data = <String, dynamic>{};
      try {
        final decoded = jsonDecode(res.body);
        if (decoded is Map<String, dynamic>) {
          data = decoded;
        }
      } catch (_) {}

      if (res.statusCode < 200 || res.statusCode >= 300) {
        final detail = data['detail']?.toString();
        if (mounted) {
          _showMsg(
            detail != null && detail.isNotEmpty
                ? detail
                : 'Unable to send password reset OTP. Please try again.',
          );
        }
        return;
      }

      if (!mounted) return;

      // The backend owns OTP generation and verification. The app never
      // invents a fallback OTP. A demo_otp may be returned by the development
      // backend so the demo flow can display the generated code.
      if (mounted) {
        _showMsg('Verification OTP sent. Please check your email or mobile.', isError: false);
        _showResetPasswordDialog(id);
      }
    } catch (_) {
      if (mounted) {
        _showMsg(
          'Unable to contact the password reset service. Please check your internet connection and try again.',
        );
      }
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  void _showResetPasswordDialog(String recipient) {
    final otpController = TextEditingController();
    final newPassController = TextEditingController();

    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (ctx) {
        return AlertDialog(
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
          title: Row(
            children: const [
              Icon(Icons.shield_outlined, color: Color(0xFF059669)),
              SizedBox(width: 10),
              Text('Enter OTP & New Password', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
            ],
          ),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Verification code sent to $recipient.', style: const TextStyle(fontSize: 11, color: Colors.grey)),
                const SizedBox(height: 12),
                TextField(
                  controller: otpController,
                  keyboardType: TextInputType.number,
                  textAlign: TextAlign.center,
                  style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold, letterSpacing: 6, color: Color(0xFF059669)),
                  decoration: InputDecoration(
                    hintText: '• • • • • •',
                    filled: true,
                    fillColor: const Color(0xFFF1F5F9),
                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
                  ),
                ),
                const SizedBox(height: 14),
                TextField(
                  controller: newPassController,
                  obscureText: true,
                  decoration: InputDecoration(
                    labelText: 'New Strong Password',
                    prefixIcon: const Icon(Icons.lock_reset_outlined, color: Color(0xFF059669)),
                    filled: true,
                    fillColor: const Color(0xFFF1F5F9),
                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
                  ),
                ),
                const SizedBox(height: 4),
                const Text('Must be 8+ chars (Uppercase, Lowercase, Number & Special Char)', style: TextStyle(fontSize: 9, color: Color(0xFF059669), fontWeight: FontWeight.bold)),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () {
                ScaffoldMessenger.of(context).hideCurrentMaterialBanner();
                Navigator.pop(ctx);
              },
              child: const Text('Cancel', style: TextStyle(color: Colors.grey)),
            ),
            ElevatedButton(
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0xFF059669),
                foregroundColor: Colors.white,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
              ),
              onPressed: () async {
                final otpInput = otpController.text.trim();
                final newPass = newPassController.text.trim();
                if (otpInput.length != 6 || newPass.isEmpty) {
                  _showMsg('Please enter a 6-digit OTP and your new password.');
                  return;
                }
                if (!_isStrongPassword(newPass)) {
                  _showMsg(
                    'Password must be 8+ characters with Uppercase, Lowercase, Number & Special Character.',
                  );
                  return;
                }
                ScaffoldMessenger.of(context).hideCurrentMaterialBanner();
                Navigator.pop(ctx);
                _executePasswordReset(recipient, newPass, otpInput);
              },
              child: const Text('Reset Password', style: TextStyle(fontWeight: FontWeight.bold)),
            ),
          ],
        );
      },
    ).whenComplete(() {
      otpController.dispose();
      newPassController.dispose();
    });
  }

  Future<void> _executePasswordReset(String recipient, String newPass, String otp) async {
    setState(() => _isLoading = true);

    try {
      await AppConfig.resolveActiveHost();

      final res = await http
          .post(
            Uri.parse(
              '${AppConfig.backendHttpUrl}/api/v1/auth/forgot-password/reset',
            ),
            headers: const {'Content-Type': 'application/json'},
            body: jsonEncode({
              'phone_or_email': recipient.trim(),
              'new_password': newPass,
              'otp_code': otp.trim(),
            }),
          )
          .timeout(const Duration(seconds: 8));

      Map<String, dynamic> data = <String, dynamic>{};
      try {
        final decoded = jsonDecode(res.body);
        if (decoded is Map<String, dynamic>) {
          data = decoded;
        }
      } catch (_) {}

      if (res.statusCode == 200 && data['status'] == 'success') {
        if (!mounted) return;
        _showMsg(
          'Password reset successfully! Please sign in with your new password.',
          isError: false,
        );
        _loginIdController.text = recipient.trim();
        _loginPassController.clear();
        _tabController.animateTo(0);
      } else {
        final detail = data['detail']?.toString() ?? data['message']?.toString();
        if (mounted) {
          _showMsg(
            detail != null && detail.isNotEmpty
                ? detail
                : 'Password reset failed. Please verify the OTP and try again.',
          );
        }
      }
    } catch (_) {
      if (mounted) {
        _showMsg('Connection error. Could not reset password.');
      }
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  bool _isStrongPassword(String password) {
    return password.length >= 8 &&
        password.contains(RegExp(r'[A-Z]')) &&
        password.contains(RegExp(r'[a-z]')) &&
        password.contains(RegExp(r'[0-9]')) &&
        password.contains(RegExp(r'[@#$%^&*!_\-+=\[\]{}|:<>,.?/]'));
  }

  String _capitalize(String s) {
    if (s.isEmpty) return s;
    return s.split(' ').map((word) {
      if (word.isEmpty) return word;
      return word[0].toUpperCase() + word.substring(1).toLowerCase();
    }).join(' ');
  }

  void _showMsg(String msg, {bool isError = true}) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).clearSnackBars();

    final bool isSuccess = msg.startsWith('✅') || msg.toLowerCase().contains('success');
    final Color bgColor = isSuccess
        ? const Color(0xFF065F46)
        : (isError ? const Color(0xFF991B1B) : const Color(0xFF1E293B));

    final IconData icon = isSuccess
        ? Icons.check_circle_rounded
        : (isError ? Icons.error_outline_rounded : Icons.info_outline_rounded);

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        behavior: SnackBarBehavior.floating,
        elevation: 8,
        margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        backgroundColor: bgColor,
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
        content: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(6),
              decoration: BoxDecoration(
                color: Colors.white.withValues(alpha: 0.2),
                shape: BoxShape.circle,
              ),
              child: Icon(icon, color: Colors.white, size: 20),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Text(
                msg.replaceAll('✅ ', ''),
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 13.5,
                  fontWeight: FontWeight.w600,
                  letterSpacing: 0.2,
                ),
              ),
            ),
          ],
        ),
        duration: const Duration(seconds: 4),
      ),
    );
  }

  Future<bool?> _showExitConfirmationDialog(BuildContext context) {
    return showDialog<bool>(
      context: context,
      builder: (ctx) {
        return AlertDialog(
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
          title: Row(
            children: const [
              Icon(Icons.exit_to_app_rounded, color: Colors.redAccent),
              SizedBox(width: 10),
              Text('Exit AgriSense?', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
            ],
          ),
          content: const Text(
            'Are you sure you want to close the AgriSense Agriculture Platform?',
            style: TextStyle(fontSize: 12, color: Color(0xFF475569)),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(ctx).pop(false),
              child: const Text('Stay in App', style: TextStyle(color: Color(0xFF059669), fontWeight: FontWeight.bold)),
            ),
            ElevatedButton(
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.redAccent,
                foregroundColor: Colors.white,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
              ),
              onPressed: () => Navigator.of(ctx).pop(true),
              child: const Text('Exit App', style: TextStyle(fontWeight: FontWeight.bold)),
            ),
          ],
        );
      },
    );
  }

  void _showServerSettingsDialog() {
    final controller = TextEditingController(text: AppConfig.userCustomHost ?? AppConfig.activeHost);
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        title: Row(
          children: const [
            Icon(Icons.dns_rounded, color: Color(0xFF10B981)),
            SizedBox(width: 10),
            Text('Server Settings', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
          ],
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Backend Host / Server URL:',
              style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: Color(0xFF475569)),
            ),
            const SizedBox(height: 8),
            TextField(
              controller: controller,
              decoration: InputDecoration(
                hintText: 'e.g. https://admin.tail4fe027.ts.net',
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                isDense: true,
              ),
            ),
            const SizedBox(height: 12),
            const Text(
              'Production Host:\n'
              '• https://admin.tail4fe027.ts.net\n'
              'Public HTTPS via Tailscale Funnel',
              style: TextStyle(fontSize: 11, color: Color(0xFF64748B)),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () {
              AppConfig.userCustomHost = null;
              AppConfig.resolveActiveHost().then((_) {
                if (mounted) setState(() {});
              });
              Navigator.pop(ctx);
              _showMsg('Reset to automatic server auto-discovery.', isError: false);
            },
            child: const Text('Auto-Detect', style: TextStyle(color: Color(0xFF64748B))),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(
              backgroundColor: const Color(0xFF10B981),
              foregroundColor: Colors.white,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
            ),
            onPressed: () {
              final val = controller.text.trim();
              if (val.isNotEmpty) {
                AppConfig.userCustomHost = val;
                AppConfig.activeHost = val;
                if (mounted) setState(() {});
                _showMsg('Updated Server Host to: ${AppConfig.backendHttpUrl}', isError: false);
              }
              Navigator.pop(ctx);
            },
            child: const Text('Save Host'),
          ),
        ],
      ),
    ).whenComplete(controller.dispose);
  }

  Future<void> _startRegistrationFlow() async {
    final name = _regNameController.text.trim();
    final id = _regIdController.text.trim();
    final pass = _regPassController.text.trim();
    final conf = _regConfirmPassController.text.trim();

    if (name.isEmpty || id.isEmpty || pass.isEmpty) {
      _showMsg('Please complete all account fields.');
      return;
    }
    if (_regGender == null) {
      _showMsg('Please select your gender.');
      return;
    }
    if (pass != conf) {
      _showMsg('Passwords do not match!');
      return;
    }
    if (!_isStrongPassword(pass)) {
      _showMsg(r'Password must be 8+ characters with Uppercase, Lowercase, Number & Special Character (@#$...).');
      return;
    }

    setState(() => _isLoading = true);
    try {
      await AppConfig.resolveActiveHost();
      final res = await http.post(
        Uri.parse('${AppConfig.backendHttpUrl}/api/v1/auth/send-otp'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'phone_or_email': id, 'full_name': name}),
      ).timeout(const Duration(seconds: 8));

      Map<String, dynamic> data = {};
      try {
        final decoded = jsonDecode(res.body);
        if (decoded is Map<String, dynamic>) data = decoded;
      } catch (_) {}

      if (res.statusCode < 200 || res.statusCode >= 300) {
        final detail = data['detail']?.toString();
        if (mounted) {
          _showMsg(detail != null && detail.isNotEmpty ? detail : 'Unable to send verification OTP. Please try again.');
        }
        return;
      }

      final demoOtp = data['demo_otp']?.toString();
      if (demoOtp == null || demoOtp.length != 6) {
        if (mounted) _showMsg('OTP service did not return a valid verification response. Please try again.');
        return;
      }

      if (!mounted) return;
      final otpController = TextEditingController();
      final verifiedOtp = await showDialog<String>(
        context: context,
        barrierDismissible: false,
        builder: (dialogContext) => AlertDialog(
          title: const Text('Verify your account'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('Enter the 6-digit OTP sent to $id.'),
              const SizedBox(height: 12),
              TextField(
                controller: otpController,
                autofocus: true,
                keyboardType: TextInputType.number,
                maxLength: 6,
                inputFormatters: [FilteringTextInputFormatter.digitsOnly],
                decoration: const InputDecoration(labelText: 'OTP', border: OutlineInputBorder()),
              ),
              if (demoOtp.isNotEmpty) ...[
                const SizedBox(height: 4),
                Text('Development OTP: $demoOtp', style: const TextStyle(fontSize: 12, color: Colors.orange)),
              ],
            ],
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(dialogContext), child: const Text('Cancel')),
            FilledButton(
              onPressed: () {
                final otp = otpController.text.trim();
                if (otp.length != 6) {
                  _showMsg('Please enter the 6-digit OTP.');
                  return;
                }
                if (otp != demoOtp) {
                  _showMsg('Invalid OTP. Please check the code and try again.');
                  return;
                }
                Navigator.pop(dialogContext, otp);
              },
              child: const Text('Verify'),
            ),
          ],
        ),
      );
      otpController.dispose();

      if (!mounted || verifiedOtp == null) return;

      Navigator.push(
        context,
        MaterialPageRoute(
          builder: (ctx) => FarmSetupWizardScreen(
            fullName: name,
            emailOrPhone: id,
            gender: _regGender!,
            age: _regAge,
            avatarId: _regAvatarId,
            password: pass,
            otpCode: verifiedOtp,
            onSetupComplete: (farmerData) {
              Navigator.pop(ctx);
              widget.onLoginSuccess(farmerData);
            },
          ),
        ),
      );
    } catch (_) {
      if (mounted) _showMsg('Unable to contact the verification service. Please check your internet connection and try again.');
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return PopScope(
      canPop: false,
      onPopInvokedWithResult: (didPop, result) async {
        if (didPop) return;

        final shouldExit = await _showExitConfirmationDialog(context);
        if (shouldExit == true) {
          SystemNavigator.pop();
        }
      },
      child: Scaffold(
        backgroundColor: const Color(0xFFF8FAFC),
        body: SafeArea(
          child: Center(
            child: SingleChildScrollView(
              physics: const BouncingScrollPhysics(),
              padding: const EdgeInsets.symmetric(horizontal: 20.0, vertical: 16.0),
              child: Column(
                children: [
                  // Top Tagline Bar & Floating Server Config Badge
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                        decoration: BoxDecoration(
                          color: const Color(0xFFECFDF5),
                          borderRadius: BorderRadius.circular(20),
                          border: Border.all(color: const Color(0xFFA7F3D0)),
                        ),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: const [
                            Icon(Icons.energy_savings_leaf_rounded, size: 13, color: Color(0xFF059669)),
                            SizedBox(width: 6),
                            Text(
                              'SMART FARMS  •  HEALTHY CROPS',
                              style: TextStyle(fontSize: 10, fontWeight: FontWeight.w800, color: Color(0xFF047857), letterSpacing: 0.4),
                            ),
                          ],
                        ),
                      ),
                      GestureDetector(
                        onTap: _showServerSettingsDialog,
                        child: Container(
                          padding: const EdgeInsets.all(8),
                          decoration: BoxDecoration(
                            color: const Color(0xFF0F172A),
                            shape: BoxShape.circle,
                            boxShadow: [
                              BoxShadow(
                                color: const Color(0xFF10B981).withValues(alpha: 0.3),
                                blurRadius: 10,
                                spreadRadius: 1,
                              ),
                            ],
                          ),
                          child: const Icon(Icons.dns_rounded, color: Color(0xFF34D399), size: 18),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 16),

                  // Brand Header
                  const AgriSenseLogoBadge(size: 72, borderRadius: 20),
                  const SizedBox(height: 12),
                  const Text('AgriSense', style: TextStyle(fontSize: 28, fontWeight: FontWeight.w900, color: Color(0xFF0F172A))),
                  const Text('Autonomous Agriculture Platform', style: TextStyle(fontSize: 12, color: Color(0xFF64748B), fontWeight: FontWeight.w500)),
                  const SizedBox(height: 20),

                  // Custom Tab Switcher
                  Container(
                    padding: const EdgeInsets.all(4),
                    decoration: BoxDecoration(
                      color: const Color(0xFFE2E8F0),
                      borderRadius: BorderRadius.circular(16),
                    ),
                    child: TabBar(
                      controller: _tabController,
                      indicator: BoxDecoration(
                        gradient: const LinearGradient(
                          colors: [Color(0xFF059669), Color(0xFF10B981)],
                        ),
                        borderRadius: BorderRadius.circular(12),
                        boxShadow: [
                          BoxShadow(
                            color: const Color(0xFF059669).withValues(alpha: 0.3),
                            blurRadius: 6,
                            offset: const Offset(0, 2),
                          ),
                        ],
                      ),
                      indicatorSize: TabBarIndicatorSize.tab,
                      labelColor: Colors.white,
                      unselectedLabelColor: const Color(0xFF64748B),
                      labelStyle: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13),
                      tabs: const [
                        Tab(text: 'Account Login'),
                        Tab(text: 'Register'),
                      ],
                    ),
                  ),
                  const SizedBox(height: 18),

                  // Form Container Card
                  Container(
                    padding: const EdgeInsets.all(22),
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(28),
                      boxShadow: [
                        BoxShadow(
                          color: Colors.black.withValues(alpha: 0.06),
                          blurRadius: 20,
                          offset: const Offset(0, 8),
                        ),
                      ],
                    ),
                    child: SizedBox(
                      height: 440,
                      child: TabBarView(
                        controller: _tabController,
                        children: [
                          // ==================== ACCOUNT LOGIN TAB ====================
                          SingleChildScrollView(
                            physics: const BouncingScrollPhysics(),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                const SizedBox(height: 6),
                                _buildField(_loginIdController, 'Mobile Number or Email', Icons.phone_android),
                                const SizedBox(height: 14),
                                _buildField(
                                  _loginPassController,
                                  'Password',
                                  Icons.lock_outline,
                                  isPass: true,
                                  obscureTextOverride: _obscureLoginPass,
                                  onToggleObscure: () => setState(() => _obscureLoginPass = !_obscureLoginPass),
                                ),
                                const SizedBox(height: 12),

                                // Persistent Remember Me requires secure local session storage.
                                // It is intentionally not presented as active until that storage is implemented.
                                Row(
                                  mainAxisAlignment: MainAxisAlignment.end,
                                  children: [
                                    const Icon(Icons.info_outline_rounded, size: 15, color: Color(0xFF94A3B8)),
                                    const SizedBox(width: 6),
                                    const Text(
                                      'Remember Me is unavailable in this release',
                                      style: TextStyle(fontSize: 11, color: Color(0xFF64748B)),
                                    ),
                                    TextButton(
                                      onPressed: _showForgotPasswordDialog,
                                      style: TextButton.styleFrom(
                                        padding: const EdgeInsets.only(left: 10),
                                        minimumSize: Size.zero,
                                        tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                                      ),
                                      child: const Text(
                                        'Forgot Password?',
                                        style: TextStyle(color: Color(0xFF059669), fontWeight: FontWeight.bold, fontSize: 12),
                                      ),
                                    ),
                                  ],
                                ),
                                const SizedBox(height: 20),

                                // Primary Gradient Sign In Button with Arrow Badge
                                _buildSubmitBtn('Sign In to Account', _submitLogin, hasArrow: true),
                                const SizedBox(height: 20),

                                // OR Divider
                                Row(
                                  children: const [
                                    Expanded(child: Divider(color: Color(0xFFE2E8F0), thickness: 1)),
                                    Padding(
                                      padding: EdgeInsets.symmetric(horizontal: 12),
                                      child: Text('OR', style: TextStyle(color: Color(0xFF94A3B8), fontSize: 11, fontWeight: FontWeight.bold)),
                                    ),
                                    Expanded(child: Divider(color: Color(0xFFE2E8F0), thickness: 1)),
                                  ],
                                ),
                                const SizedBox(height: 18),

                                // Social SSO Row (Google & Microsoft)
                                Row(
                                  children: [
                                    Expanded(
                                      child: OutlinedButton(
                                        style: OutlinedButton.styleFrom(
                                          padding: const EdgeInsets.symmetric(vertical: 12),
                                          side: const BorderSide(color: Color(0xFFE2E8F0)),
                                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                                          backgroundColor: Colors.white,
                                        ),
                                        onPressed: () => _submitSSOLogin('google'),
                                        child: Row(
                                          mainAxisAlignment: MainAxisAlignment.center,
                                          children: const [
                                            GoogleLogoWidget(),
                                            SizedBox(width: 8),
                                            Text('Google', style: TextStyle(color: Color(0xFF334155), fontWeight: FontWeight.w600, fontSize: 13)),
                                          ],
                                        ),
                                      ),
                                    ),
                                    const SizedBox(width: 12),
                                    Expanded(
                                      child: OutlinedButton(
                                        style: OutlinedButton.styleFrom(
                                          padding: const EdgeInsets.symmetric(vertical: 12),
                                          side: const BorderSide(color: Color(0xFFE2E8F0)),
                                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                                          backgroundColor: Colors.white,
                                        ),
                                        onPressed: () => _submitSSOLogin('microsoft'),
                                        child: Row(
                                          mainAxisAlignment: MainAxisAlignment.center,
                                          children: const [
                                            MicrosoftLogoWidget(),
                                            SizedBox(width: 8),
                                            Text('Microsoft', style: TextStyle(color: Color(0xFF334155), fontWeight: FontWeight.w600, fontSize: 13)),
                                          ],
                                        ),
                                      ),
                                    ),
                                  ],
                                ),
                              ],
                            ),
                          ),

                          // ==================== CREATE ACCOUNT TAB ====================
                          SingleChildScrollView(
                            physics: const BouncingScrollPhysics(),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                const SizedBox(height: 6),
                                _buildField(_regNameController, 'Full Name', Icons.person_outline, isCap: true),
                                const SizedBox(height: 10),
                                _buildField(_regIdController, 'Mobile Number or Email', Icons.phone_android),
                                const SizedBox(height: 10),

                                // Gender & Age Row
                                Row(
                                  children: [
                                    Expanded(
                                      child: Container(
                                        padding: const EdgeInsets.symmetric(horizontal: 10),
                                        decoration: BoxDecoration(
                                          color: const Color(0xFFF8FAFC),
                                          borderRadius: BorderRadius.circular(12),
                                          border: Border.all(color: const Color(0xFFE2E8F0)),
                                        ),
                                        child: DropdownButtonHideUnderline(
                                          child: DropdownButton<String>(
                                            value: _regGender,
                                            hint: const Text('Select Gender', style: TextStyle(color: Color(0xFF94A3B8), fontSize: 12)),
                                            isExpanded: true,
                                            style: const TextStyle(color: Color(0xFF0F172A), fontSize: 12),
                                            onChanged: (val) => setState(() => _regGender = val),
                                            items: ["Male", "Female", "Other"]
                                                .map((g) => DropdownMenuItem(value: g, child: Text(g)))
                                                .toList(),
                                          ),
                                        ),
                                      ),
                                    ),
                                    const SizedBox(width: 8),
                                    Expanded(
                                      child: TextField(
                                        keyboardType: TextInputType.number,
                                        decoration: InputDecoration(
                                          labelText: 'Age (Years)',
                                          labelStyle: const TextStyle(fontSize: 11, color: Color(0xFF64748B)),
                                          prefixIcon: const Icon(Icons.cake_outlined, color: Color(0xFF059669), size: 18),
                                          filled: true,
                                          fillColor: const Color(0xFFF8FAFC),
                                          contentPadding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                                          border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: const BorderSide(color: Color(0xFFE2E8F0))),
                                        ),
                                        onChanged: (v) => _regAge = int.tryParse(v) ?? 32,
                                      ),
                                    ),
                                  ],
                                ),
                                const SizedBox(height: 10),

                                // Avatar Choice
                                const Text('Choose Avatar:', style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: Color(0xFF0F172A))),
                                const SizedBox(height: 6),
                                Row(
                                  mainAxisAlignment: MainAxisAlignment.spaceAround,
                                  children: [1, 2, 3, 4, 5, 6].map((id) {
                                    final isSel = _regAvatarId == id;
                                    return InkWell(
                                      onTap: () => setState(() => _regAvatarId = id),
                                      child: Container(
                                        padding: const EdgeInsets.all(3),
                                        decoration: BoxDecoration(
                                          shape: BoxShape.circle,
                                          border: Border.all(color: isSel ? const Color(0xFF059669) : Colors.transparent, width: 2),
                                        ),
                                        child: CircleAvatar(
                                          radius: 16,
                                          backgroundColor: isSel ? const Color(0xFF059669) : const Color(0xFFE2E8F0),
                                          child: Icon(
                                            id == 1 ? Icons.face : id == 2 ? Icons.person : id == 3 ? Icons.agriculture : id == 4 ? Icons.nature_people : id == 5 ? Icons.account_circle : Icons.local_florist_rounded,
                                            color: isSel ? Colors.white : const Color(0xFF64748B),
                                            size: 18,
                                          ),
                                        ),
                                      ),
                                    );
                                  }).toList(),
                                ),
                                const SizedBox(height: 10),

                                _buildField(
                                  _regPassController,
                                  'Password',
                                  Icons.lock_outline,
                                  isPass: true,
                                  obscureTextOverride: _obscureRegPass,
                                  onToggleObscure: () => setState(() => _obscureRegPass = !_obscureRegPass),
                                  onChanged: (_) => setState(() {}),
                                ),
                                _buildPasswordRequirementsWidget(_regPassController.text),
                                const SizedBox(height: 6),
                                _buildField(
                                  _regConfirmPassController,
                                  'Confirm Password',
                                  Icons.lock_reset_outlined,
                                  isPass: true,
                                  obscureTextOverride: _obscureRegConfirmPass,
                                  onToggleObscure: () => setState(() => _obscureRegConfirmPass = !_obscureRegConfirmPass),
                                ),
                                const SizedBox(height: 14),

                                _buildSubmitBtn('Create Account & Continue →', _startRegistrationFlow),
                              ],
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),

                  // Bottom Footer Badge & Feature Highlights
                  const SizedBox(height: 20),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
                    decoration: BoxDecoration(
                      color: const Color(0xFF0F172A),
                      borderRadius: BorderRadius.circular(20),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: const [
                        Icon(Icons.eco_rounded, size: 12, color: Color(0xFF10B981)),
                        SizedBox(width: 6),
                        Text(
                          'Technology for a Greener Tomorrow',
                          style: TextStyle(fontSize: 10, fontWeight: FontWeight.w600, color: Colors.white70),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 14),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                    children: [
                      _buildFooterFeature(Icons.radar_rounded, 'Monitor Fields'),
                      _buildFooterFeature(Icons.health_and_safety_rounded, 'Analyze Health'),
                      _buildFooterFeature(Icons.smart_toy_rounded, 'Automate Ops'),
                    ],
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildFooterFeature(IconData icon, String label) {
    return Row(
      children: [
        Icon(icon, size: 13, color: const Color(0xFF059669)),
        const SizedBox(width: 4),
        Text(
          label,
          style: const TextStyle(fontSize: 10, fontWeight: FontWeight.w600, color: Color(0xFF64748B)),
        ),
      ],
    );
  }

  Widget _buildPasswordRequirementsWidget(String pass) {
    final hasMinLength = pass.length >= 8;
    final hasUpper = pass.contains(RegExp(r'[A-Z]'));
    final hasLower = pass.contains(RegExp(r'[a-z]'));
    final hasNumber = pass.contains(RegExp(r'[0-9]'));
    final hasSpecial = pass.contains(RegExp(r'[@#$%^&*!_\-+=\[\]{}|:<>,.?/]'));

    Widget buildItem(String text, bool met) {
      return Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            met ? Icons.check_circle_rounded : Icons.radio_button_unchecked_rounded,
            size: 11,
            color: met ? const Color(0xFF059669) : const Color(0xFF94A3B8),
          ),
          const SizedBox(width: 3),
          Text(
            text,
            style: TextStyle(
              fontSize: 10,
              color: met ? const Color(0xFF065F46) : const Color(0xFF64748B),
              fontWeight: met ? FontWeight.bold : FontWeight.normal,
            ),
          ),
        ],
      );
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      margin: const EdgeInsets.only(top: 4, bottom: 6),
      decoration: BoxDecoration(
        color: const Color(0xFFF1F5F9),
        borderRadius: BorderRadius.circular(10),
      ),
      child: Wrap(
        spacing: 8,
        runSpacing: 4,
        children: [
          buildItem('8+ Chars', hasMinLength),
          buildItem('ABC (Upper)', hasUpper),
          buildItem('abc (Lower)', hasLower),
          buildItem('123 (Number)', hasNumber),
          buildItem(r'@#$ (Symbol)', hasSpecial),
        ],
      ),
    );
  }

  Widget _buildField(TextEditingController ctrl, String label, IconData icon, {bool isPass = false, bool isCap = false, bool? obscureTextOverride, VoidCallback? onToggleObscure, ValueChanged<String>? onChanged}) {
    final isObscured = isPass ? (obscureTextOverride ?? true) : false;
    return TextField(
      controller: ctrl,
      onChanged: onChanged,
      obscureText: isObscured,
      textCapitalization: isCap ? TextCapitalization.words : TextCapitalization.none,
      style: const TextStyle(color: Color(0xFF0F172A), fontSize: 13),
      decoration: InputDecoration(
        labelText: label,
        labelStyle: const TextStyle(fontSize: 12, color: Color(0xFF64748B)),
        prefixIcon: Icon(icon, color: const Color(0xFF059669), size: 20),
        suffixIcon: isPass
            ? IconButton(
                icon: Icon(
                  isObscured ? Icons.visibility_off_rounded : Icons.visibility_rounded,
                  color: const Color(0xFF059669),
                  size: 20,
                ),
                onPressed: onToggleObscure,
              )
            : null,
        filled: true,
        fillColor: const Color(0xFFF8FAFC),
        contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: const BorderSide(color: Color(0xFFE2E8F0))),
        enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: const BorderSide(color: Color(0xFFE2E8F0))),
      ),
    );
  }

  Widget _buildSubmitBtn(String label, VoidCallback onPressed, {bool hasArrow = false}) {
    return Container(
      width: double.infinity,
      height: 52,
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [Color(0xFF059669), Color(0xFF10B981)],
          begin: Alignment.centerLeft,
          end: Alignment.centerRight,
        ),
        borderRadius: BorderRadius.circular(16),
        boxShadow: [
          BoxShadow(
            color: const Color(0xFF059669).withValues(alpha: 0.35),
            blurRadius: 12,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: ElevatedButton(
        style: ElevatedButton.styleFrom(
          backgroundColor: Colors.transparent,
          shadowColor: Colors.transparent,
          foregroundColor: Colors.white,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        ),
        onPressed: _isLoading ? null : onPressed,
        child: _isLoading
            ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
            : Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Text(label, style: const TextStyle(fontSize: 15, fontWeight: FontWeight.bold, letterSpacing: 0.3)),
                  if (hasArrow) ...[
                    const SizedBox(width: 10),
                    Container(
                      padding: const EdgeInsets.all(4),
                      decoration: const BoxDecoration(
                        color: Colors.white24,
                        shape: BoxShape.circle,
                      ),
                      child: const Icon(Icons.arrow_forward_rounded, size: 16, color: Colors.white),
                    ),
                  ],
                ],
              ),
      ),
    );
  }
}
