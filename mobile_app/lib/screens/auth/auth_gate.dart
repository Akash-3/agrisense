import 'package:flutter/material.dart';
import '../../services/auth_service.dart';
import '../home/main_navigation_screen.dart';
import 'auth_screen.dart';

class AuthGate extends StatefulWidget {
  const AuthGate({super.key});

  @override
  State<AuthGate> createState() => _AuthGateState();
}

class _AuthGateState extends State<AuthGate> {
  Map<String, dynamic>? _currentFarmer;
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _checkStoredSession();
  }

  Future<void> _checkStoredSession() async {
    const authService = AuthService();
    final storedFarmer = await authService.getStoredFarmer();
    if (mounted) {
      setState(() {
        _currentFarmer = storedFarmer;
        _isLoading = false;
      });
    }
  }

  void _handleLogin(Map<String, dynamic> farmerData) {
    setState(() => _currentFarmer = farmerData);
  }

  void _handleLogout() async {
    const authService = AuthService();
    await authService.clearSession();
    if (mounted) {
      setState(() => _currentFarmer = null);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return const Scaffold(
        body: Center(child: CircularProgressIndicator()),
      );
    }
    
    return _currentFarmer != null
        ? MainNavigationScreen(
            farmer: _currentFarmer!,
            onLogout: _handleLogout,
          )
        : AuthScreen(
            onLoginSuccess: _handleLogin,
          );
  }
}