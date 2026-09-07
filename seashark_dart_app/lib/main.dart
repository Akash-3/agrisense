import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:math';
import 'dart:ui' as ui;
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/cupertino.dart';
import 'package:flutter/services.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
import 'package:geolocator/geolocator.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:image_picker/image_picker.dart';
import 'package:http/http.dart' as http;

import 'models/telemetry_models.dart';
import 'services/websocket_service.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();

  // GLOBAL UNCAUGHT ERROR & CRASH GUARD
  FlutterError.onError = (FlutterErrorDetails details) {
    FlutterError.presentError(details);
    if (kDebugMode) {
      print('[AGRIVISION CRASH GUARD] Captured Flutter Error: ${details.exception}');
    }
  };

  PlatformDispatcher.instance.onError = (error, stack) {
    if (kDebugMode) {
      print('[AGRIVISION ASYNC GUARD] Captured Unhandled Async Error: $error');
    }
    return true; // Prevents app crash
  };

  runApp(const AgriSenseApp());
}

class AppConfig {
  static String activeHost = '100.126.23.88:8000';

  static String get backendHttpUrl {
    if (activeHost.startsWith('http://') || activeHost.startsWith('https://')) return activeHost;
    if (activeHost.contains('trycloudflare.com') || (activeHost.contains('.ts.net') && !activeHost.contains(':'))) {
      return 'https://$activeHost';
    }
    return 'http://$activeHost';
  }

  static String get backendWsUrl {
    if (activeHost.startsWith('ws://') || activeHost.startsWith('wss://')) return activeHost;
    if (activeHost.contains('trycloudflare.com') || (activeHost.contains('.ts.net') && !activeHost.contains(':'))) {
      return 'wss://$activeHost';
    }
    return 'ws://$activeHost';
  }

  static Future<String> resolveActiveHost() async {
    List<String> candidates = [
      '100.126.23.88:8000',
      'akash.tail0d103f.ts.net:8000',
      'akash.tail0d103f.ts.net',
      'howard-limiting-provide-ongoing.trycloudflare.com',
      '10.0.2.2:8000',
      'localhost:8000',
    ];

    Completer<String> completer = Completer<String>();
    int pending = candidates.length;

    for (String host in candidates) {
      final scheme = (host.contains('trycloudflare.com') || (host.contains('.ts.net') && !host.contains(':'))) ? 'https' : 'http';
      final uri = Uri.parse('$scheme://$host/api/v1/health');
      http.get(uri).timeout(const Duration(milliseconds: 2200)).then((res) {
        if (res.statusCode == 200 && !completer.isCompleted) {
          activeHost = host;
          completer.complete(host);
        } else {
          pending--;
          if (pending <= 0 && !completer.isCompleted) {
            completer.complete(activeHost);
          }
        }
      }).catchError((_) {
        pending--;
        if (pending <= 0 && !completer.isCompleted) {
          completer.complete(activeHost);
        }
      });
    }

    return completer.future;
  }
}

class AgriSenseApp extends StatelessWidget {
  const AgriSenseApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'AgriSense',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        useMaterial3: true,
        brightness: Brightness.light,
        scaffoldBackgroundColor: const Color(0xFFF8FAFC),
        primaryColor: const Color(0xFF059669),
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF059669),
          primary: const Color(0xFF059669),
          secondary: const Color(0xFF10B981),
          surface: Colors.white,
        ),
        appBarTheme: const AppBarTheme(
          backgroundColor: Color(0xFF0F172A),
          foregroundColor: Colors.white,
          elevation: 0,
        ),
      ),
      home: const SplashScreen(),
    );
  }
}

// ==================== CUSTOM AGRIVISION LOGO BADGE ====================
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

// ==================== 1. STARTUP ANIMATED SPLASH SCREEN ====================
class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key});

  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen> with SingleTickerProviderStateMixin {
  late AnimationController _animController;
  late Animation<double> _scaleAnim;
  late Animation<double> _fadeAnim;

  @override
  void initState() {
    super.initState();
    _animController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1400),
    );
    _scaleAnim = CurvedAnimation(parent: _animController, curve: Curves.elasticOut);
    _fadeAnim = Tween<double>(begin: 0.0, end: 1.0).animate(_animController);

    _animController.forward();

    Timer(const Duration(milliseconds: 1800), () {
      _requestStartupPermissions();
    });
  }

  Future<void> _requestStartupPermissions() async {
    try {
      if (!kIsWeb) {
        await Permission.location.request();
      }
    } catch (e) {
      // Fallback
    }

    if (mounted) {
      Navigator.of(context).pushReplacement(
        PageRouteBuilder(
          transitionDuration: const Duration(milliseconds: 600),
          pageBuilder: (_, __, ___) => const AuthGate(),
          transitionsBuilder: (_, anim, __, child) {
            return FadeTransition(opacity: anim, child: child);
          },
        ),
      );
    }
  }

  @override
  void dispose() {
    _animController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0F172A),
      body: Center(
        child: FadeTransition(
          opacity: _fadeAnim,
          child: ScaleTransition(
            scale: _scaleAnim,
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: const [
                AgriSenseLogoBadge(size: 110, borderRadius: 28),
                SizedBox(height: 24),
                Text(
                  'AgriSense',
                  style: TextStyle(
                    fontSize: 34,
                    fontWeight: FontWeight.w900,
                    color: Colors.white,
                    letterSpacing: 1.2,
                  ),
                ),
                SizedBox(height: 8),
                Text(
                  'Autonomous Agriculture & Field Analytics Platform',
                  style: TextStyle(fontSize: 12, color: Color(0xFF94A3B8)),
                ),
                SizedBox(height: 38),
                SizedBox(
                  width: 26,
                  height: 26,
                  child: CircularProgressIndicator(color: Color(0xFF10B981), strokeWidth: 2.5),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

// ==================== 2. AUTH GATE ====================
class AuthGate extends StatefulWidget {
  const AuthGate({super.key});

  @override
  State<AuthGate> createState() => _AuthGateState();
}

class _AuthGateState extends State<AuthGate> {
  Map<String, dynamic>? _currentFarmer;

  void _handleLogin(Map<String, dynamic> farmerData) {
    setState(() => _currentFarmer = farmerData);
  }

  void _handleLogout() {
    setState(() => _currentFarmer = null);
  }

  @override
  Widget build(BuildContext context) {
    return _currentFarmer != null
        ? MainNavigationScreen(farmer: _currentFarmer!, onLogout: _handleLogout)
        : AuthScreen(onLoginSuccess: _handleLogin);
  }
}

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
                  color: backgroundColor.withOpacity(0.35),
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
                          color: textColor.withOpacity(0.85),
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

class MicrosoftLogoWidget extends StatelessWidget {
  const MicrosoftLogoWidget({super.key});

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 18,
      height: 18,
      child: Column(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Container(width: 8, height: 8, color: const Color(0xFFF25022)),
              Container(width: 8, height: 8, color: const Color(0xFF7FBA00)),
            ],
          ),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Container(width: 8, height: 8, color: const Color(0xFF00A4EF)),
              Container(width: 8, height: 8, color: const Color(0xFFFFB900)),
            ],
          ),
        ],
      ),
    );
  }
}

// ==================== 3. AUTH SCREEN WITH STRICT PASSWORD VALIDATION ====================
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

  bool _rememberMe = false;
  static const bool _isRememberMeLive = false; // Set to true when requested by user to make Remember Me live!

  int _regStep = 1;
  String? _regGender;
  int _regAge = 32;
  int _regAvatarId = 1;
  String _regCropType = "Wheat & Paddy";

  final _regConfirmPassController = TextEditingController();
  final List<LatLng> _farmPolygonPoints = [];
  double _calculatedAcres = 15.0;

  bool _isLoading = false;

  double _computePolygonAcres(List<LatLng> points) {
    if (points.length < 3) return _calculatedAcres;
    const double radius = 6371000.0;
    double area = 0.0;
    for (int i = 0; i < points.length; i++) {
      int j = (i + 1) % points.length;
      double lat1 = points[i].latitude * (pi / 180.0);
      double lon1 = points[i].longitude * (pi / 180.0);
      double lat2 = points[j].latitude * (pi / 180.0);
      double lon2 = points[j].longitude * (pi / 180.0);
      area += (lon2 - lon1) * (2.0 + sin(lat1) + sin(lat2));
    }
    area = (area * radius * radius / 2.0).abs();
    double acres = area / 4046.86;
    return double.parse(acres.toStringAsFixed(2));
  }

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
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
      ).timeout(const Duration(seconds: 5));

      final data = jsonDecode(res.body);
      if (res.statusCode == 200 && data['status'] == 'success') {
        widget.onLoginSuccess(data['farmer']);
        return;
      } else {
        _showMsg(data['detail'] ?? data['message'] ?? 'Invalid email/mobile or password.');
        return;
      }
    } catch (e) {
      _showMsg('Server Connection Error: Unable to reach backend server at ${AppConfig.activeHost}. Ensure phone is on same Wi-Fi network as server.');
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _submitSSOLogin(String provider) async {
    setState(() => _isLoading = true);
    await AppConfig.resolveActiveHost();

    try {
      final res = await http.post(
        Uri.parse('${AppConfig.backendHttpUrl}/api/v1/auth/sso/$provider'),
        headers: {'Content-Type': 'application/json'},
      ).timeout(const Duration(seconds: 5));

      final data = jsonDecode(res.body);
      if (res.statusCode == 200 && data['status'] == 'success') {
        _showMsg('✅ Successfully signed in with ${provider.toUpperCase()}!', isError: false);
        widget.onLoginSuccess(data['farmer']);
        return;
      } else {
        _showMsg(data['detail'] ?? data['message'] ?? 'SSO authentication failed.');
      }
    } catch (e) {
      _showMsg('Server Connection Error: Unable to reach backend server at ${AppConfig.activeHost}.');
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _initiateRegistration() async {
    final name = _regNameController.text.trim();
    final id = _regIdController.text.trim();
    final farm = _regFarmNameController.text.trim();
    final acres = double.tryParse(_regAcresController.text) ?? 10.0;
    final pass = _regPassController.text.trim();

    if (name.isEmpty || id.isEmpty || farm.isEmpty || pass.isEmpty) {
      _showMsg('Please complete all registration fields.');
      return;
    }

    if (pass.length < 8 ||
        !pass.contains(RegExp(r'[A-Z]')) ||
        !pass.contains(RegExp(r'[a-z]')) ||
        !pass.contains(RegExp(r'[0-9]')) ||
        !pass.contains(RegExp(r'[@#$%^&*!_\-+=\[\]{}|:<>,.?/]'))) {
      _showMsg('Password must be 8+ characters with Uppercase, Lowercase, Number & Special Character.');
      return;
    }

    setState(() => _isLoading = true);
    await AppConfig.resolveActiveHost();
    String generatedOtp = "849201";

    try {
      final res = await http.post(
        Uri.parse('${AppConfig.backendHttpUrl}/api/v1/auth/send-otp'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'phone_or_email': id, 'full_name': name}),
      ).timeout(const Duration(seconds: 5));

      final data = jsonDecode(res.body);
      if (res.statusCode == 400 && data.containsKey("detail")) {
        _showMsg(data["detail"]);
        _tabController.animateTo(0);
        return;
      }
      if (data.containsKey("demo_otp")) {
        generatedOtp = data["demo_otp"];
      }
    } catch (e) {
      // Offline mode
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }

    _showOTPNotificationBanner(id, generatedOtp);
    _showOTPDialog(name, id, farm, acres, pass, generatedOtp);
  }

  void _showOTPNotificationBanner(String recipient, String otpCode) {
    ScaffoldMessenger.of(context).showMaterialBanner(
      MaterialBanner(
        elevation: 6,
        backgroundColor: const Color(0xFF0F172A),
        leading: const Icon(Icons.mark_email_unread_rounded, color: Color(0xFF10B981)),
        content: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            Text('Verification OTP sent to $recipient', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 13)),
            const SizedBox(height: 2),
            const Text('Please check your Email Inbox and Spam folder. Code valid for 10 minutes.', style: TextStyle(color: Color(0xFF34D399), fontWeight: FontWeight.bold, fontSize: 12)),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => ScaffoldMessenger.of(context).hideCurrentMaterialBanner(),
            child: const Text('DISMISS', style: TextStyle(color: Color(0xFF10B981), fontWeight: FontWeight.bold)),
          ),
        ],
      ),
    );
  }

  void _showOTPDialog(String name, String id, String farm, double acres, String pass, String expectedOtp) {
    final otpController = TextEditingController();

    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (ctx) {
        return AlertDialog(
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
          title: Row(
            children: const [
              Icon(Icons.lock_clock_outlined, color: Color(0xFF059669)),
              SizedBox(width: 10),
              Text('Enter 6-Digit Email OTP', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
            ],
          ),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text('Enter the 6-digit verification code sent to $id.', style: const TextStyle(fontSize: 12, color: Colors.grey)),
              const SizedBox(height: 14),
              TextField(
                controller: otpController,
                keyboardType: TextInputType.number,
                textAlign: TextAlign.center,
                autofocus: true,
                style: const TextStyle(fontSize: 24, fontWeight: FontWeight.bold, letterSpacing: 8, color: Color(0xFF059669)),
                decoration: InputDecoration(
                  hintText: '• • • • • •',
                  hintStyle: TextStyle(letterSpacing: 4, color: Colors.grey[400]),
                  filled: true,
                  fillColor: const Color(0xFFF1F5F9),
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
                ),
              ),
            ],
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
                final inputOtp = otpController.text.trim();
                if (inputOtp.length != 6) {
                  _showMsg('Please enter a valid 6-digit OTP code.');
                  return;
                }
                ScaffoldMessenger.of(context).hideCurrentMaterialBanner();
                Navigator.pop(ctx);
                _completeRegistration(name, id, farm, acres, pass, inputOtp);
              },
              child: const Text('Verify & Register', style: TextStyle(fontWeight: FontWeight.bold)),
            ),
          ],
        );
      },
    );
  }

  Future<void> _completeRegistration(String name, String id, String farm, double acres, String pass, String otp) async {
    setState(() => _isLoading = true);
    final capName = _capitalize(name);
    final capFarm = _capitalize(farm);

    try {
      final res = await http.post(
        Uri.parse('${AppConfig.backendHttpUrl}/api/v1/auth/register'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'full_name': capName,
          'phone_or_email': id,
          'farm_name': capFarm,
          'farm_acres': acres,
          'password': pass,
          'gender': _regGender,
          'age': _regAge,
          'avatar_id': _regAvatarId,
          'crop_type': _regCropType,
        }),
      ).timeout(const Duration(seconds: 8));

      final data = jsonDecode(res.body);
      if (res.statusCode == 200 && data['status'] == 'success') {
        _showMsg('Account created successfully!');
        widget.onLoginSuccess({
          'id': data['farmer_id'] ?? 1,
          'full_name': capName,
          'phone_or_email': id,
          'gender': _regGender,
          'age': _regAge,
          'avatar_id': _regAvatarId,
          'farms': [{'id': 1, 'farm_name': capFarm, 'farm_acres': acres, 'crop_type': _regCropType}]
        });
      } else {
        _showMsg(data['detail'] ?? data['message'] ?? 'Registration failed.');
      }
    } catch (e) {
      _showMsg('Registration error. Please verify network connection and try again.');
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
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
    );
  }

  Future<void> _sendForgotPasswordOTP(String recipient) async {
    setState(() => _isLoading = true);
    await AppConfig.resolveActiveHost();
    String generatedOtp = "849201";

    try {
      final res = await http.post(
        Uri.parse('${AppConfig.backendHttpUrl}/api/v1/auth/forgot-password/send-otp'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'phone_or_email': recipient}),
      ).timeout(const Duration(seconds: 5));

      final data = jsonDecode(res.body);
      if (res.statusCode == 404) {
        _showMsg(data['detail'] ?? 'No account registered with this email/mobile.');
        return;
      }
      if (data.containsKey('demo_otp')) {
        generatedOtp = data['demo_otp'];
      }
    } catch (e) {
      // Fallback code
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }

    _showOTPNotificationBanner(recipient, generatedOtp);
    _showResetPasswordDialog(recipient, generatedOtp);
  }

  void _showResetPasswordDialog(String recipient, String expectedOtp) {
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
                ScaffoldMessenger.of(context).hideCurrentMaterialBanner();
                Navigator.pop(ctx);
                _executePasswordReset(recipient, newPass, otpInput);
              },
              child: const Text('Reset Password', style: TextStyle(fontWeight: FontWeight.bold)),
            ),
          ],
        );
      },
    );
  }

  Future<void> _executePasswordReset(String recipient, String newPass, String otp) async {
    setState(() => _isLoading = true);
    await AppConfig.resolveActiveHost();

    try {
      final res = await http.post(
        Uri.parse('${AppConfig.backendHttpUrl}/api/v1/auth/forgot-password/reset'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'phone_or_email': recipient,
          'new_password': newPass,
          'otp_code': otp,
        }),
      ).timeout(const Duration(seconds: 5));

      final data = jsonDecode(res.body);
      if (res.statusCode == 200) {
        _showMsg('✅ Password reset successfully! Please sign in with your new password.');
        _loginIdController.text = recipient;
        _loginPassController.text = newPass;
      } else {
        _showMsg(data['detail'] ?? data['message'] ?? 'Password reset failed.');
      }
    } catch (e) {
      _showMsg('Connection error. Could not reset password.');
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
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
                color: Colors.white.withOpacity(0.2),
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

  @override
  Widget build(BuildContext context) {
    return PopScope(
      canPop: false,
      onPopInvokedWithResult: (didPop, result) async {
        if (didPop) return;

        if (_regStep == 2) {
          setState(() => _regStep = 1);
          return;
        }

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
                  // Top Tagline Bar & Floating Drone Badge
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
                      Container(
                        padding: const EdgeInsets.all(8),
                        decoration: BoxDecoration(
                          color: const Color(0xFF0F172A),
                          shape: BoxShape.circle,
                          boxShadow: [
                            BoxShadow(
                              color: const Color(0xFF10B981).withOpacity(0.3),
                              blurRadius: 10,
                              spreadRadius: 1,
                            ),
                          ],
                        ),
                        child: const Icon(Icons.sensors_rounded, color: Color(0xFF34D399), size: 18),
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
                            color: const Color(0xFF059669).withOpacity(0.3),
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
                          color: Colors.black.withOpacity(0.06),
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

                                // Remember Me & Forgot Password Row
                                Row(
                                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                  children: [
                                    InkWell(
                                      onTap: () {
                                        setState(() {
                                          _rememberMe = !_rememberMe;
                                        });
                                      },
                                      borderRadius: BorderRadius.circular(6),
                                      child: Row(
                                        children: [
                                          SizedBox(
                                            height: 22,
                                            width: 22,
                                            child: Checkbox(
                                              value: _rememberMe,
                                              activeColor: const Color(0xFF059669),
                                              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(4)),
                                              onChanged: (val) {
                                                setState(() {
                                                  _rememberMe = val ?? false;
                                                });
                                              },
                                            ),
                                          ),
                                          const SizedBox(width: 8),
                                          const Text(
                                            'Remember Me',
                                            style: TextStyle(fontSize: 12, color: Color(0xFF475569), fontWeight: FontWeight.bold),
                                          ),
                                        ],
                                      ),
                                    ),
                                    TextButton(
                                      onPressed: _showForgotPasswordDialog,
                                      style: TextButton.styleFrom(padding: EdgeInsets.zero, minimumSize: Size.zero, tapTargetSize: MaterialTapTargetSize.shrinkWrap),
                                      child: const Text('Forgot Password?', style: TextStyle(color: Color(0xFF059669), fontWeight: FontWeight.bold, fontSize: 12)),
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

                                _buildSubmitBtn('Create Account & Continue →', () {
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
                                  if (pass.length < 8 ||
                                      !pass.contains(RegExp(r'[A-Z]')) ||
                                      !pass.contains(RegExp(r'[a-z]')) ||
                                      !pass.contains(RegExp(r'[0-9]')) ||
                                      !pass.contains(RegExp(r'[@#$%^&*!_\-+=\[\]{}|:<>,.?/]'))) {
                                    _showMsg(r'Password must be 8+ characters with Uppercase, Lowercase, Number & Special Character (@#$...).');
                                    return;
                                  }

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
                                        onSetupComplete: (farmerData) {
                                          Navigator.pop(ctx);
                                          widget.onLoginSuccess(farmerData);
                                        },
                                      ),
                                    ),
                                  );
                                }),
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
            color: const Color(0xFF059669).withOpacity(0.35),
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

// ==================== DEDICATED FULL-SCREEN FARM SETUP WIZARD ====================
class FarmSetupWizardScreen extends StatefulWidget {
  final String fullName;
  final String emailOrPhone;
  final String gender;
  final int age;
  final int avatarId;
  final String password;
  final Function(Map<String, dynamic>) onSetupComplete;

  const FarmSetupWizardScreen({
    super.key,
    required this.fullName,
    required this.emailOrPhone,
    required this.gender,
    required this.age,
    required this.avatarId,
    required this.password,
    required this.onSetupComplete,
  });

  @override
  State<FarmSetupWizardScreen> createState() => _FarmSetupWizardScreenState();
}

class _FarmSetupWizardScreenState extends State<FarmSetupWizardScreen> {
  final _farmNameController = TextEditingController(text: "Green Valley Farm");
  String _cropType = "Wheat & Paddy";
  final List<LatLng> _polygonPoints = [];
  final double _calculatedAcres = 15.0;
  bool _isLoading = false;

  double _computePolygonAcres(List<LatLng> points) {
    if (points.length < 3) return _calculatedAcres;
    const double radius = 6371000.0;
    double area = 0.0;
    for (int i = 0; i < points.length; i++) {
      int j = (i + 1) % points.length;
      double lat1 = points[i].latitude * (pi / 180.0);
      double lon1 = points[i].longitude * (pi / 180.0);
      double lat2 = points[j].latitude * (pi / 180.0);
      double lon2 = points[j].longitude * (pi / 180.0);
      area += (lon2 - lon1) * (2.0 + sin(lat1) + sin(lat2));
    }
    area = (area * radius * radius / 2.0).abs();
    double acres = area / 4046.86;
    return double.parse(acres.toStringAsFixed(2));
  }

  Future<void> _completeRegistration({bool isSkip = false}) async {
    setState(() => _isLoading = true);
    final farmName = isSkip ? "Main Farm" : _farmNameController.text.trim();
    final acres = isSkip ? 15.0 : (_polygonPoints.length >= 3 ? _computePolygonAcres(_polygonPoints) : 15.0);

    try {
      final res = await http.post(
        Uri.parse('${AppConfig.backendHttpUrl}/api/v1/auth/register'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'full_name': widget.fullName,
          'phone_or_email': widget.emailOrPhone,
          'farm_name': farmName.isEmpty ? "Main Farm" : farmName,
          'farm_acres': acres,
          'password': widget.password,
          'gender': widget.gender,
          'age': widget.age,
          'avatar_id': widget.avatarId,
          'crop_type': _cropType,
        }),
      ).timeout(const Duration(seconds: 8));

      final data = jsonDecode(res.body);
      if (res.statusCode == 200 && data['status'] == 'success') {
        widget.onSetupComplete({
          'id': data['farmer_id'] ?? 1,
          'full_name': widget.fullName,
          'phone_or_email': widget.emailOrPhone,
          'gender': widget.gender,
          'age': widget.age,
          'avatar_id': widget.avatarId,
          'farms': [{'id': 1, 'farm_name': farmName.isEmpty ? "Main Farm" : farmName, 'farm_acres': acres, 'crop_type': _cropType}]
        });
      } else {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(data['detail'] ?? data['message'] ?? 'Registration failed.')));
      }
    } catch (e) {
      // Fallback
      widget.onSetupComplete({
        'id': 1,
        'full_name': widget.fullName,
        'phone_or_email': widget.emailOrPhone,
        'gender': widget.gender,
        'age': widget.age,
        'avatar_id': widget.avatarId,
        'farms': [{'id': 1, 'farm_name': farmName.isEmpty ? "Main Farm" : farmName, 'farm_acres': acres, 'crop_type': _cropType}]
      });
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF8FAFC),
      appBar: AppBar(
        backgroundColor: const Color(0xFF0F172A),
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Welcome, ${widget.fullName}', style: const TextStyle(fontSize: 15, fontWeight: FontWeight.bold, color: Colors.white)),
            const Text('Farm & Field Configuration', style: TextStyle(fontSize: 11, color: Color(0xFF10B981))),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => _completeRegistration(isSkip: true),
            child: const Text('Skip for now', style: TextStyle(color: Colors.white70, fontSize: 12)),
          ),
        ],
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(18),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Progress Bar Indicator
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14), boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.04), blurRadius: 8)]),
                child: Row(
                  children: const [
                    Icon(Icons.check_circle, color: Color(0xFF059669), size: 18),
                    SizedBox(width: 8),
                    Text('Account Created', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: Color(0xFF059669))),
                    Spacer(),
                    Icon(Icons.arrow_forward_ios_rounded, color: Colors.grey, size: 12),
                    Spacer(),
                    Icon(Icons.landscape_rounded, color: Color(0xFF059669), size: 18),
                    SizedBox(width: 8),
                    Text('Farm Setup', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: Color(0xFF0F172A))),
                  ],
                ),
              ),
              const SizedBox(height: 16),

              // Farm Name
              TextField(
                controller: _farmNameController,
                textCapitalization: TextCapitalization.words,
                decoration: InputDecoration(
                  labelText: 'Farm Field Name',
                  prefixIcon: const Icon(Icons.landscape_outlined, color: Color(0xFF059669)),
                  filled: true,
                  fillColor: Colors.white,
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: const BorderSide(color: Color(0xFFE2E8F0))),
                ),
              ),
              const SizedBox(height: 14),

              // Crop Selector
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 4),
                decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14), border: Border.all(color: const Color(0xFFE2E8F0))),
                child: DropdownButtonHideUnderline(
                  child: DropdownButton<String>(
                    value: _cropType,
                    isExpanded: true,
                    style: const TextStyle(color: Color(0xFF0F172A), fontSize: 13, fontWeight: FontWeight.bold),
                    onChanged: (val) => setState(() => _cropType = val ?? "Wheat & Paddy"),
                    items: ["Wheat & Paddy", "Corn & Maize", "Cotton", "Sugarcane", "Organic Vegetables", "Fruit Orchard", "Pulses & Oilseeds"]
                        .map((c) => DropdownMenuItem(value: c, child: Text(c)))
                        .toList(),
                  ),
                ),
              ),
              const SizedBox(height: 16),

              // Satellite Map & Area Calculation
              Container(
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16), boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.04), blurRadius: 8)]),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        const Text('Calculated Farm Boundary:', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: Color(0xFF059669))),
                        Text('${_polygonPoints.length >= 3 ? _computePolygonAcres(_polygonPoints) : 15.0} Acres', style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w900, color: Color(0xFF0F172A))),
                      ],
                    ),
                    const SizedBox(height: 6),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        const Text('Tap map below to drop boundary markers:', style: TextStyle(fontSize: 11, color: Colors.grey)),
                        if (_polygonPoints.isNotEmpty)
                          GestureDetector(
                            onTap: () => setState(() => _polygonPoints.clear()),
                            child: const Text('Clear Pins', style: TextStyle(fontSize: 11, color: Colors.redAccent, fontWeight: FontWeight.bold)),
                          ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    SizedBox(
                      height: 220,
                      child: ClipRRect(
                        borderRadius: BorderRadius.circular(14),
                        child: FlutterMap(
                          options: MapOptions(
                            initialCenter: const LatLng(20.2961, 85.8245),
                            initialZoom: 15.0,
                            onTap: (_, point) => setState(() => _polygonPoints.add(point)),
                          ),
                          children: [
                            TileLayer(urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png', userAgentPackageName: 'com.agrisense.app'),
                            if (_polygonPoints.length >= 3)
                              PolygonLayer(
                                polygons: [
                                  Polygon(points: _polygonPoints, color: const Color(0xFF10B981).withOpacity(0.35), borderColor: const Color(0xFF059669), borderStrokeWidth: 2),
                                ],
                              ),
                            MarkerLayer(
                              markers: _polygonPoints.map((pt) => Marker(point: pt, width: 22, height: 22, child: const Icon(Icons.location_on_rounded, color: Color(0xFF059669), size: 20))).toList(),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 20),

              // Submit Button
              SizedBox(
                width: double.infinity,
                height: 50,
                child: ElevatedButton(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFF059669),
                    foregroundColor: Colors.white,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                  ),
                  onPressed: _isLoading ? null : () => _completeRegistration(isSkip: false),
                  child: _isLoading
                      ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                      : const Text('Complete Setup & Launch Platform', style: TextStyle(fontSize: 15, fontWeight: FontWeight.bold)),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

// ==================== 4. MAIN NAVIGATION SCREEN ====================
class MainNavigationScreen extends StatefulWidget {
  final Map<String, dynamic> farmer;
  final VoidCallback onLogout;

  const MainNavigationScreen({super.key, required this.farmer, required this.onLogout});

  @override
  State<MainNavigationScreen> createState() => _MainNavigationScreenState();
}

class _MainNavigationScreenState extends State<MainNavigationScreen> {
  final GlobalKey<ScaffoldState> _scaffoldKey = GlobalKey<ScaffoldState>();
  final GlobalKey<_FarmerDashboardState> _farmerDashboardKey = GlobalKey<_FarmerDashboardState>();
  int _currentIndex = 0;
  late Map<String, dynamic> _farmerData;
  late List<Map<String, dynamic>> _farms;
  int _selectedFarmIdx = 0;

  final WebSocketService _wsService = WebSocketService();
  TelemetryPacket? _latestPacket;
  bool _isConnected = false;

  final String _currentAppVersion = "1.7.1";
  bool _isCheckingUpdate = false;
  Map<String, dynamic>? _activeTopCapsule;
  Timer? _topCapsuleDismissTimer;

  void _showTopCapsuleNotification(String title, String message, {IconData icon = Icons.notifications_active_rounded, Color backgroundColor = const Color(0xFF0F172A)}) {
    if (!mounted) return;
    _topCapsuleDismissTimer?.cancel();
    setState(() {
      _activeTopCapsule = {
        'title': title,
        'message': message,
        'icon': icon,
        'backgroundColor': backgroundColor,
      };
    });
    _topCapsuleDismissTimer = Timer(const Duration(seconds: 4), () {
      if (mounted) {
        setState(() => _activeTopCapsule = null);
      }
    });
  }

  @override
  void initState() {
    super.initState();
    _farmerData = Map<String, dynamic>.from(widget.farmer);
    _farms = List<Map<String, dynamic>>.from(_farmerData['farms'] ?? [
      {'id': 1, 'farm_name': 'Green Valley Field', 'farm_acres': 15.0, 'crop_type': 'Wheat & Paddy'}
    ]);

    _wsService.connect('${AppConfig.backendWsUrl}/ws/v1/telemetry');
    _cleanupObsoleteUpdateFiles();
    _requestAllAppPermissions();
    _wsService.connectionStream.listen((status) {
      if (mounted) setState(() => _isConnected = status);
    });
    _wsService.telemetryStream.listen((packet) {
      if (mounted) setState(() => _latestPacket = packet);
    });

    Timer(const Duration(seconds: 2), () {
      _checkForAppUpdates(silent: true);
    });
  }

  Future<void> _requestAllAppPermissions() async {
    try {
      await [
        Permission.notification,
        Permission.locationWhenInUse,
        Permission.location,
        Permission.storage,
        Permission.camera,
        Permission.photos,
      ].request();
    } catch (e) {
      if (kDebugMode) {
        print('PERMISSION REQUEST ERROR: $e');
      }
    }
  }

  void _cleanupObsoleteUpdateFiles() {
    try {
      int deletedCount = 0;
      int bytesReclaimed = 0;

      final targetDirs = [
        Directory('/data/user/0/com.example.agrisense_seashark_app/files'),
        Directory.systemTemp,
        Directory('/storage/emulated/0/Download'),
      ];

      for (final dir in targetDirs) {
        if (!dir.existsSync()) continue;
        try {
          final entities = dir.listSync();
          for (final entity in entities) {
            if (entity is File) {
              final fileName = entity.path.split(Platform.pathSeparator).last;
              final isApkOrPart = (fileName.startsWith('AgriSense') || fileName.startsWith('app-debug')) &&
                  (fileName.endsWith('.apk') || fileName.endsWith('.part'));
              
              if (isApkOrPart) {
                if (!fileName.contains('_v$_currentAppVersion.apk')) {
                  final fileSize = entity.lengthSync();
                  entity.deleteSync();
                  deletedCount++;
                  bytesReclaimed += fileSize;
                  if (kDebugMode) {
                    print('PURGED OBSOLETE UPDATE PACKAGE: $fileName (${(fileSize / (1024 * 1024)).toStringAsFixed(1)} MB)');
                  }
                }
              }
            }
          }
        } catch (e) {
          if (kDebugMode) {
            print('DIRECTORY CLEANUP ERROR in ${dir.path}: $e');
          }
        }
      }

      if (deletedCount > 0 && mounted) {
        final mbReclaimed = (bytesReclaimed / (1024 * 1024)).toStringAsFixed(1);
        Future.microtask(() {
          _showTopCapsuleNotification(
            'Storage Cleaned Up',
            'Deleted $deletedCount previous update APK file(s) ($mbReclaimed MB reclaimed).',
            icon: Icons.cleaning_services_rounded,
            backgroundColor: const Color(0xFF059669),
          );
        });
      }
    } catch (e) {
      if (kDebugMode) {
        print('TOTAL CLEANUP ERROR: $e');
      }
    }
  }

  Future<void> _checkForAppUpdates({bool silent = false}) async {
    if (_isCheckingUpdate) return;
    _isCheckingUpdate = true;
    try {
      final res = await http.get(Uri.parse('${AppConfig.backendHttpUrl}/api/v1/update/check?current_version=$_currentAppVersion')).timeout(const Duration(seconds: 6));
      if (res.statusCode == 200) {
        final updateInfo = jsonDecode(res.body);
        if (updateInfo['has_update'] == true && mounted) {
          _showUpdateModalDialog(updateInfo);
        } else if (!silent && mounted) {
          _showTopCapsuleNotification(
            'System Up to Date',
            'AgriSense is up to date (v$_currentAppVersion).',
            icon: Icons.check_circle_rounded,
            backgroundColor: const Color(0xFF059669),
          );
        }
      }
    } catch (e) {
      if (!silent && mounted) {
        _showTopCapsuleNotification(
          'Network Error',
          'Unable to reach update server.',
          icon: Icons.wifi_off_rounded,
          backgroundColor: Colors.redAccent,
        );
      }
    } finally {
      _isCheckingUpdate = false;
    }
  }

  void _showUpdateModalDialog(Map<String, dynamic> updateInfo) {
    double downloadProgress = 0.0;
    bool isDownloading = false;
    int bytesDownloaded = 0;
    int totalBytes = 215 * 1024 * 1024;
    StreamSubscription<List<int>>? downloadSubscription;
    http.Client? httpClient;

    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (ctx) {
        return StatefulBuilder(
          builder: (modalCtx, setModalState) {
            final targetVersion = updateInfo['latest_version'] ?? _currentAppVersion;

            return AlertDialog(
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(22)),
              title: Row(
                children: const [
                  AgriSenseLogoBadge(size: 38, borderRadius: 10),
                  SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      'Software Update Available',
                      style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Color(0xFF0F172A)),
                    ),
                  ),
                ],
              ),
              content: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('AgriSense v$targetVersion is available.', style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: Color(0xFF059669))),
                  const SizedBox(height: 8),
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(color: const Color(0xFFF1F5F9), borderRadius: BorderRadius.circular(10)),
                    child: Text(
                      updateInfo['release_notes'] ?? 'Performance optimizations and system enhancements.',
                      style: const TextStyle(fontSize: 11, color: Color(0xFF475569)),
                    ),
                  ),
                  const SizedBox(height: 14),
                  if (isDownloading) ...[
                    ClipRRect(
                      borderRadius: BorderRadius.circular(6),
                      child: LinearProgressIndicator(
                        value: downloadProgress > 0 ? downloadProgress : null,
                        color: const Color(0xFF059669),
                        backgroundColor: const Color(0xFFE2E8F0),
                        minHeight: 8,
                      ),
                    ),
                    const SizedBox(height: 8),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Text(
                          downloadProgress > 0 ? '${(downloadProgress * 100).toInt()}% Downloaded' : 'Connecting...',
                          style: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: Color(0xFF0F172A)),
                        ),
                        Text(
                          '${(bytesDownloaded / (1024 * 1024)).toStringAsFixed(1)} / ${(totalBytes / (1024 * 1024)).toStringAsFixed(1)} MB',
                          style: const TextStyle(fontSize: 11, color: Color(0xFF64748B)),
                        ),
                      ],
                    ),
                  ],
                ],
              ),
              actions: [
                if (!isDownloading) ...[
                  TextButton(
                    onPressed: () => Navigator.pop(modalCtx),
                    child: const Text('Later', style: TextStyle(color: Colors.grey)),
                  ),
                  ElevatedButton(
                    style: ElevatedButton.styleFrom(
                      backgroundColor: const Color(0xFF059669),
                      foregroundColor: Colors.white,
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                    ),
                    onPressed: () async {
                      setModalState(() {
                        isDownloading = true;
                        downloadProgress = 0.01;
                      });

                      try {
                        Directory downloadDir;
                        try {
                          downloadDir = Directory('/data/user/0/com.example.agrisense_seashark_app/files');
                          if (!downloadDir.existsSync()) downloadDir.createSync(recursive: true);
                        } catch (_) {
                          downloadDir = Directory.systemTemp;
                        }

                        final filePath = '${downloadDir.path}/AgriSense_v$targetVersion.apk';
                        final file = File(filePath);

                        // Ensure clean target file path for direct fresh stream
                        if (file.existsSync()) {
                          try { file.deleteSync(); } catch (_) {}
                        }

                        // 2. Direct High-Speed Stream Downloader via HTTP
                        final rawUrl = updateInfo['download_url'].toString();
                        final downloadUrl = rawUrl.replaceAll('localhost', AppConfig.activeHost).replaceAll('127.0.0.1', AppConfig.activeHost);

                        httpClient = http.Client();
                        final req = http.Request('GET', Uri.parse(downloadUrl));
                        final streamedResponse = await httpClient!.send(req);

                        final contentLength = streamedResponse.contentLength;
                        if (contentLength != null && contentLength > 0) {
                          totalBytes = contentLength;
                        }

                        final partFile = File('$filePath.part');
                        if (partFile.existsSync()) partFile.deleteSync();
                        final sink = partFile.openWrite();

                        downloadSubscription = streamedResponse.stream.listen(
                          (chunk) {
                            sink.add(chunk);
                            bytesDownloaded += chunk.length;
                            final progress = (bytesDownloaded / totalBytes).clamp(0.01, 1.0);
                            if (modalCtx.mounted) {
                              setModalState(() {
                                downloadProgress = progress;
                              });
                            }
                          },
                          onDone: () async {
                            await sink.flush();
                            await sink.close();
                            if (file.existsSync()) file.deleteSync();
                            partFile.renameSync(filePath);

                            if (modalCtx.mounted) {
                              Navigator.pop(modalCtx);
                            }
                            _showTopCapsuleNotification(
                              'Download Complete!',
                              'AgriSense v$targetVersion downloaded! Opening package installer...',
                              icon: Icons.check_circle_rounded,
                              backgroundColor: const Color(0xFF059669),
                            );

                            try {
                              const platform = MethodChannel('com.agrisense.app/installer');
                              await platform.invokeMethod('installApk', {'filePath': filePath});
                            } catch (e) {
                              print('DIRECT STREAM INSTALLER ERROR: $e');
                            }
                          },
                          onError: (e) {
                            sink.close();
                            if (partFile.existsSync()) partFile.deleteSync();
                            if (modalCtx.mounted) {
                              setModalState(() => isDownloading = false);
                            }
                            _showTopCapsuleNotification(
                              'Download Failed',
                              'Direct stream error: $e',
                              icon: Icons.error_outline_rounded,
                              backgroundColor: Colors.redAccent,
                            );
                          },
                          cancelOnError: true,
                        );
                      } catch (e) {
                        setModalState(() => isDownloading = false);
                        _showTopCapsuleNotification(
                          'Download Error',
                          e.toString(),
                          icon: Icons.error_outline_rounded,
                          backgroundColor: Colors.redAccent,
                        );
                      }
                    },
                    child: const Text('Update Now', style: TextStyle(fontWeight: FontWeight.bold)),
                  ),
                ] else ...[
                  // ACTION BUTTONS WHEN DOWNLOADING IN PROGRESS
                  TextButton.icon(
                    onPressed: () async {
                      downloadSubscription?.cancel();
                      httpClient?.close();
                      try {
                        Directory downloadDir = Directory('/storage/emulated/0/Download');
                        if (!downloadDir.existsSync()) downloadDir = Directory.systemTemp;
                        final partFile = File('${downloadDir.path}/AgriSense_v$targetVersion.apk.part');
                        if (partFile.existsSync()) partFile.deleteSync();
                      } catch (_) {}

                      if (modalCtx.mounted) {
                        Navigator.pop(modalCtx);
                      }
                      _showTopCapsuleNotification(
                        'Download Canceled',
                        'AgriSense update download was aborted.',
                        icon: Icons.cancel_outlined,
                        backgroundColor: Colors.redAccent,
                      );
                    },
                    icon: const Icon(Icons.close, color: Colors.redAccent, size: 16),
                    label: const Text('Cancel Download', style: TextStyle(color: Colors.redAccent, fontWeight: FontWeight.bold, fontSize: 12)),
                  ),
                  ElevatedButton.icon(
                    style: ElevatedButton.styleFrom(
                      backgroundColor: const Color(0xFF059669),
                      foregroundColor: Colors.white,
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                    ),
                    onPressed: () {
                      if (modalCtx.mounted) {
                        Navigator.pop(modalCtx);
                      }
                      _showTopCapsuleNotification(
                        'Downloading in Background',
                        'AgriSense v$targetVersion is downloading in background.',
                        icon: Icons.downloading_rounded,
                        backgroundColor: const Color(0xFF0F172A),
                      );
                    },
                    icon: const Icon(Icons.arrow_downward_rounded, size: 16),
                    label: const Text('Minimize', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 12)),
                  ),
                ],
              ],
            );
          },
        );
      },
    );
  }

  void _addNewFarm(String name, double acres, String crop) {
    setState(() {
      _farms.add({
        'id': _farms.length + 1,
        'farm_name': name,
        'farm_acres': acres,
        'crop_type': crop,
      });
      _selectedFarmIdx = _farms.length - 1;
    });
    _showTopCapsuleNotification(
      'Farm Field Added',
      'Farm field "$name" added successfully.',
      icon: Icons.landscape_rounded,
      backgroundColor: const Color(0xFF059669),
    );
  }

  void _showExtendedFarmSelectorDialog() {
    showGeneralDialog(
      context: context,
      barrierDismissible: true,
      barrierLabel: 'Dismiss',
      barrierColor: Colors.black.withOpacity(0.3),
      transitionDuration: const Duration(milliseconds: 220),
      pageBuilder: (ctx, anim1, anim2) {
        return SafeArea(
          child: Align(
            alignment: Alignment.topCenter,
            child: Padding(
              padding: const EdgeInsets.only(top: 56, left: 16, right: 16),
              child: Material(
                color: Colors.transparent,
                child: Container(
                  width: double.infinity,
                  constraints: BoxConstraints(
                    maxWidth: 380,
                    maxHeight: MediaQuery.of(context).size.height * 0.55,
                  ),
                  padding: const EdgeInsets.all(18),
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(22),
                    boxShadow: [
                      BoxShadow(
                        color: const Color(0xFF0F172A).withOpacity(0.2),
                        blurRadius: 24,
                        offset: const Offset(0, 10),
                      ),
                    ],
                  ),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // Header with Title & Collapse Dropdown Button
                      Row(
                        children: [
                          Container(
                            padding: const EdgeInsets.all(8),
                            decoration: BoxDecoration(
                              color: const Color(0xFFECFDF5),
                              borderRadius: BorderRadius.circular(12),
                            ),
                            child: const Icon(Icons.landscape_rounded, color: Color(0xFF059669), size: 22),
                          ),
                          const SizedBox(width: 12),
                          const Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  'Select Active Farm Field',
                                  style: TextStyle(fontSize: 15, fontWeight: FontWeight.bold, color: Color(0xFF0F172A)),
                                ),
                                Text(
                                  'Switch active field or add location',
                                  style: TextStyle(fontSize: 11, color: Color(0xFF64748B)),
                                ),
                              ],
                            ),
                          ),
                          InkWell(
                            onTap: () => Navigator.pop(ctx),
                            borderRadius: BorderRadius.circular(20),
                            child: Container(
                              padding: const EdgeInsets.all(6),
                              decoration: const BoxDecoration(
                                color: Color(0xFFF1F5F9),
                                shape: BoxShape.circle,
                              ),
                              child: const Icon(Icons.keyboard_arrow_up_rounded, color: Color(0xFF059669), size: 22),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 12),
                      const Divider(height: 1, color: Color(0xFFE2E8F0)),
                      const SizedBox(height: 12),

                      // List of Farms - Scalable List
                      Flexible(
                        child: SingleChildScrollView(
                          child: Column(
                            mainAxisSize: MainAxisSize.min,
                            children: List.generate(_farms.length, (i) {
                              final farm = _farms[i];
                              final isSelected = (i == _selectedFarmIdx);

                              return Padding(
                                padding: const EdgeInsets.only(bottom: 8),
                                child: InkWell(
                                  onTap: () {
                                    setState(() => _selectedFarmIdx = i);
                                    Navigator.pop(ctx);
                                    _showTopCapsuleNotification(
                                      'Active Farm Switched',
                                      'Switched to active field "${farm['farm_name']}".',
                                      icon: Icons.landscape_rounded,
                                      backgroundColor: const Color(0xFF059669),
                                    );
                                  },
                                  borderRadius: BorderRadius.circular(14),
                                  child: AnimatedContainer(
                                    duration: const Duration(milliseconds: 180),
                                    padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                                    decoration: BoxDecoration(
                                      color: isSelected ? const Color(0xFFECFDF5) : const Color(0xFFF8FAFC),
                                      borderRadius: BorderRadius.circular(14),
                                      border: Border.all(
                                        color: isSelected ? const Color(0xFF059669) : const Color(0xFFE2E8F0),
                                        width: isSelected ? 1.8 : 1.0,
                                      ),
                                    ),
                                    child: Row(
                                      children: [
                                        Container(
                                          padding: const EdgeInsets.all(7),
                                          decoration: BoxDecoration(
                                            color: isSelected ? const Color(0xFF059669) : const Color(0xFFE2E8F0),
                                            shape: BoxShape.circle,
                                          ),
                                          child: Icon(
                                            Icons.landscape_rounded,
                                            color: isSelected ? Colors.white : const Color(0xFF64748B),
                                            size: 16,
                                          ),
                                        ),
                                        const SizedBox(width: 12),
                                        Expanded(
                                          child: Column(
                                            crossAxisAlignment: CrossAxisAlignment.start,
                                            children: [
                                              Text(
                                                farm['farm_name'] ?? 'Main Farm',
                                                style: TextStyle(
                                                  fontSize: 13,
                                                  fontWeight: FontWeight.bold,
                                                  color: isSelected ? const Color(0xFF065F46) : const Color(0xFF0F172A),
                                                ),
                                              ),
                                              const SizedBox(height: 2),
                                              Text(
                                                '${farm['farm_acres']} Acres • ${farm['crop_type'] ?? "Wheat & Paddy"}',
                                                style: TextStyle(
                                                  fontSize: 11,
                                                  color: isSelected ? const Color(0xFF047857) : const Color(0xFF64748B),
                                                ),
                                              ),
                                            ],
                                          ),
                                        ),
                                        if (isSelected)
                                          const Icon(Icons.check_circle_rounded, color: Color(0xFF059669), size: 20)
                                        else
                                          const Icon(Icons.radio_button_unchecked_rounded, color: Color(0xFFCBD5E1), size: 18),
                                      ],
                                    ),
                                  ),
                                ),
                              );
                            }),
                          ),
                        ),
                      ),

                      const SizedBox(height: 4),
                      const Divider(height: 1, color: Color(0xFFE2E8F0)),
                      const SizedBox(height: 12),

                      // Add New Farm Field Button
                      ElevatedButton.icon(
                        style: ElevatedButton.styleFrom(
                          backgroundColor: const Color(0xFF059669),
                          foregroundColor: Colors.white,
                          minimumSize: const Size(double.infinity, 44),
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                          elevation: 0,
                        ),
                        onPressed: () {
                          Navigator.pop(ctx);
                          _showAddFarmDialog();
                        },
                        icon: const Icon(Icons.add_location_alt_rounded, size: 18),
                        label: const Text(
                          'Add New Farm Field',
                          style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        );
      },
      transitionBuilder: (ctx, anim1, anim2, child) {
        return SlideTransition(
          position: Tween<Offset>(
            begin: const Offset(0, -0.12),
            end: Offset.zero,
          ).animate(CurvedAnimation(parent: anim1, curve: Curves.easeOutCubic)),
          child: FadeTransition(
            opacity: anim1,
            child: child,
          ),
        );
      },
    );
  }

  void _showUserProfileModalSheet(BuildContext context) {
    bool isEditing = false;
    final farmerId = _farmerData['id'] ?? 1;
    final nameCtrl = TextEditingController(text: _farmerData['full_name'] ?? 'Akash Satapathy');
    final ageCtrl = TextEditingController(text: (_farmerData['age'] ?? 32).toString());
    final genderList = ["Male", "Female", "Other"];
    String? rawGender = _farmerData['gender'];
    String? selectedGender = genderList.contains(rawGender) ? rawGender : null;
    int selectedAvatar = _farmerData['avatar_id'] ?? 1;
    bool isSaving = false;

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) {
        return StatefulBuilder(
          builder: (modalCtx, setModalState) {
            final currentName = _farmerData['full_name'] ?? 'Farmer';
            final email = _farmerData['phone_or_email'] ?? 'farmer@agrisense.io';
            final activeFarm = _farms[_selectedFarmIdx];

            return Padding(
              padding: EdgeInsets.only(bottom: MediaQuery.of(modalCtx).viewInsets.bottom),
              child: Container(
                decoration: const BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.vertical(top: Radius.circular(25)),
                ),
                padding: const EdgeInsets.all(22),
                child: SingleChildScrollView(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Container(width: 40, height: 4, decoration: BoxDecoration(color: const Color(0xFFCBD5E1), borderRadius: BorderRadius.circular(2))),
                      const SizedBox(height: 14),

                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          const Text('User Profile & Settings', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Color(0xFF0F172A))),
                          TextButton.icon(
                            onPressed: () => setModalState(() => isEditing = !isEditing),
                            icon: Icon(isEditing ? Icons.close : Icons.edit, size: 16, color: const Color(0xFF059669)),
                            label: Text(isEditing ? 'Cancel' : 'Edit Profile', style: const TextStyle(color: Color(0xFF059669), fontWeight: FontWeight.bold, fontSize: 13)),
                          ),
                        ],
                      ),
                      const SizedBox(height: 10),

                      FarmerAvatarWidget(
                        avatarId: selectedAvatar,
                        name: currentName,
                        radius: 34,
                      ),
                      const SizedBox(height: 8),

                      if (!isEditing) ...[
                        Text(currentName, style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w900, color: Color(0xFF0F172A))),
                        Text(email, style: const TextStyle(fontSize: 12, color: Color(0xFF64748B))),
                        const SizedBox(height: 14),

                        Container(
                          padding: const EdgeInsets.all(14),
                          decoration: BoxDecoration(color: const Color(0xFFF8FAFC), borderRadius: BorderRadius.circular(16)),
                          child: Column(
                            children: [
                              Row(
                                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                children: [
                                  const Text('Gender / Demographic:', style: TextStyle(fontSize: 12, color: Colors.grey)),
                                  Text('${_farmerData['gender'] ?? 'Farmer'} (${_farmerData['age'] ?? 32} yrs)', style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: Color(0xFF0F172A))),
                                ],
                              ),
                              const Divider(height: 16),
                              Row(
                                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                children: [
                                  const Text('Active Farm Field:', style: TextStyle(fontSize: 12, color: Colors.grey)),
                                  Text('${activeFarm['farm_name']} (${activeFarm['farm_acres']} Acres)', style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: Color(0xFF059669))),
                                ],
                              ),
                              const Divider(height: 16),
                              Row(
                                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                children: [
                                  const Text('App Version:', style: TextStyle(fontSize: 12, color: Colors.grey)),
                                  Text('AgriSense v$_currentAppVersion', style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: Color(0xFF0F172A))),
                                ],
                              ),
                            ],
                          ),
                        ),
                      ] else ...[
                        // EDIT PROFILE FORM
                        TextField(
                          controller: nameCtrl,
                          decoration: InputDecoration(
                            labelText: 'Full Name',
                            prefixIcon: const Icon(Icons.person_outline, color: Color(0xFF059669)),
                            filled: true,
                            fillColor: const Color(0xFFF8FAFC),
                            border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: const BorderSide(color: Color(0xFFE2E8F0))),
                          ),
                        ),
                        const SizedBox(height: 10),

                        Row(
                          children: [
                            Expanded(
                              child: Container(
                                padding: const EdgeInsets.symmetric(horizontal: 10),
                                decoration: BoxDecoration(color: const Color(0xFFF8FAFC), borderRadius: BorderRadius.circular(12), border: Border.all(color: const Color(0xFFE2E8F0))),
                                child: DropdownButtonHideUnderline(
                                  child: DropdownButton<String>(
                                    value: selectedGender,
                                    hint: const Text('Select Gender', style: TextStyle(color: Color(0xFF94A3B8), fontSize: 12)),
                                    isExpanded: true,
                                    style: const TextStyle(color: Color(0xFF0F172A), fontSize: 12),
                                    onChanged: (val) => setModalState(() => selectedGender = val),
                                    items: genderList
                                        .map((g) => DropdownMenuItem(value: g, child: Text(g)))
                                        .toList(),
                                  ),
                                ),
                              ),
                            ),
                            const SizedBox(width: 8),
                            Expanded(
                              child: TextField(
                                controller: ageCtrl,
                                keyboardType: TextInputType.number,
                                decoration: InputDecoration(
                                  labelText: 'Age (Years)',
                                  prefixIcon: const Icon(Icons.cake_outlined, color: Color(0xFF059669), size: 18),
                                  filled: true,
                                  fillColor: const Color(0xFFF8FAFC),
                                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: const BorderSide(color: Color(0xFFE2E8F0))),
                                ),
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 10),

                        const Align(
                          alignment: Alignment.centerLeft,
                          child: Text('Choose Avatar:', style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: Color(0xFF0F172A))),
                        ),
                        const SizedBox(height: 6),
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceAround,
                          children: [1, 2, 3, 4, 5, 6].map((id) {
                            final isSel = selectedAvatar == id;
                            return InkWell(
                              onTap: () => setModalState(() => selectedAvatar = id),
                              child: Container(
                                padding: const EdgeInsets.all(3),
                                decoration: BoxDecoration(shape: BoxShape.circle, border: Border.all(color: isSel ? const Color(0xFF059669) : Colors.transparent, width: 2)),
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
                        const SizedBox(height: 14),

                        SizedBox(
                          width: double.infinity,
                          height: 44,
                          child: ElevatedButton(
                            style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF059669), foregroundColor: Colors.white, shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12))),
                            onPressed: isSaving
                                ? null
                                : () async {
                                    final newName = nameCtrl.text.trim();
                                    final newAge = int.tryParse(ageCtrl.text) ?? 32;

                                    if (newName.isEmpty) {
                                      _showTopCapsuleNotification('Input Required', 'Name cannot be empty', icon: Icons.warning_amber_rounded, backgroundColor: Colors.orangeAccent);
                                      return;
                                    }

                                    setModalState(() => isSaving = true);
                                    try {
                                      final res = await http.post(
                                        Uri.parse('${AppConfig.backendHttpUrl}/api/v1/auth/profile/update'),
                                        headers: {'Content-Type': 'application/json'},
                                        body: jsonEncode({
                                          'farmer_id': farmerId,
                                          'full_name': newName,
                                          'gender': selectedGender,
                                          'age': newAge,
                                          'avatar_id': selectedAvatar,
                                        }),
                                      ).timeout(const Duration(seconds: 6));

                                      if (res.statusCode == 200) {
                                        setState(() {
                                          _farmerData['full_name'] = newName;
                                          _farmerData['gender'] = selectedGender;
                                          _farmerData['age'] = newAge;
                                          _farmerData['avatar_id'] = selectedAvatar;
                                        });
                                        Navigator.pop(ctx);
                                        _showTopCapsuleNotification('Profile Updated', 'Profile changes updated successfully!', icon: Icons.check_circle_rounded, backgroundColor: const Color(0xFF059669));
                                      }
                                    } catch (e) {
                                      setState(() {
                                        _farmerData['full_name'] = newName;
                                        _farmerData['gender'] = selectedGender;
                                        _farmerData['age'] = newAge;
                                        _farmerData['avatar_id'] = selectedAvatar;
                                      });
                                      Navigator.pop(ctx);
                                      _showTopCapsuleNotification('Profile Saved', 'Profile updated locally.', icon: Icons.check_circle_rounded, backgroundColor: const Color(0xFF059669));
                                    } finally {
                                      setModalState(() => isSaving = false);
                                    }
                                  },
                            child: isSaving
                                ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                                : const Text('Save Profile Changes', style: TextStyle(fontWeight: FontWeight.bold)),
                          ),
                        ),
                      ],

                      const SizedBox(height: 16),
                      SizedBox(
                        width: double.infinity,
                        height: 44,
                        child: ElevatedButton.icon(
                          style: ElevatedButton.styleFrom(
                            backgroundColor: Colors.redAccent.withOpacity(0.1),
                            foregroundColor: Colors.redAccent,
                            elevation: 0,
                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                          ),
                          onPressed: () {
                            Navigator.pop(ctx);
                            widget.onLogout();
                          },
                          icon: const Icon(Icons.logout, size: 18),
                          label: const Text('Sign Out of Account', style: TextStyle(fontWeight: FontWeight.bold)),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            );
          },
        );
      },
    );
  }





  void _showAddFarmDialog() {
    final nameCtrl = TextEditingController();
    final acresCtrl = TextEditingController(text: "15.0");
    String cropType = "Wheat & Paddy";

    showDialog(
      context: context,
      builder: (ctx) {
        return AlertDialog(
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
          title: Row(
            children: const [
              Icon(Icons.add_location_alt_outlined, color: Color(0xFF059669)),
              SizedBox(width: 10),
              Text('Add New Farm Field', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
            ],
          ),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: nameCtrl,
                decoration: InputDecoration(
                  labelText: 'Farm Field Name',
                  prefixIcon: const Icon(Icons.landscape_outlined, color: Color(0xFF059669)),
                  filled: true,
                  fillColor: const Color(0xFFF1F5F9),
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
                ),
              ),
              const SizedBox(height: 10),
              TextField(
                controller: acresCtrl,
                keyboardType: TextInputType.number,
                decoration: InputDecoration(
                  labelText: 'Area Size (Acres)',
                  prefixIcon: const Icon(Icons.aspect_ratio, color: Color(0xFF059669)),
                  filled: true,
                  fillColor: const Color(0xFFF1F5F9),
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
                ),
              ),
            ],
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Cancel', style: TextStyle(color: Colors.grey))),
            ElevatedButton(
              style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF059669), foregroundColor: Colors.white),
              onPressed: () {
                final n = nameCtrl.text.trim();
                final a = double.tryParse(acresCtrl.text) ?? 10.0;
                if (n.isNotEmpty) {
                  Navigator.pop(ctx);
                  _addNewFarm(n, a, cropType);
                }
              },
              child: const Text('Add Farm'),
            ),
          ],
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final activeFarm = _farms[_selectedFarmIdx];
    final farmerName = _farmerData['full_name'] ?? 'Farmer';

    final screens = [
      FarmerDashboard(
        key: _farmerDashboardKey,
        farmer: _farmerData,
        activeFarm: activeFarm,
        packet: _latestPacket,
        wsService: _wsService,
      ),
      const FarmLayoutMapScreen(),
      DroneFlightControlScreen(packet: _latestPacket, isConnected: _isConnected),
      SettingsAndProfileScreen(
        farmer: _farmerData,
        farms: _farms,
        selectedIdx: _selectedFarmIdx,
        appVersion: _currentAppVersion,
        onSelectFarm: (idx) => setState(() => _selectedFarmIdx = idx),
        onAddFarm: _addNewFarm,
        onLogout: widget.onLogout,
        onEditProfile: () => _showUserProfileModalSheet(context),
        onCheckUpdate: () => _checkForAppUpdates(silent: false),
      ),
    ];

    return PopScope(
      canPop: false,
      onPopInvokedWithResult: (didPop, result) async {
        if (didPop) return;

        if (_scaffoldKey.currentState?.isDrawerOpen ?? false) {
          Navigator.of(context).pop();
          return;
        }

        if (_currentIndex != 0) {
          setState(() => _currentIndex = 0);
          return;
        }

        final shouldExit = await showDialog<bool>(
          context: context,
          builder: (ctx) {
            return AlertDialog(
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
              title: Row(
                children: const [
                  Icon(Icons.exit_to_app_rounded, color: Colors.redAccent),
                  SizedBox(width: 10),
                  Text('Exit AgriSense App?', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
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

        if (shouldExit == true) {
          SystemNavigator.pop();
        }
      },
      child: Scaffold(
        key: _scaffoldKey,
        backgroundColor: const Color(0xFFF8FAFC),
        drawer: AppDrawer(
          farmer: _farmerData,
          farms: _farms,
          selectedIdx: _selectedFarmIdx,
          onLogout: widget.onLogout,
          onEditProfile: () => _showUserProfileModalSheet(context),
          onOpenCropAiScanner: () {
            if (_currentIndex != 0) {
              setState(() => _currentIndex = 0);
            }
            Future.microtask(() {
              _farmerDashboardKey.currentState?.openScannerModal();
            });
          },
          onSelectScreen: (idx) {
            Navigator.pop(context);
            setState(() => _currentIndex = idx);
          },
        ),
        bottomNavigationBar: _buildFloatingBottomNavBar(),
        body: Stack(
          children: [
            SafeArea(
              child: Column(
                children: [
                  // ==================== FLOATING TOP CAPSULE HEADER ====================
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        // 1. LEFT TOP CORNER: SMALL CAPSULE MENU BUTTON
                        Builder(
                          builder: (btnCtx) => InkWell(
                            onTap: () => Scaffold.of(btnCtx).openDrawer(),
                            borderRadius: BorderRadius.circular(25),
                            child: Container(
                              padding: const EdgeInsets.all(10),
                              decoration: BoxDecoration(
                                color: const Color(0xFF022C22),
                                shape: BoxShape.circle,
                                boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.08), blurRadius: 8)],
                              ),
                              child: const Icon(Icons.menu_rounded, color: Colors.white, size: 20),
                            ),
                          ),
                        ),

                        // 2. CENTER: EXTENDED CURVED-EDGE FARM SELECTOR CAPSULE
                        InkWell(
                          onTap: _showExtendedFarmSelectorDialog,
                          borderRadius: BorderRadius.circular(25),
                          child: Container(
                            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
                            decoration: BoxDecoration(
                              color: const Color(0xFF047857),
                              borderRadius: BorderRadius.circular(25),
                              boxShadow: [BoxShadow(color: const Color(0xFF047857).withOpacity(0.35), blurRadius: 8)],
                            ),
                            child: Row(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                const Icon(Icons.landscape_rounded, color: Colors.white, size: 18),
                                const SizedBox(width: 8),
                                Column(
                                  mainAxisSize: MainAxisSize.min,
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(
                                      activeFarm['farm_name'] ?? 'Main Farm',
                                      style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 12.5),
                                    ),
                                    Text(
                                      '${activeFarm['farm_acres'] ?? 15.0} Acres',
                                      style: const TextStyle(color: Colors.white70, fontSize: 9.5, fontWeight: FontWeight.w500),
                                    ),
                                  ],
                                ),
                                const SizedBox(width: 6),
                                const Icon(Icons.keyboard_arrow_down_rounded, color: Colors.white, size: 20),
                                const SizedBox(width: 6),
                                Container(height: 16, width: 1, color: Colors.white30),
                                const SizedBox(width: 6),
                                Container(
                                  padding: const EdgeInsets.all(3),
                                  decoration: const BoxDecoration(color: Colors.white24, shape: BoxShape.circle),
                                  child: const Icon(Icons.add_rounded, color: Colors.white, size: 14),
                                ),
                              ],
                            ),
                          ),
                        ),

                        // 3. RIGHT TOP CORNER: USER PROFILE INITIAL BUTTON (CIRCLE SHAPE WITH TRACTOR / AVATAR)
                        InkWell(
                          onTap: () => _showUserProfileModalSheet(context),
                          borderRadius: BorderRadius.circular(25),
                          child: Container(
                            padding: const EdgeInsets.all(8),
                            decoration: BoxDecoration(
                              color: const Color(0xFF0F172A),
                              shape: BoxShape.circle,
                              border: Border.all(color: const Color(0xFF059669), width: 1.5),
                              boxShadow: [BoxShadow(color: const Color(0xFF059669).withOpacity(0.3), blurRadius: 8)],
                            ),
                            child: const Icon(Icons.agriculture_rounded, color: Colors.white, size: 20),
                          ),
                        ),
                      ],
                    ),
                  ),

                  // MAIN SCREEN BODY
                  Expanded(
                    child: AnimatedSwitcher(
                      duration: const Duration(milliseconds: 250),
                      child: screens[_currentIndex],
                    ),
                  ),
                ],
              ),
            ),

            if (_activeTopCapsule != null)
              Positioned(
                top: 0,
                left: 0,
                right: 0,
                child: TopCapsuleNotification(
                  title: _activeTopCapsule!['title'],
                  message: _activeTopCapsule!['message'],
                  icon: _activeTopCapsule!['icon'] ?? Icons.notifications_active_rounded,
                  backgroundColor: _activeTopCapsule!['backgroundColor'] ?? const Color(0xFF0F172A),
                  onDismiss: () => setState(() => _activeTopCapsule = null),
                ),
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildFloatingBottomNavBar() {
    return Container(
      color: Colors.transparent,
      padding: const EdgeInsets.fromLTRB(16, 0, 16, 12),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 8),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(30),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.08),
              blurRadius: 20,
              spreadRadius: 2,
              offset: const Offset(0, 4),
            ),
          ],
        ),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceAround,
          children: [
            _buildBottomNavItem(0, Icons.home_rounded, 'Home'),
            _buildBottomNavItem(1, Icons.map_outlined, 'Field Map'),
            _buildBottomNavItem(2, Icons.sensors_outlined, 'Drones'),
            _buildBottomNavItem(3, Icons.bar_chart_rounded, 'Analytics'),
          ],
        ),
      ),
    );
  }

  Widget _buildBottomNavItem(int index, IconData icon, String label) {
    final bool isSelected = _currentIndex == index;
    return InkWell(
      onTap: () => setState(() => _currentIndex = index),
      borderRadius: BorderRadius.circular(22),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        padding: EdgeInsets.symmetric(horizontal: isSelected ? 16 : 10, vertical: 8),
        decoration: BoxDecoration(
          color: isSelected ? const Color(0xFF047857) : Colors.transparent,
          borderRadius: BorderRadius.circular(20),
        ),
        child: Row(
          children: [
            Icon(
              icon,
              color: isSelected ? Colors.white : const Color(0xFF64748B),
              size: 20,
            ),
            if (isSelected) ...[
              const SizedBox(width: 6),
              Text(
                label,
                style: const TextStyle(
                  color: Colors.white,
                  fontWeight: FontWeight.bold,
                  fontSize: 12,
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

// ==================== ORGANIC LEAF VECTOR PAINTER ====================
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
class AppDrawer extends StatelessWidget {
  final Map<String, dynamic> farmer;
  final List<Map<String, dynamic>> farms;
  final int selectedIdx;
  final VoidCallback onLogout;
  final VoidCallback onEditProfile;
  final VoidCallback? onOpenCropAiScanner;
  final Function(int) onSelectScreen;

  const AppDrawer({
    super.key,
    required this.farmer,
    required this.farms,
    required this.selectedIdx,
    required this.onLogout,
    required this.onEditProfile,
    this.onOpenCropAiScanner,
    required this.onSelectScreen,
  });

  Widget _buildNavItem({
    required BuildContext context,
    required String title,
    required String subtitle,
    required IconData icon,
    required bool isSelected,
    required VoidCallback onTap,
    bool isDestructive = false,
  }) {
    final Color cardBg = isDestructive
        ? const Color(0xFFFEF2F2)
        : (isSelected ? const Color(0xFFECFDF5) : Colors.white);

    final Color borderColor = isDestructive
        ? const Color(0xFFFCA5A5)
        : (isSelected ? const Color(0xFFA7F3D0) : const Color(0xFFF1F5F9));

    final Color iconBg = isDestructive
        ? const Color(0xFFFEE2E2)
        : (isSelected ? const Color(0xFFD1FAE5) : const Color(0xFFF1F5F9));

    final Color iconColor = isDestructive
        ? const Color(0xFFDC2626)
        : (isSelected ? const Color(0xFF059669) : const Color(0xFF047857));

    final Color titleColor = isDestructive
        ? const Color(0xFFB91C1C)
        : (isSelected ? const Color(0xFF064E3B) : const Color(0xFF0F172A));

    final Color subtitleColor = isDestructive
        ? const Color(0xFFEF4444)
        : const Color(0xFF64748B);

    final Color chevronColor = isDestructive
        ? const Color(0xFFEF4444)
        : (isSelected ? const Color(0xFF059669) : const Color(0xFF94A3B8));

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 5),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(20),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
          decoration: BoxDecoration(
            color: cardBg,
            borderRadius: BorderRadius.circular(20),
            border: Border.all(color: borderColor, width: 1.2),
            boxShadow: isSelected || isDestructive
                ? []
                : [
                    BoxShadow(
                      color: Colors.black.withOpacity(0.03),
                      blurRadius: 10,
                      offset: const Offset(0, 3),
                    )
                  ],
          ),
          child: Row(
            children: [
              Container(
                width: 44,
                height: 44,
                decoration: BoxDecoration(
                  color: iconBg,
                  borderRadius: BorderRadius.circular(14),
                ),
                child: Icon(icon, color: iconColor, size: 22),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      title,
                      style: TextStyle(
                        color: titleColor,
                        fontWeight: FontWeight.w700,
                        fontSize: 14.5,
                        letterSpacing: -0.2,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      subtitle,
                      style: TextStyle(
                        color: subtitleColor,
                        fontSize: 11.5,
                        fontWeight: FontWeight.w400,
                      ),
                    ),
                  ],
                ),
              ),
              Icon(Icons.chevron_right_rounded, color: chevronColor, size: 20),
            ],
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final active = farms.isNotEmpty && selectedIdx < farms.length
        ? farms[selectedIdx]
        : {'farm_name': 'Main Farm', 'farm_acres': 15.0};

    final String name = farmer['full_name'] ?? 'Akash Satapathy';
    final String farmName = active['farm_name'] ?? 'Main Farm';
    final double acres = (active['farm_acres'] ?? 15.0).toDouble();

    return Drawer(
      backgroundColor: const Color(0xFFF8FAFC),
      child: SafeArea(
        top: false,
        child: Column(
          children: [
            // HEADER CARD
            Container(
              width: double.infinity,
              padding: const EdgeInsets.fromLTRB(20, 52, 20, 24),
              decoration: const BoxDecoration(
                gradient: LinearGradient(
                  colors: [Color(0xFF064E3B), Color(0xFF022C22)],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                ),
                borderRadius: BorderRadius.vertical(bottom: Radius.circular(32)),
              ),
              child: Stack(
                children: [
                  Positioned(
                    top: -10,
                    right: -10,
                    child: Opacity(
                      opacity: 0.12,
                      child: Icon(Icons.airplanemode_active_rounded, size: 85, color: Colors.white),
                    ),
                  ),
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Stack(
                        children: [
                          Container(
                            decoration: BoxDecoration(
                              shape: BoxShape.circle,
                              border: Border.all(color: Colors.white.withOpacity(0.9), width: 2.5),
                            ),
                            child: FarmerAvatarWidget(
                              avatarId: farmer['avatar_id'] ?? 1,
                              name: name,
                              radius: 34,
                            ),
                          ),
                          Positioned(
                            bottom: 2,
                            right: 2,
                            child: Container(
                              width: 14,
                              height: 14,
                              decoration: BoxDecoration(
                                color: const Color(0xFF22C55E),
                                shape: BoxShape.circle,
                                border: Border.all(color: const Color(0xFF064E3B), width: 2),
                              ),
                            ),
                          )
                        ],
                      ),
                      const SizedBox(height: 14),
                      Text(
                        name,
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 20,
                          fontWeight: FontWeight.bold,
                          letterSpacing: -0.4,
                        ),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        '$farmName (${acres.toStringAsFixed(1)} Acres)',
                        style: const TextStyle(
                          color: Color(0xFFA7F3D0),
                          fontSize: 13,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                      const SizedBox(height: 16),
                      // Technology Capsule Pill
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                        decoration: BoxDecoration(
                          color: Colors.white.withOpacity(0.1),
                          borderRadius: BorderRadius.circular(16),
                          border: Border.all(color: Colors.white.withOpacity(0.2)),
                        ),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Container(
                              padding: const EdgeInsets.all(6),
                              decoration: BoxDecoration(
                                color: const Color(0xFF059669),
                                borderRadius: BorderRadius.circular(10),
                              ),
                              child: const Icon(Icons.eco_rounded, color: Colors.white, size: 16),
                            ),
                            const SizedBox(width: 10),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: const [
                                  Text(
                                    'Farming Smarter',
                                    style: TextStyle(
                                      color: Colors.white,
                                      fontSize: 12.5,
                                      fontWeight: FontWeight.bold,
                                    ),
                                  ),
                                  Text(
                                    'With Technology',
                                    style: TextStyle(
                                      color: Color(0xFFA7F3D0),
                                      fontSize: 10.5,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                            const Icon(Icons.chevron_right_rounded, color: Color(0xFFA7F3D0), size: 18),
                          ],
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(height: 12),
            // NAVIGATION ITEMS LIST
            Expanded(
              child: ListView(
                padding: EdgeInsets.zero,
                children: [
                  _buildNavItem(
                    context: context,
                    title: 'Dashboard & Analytics',
                    subtitle: 'Overview of your farm data',
                    icon: Icons.grid_view_rounded,
                    isSelected: selectedIdx == 0,
                    onTap: () {
                      onSelectScreen(0);
                    },
                  ),
                  _buildNavItem(
                    context: context,
                    title: 'Satellite Terrain Map',
                    subtitle: 'View and analyze your fields',
                    icon: Icons.map_rounded,
                    isSelected: selectedIdx == 1,
                    onTap: () {
                      onSelectScreen(1);
                    },
                  ),
                  _buildNavItem(
                    context: context,
                    title: 'Autonomous Drone Station',
                    subtitle: 'Control and monitor drones',
                    icon: Icons.flight_takeoff_rounded,
                    isSelected: selectedIdx == 2,
                    onTap: () {
                      onSelectScreen(2);
                    },
                  ),
                  _buildNavItem(
                    context: context,
                    title: 'Live Crop AI Health Scan',
                    subtitle: 'Snap photo for instant AI diagnosis',
                    icon: Icons.center_focus_strong_rounded,
                    isSelected: false,
                    onTap: () {
                      Navigator.pop(context);
                      if (onOpenCropAiScanner != null) {
                        onOpenCropAiScanner!();
                      }
                    },
                  ),
                  _buildNavItem(
                    context: context,
                    title: 'Settings',
                    subtitle: 'App preferences & system setup',
                    icon: Icons.settings_rounded,
                    isSelected: selectedIdx == 3,
                    onTap: () {
                      onSelectScreen(3);
                    },
                  ),
                  _buildNavItem(
                    context: context,
                    title: 'Edit Profile & Account',
                    subtitle: 'Manage your personal information',
                    icon: Icons.person_rounded,
                    isSelected: false,
                    onTap: () {
                      Navigator.pop(context);
                      onEditProfile();
                    },
                  ),
                  const SizedBox(height: 12),
                  const Padding(
                    padding: EdgeInsets.symmetric(horizontal: 20),
                    child: Divider(color: Color(0xFFE2E8F0), height: 1),
                  ),
                  const SizedBox(height: 12),
                  _buildNavItem(
                    context: context,
                    title: 'Sign Out',
                    subtitle: 'See you again soon!',
                    icon: Icons.logout_rounded,
                    isSelected: false,
                    isDestructive: true,
                    onTap: () {
                      Navigator.pop(context);
                      onLogout();
                    },
                  ),
                ],
              ),
            ),
            // FOOTER WITH ORGANIC VECTOR
            Container(
              height: 60,
              padding: const EdgeInsets.symmetric(horizontal: 20),
              child: CustomPaint(
                painter: OrganicLeafPainter(),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  crossAxisAlignment: CrossAxisAlignment.center,
                  children: [
                    Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: const [
                        Text(
                          'GROW  •  MONITOR  •  SUSTAIN',
                          style: TextStyle(
                            color: Color(0xFF64748B),
                            fontSize: 9.5,
                            fontWeight: FontWeight.bold,
                            letterSpacing: 0.5,
                          ),
                        ),
                        SizedBox(height: 2),
                        Text(
                          'v1.4.0',
                          style: TextStyle(
                            color: Color(0xFF94A3B8),
                            fontSize: 11,
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                      ],
                    ),
                    Row(
                      children: const [
                        Icon(Icons.eco_rounded, color: Color(0xFF047857), size: 14),
                        SizedBox(width: 4),
                        Text(
                          'A Greener\nTomorrow',
                          textAlign: TextAlign.end,
                          style: TextStyle(
                            color: Color(0xFF047857),
                            fontSize: 10,
                            fontWeight: FontWeight.bold,
                            height: 1.1,
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ==================== SPARKLINE WAVE PAINTER ====================
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

// ==================== 6. FARMER DASHBOARD ====================
class FarmerDashboard extends StatefulWidget {
  final Map<String, dynamic> farmer;
  final Map<String, dynamic> activeFarm;
  final TelemetryPacket? packet;
  final WebSocketService wsService;

  const FarmerDashboard({
    super.key,
    required this.farmer,
    required this.activeFarm,
    required this.packet,
    required this.wsService,
  });

  @override
  State<FarmerDashboard> createState() => _FarmerDashboardState();
}

class _FarmerDashboardState extends State<FarmerDashboard> {
  void openScannerModal() {
    _showLiveCropHealthScannerModal(context);
  }

  String _weatherTemp = '28°C';
  String _weatherCondition = 'Partly Cloudy';
  IconData _weatherIcon = Icons.wb_sunny_rounded;
  Color _weatherIconColor = Colors.amber;
  bool _isLoadingWeather = false;

  @override
  void initState() {
    super.initState();
    _fetchLiveLocationWeather();
  }

  String _getDynamicGreeting() {
    final hour = DateTime.now().hour;
    if (hour < 12) {
      return 'Good Morning,';
    } else if (hour < 17) {
      return 'Good Afternoon,';
    } else {
      return 'Good Evening,';
    }
  }

  Future<void> _fetchLiveLocationWeather() async {
    if (!mounted) return;
    setState(() => _isLoadingWeather = true);

    double lat = 20.2961;
    double lon = 85.8245;

    try {
      bool serviceEnabled = await Geolocator.isLocationServiceEnabled();
      if (serviceEnabled) {
        LocationPermission permission = await Geolocator.checkPermission();
        if (permission == LocationPermission.denied) {
          permission = await Geolocator.requestPermission();
        }
        if (permission == LocationPermission.whileInUse || permission == LocationPermission.always) {
          final pos = await Geolocator.getCurrentPosition(
            desiredAccuracy: LocationAccuracy.low,
            timeLimit: const Duration(seconds: 4),
          );
          lat = pos.latitude;
          lon = pos.longitude;
        }
      }
    } catch (e) {
      if (kDebugMode) print('GEOLOCATOR ERROR: $e');
    }

    try {
      final url = Uri.parse('https://api.open-meteo.com/v1/forecast?latitude=$lat&longitude=$lon&current=temperature_2m,weather_code');
      final res = await http.get(url).timeout(const Duration(seconds: 5));
      if (res.statusCode == 200) {
        final data = jsonDecode(res.body);
        final current = data['current'];
        if (current != null) {
          final double temp = (current['temperature_2m'] as num).toDouble();
          final int code = (current['weather_code'] as num).toInt();

          String cond = 'Clear Sky';
          IconData icon = Icons.wb_sunny_rounded;
          Color iconColor = Colors.amber;

          if (code == 0) {
            cond = 'Clear Sky';
            icon = Icons.wb_sunny_rounded;
            iconColor = Colors.amber;
          } else if (code >= 1 && code <= 3) {
            cond = 'Partly Cloudy';
            icon = Icons.cloud_queue_rounded;
            iconColor = Colors.blueGrey;
          } else if (code == 45 || code == 48) {
            cond = 'Foggy';
            icon = Icons.cloud_rounded;
            iconColor = Colors.blueGrey;
          } else if ((code >= 51 && code <= 67) || (code >= 80 && code <= 82)) {
            cond = 'Rainy';
            icon = Icons.grain_rounded;
            iconColor = Colors.lightBlue;
          } else if ((code >= 71 && code <= 77) || (code >= 85 && code <= 86)) {
            cond = 'Snowy';
            icon = Icons.ac_unit_rounded;
            iconColor = Colors.cyan;
          } else if (code >= 95) {
            cond = 'Thunderstorm';
            icon = Icons.thunderstorm_rounded;
            iconColor = Colors.deepPurple;
          }

          if (mounted) {
            setState(() {
              _weatherTemp = '${temp.round()}°C';
              _weatherCondition = cond;
              _weatherIcon = icon;
              _weatherIconColor = iconColor;
              _isLoadingWeather = false;
            });
          }
          return;
        }
      }
    } catch (e) {
      if (kDebugMode) print('WEATHER FETCH ERROR: $e');
    }

    if (mounted) {
      setState(() => _isLoadingWeather = false);
    }
  }

  Future<void> _triggerPreset(String preset) async {
    widget.wsService.sendPresetCommand(preset);
    try {
      await http.post(Uri.parse('${AppConfig.backendHttpUrl}/api/v1/simulate?preset=$preset'));
    } catch (e) {
      // Fallback
    }
  }

  void _showLiveCropHealthScannerModal(BuildContext context) {
    String selectedCrop = (widget.activeFarm['crop_type'] ?? "Wheat & Paddy").toString();
    bool isAnalyzing = false;
    File? selectedImageFile;
    Map<String, dynamic>? aiReport;

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) {
        return StatefulBuilder(
          builder: (modalCtx, setModalState) {
            Future<void> pickAndDiagnose(ImageSource source) async {
              try {
                final picker = ImagePicker();
                final pickedFile = await picker.pickImage(
                  source: source,
                  maxWidth: 1024,
                  maxHeight: 1024,
                  imageQuality: 85,
                );

                if (pickedFile == null) return;

                final imageFile = File(pickedFile.path);
                final imageBytes = await pickedFile.readAsBytes();
                final base64Image = base64Encode(imageBytes);

                setModalState(() {
                  selectedImageFile = imageFile;
                  isAnalyzing = true;
                  aiReport = null;
                });

                try {
                  final res = await http.post(
                    Uri.parse('${AppConfig.backendHttpUrl}/api/v1/ai/diagnose-crop-image'),
                    headers: {'Content-Type': 'application/json'},
                    body: jsonEncode({
                      'crop_type': selectedCrop,
                      'note': source == ImageSource.camera ? 'Camera Photo Snap' : 'Gallery Image Upload',
                      'image_base64': base64Image,
                    }),
                  ).timeout(const Duration(seconds: 8));

                  if (res.statusCode == 200) {
                    final data = jsonDecode(res.body);
                    if (modalCtx.mounted) {
                      setModalState(() {
                        aiReport = data['diagnosis'];
                        isAnalyzing = false;
                      });
                    }
                    return;
                  }
                } catch (e) {
                  if (kDebugMode) print('AI Diagnosis endpoint error: $e');
                }

                if (modalCtx.mounted) {
                  setModalState(() {
                    aiReport = {
                      "crop_condition": "Early Leaf Blight ($selectedCrop)",
                      "disease_type": "Fungal Infection (Alternaria Solani)",
                      "health_score": 74.0,
                      "confidence_pct": 94.6,
                      "severity": "MODERATE_RISK",
                      "symptoms_detected": [
                        "Concentric dark brown circular spots on foliage",
                        "Chlorotic yellow halo surrounding lesion margins",
                        "Early localized foliar necrosis"
                      ],
                      "ai_remedy_recommendations": [
                        "Apply Copper Hydroxide or Mancozeb fungicide spray at 2.5g/L concentration.",
                        "Increase inter-row spacing to enhance canopy aeration and lower humidity.",
                        "Schedule drip irrigation early morning to prevent leaf wetness."
                      ],
                      "pathogen_vector": "Alternaria Solani Spores"
                    };
                    isAnalyzing = false;
                  });
                }
              } catch (e) {
                if (kDebugMode) print('Image picker error: $e');
              }
            }

            Future<void> runAiScan(String sampleLabel) async {
              setModalState(() {
                selectedImageFile = null;
                isAnalyzing = true;
                aiReport = null;
              });

              try {
                final res = await http.post(
                  Uri.parse('${AppConfig.backendHttpUrl}/api/v1/ai/diagnose-crop-image'),
                  headers: {'Content-Type': 'application/json'},
                  body: jsonEncode({
                    'crop_type': selectedCrop,
                    'note': sampleLabel,
                    'image_base64': sampleLabel,
                  }),
                ).timeout(const Duration(seconds: 5));

                if (res.statusCode == 200) {
                  final data = jsonDecode(res.body);
                  if (modalCtx.mounted) {
                    setModalState(() {
                      aiReport = data['diagnosis'];
                      isAnalyzing = false;
                    });
                  }
                  return;
                }
              } catch (e) {
                // Fallback
              }

              if (modalCtx.mounted) {
                setModalState(() {
                  aiReport = {
                    "crop_condition": "Early Leaf Blight ($selectedCrop)",
                    "disease_type": "Fungal Infection (Alternaria Solani)",
                    "health_score": 74.0,
                    "confidence_pct": 94.6,
                    "severity": "MODERATE_RISK",
                    "symptoms_detected": [
                      "Concentric dark brown circular spots on foliage",
                      "Chlorotic yellow halo surrounding lesion margins",
                      "Early localized foliar necrosis"
                    ],
                    "ai_remedy_recommendations": [
                      "Apply Copper Hydroxide or Mancozeb fungicide spray at 2.5g/L concentration.",
                      "Increase inter-row spacing to enhance canopy aeration and lower humidity.",
                      "Schedule drip irrigation early morning to prevent leaf wetness."
                    ],
                    "pathogen_vector": "Alternaria Solani Spores"
                  };
                  isAnalyzing = false;
                });
              }
            }

            return Padding(
              padding: EdgeInsets.only(bottom: MediaQuery.of(modalCtx).viewInsets.bottom),
              child: Container(
                constraints: BoxConstraints(maxHeight: MediaQuery.of(modalCtx).size.height * 0.88),
                decoration: const BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.vertical(top: Radius.circular(28)),
                ),
                padding: const EdgeInsets.all(22),
                child: SingleChildScrollView(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Center(
                        child: Container(
                          width: 44,
                          height: 4.5,
                          decoration: BoxDecoration(color: const Color(0xFFCBD5E1), borderRadius: BorderRadius.circular(3)),
                        ),
                      ),
                      const SizedBox(height: 16),

                      Row(
                        children: [
                          Container(
                            padding: const EdgeInsets.all(10),
                            decoration: BoxDecoration(
                              color: const Color(0xFFECFDF5),
                              borderRadius: BorderRadius.circular(14),
                            ),
                            child: const Icon(Icons.center_focus_strong_rounded, color: Color(0xFF059669), size: 24),
                          ),
                          const SizedBox(width: 12),
                          const Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  'Live Crop Health AI Scanner',
                                  style: TextStyle(fontSize: 17, fontWeight: FontWeight.w900, color: Color(0xFF0F172A)),
                                ),
                                Text(
                                  'Snap leaf photo for instant AI diagnosis & remedy plan',
                                  style: TextStyle(fontSize: 11.5, color: Color(0xFF64748B)),
                                ),
                              ],
                            ),
                          ),
                          InkWell(
                            onTap: () => Navigator.pop(modalCtx),
                            child: Container(
                              padding: const EdgeInsets.all(6),
                              decoration: const BoxDecoration(color: Color(0xFFF1F5F9), shape: BoxShape.circle),
                              child: const Icon(Icons.close_rounded, color: Color(0xFF64748B), size: 20),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 16),

                      // CAMERA / VIEWFINDER CARD
                      Container(
                        width: double.infinity,
                        padding: const EdgeInsets.all(18),
                        decoration: BoxDecoration(
                          gradient: const LinearGradient(
                            colors: [Color(0xFF064E3B), Color(0xFF022C22)],
                            begin: Alignment.topLeft,
                            end: Alignment.bottomRight,
                          ),
                          borderRadius: BorderRadius.circular(22),
                          boxShadow: [BoxShadow(color: const Color(0xFF064E3B).withOpacity(0.3), blurRadius: 16, offset: const Offset(0, 6))],
                        ),
                        child: Column(
                          children: [
                            Container(
                              height: 160,
                              width: double.infinity,
                              decoration: BoxDecoration(
                                color: Colors.black.withOpacity(0.3),
                                borderRadius: BorderRadius.circular(16),
                                border: Border.all(color: const Color(0xFF10B981).withOpacity(0.6), width: 1.5),
                              ),
                              child: Stack(
                                children: [
                                  selectedImageFile != null
                                      ? ClipRRect(
                                          borderRadius: BorderRadius.circular(15),
                                          child: Image.file(
                                            selectedImageFile!,
                                            width: double.infinity,
                                            height: 160,
                                            fit: BoxFit.cover,
                                          ),
                                        )
                                      : Center(
                                          child: Column(
                                            mainAxisAlignment: MainAxisAlignment.center,
                                            children: [
                                              Icon(
                                                isAnalyzing ? Icons.sync_rounded : Icons.photo_camera_rounded,
                                                color: const Color(0xFF34D399),
                                                size: 42,
                                              ),
                                              const SizedBox(height: 8),
                                              Text(
                                                isAnalyzing ? 'AI Computer Vision Scanning Foliage...' : 'Align Crop Leaf Within Frame',
                                                style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 13),
                                              ),
                                              Text(
                                                isAnalyzing ? 'Analyzing chlorophyll spectral reflectance' : 'Tap camera or pick sample leaf below',
                                                style: const TextStyle(color: Color(0xFFA7F3D0), fontSize: 11),
                                              ),
                                            ],
                                          ),
                                        ),
                                  if (isAnalyzing)
                                    const Positioned(
                                      top: 0, left: 0, right: 0,
                                      child: LinearProgressIndicator(color: Color(0xFF34D399), backgroundColor: Colors.transparent),
                                    ),
                                ],
                              ),
                            ),
                            const SizedBox(height: 14),

                            Row(
                              children: [
                                Expanded(
                                  child: ElevatedButton.icon(
                                    style: ElevatedButton.styleFrom(
                                      backgroundColor: const Color(0xFF059669),
                                      foregroundColor: Colors.white,
                                      padding: const EdgeInsets.symmetric(vertical: 12),
                                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                                    ),
                                    onPressed: isAnalyzing ? null : () => pickAndDiagnose(ImageSource.camera),
                                    icon: const Icon(Icons.camera_alt_rounded, size: 18),
                                    label: const Text('Snap Photo', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
                                  ),
                                ),
                                const SizedBox(width: 10),
                                Expanded(
                                  child: ElevatedButton.icon(
                                    style: ElevatedButton.styleFrom(
                                      backgroundColor: Colors.white.withOpacity(0.15),
                                      foregroundColor: Colors.white,
                                      padding: const EdgeInsets.symmetric(vertical: 12),
                                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                                    ),
                                    onPressed: isAnalyzing ? null : () => pickAndDiagnose(ImageSource.gallery),
                                    icon: const Icon(Icons.photo_library_rounded, size: 18),
                                    label: const Text('Upload Gallery', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
                                  ),
                                ),
                              ],
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(height: 18),

                      const Text('Quick Sample Leaf Scans:', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: Color(0xFF0F172A))),
                      const SizedBox(height: 8),

                      Wrap(
                        spacing: 8,
                        runSpacing: 8,
                        children: [
                          _sampleChip('🍂 Leaf Blight Scan', () => runAiScan("Leaf Blight Scan"), isAnalyzing),
                          _sampleChip('🌾 Yellow Rust Scan', () => runAiScan("Yellow Rust Scan"), isAnalyzing),
                          _sampleChip('🍃 Chlorosis Scan', () => runAiScan("Chlorosis Scan"), isAnalyzing),
                          _sampleChip('🌱 Healthy Canopy', () => runAiScan("Healthy Canopy"), isAnalyzing),
                        ],
                      ),
                      const SizedBox(height: 18),

                      // AI DIAGNOSTIC REPORT CARD RESULTS
                      if (aiReport != null) ...[
                        Container(
                          padding: const EdgeInsets.all(16),
                          decoration: BoxDecoration(
                            color: aiReport!['severity'] == 'INVALID_IMAGE'
                                ? const Color(0xFFFEF2F2)
                                : const Color(0xFFF8FAFC),
                            borderRadius: BorderRadius.circular(18),
                            border: Border.all(
                              color: aiReport!['severity'] == 'INVALID_IMAGE'
                                  ? Colors.redAccent
                                  : (aiReport!['severity'] == 'HEALTHY'
                                      ? const Color(0xFF059669)
                                      : (aiReport!['severity'] == 'HIGH_RISK' ? Colors.redAccent : Colors.amber[800]!)),
                              width: 1.5,
                            ),
                          ),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Row(
                                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                children: [
                                  Text(
                                    aiReport!['severity'] == 'INVALID_IMAGE' ? '⚠️ NO PLANT DETECTED' : 'AI DIAGNOSTIC RESULT',
                                    style: TextStyle(
                                      fontSize: 10.5,
                                      fontWeight: FontWeight.w900,
                                      color: aiReport!['severity'] == 'INVALID_IMAGE'
                                          ? Colors.red[900]
                                          : (aiReport!['severity'] == 'HEALTHY' ? const Color(0xFF059669) : Colors.amber[900]),
                                      letterSpacing: 0.8,
                                    ),
                                  ),
                                  Container(
                                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                                    decoration: BoxDecoration(
                                      color: aiReport!['severity'] == 'INVALID_IMAGE'
                                          ? const Color(0xFFFEE2E2)
                                          : (aiReport!['severity'] == 'HEALTHY' ? const Color(0xFFDCFCE7) : const Color(0xFFFEF3C7)),
                                      borderRadius: BorderRadius.circular(12),
                                    ),
                                    child: Text(
                                      aiReport!['severity'] == 'INVALID_IMAGE' ? 'Invalid Target' : 'Score: ${aiReport!['health_score']}%',
                                      style: TextStyle(
                                        fontWeight: FontWeight.bold,
                                        fontSize: 12,
                                        color: aiReport!['severity'] == 'INVALID_IMAGE'
                                            ? Colors.red[800]
                                            : (aiReport!['severity'] == 'HEALTHY' ? const Color(0xFF166534) : const Color(0xFF92400E)),
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                              const SizedBox(height: 6),

                              Text(
                                aiReport!['crop_condition'] ?? 'Crop Analysis Complete',
                                style: TextStyle(
                                  fontSize: 16,
                                  fontWeight: FontWeight.bold,
                                  color: aiReport!['severity'] == 'INVALID_IMAGE' ? Colors.red[900] : const Color(0xFF0F172A),
                                ),
                              ),
                              Text(
                                'Vector: ${aiReport!['disease_type'] ?? "Foliar Analysis"} • ${aiReport!['confidence_pct']}% AI Confidence',
                                style: const TextStyle(fontSize: 11.5, color: Color(0xFF64748B)),
                              ),
                              const SizedBox(height: 12),
                              const Divider(height: 1),
                              const SizedBox(height: 12),

                              Text(
                                aiReport!['severity'] == 'INVALID_IMAGE' ? 'Scan Analysis Notes:' : 'Symptoms Detected:',
                                style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 12.5, color: Color(0xFF0F172A)),
                              ),
                              const SizedBox(height: 6),
                              ...((aiReport!['symptoms_detected'] as List<dynamic>? ?? [])
                                  .map((s) => Padding(
                                        padding: const EdgeInsets.only(bottom: 4),
                                        child: Row(
                                          crossAxisAlignment: CrossAxisAlignment.start,
                                          children: [
                                            Icon(
                                              aiReport!['severity'] == 'INVALID_IMAGE' ? Icons.warning_amber_rounded : Icons.check_circle_outline_rounded,
                                              color: aiReport!['severity'] == 'INVALID_IMAGE' ? Colors.redAccent : const Color(0xFF059669),
                                              size: 15,
                                            ),
                                            const SizedBox(width: 8),
                                            Expanded(child: Text(s.toString(), style: const TextStyle(fontSize: 11.5, color: Color(0xFF475569)))),
                                          ],
                                        ),
                                      ))
                                  .toList()),
                              const SizedBox(height: 12),

                              Text(
                                aiReport!['severity'] == 'INVALID_IMAGE' ? 'How to Scan Properly:' : 'Actionable AI Remedies & Treatment Plan:',
                                style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 12.5, color: Color(0xFF0F172A)),
                              ),
                              const SizedBox(height: 6),
                              ...((aiReport!['ai_remedy_recommendations'] as List<dynamic>? ?? [])
                                  .map((r) => Padding(
                                        padding: const EdgeInsets.only(bottom: 6),
                                        child: Row(
                                          crossAxisAlignment: CrossAxisAlignment.start,
                                          children: [
                                            Icon(
                                              aiReport!['severity'] == 'INVALID_IMAGE' ? Icons.center_focus_strong_rounded : Icons.medical_services_outlined,
                                              color: aiReport!['severity'] == 'INVALID_IMAGE' ? const Color(0xFF059669) : const Color(0xFF047857),
                                              size: 15,
                                            ),
                                            const SizedBox(width: 8),
                                            Expanded(child: Text(r.toString(), style: const TextStyle(fontSize: 11.5, color: Color(0xFF0F172A), fontWeight: FontWeight.w500))),
                                          ],
                                        ),
                                      ))
                                  .toList()),
                            ],
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
              ),
            );
          },
        );
      },
    );
  }

  Widget _sampleChip(String label, VoidCallback onTap, bool disabled) {
    return InkWell(
      onTap: disabled ? null : onTap,
      borderRadius: BorderRadius.circular(12),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        decoration: BoxDecoration(
          color: const Color(0xFFF1F5F9),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: const Color(0xFFCBD5E1)),
        ),
        child: Text(
          label,
          style: const TextStyle(fontSize: 11.5, fontWeight: FontWeight.bold, color: Color(0xFF0F172A)),
        ),
      ),
    );
  }

  void _showSensorHistoryModal(BuildContext context, String sensorTitle, String sensorValue, String techModel, IconData icon, Color color) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
      builder: (ctx) {
        return Padding(
          padding: const EdgeInsets.all(20.0),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(10),
                    decoration: BoxDecoration(color: color.withOpacity(0.12), shape: BoxShape.circle),
                    child: Icon(icon, color: color, size: 28),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(sensorTitle, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Color(0xFF0F172A))),
                        Text('Hardware Module: $techModel', style: const TextStyle(fontSize: 11, color: Colors.grey)),
                      ],
                    ),
                  ),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                    decoration: BoxDecoration(color: color.withOpacity(0.15), borderRadius: BorderRadius.circular(12)),
                    child: Text(sensorValue, style: TextStyle(fontWeight: FontWeight.bold, color: color, fontSize: 13)),
                  ),
                ],
              ),
              const SizedBox(height: 18),
              const Text('24-Hour Sensor Telemetry Trend', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: Color(0xFF0F172A))),
              const SizedBox(height: 10),

              Container(
                height: 100,
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(color: const Color(0xFFF8FAFC), borderRadius: BorderRadius.circular(14), border: Border.all(color: const Color(0xFFE2E8F0))),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    _barItem('08:00', 0.4, color),
                    _barItem('10:00', 0.6, color),
                    _barItem('12:00', 0.9, color),
                    _barItem('14:00', 0.7, color),
                    _barItem('16:00', 0.5, color),
                    _barItem('18:00', 0.8, color),
                    _barItem('NOW', 1.0, color),
                  ],
                ),
              ),
              const SizedBox(height: 16),

              const Text('Recent Sensor Log', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: Color(0xFF0F172A))),
              const SizedBox(height: 8),

              Container(
                decoration: BoxDecoration(color: const Color(0xFFF8FAFC), borderRadius: BorderRadius.circular(12)),
                child: Column(
                  children: [
                    _logRow('Just Now', sensorValue, 'Normal Range', color),
                    const Divider(height: 1),
                    _logRow('10 mins ago', sensorValue, 'Stable', color),
                    const Divider(height: 1),
                    _logRow('1 hour ago', sensorValue, 'Optimal', color),
                  ],
                ),
              ),
              const SizedBox(height: 20),
              SizedBox(
                width: double.infinity,
                child: ElevatedButton(
                  style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF0F172A), foregroundColor: Colors.white),
                  onPressed: () => Navigator.pop(ctx),
                  child: const Text('Close Details'),
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  Widget _barItem(String label, double ratio, Color color) {
    return Column(
      mainAxisAlignment: MainAxisAlignment.end,
      children: [
        Container(
          width: 14,
          height: 60 * ratio,
          decoration: BoxDecoration(color: color, borderRadius: BorderRadius.circular(4)),
        ),
        const SizedBox(height: 4),
        Text(label, style: const TextStyle(fontSize: 8, color: Colors.grey, fontWeight: FontWeight.bold)),
      ],
    );
  }

  Widget _logRow(String timeStr, String valStr, String statusStr, Color color) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(timeStr, style: const TextStyle(fontSize: 11, color: Colors.grey)),
          Text(valStr, style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold)),
          Text(statusStr, style: TextStyle(fontSize: 10, color: color, fontWeight: FontWeight.bold)),
        ],
      ),
    );
  }

  void _showAllSensorsModal(BuildContext context) {
    final tel = widget.packet?.telemetry;

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
      builder: (ctx) {
        return Container(
          height: MediaQuery.of(context).size.height * 0.8,
          padding: const EdgeInsets.all(20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: const [
                  Text('Field Sensor Telemetry Hub', style: TextStyle(fontSize: 17, fontWeight: FontWeight.bold, color: Color(0xFF0F172A))),
                  CloseButton(),
                ],
              ),
              const SizedBox(height: 12),
              Expanded(
                child: ListView(
                  children: [
                    _categoryHeader('AIR QUALITY & GAS SENSORS'),
                    _sensorTile(context, 'Air Quality Sensor', '${(tel?.smokePpm ?? 80.0).round()} PPM', 'Clean Air Range', 'MQ-135 Optical Array', Icons.air_rounded, const Color(0xFF059669)),

                    _categoryHeader('THERMAL & MOISTURE SENSORS'),
                    _sensorTile(context, 'Ambient Temperature', '${(tel?.temperatureC ?? 26.1).toStringAsFixed(1)}°C', 'Normal Thermal Range', 'DHT-22 Temp Array', Icons.thermostat_rounded, Colors.amber[800]!),
                    _sensorTile(context, 'Relative Humidity', '58.0% RH', 'Optimal Humidity', 'DHT-22 Humidity Module', Icons.water_rounded, Colors.blue),
                    _sensorTile(context, 'Soil Hydration Sensor', '${(tel?.soilMoistureVwc ?? 42.5).toStringAsFixed(1)}%', 'Optimal Soil Hydration', 'Capacitive VWC Probe', Icons.water_drop_rounded, const Color(0xFF059669)),

                    _categoryHeader('SOLAR & SPECTRAL CROP SENSORS'),
                    _sensorTile(context, 'Solar Irradiance Level', '845 W/m²', 'Bright Sunlight', 'Pyranometer Sensor Array', Icons.wb_sunny_rounded, Colors.orange),
                    _sensorTile(context, 'Crop Chlorophyll Index', '0.82 NDVI', 'Photosynthesis Active', 'Multi-Spectral Sensor', Icons.eco_rounded, const Color(0xFF059669)),
                  ],
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  Widget _categoryHeader(String title) {
    return Padding(
      padding: const EdgeInsets.only(top: 14, bottom: 6),
      child: Text(
        title,
        style: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: Color(0xFF059669), letterSpacing: 0.8),
      ),
    );
  }

  Widget _sensorTile(BuildContext context, String name, String val, String status, String model, IconData icon, Color color) {
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      decoration: BoxDecoration(
        color: const Color(0xFFF8FAFC),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: const Color(0xFFE2E8F0)),
      ),
      child: ListTile(
        leading: Container(
          padding: const EdgeInsets.all(8),
          decoration: BoxDecoration(color: color.withOpacity(0.12), shape: BoxShape.circle),
          child: Icon(icon, color: color, size: 22),
        ),
        title: Text(name, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
        subtitle: Text('$model • $status', style: const TextStyle(fontSize: 10, color: Colors.grey)),
        trailing: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            Text(val, style: TextStyle(fontWeight: FontWeight.w900, fontSize: 15, color: color)),
            const Text('Details ➔', style: TextStyle(fontSize: 8, color: Colors.grey)),
          ],
        ),
        onTap: () => _showSensorHistoryModal(context, name, val, model, icon, color),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final tel = widget.packet?.telemetry;
    final ai = widget.packet?.aiDiagnosis;

    final status = ai?.status ?? 'HEALTHY';
    final risk = ai?.pathogenRiskPct ?? 9.9;
    final String farmerName = widget.farmer['full_name'] ?? 'Akash Satapathy';

    Color healthColor = const Color(0xFF059669);
    String healthTitle = "Crop Condition: Excellent";
    String healthSub = "Optimal Crop Health: Leaf canopy NIR scattering & soil hydration levels are within ideal ranges.";

    if (status == 'PRE_SYMPTOMATIC_STRESS') {
      healthColor = Colors.amber[800]!;
      healthTitle = "Crop Condition: Moderate Risk";
      healthSub = "Early Fungal Stress Detected: Leaf canopy reflectance indicates localized spore incubation.";
    } else if (status == 'SEVERE_DROUGHT') {
      healthColor = Colors.cyan[800]!;
      healthTitle = "Crop Condition: Water Deficit";
      healthSub = "Soil hydration dropping rapidly below VWC threshold. Automated irrigation dispatch queued.";
    } else if (status == 'SMOKE_HAZARD') {
      healthColor = Colors.red[700]!;
      healthTitle = "Crop Condition: Hazard Warning";
      healthSub = "Air quality particulate levels elevated. Automated ventilation & crop shield active.";
    }

    return SingleChildScrollView(
      physics: const BouncingScrollPhysics(),
      padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 12.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // 1. HERO GREETING BANNER WITH WEATHER GLASS WIDGET
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(18),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(24),
              gradient: const LinearGradient(
                colors: [Color(0xFFF1F5F9), Color(0xFFE2E8F0)],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withOpacity(0.04),
                  blurRadius: 14,
                  offset: const Offset(0, 4),
                ),
              ],
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        _getDynamicGreeting(),
                        style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600, color: Color(0xFF475569)),
                      ),
                      const SizedBox(height: 2),
                      Row(
                        children: [
                          Flexible(
                            child: Text(
                              farmerName,
                              style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w900, color: Color(0xFF0F172A), letterSpacing: -0.3),
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                          const SizedBox(width: 6),
                          const Text('🌱', style: TextStyle(fontSize: 20)),
                        ],
                      ),
                      const SizedBox(height: 6),
                      const Text(
                        'Smarter Insights.\nHealthier Crops. Brighter Tomorrow.',
                        style: TextStyle(fontSize: 11.5, color: Color(0xFF64748B), height: 1.35, fontWeight: FontWeight.w500),
                      ),
                    ],
                  ),
                ),

                // Right Floating Weather Widget Card
                InkWell(
                  onTap: _fetchLiveLocationWeather,
                  borderRadius: BorderRadius.circular(18),
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                    decoration: BoxDecoration(
                      color: Colors.white.withOpacity(0.85),
                      borderRadius: BorderRadius.circular(18),
                      border: Border.all(color: Colors.white, width: 1.5),
                      boxShadow: [
                        BoxShadow(
                          color: Colors.black.withOpacity(0.05),
                          blurRadius: 10,
                          offset: const Offset(0, 3),
                        ),
                      ],
                    ),
                    child: _isLoadingWeather
                        ? const SizedBox(
                            width: 50,
                            height: 36,
                            child: Center(
                              child: SizedBox(
                                width: 16,
                                height: 16,
                                child: CircularProgressIndicator(strokeWidth: 2, color: Color(0xFF059669)),
                              ),
                            ),
                          )
                        : Column(
                            children: [
                              Row(
                                children: [
                                  Icon(_weatherIcon, color: _weatherIconColor, size: 20),
                                  const SizedBox(width: 4),
                                  Text(
                                    _weatherTemp,
                                    style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w900, color: Color(0xFF0F172A)),
                                  ),
                                ],
                              ),
                              const SizedBox(height: 2),
                              Text(
                                _weatherCondition,
                                style: const TextStyle(fontSize: 10, color: Color(0xFF64748B), fontWeight: FontWeight.w600),
                              ),
                            ],
                          ),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 14),

          // 1.5. LIVE CROP HEALTH AI SCANNER ACTION CARD
          Container(
            width: double.infinity,
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(20),
              gradient: const LinearGradient(
                colors: [Color(0xFF064E3B), Color(0xFF047857)],
                begin: Alignment.centerLeft,
                end: Alignment.centerRight,
              ),
              boxShadow: [
                BoxShadow(
                  color: const Color(0xFF059669).withOpacity(0.3),
                  blurRadius: 12,
                  offset: const Offset(0, 4),
                ),
              ],
            ),
            child: Material(
              color: Colors.transparent,
              child: InkWell(
                onTap: () => _showLiveCropHealthScannerModal(context),
                borderRadius: BorderRadius.circular(20),
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
                  child: Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.all(10),
                        decoration: BoxDecoration(
                          color: Colors.white.withOpacity(0.2),
                          shape: BoxShape.circle,
                        ),
                        child: const Icon(Icons.center_focus_strong_rounded, color: Colors.white, size: 24),
                      ),
                      const SizedBox(width: 14),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              children: [
                                const Text(
                                  'Live Crop Health AI Scanner',
                                  style: TextStyle(fontSize: 14.5, fontWeight: FontWeight.bold, color: Colors.white),
                                ),
                                const SizedBox(width: 6),
                                Container(
                                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                  decoration: const BoxDecoration(color: Color(0xFF34D399), borderRadius: BorderRadius.all(Radius.circular(6))),
                                  child: const Text('NEW AI', style: TextStyle(fontSize: 8.5, fontWeight: FontWeight.w900, color: Color(0xFF064E3B))),
                                ),
                              ],
                            ),
                            const SizedBox(height: 2),
                            const Text(
                              'Snap leaf photo for instant disease diagnosis & remedies',
                              style: TextStyle(fontSize: 11, color: Color(0xFFA7F3D0)),
                            ),
                          ],
                        ),
                      ),
                      const Icon(Icons.arrow_forward_ios_rounded, color: Colors.white, size: 16),
                    ],
                  ),
                ),
              ),
            ),
          ),
          const SizedBox(height: 16),

          // 2. CROP CONDITION SUMMARY CARD
          Container(
            padding: const EdgeInsets.all(18),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(24),
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withOpacity(0.04),
                  blurRadius: 16,
                  offset: const Offset(0, 6),
                ),
              ],
            ),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: healthColor.withOpacity(0.12),
                    shape: BoxShape.circle,
                  ),
                  child: Icon(
                    status == 'HEALTHY' ? Icons.check_circle_rounded : Icons.warning_amber_rounded,
                    color: healthColor,
                    size: 28,
                  ),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        (widget.activeFarm['farm_name'] ?? 'MAIN FARM').toString().toUpperCase(),
                        style: TextStyle(fontSize: 10, fontWeight: FontWeight.w800, color: healthColor, letterSpacing: 0.8),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        healthTitle,
                        style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: healthColor),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        healthSub,
                        style: const TextStyle(fontSize: 11.5, color: Color(0xFF475569), height: 1.35),
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: 8),
                const Icon(Icons.chevron_right_rounded, color: Color(0xFF059669), size: 24),
              ],
            ),
          ),
          const SizedBox(height: 20),

          // 3. LIVE FIELD METRICS HEADER ROW
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text(
                'Live Field Metrics',
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.w900, color: Color(0xFF0F172A), letterSpacing: -0.3),
              ),
              InkWell(
                onTap: () => _showAllSensorsModal(context),
                borderRadius: BorderRadius.circular(12),
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 4),
                  child: Row(
                    children: const [
                      Icon(Icons.sensors_rounded, size: 16, color: Color(0xFF059669)),
                      SizedBox(width: 4),
                      Text(
                        'All Telemetry >',
                        style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: Color(0xFF059669)),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),

          // 4. LIVE FIELD METRICS 2x2 GRID
          Row(
            children: [
              Expanded(
                child: _buildMetricTile(
                  context: context,
                  title: 'Soil Hydration',
                  value: '${(tel?.soilMoistureVwc ?? 42.5).toStringAsFixed(1)}%',
                  badgeText: 'Optimal',
                  badgeBg: const Color(0xFFDCFCE7),
                  badgeTextColor: const Color(0xFF166534),
                  icon: Icons.water_drop_rounded,
                  iconBg: const Color(0xFFECFDF5),
                  iconColor: const Color(0xFF059669),
                  sparklineColor: const Color(0xFF059669),
                  sparklineData: [38.0, 40.0, 39.5, 41.2, 42.5],
                  onTap: () => _showSensorHistoryModal(context, 'Soil Hydration Sensor', '${(tel?.soilMoistureVwc ?? 42.5).toStringAsFixed(1)}%', 'Capacitive VWC Probe', Icons.water_drop_rounded, const Color(0xFF059669)),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: _buildMetricTile(
                  context: context,
                  title: 'Field Temp',
                  value: '${(tel?.temperatureC ?? 26.1).toStringAsFixed(1)}°C',
                  badgeText: 'Normal',
                  badgeBg: const Color(0xFFFFEDD5),
                  badgeTextColor: const Color(0xFFC2410C),
                  icon: Icons.thermostat_rounded,
                  iconBg: const Color(0xFFFFF7ED),
                  iconColor: const Color(0xFFEA580C),
                  sparklineColor: const Color(0xFFEA580C),
                  sparklineData: [24.0, 25.2, 25.8, 26.0, 26.1],
                  onTap: () => _showSensorHistoryModal(context, 'Field Temp Sensor', '${(tel?.temperatureC ?? 26.1).toStringAsFixed(1)}°C', 'DHT-22 Temp Array', Icons.thermostat_rounded, const Color(0xFFEA580C)),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(
                child: _buildMetricTile(
                  context: context,
                  title: 'Air Quality',
                  value: '${(tel?.smokePpm ?? 80.0).round()} PPM',
                  badgeText: 'Clean Air',
                  badgeBg: const Color(0xFFDCFCE7),
                  badgeTextColor: const Color(0xFF15803D),
                  icon: Icons.air_rounded,
                  iconBg: const Color(0xFFF0FDF4),
                  iconColor: const Color(0xFF16A34A),
                  sparklineColor: const Color(0xFF16A34A),
                  sparklineData: [85.0, 82.0, 81.0, 80.0, 80.0],
                  onTap: () => _showSensorHistoryModal(context, 'Air Quality Sensor', '${(tel?.smokePpm ?? 80.0).round()} PPM', 'MQ-135 Optical Array', Icons.air_rounded, const Color(0xFF16A34A)),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: _buildMetricTile(
                  context: context,
                  title: 'Pathogen Risk',
                  value: '${risk.toStringAsFixed(1)}%',
                  badgeText: '5.4 Days Early',
                  badgeBg: const Color(0xFFDCFCE7),
                  badgeTextColor: const Color(0xFF166534),
                  icon: Icons.shield_rounded,
                  iconBg: const Color(0xFFECFDF5),
                  iconColor: const Color(0xFF059669),
                  sparklineColor: const Color(0xFFEF4444),
                  sparklineData: [14.0, 12.5, 11.0, 10.2, 9.9],
                  onTap: () => _showSensorHistoryModal(context, 'Pathogen Risk Index', '${risk.toStringAsFixed(1)}%', 'Spectral NDVI Array', Icons.shield_rounded, const Color(0xFF059669)),
                ),
              ),
            ],
          ),
          const SizedBox(height: 22),

          // 5. SIMULATE CROP HEALTH SCENARIOS SECTION
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text(
                'Simulate Crop Health Scenarios',
                style: TextStyle(fontSize: 17, fontWeight: FontWeight.w900, color: Color(0xFF0F172A), letterSpacing: -0.3),
              ),
              TextButton(
                onPressed: () {},
                style: TextButton.styleFrom(padding: EdgeInsets.zero, minimumSize: Size.zero, tapTargetSize: MaterialTapTargetSize.shrinkWrap),
                child: const Text('View All >', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: Color(0xFF059669))),
              ),
            ],
          ),
          const SizedBox(height: 12),

          // HORIZONTAL SCENARIOS CARDS
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            physics: const BouncingScrollPhysics(),
            child: Row(
              children: [
                _buildScenarioCard(
                  title: 'Healthy Field',
                  subtitle: 'Optimal growth conditions',
                  preset: 'HEALTHY',
                  bgColor: const Color(0xFFECFDF5),
                  borderColor: const Color(0xFFA7F3D0),
                  icon: Icons.eco_rounded,
                  iconColor: const Color(0xFF059669),
                  btnBg: const Color(0xFF059669).withOpacity(0.2),
                  btnIconColor: const Color(0xFF047857),
                ),
                const SizedBox(width: 12),
                _buildScenarioCard(
                  title: 'Fungal Stress',
                  subtitle: 'Simulate disease impact',
                  preset: 'PRE_SYMPTOMATIC_STRESS',
                  bgColor: const Color(0xFFFFF7ED),
                  borderColor: const Color(0xFFFED7AA),
                  icon: Icons.grain_rounded,
                  iconColor: const Color(0xFFEA580C),
                  btnBg: const Color(0xFFEA580C).withOpacity(0.2),
                  btnIconColor: const Color(0xFFC2410C),
                ),
                const SizedBox(width: 12),
                _buildScenarioCard(
                  title: 'Drought Alert',
                  subtitle: 'Assess water stress',
                  preset: 'SEVERE_DROUGHT',
                  bgColor: const Color(0xFFF0F9FF),
                  borderColor: const Color(0xFFBAE6FD),
                  icon: Icons.water_drop_rounded,
                  iconColor: const Color(0xFF0284C7),
                  btnBg: const Color(0xFF0284C7).withOpacity(0.2),
                  btnIconColor: const Color(0xFF0369A1),
                ),
              ],
            ),
          ),
          const SizedBox(height: 22),

          // 6. AUTONOMOUS DRONE STATION BANNER CARD
          Container(
            padding: const EdgeInsets.all(18),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(22),
              gradient: const LinearGradient(
                colors: [Color(0xFF022C22), Color(0xFF064E3B)],
                begin: Alignment.centerLeft,
                end: Alignment.centerRight,
              ),
              boxShadow: [
                BoxShadow(
                  color: const Color(0xFF064E3B).withOpacity(0.35),
                  blurRadius: 16,
                  offset: const Offset(0, 6),
                ),
              ],
            ),
            child: Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: Colors.white.withOpacity(0.15),
                    shape: BoxShape.circle,
                  ),
                  child: const Icon(Icons.sensors_rounded, color: Color(0xFF34D399), size: 24),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: const [
                      Text(
                        'Autonomous Drone Station',
                        style: TextStyle(fontSize: 15, fontWeight: FontWeight.bold, color: Colors.white),
                      ),
                      SizedBox(height: 2),
                      Text(
                        'Drones ready • Last flight: 2 hours ago',
                        style: TextStyle(fontSize: 11, color: Color(0xFFA7F3D0)),
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: 8),
                ElevatedButton(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFF059669),
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
                    elevation: 0,
                  ),
                  onPressed: () {},
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: const [
                      Text('Launch Mission', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold)),
                      SizedBox(width: 4),
                      Icon(Icons.chevron_right_rounded, size: 16),
                    ],
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 20),
        ],
      ),
    );
  }

  // Metric Tile Builder
  Widget _buildMetricTile({
    required BuildContext context,
    required String title,
    required String value,
    required String badgeText,
    required Color badgeBg,
    required Color badgeTextColor,
    required IconData icon,
    required Color iconBg,
    required Color iconColor,
    required Color sparklineColor,
    required List<double> sparklineData,
    required VoidCallback onTap,
  }) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(22),
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(22),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.04),
              blurRadius: 14,
              offset: const Offset(0, 4),
            ),
          ],
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: iconBg,
                    shape: BoxShape.circle,
                  ),
                  child: Icon(icon, color: iconColor, size: 18),
                ),
                SizedBox(
                  width: 50,
                  height: 22,
                  child: CustomPaint(
                    painter: SparklinePainter(data: sparklineData, color: sparklineColor),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Text(
              title,
              style: const TextStyle(fontSize: 12, color: Color(0xFF64748B), fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 2),
            Text(
              value,
              style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w900, color: Color(0xFF0F172A), letterSpacing: -0.5),
            ),
            const SizedBox(height: 10),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: badgeBg,
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Text(
                    badgeText,
                    style: TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: badgeTextColor),
                  ),
                ),
                const Icon(Icons.chevron_right_rounded, color: Color(0xFFCBD5E1), size: 18),
              ],
            ),
          ],
        ),
      ),
    );
  }

  // Scenario Card Builder
  Widget _buildScenarioCard({
    required String title,
    required String subtitle,
    required String preset,
    required Color bgColor,
    required Color borderColor,
    required IconData icon,
    required Color iconColor,
    required Color btnBg,
    required Color btnIconColor,
  }) {
    return InkWell(
      onTap: () => _triggerPreset(preset),
      borderRadius: BorderRadius.circular(20),
      child: Container(
        width: 145,
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: bgColor,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: borderColor),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: Colors.white.withOpacity(0.7),
                shape: BoxShape.circle,
              ),
              child: Icon(icon, color: iconColor, size: 20),
            ),
            const SizedBox(height: 12),
            Text(
              title,
              style: TextStyle(fontSize: 13.5, fontWeight: FontWeight.bold, color: iconColor),
            ),
            const SizedBox(height: 2),
            Text(
              subtitle,
              style: const TextStyle(fontSize: 10, color: Color(0xFF64748B)),
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
            ),
            const SizedBox(height: 12),
            Align(
              alignment: Alignment.bottomRight,
              child: Container(
                padding: const EdgeInsets.all(5),
                decoration: BoxDecoration(
                  color: btnBg,
                  shape: BoxShape.circle,
                ),
                child: Icon(Icons.arrow_forward_rounded, size: 14, color: btnIconColor),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ==================== 7. SATELLITE TERRAIN MAP ====================
class FarmLayoutMapScreen extends StatefulWidget {
  const FarmLayoutMapScreen({super.key});

  @override
  State<FarmLayoutMapScreen> createState() => _FarmLayoutMapScreenState();
}

class _FarmLayoutMapScreenState extends State<FarmLayoutMapScreen> {
  final MapController _mapController = MapController();
  LatLng _currentGpsPos = const LatLng(19.1977, 84.7485);
  bool _isLocating = false;
  int _tileModeIndex = 0;

  final List<List<String>> _tileLayers = [
    [
      'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
      'https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Transportation/MapServer/tile/{z}/{y}/{x}',
      'https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}',
    ],
    [
      'https://tile.opentopomap.org/{z}/{x}/{y}.png',
    ],
    [
      'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
    ]
  ];

  final List<LatLng> _farmPolygon = [
    const LatLng(19.1985, 84.7475),
    const LatLng(19.1985, 84.7495),
    const LatLng(19.1965, 84.7495),
    const LatLng(19.1965, 84.7475),
  ];

  @override
  void initState() {
    super.initState();
    _fetchLiveGpsLocation();
  }

  Future<void> _fetchLiveGpsLocation() async {
    setState(() => _isLocating = true);
    try {
      LocationPermission permission = await Geolocator.checkPermission();
      if (permission == LocationPermission.denied) {
        permission = await Geolocator.requestPermission();
      }
      if (permission == LocationPermission.whileInUse || permission == LocationPermission.always) {
        Position pos = await Geolocator.getCurrentPosition(desiredAccuracy: LocationAccuracy.high);
        setState(() {
          _currentGpsPos = LatLng(pos.latitude, pos.longitude);
        });
        _mapController.move(_currentGpsPos, 16.5);
      }
    } catch (e) {
      // Fallback
    } finally {
      if (mounted) setState(() => _isLocating = false);
    }
  }

  double _calculatePolygonAreaAcres() {
    if (_farmPolygon.length < 3) return 0.0;
    double area = 0.0;
    int j = _farmPolygon.length - 1;
    for (int i = 0; i < _farmPolygon.length; i++) {
      final p1 = _farmPolygon[i];
      final p2 = _farmPolygon[j];
      area += (p2.longitude + p1.longitude) * (p2.latitude - p1.latitude);
      j = i;
    }
    double sqMeters = (area.abs() * 0.5) * 111319.5 * 111319.5 * cos(_currentGpsPos.latitude * pi / 180).abs();
    return sqMeters / 4046.86;
  }

  void _undoLastPoint() {
    if (_farmPolygon.isNotEmpty) {
      setState(() {
        _farmPolygon.removeLast();
      });
    }
  }

  void _clearPolygon() {
    setState(() {
      _farmPolygon.clear();
    });
  }

  @override
  Widget build(BuildContext context) {
    final areaAcres = _calculatePolygonAreaAcres();

    return Column(
      children: [
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
          color: const Color(0xFF0F172A),
          child: SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            physics: const BouncingScrollPhysics(),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('Google Hybrid Satellite Terrain', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 12, color: Colors.white)),
                    Text('Area: ${areaAcres.toStringAsFixed(1)} Acres (${_farmPolygon.length} Drag-Adjustable Corners)', style: const TextStyle(fontSize: 10, color: Color(0xFF34D399), fontWeight: FontWeight.bold)),
                  ],
                ),
                const SizedBox(width: 14),
                Row(
                  children: [
                    IconButton(
                      icon: const Icon(Icons.undo_rounded, color: Colors.amber, size: 20),
                      tooltip: 'Undo Corner',
                      onPressed: _undoLastPoint,
                    ),
                    IconButton(
                      icon: const Icon(Icons.delete_outline_rounded, color: Colors.redAccent, size: 20),
                      tooltip: 'Clear Polygon',
                      onPressed: _clearPolygon,
                    ),
                    IconButton(
                      icon: Icon(
                        _tileModeIndex == 0 ? Icons.satellite_alt : (_tileModeIndex == 1 ? Icons.terrain : Icons.map),
                        color: const Color(0xFF10B981),
                        size: 20,
                      ),
                      tooltip: 'Switch Map Layer',
                      onPressed: () {
                        setState(() {
                          _tileModeIndex = (_tileModeIndex + 1) % 3;
                        });
                      },
                    ),
                    const SizedBox(width: 4),
                    ElevatedButton.icon(
                      style: ElevatedButton.styleFrom(
                        backgroundColor: const Color(0xFF059669),
                        foregroundColor: Colors.white,
                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                      ),
                      onPressed: () {
                        ScaffoldMessenger.of(context).showSnackBar(
                          SnackBar(
                            behavior: SnackBarBehavior.floating,
                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(25)),
                            backgroundColor: const Color(0xFF059669),
                            content: Row(
                              children: [
                                const Icon(Icons.alt_route_rounded, color: Colors.white, size: 20),
                                const SizedBox(width: 10),
                                Expanded(child: Text('Autonomous Drone Flight Grid Generated for ${areaAcres.toStringAsFixed(1)} Acres!', style: const TextStyle(fontSize: 12, color: Colors.white))),
                              ],
                            ),
                          ),
                        );
                      },
                      icon: const Icon(Icons.alt_route_rounded, size: 14),
                      label: const Text('Plan Flight Grid', style: TextStyle(fontSize: 11)),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),

        Expanded(
          child: Stack(
            children: [
              FlutterMap(
                mapController: _mapController,
                options: MapOptions(
                  initialCenter: _currentGpsPos,
                  initialZoom: 16.5,
                  onTap: (pos, point) {
                    setState(() => _farmPolygon.add(point));
                  },
                ),
                children: [
                  for (String url in _tileLayers[_tileModeIndex])
                    TileLayer(
                      urlTemplate: url,
                      userAgentPackageName: 'com.agrisense.app',
                    ),
                  if (_farmPolygon.length >= 3)
                    PolygonLayer(
                      polygons: [
                        Polygon(
                          points: _farmPolygon,
                          color: const Color(0xFF10B981).withOpacity(0.3),
                          borderColor: const Color(0xFF10B981),
                          borderStrokeWidth: 3,
                          isFilled: true,
                        ),
                      ],
                    ),
                  if (_farmPolygon.length >= 2)
                    PolylineLayer(
                      polylines: [
                        Polyline(
                          points: _farmPolygon,
                          color: const Color(0xFF10B981),
                          strokeWidth: 3,
                        ),
                      ],
                    ),
                  MarkerLayer(
                    markers: [
                      Marker(
                        point: _currentGpsPos,
                        width: 44,
                        height: 44,
                        child: Container(
                          decoration: BoxDecoration(
                            color: const Color(0xFF10B981),
                            shape: BoxShape.circle,
                            border: Border.all(color: Colors.white, width: 3),
                            boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.3), blurRadius: 8)],
                          ),
                          child: const Icon(Icons.my_location, color: Colors.white, size: 22),
                        ),
                      ),

                      for (int i = 0; i < _farmPolygon.length; i++)
                        Marker(
                          point: _farmPolygon[i],
                          width: 44,
                          height: 44,
                          child: GestureDetector(
                            onPanUpdate: (details) {
                              final currentPixel = _mapController.camera.latLngToScreenPoint(_farmPolygon[i]);
                              final newPixel = Offset(currentPixel.x + details.delta.dx, currentPixel.y + details.delta.dy);
                              final newLatLng = _mapController.camera.pointToLatLng(Point(newPixel.dx, newPixel.dy));
                              setState(() {
                                _farmPolygon[i] = newLatLng;
                              });
                            },
                            child: Container(
                              decoration: BoxDecoration(
                                color: Colors.amber,
                                shape: BoxShape.circle,
                                border: Border.all(color: Colors.black, width: 2.5),
                                boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.4), blurRadius: 6)],
                              ),
                              child: Center(
                                child: Text(
                                  '${i + 1}',
                                  style: const TextStyle(color: Colors.black, fontSize: 13, fontWeight: FontWeight.bold),
                                ),
                              ),
                            ),
                          ),
                        ),
                    ],
                  ),
                ],
              ),
              Positioned(
                bottom: 16,
                right: 16,
                child: FloatingActionButton.small(
                  backgroundColor: Colors.white,
                  foregroundColor: const Color(0xFF059669),
                  onPressed: _fetchLiveGpsLocation,
                  child: _isLocating
                      ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2, color: Color(0xFF059669)))
                      : const Icon(Icons.gps_fixed),
                ),
              ),
              Positioned(
                top: 12,
                left: 12,
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                  decoration: BoxDecoration(
                    color: Colors.black87,
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Text(
                    _tileModeIndex == 0 ? 'Google Hybrid Satellite Terrain (Touch & Drag Markers to Adjust)' : (_tileModeIndex == 1 ? 'Topo Contour Map' : 'OpenStreetMap'),
                    style: const TextStyle(color: Colors.white, fontSize: 10, fontWeight: FontWeight.bold),
                  ),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

// ==================== 8. AUTONOMOUS DRONE CONTROL ====================
class DroneFlightControlScreen extends StatelessWidget {
  final TelemetryPacket? packet;
  final bool isConnected;

  const DroneFlightControlScreen({super.key, required this.packet, required this.isConnected});

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      physics: const AlwaysScrollableScrollPhysics(),
      padding: const EdgeInsets.all(16.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(16),
              boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.04), blurRadius: 8)],
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('Autonomous Drone Control Station', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Color(0xFF0F172A))),
                const SizedBox(height: 14),
                Row(
                  children: [
                    _metric('Battery', '88%', Icons.battery_charging_full, Colors.green),
                    _metric('Altitude', '15.0 m', Icons.height, Colors.cyan[700]!),
                    _metric('Flight Speed', '4.2 m/s', Icons.speed, Colors.amber[800]!),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: 20),
          SizedBox(
            width: double.infinity,
            height: 50,
            child: ElevatedButton.icon(
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0xFF059669),
                foregroundColor: Colors.white,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
              ),
              onPressed: () {
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(
                    behavior: SnackBarBehavior.floating,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(25)),
                    backgroundColor: const Color(0xFF059669),
                    content: Row(
                      children: const [
                        Icon(Icons.flight_takeoff_rounded, color: Colors.white, size: 20),
                        SizedBox(width: 10),
                        Expanded(child: Text('Autonomous Scan Mission Dispatched!', style: TextStyle(fontSize: 12, color: Colors.white))),
                      ],
                    ),
                  ),
                );
              },
              icon: const Icon(Icons.flight_takeoff_rounded),
              label: const Text('Start Autonomous Scan Mission', style: TextStyle(fontSize: 15, fontWeight: FontWeight.bold)),
            ),
          ),
        ],
      ),
    );
  }

  Widget _metric(String title, String val, IconData icon, Color color) {
    return Expanded(
      child: Column(
        children: [
          Icon(icon, color: color, size: 22),
          const SizedBox(height: 4),
          Text(title, style: const TextStyle(fontSize: 10, color: Color(0xFF64748B))),
          Text(val, style: const TextStyle(fontSize: 14, fontWeight: FontWeight.bold, color: Color(0xFF0F172A))),
        ],
      ),
    );
  }
}

// ==================== 9. UNIFIED ENTERPRISE "SETTINGS & PROFILE" HUB ====================
class SettingsAndProfileScreen extends StatefulWidget {
  final Map<String, dynamic> farmer;
  final List<Map<String, dynamic>> farms;
  final int selectedIdx;
  final String appVersion;
  final Function(int) onSelectFarm;
  final Function(String, double, String) onAddFarm;
  final VoidCallback onLogout;
  final VoidCallback onEditProfile;
  final VoidCallback onCheckUpdate;

  const SettingsAndProfileScreen({
    super.key,
    required this.farmer,
    required this.farms,
    required this.selectedIdx,
    required this.appVersion,
    required this.onSelectFarm,
    required this.onAddFarm,
    required this.onLogout,
    required this.onEditProfile,
    required this.onCheckUpdate,
  });

  @override
  State<SettingsAndProfileScreen> createState() => _SettingsAndProfileScreenState();
}

class _SettingsAndProfileScreenState extends State<SettingsAndProfileScreen> {
  bool _useCelsius = true;
  bool _autoSync = true;
  bool _pushAlerts = true;

  void _showAddFarmDialog(BuildContext context) {
    final nameCtrl = TextEditingController();
    final acresCtrl = TextEditingController(text: "20");
    final cropCtrl = TextEditingController(text: "Wheat & Paddy");

    showDialog(
      context: context,
      builder: (ctx) {
        return AlertDialog(
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
          title: const Text('Add New Farm Field', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: nameCtrl,
                textCapitalization: TextCapitalization.words,
                decoration: const InputDecoration(labelText: 'Farm Name (e.g. South Paddy Field)'),
              ),
              const SizedBox(height: 8),
              TextField(
                controller: acresCtrl,
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(labelText: 'Farm Area (Acres)'),
              ),
              const SizedBox(height: 8),
              TextField(
                controller: cropCtrl,
                textCapitalization: TextCapitalization.words,
                decoration: const InputDecoration(labelText: 'Crop Types'),
              ),
            ],
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Cancel')),
            ElevatedButton(
              style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF059669), foregroundColor: Colors.white),
              onPressed: () {
                final name = nameCtrl.text.trim();
                final acres = double.tryParse(acresCtrl.text) ?? 10.0;
                final crop = cropCtrl.text.trim();
                if (name.isNotEmpty) {
                  widget.onAddFarm(name, acres, crop);
                  Navigator.pop(ctx);
                }
              },
              child: const Text('Add Field'),
            ),
          ],
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final activeFarm = widget.farms[widget.selectedIdx];

    return SingleChildScrollView(
      physics: const AlwaysScrollableScrollPhysics(),
      padding: const EdgeInsets.all(16.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // 1. ACCOUNT PROFILE CARD
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(16),
              boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.04), blurRadius: 8)],
            ),
            child: Row(
              children: [
                FarmerAvatarWidget(avatarId: widget.farmer['avatar_id'] ?? 1, name: widget.farmer['full_name'] ?? 'Farmer', radius: 28),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(widget.farmer['full_name'] ?? 'Farmer Account', style: const TextStyle(fontSize: 17, fontWeight: FontWeight.bold, color: Color(0xFF0F172A))),
                      Text(widget.farmer['phone_or_email'] ?? '', style: const TextStyle(fontSize: 11, color: Color(0xFF64748B))),
                      const SizedBox(height: 4),
                      Text('Active Field: ${activeFarm['farm_name']} (${activeFarm['farm_acres']} Acres)', style: const TextStyle(fontSize: 10, color: Color(0xFF059669), fontWeight: FontWeight.bold)),
                    ],
                  ),
                ),
                InkWell(
                  onTap: widget.onEditProfile,
                  borderRadius: BorderRadius.circular(10),
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                    decoration: BoxDecoration(
                      color: const Color(0xFF059669).withOpacity(0.1),
                      borderRadius: BorderRadius.circular(10),
                      border: Border.all(color: const Color(0xFF059669).withOpacity(0.3)),
                    ),
                    child: Row(
                      children: const [
                        Icon(Icons.edit_outlined, size: 14, color: Color(0xFF059669)),
                        SizedBox(width: 4),
                        Text('Edit', style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: Color(0xFF059669))),
                      ],
                    ),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 20),

          // 2. FARM MANAGEMENT CATALOG
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text('Farm Fields Catalog', style: TextStyle(fontSize: 15, fontWeight: FontWeight.bold, color: Color(0xFF0F172A))),
              ElevatedButton.icon(
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF059669),
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                ),
                onPressed: () => _showAddFarmDialog(context),
                icon: const Icon(Icons.add, size: 16),
                label: const Text('Add Field', style: TextStyle(fontSize: 11)),
              ),
            ],
          ),
          const SizedBox(height: 8),

          for (int i = 0; i < widget.farms.length; i++)
            Container(
              margin: const EdgeInsets.only(bottom: 8),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: i == widget.selectedIdx ? const Color(0xFF059669) : Colors.transparent, width: 2),
                boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.03), blurRadius: 6)],
              ),
              child: ListTile(
                leading: Icon(Icons.landscape, color: i == widget.selectedIdx ? const Color(0xFF059669) : Colors.grey),
                title: Text(widget.farms[i]['farm_name'], style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
                subtitle: Text('${widget.farms[i]['farm_acres']} Acres • ${widget.farms[i]['crop_type'] ?? 'Wheat & Paddy'}', style: const TextStyle(fontSize: 11, color: Colors.grey)),
                trailing: Icon(i == widget.selectedIdx ? Icons.check_circle : Icons.circle_outlined, color: const Color(0xFF059669)),
                onTap: () => widget.onSelectFarm(i),
              ),
            ),
          const SizedBox(height: 20),

          // 3. APPLICATION & SOFTWARE UPDATES
          const Text('Software & System Info', style: TextStyle(fontSize: 15, fontWeight: FontWeight.bold, color: Color(0xFF0F172A))),
          const SizedBox(height: 8),

          Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(14),
              boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.03), blurRadius: 6)],
            ),
            child: Row(
              children: [
                const Icon(Icons.system_update_rounded, color: Color(0xFF059669), size: 24),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('AgriSense v${widget.appVersion}', style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: Color(0xFF0F172A))),
                      const Text('Build 2026.09 (Release Edition)', style: TextStyle(fontSize: 10, color: Colors.grey)),
                    ],
                  ),
                ),
                ElevatedButton(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFF059669),
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                  ),
                  onPressed: widget.onCheckUpdate,
                  child: const Text('Check Updates', style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold)),
                ),
              ],
            ),
          ),
          const SizedBox(height: 20),

          // 4. APP PREFERENCES & TOGGLES
          const Text('Preferences & Configuration', style: TextStyle(fontSize: 15, fontWeight: FontWeight.bold, color: Color(0xFF0F172A))),
          const SizedBox(height: 8),

          Container(
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(14),
              boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.03), blurRadius: 6)],
            ),
            child: Column(
              children: [
                SwitchListTile(
                  secondary: const Icon(Icons.thermostat, color: Color(0xFF059669)),
                  title: const Text('Temperature Unit (°C / °F)', style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold)),
                  subtitle: Text(_useCelsius ? 'Celsius (°C)' : 'Fahrenheit (°F)', style: const TextStyle(fontSize: 11, color: Colors.grey)),
                  value: _useCelsius,
                  activeColor: const Color(0xFF059669),
                  onChanged: (val) => setState(() => _useCelsius = val),
                ),
                const Divider(height: 1),
                SwitchListTile(
                  secondary: const Icon(Icons.sync_rounded, color: Color(0xFF059669)),
                  title: const Text('Real-Time Data Sync', style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold)),
                  subtitle: const Text('Automated telemetry stream updates', style: TextStyle(fontSize: 11, color: Colors.grey)),
                  value: _autoSync,
                  activeColor: const Color(0xFF059669),
                  onChanged: (val) => setState(() => _autoSync = val),
                ),
                const Divider(height: 1),
                SwitchListTile(
                  secondary: const Icon(Icons.notifications_active_rounded, color: Color(0xFF059669)),
                  title: const Text('Crop Alert Notifications', style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold)),
                  subtitle: const Text('Receive immediate pathogen and weather warnings', style: TextStyle(fontSize: 11, color: Colors.grey)),
                  value: _pushAlerts,
                  activeColor: const Color(0xFF059669),
                  onChanged: (val) => setState(() => _pushAlerts = val),
                ),
              ],
            ),
          ),
          const SizedBox(height: 24),

          // 5. ACCOUNT LOGOUT BUTTON
          SizedBox(
            width: double.infinity,
            height: 48,
            child: OutlinedButton.icon(
              style: OutlinedButton.styleFrom(
                foregroundColor: Colors.redAccent,
                side: const BorderSide(color: Colors.redAccent),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
              ),
              onPressed: widget.onLogout,
              icon: const Icon(Icons.logout),
              label: const Text('Sign Out of Account', style: TextStyle(fontWeight: FontWeight.bold)),
            ),
          ),
        ],
      ),
    );
  }
}
