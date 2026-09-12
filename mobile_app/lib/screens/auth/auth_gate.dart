import 'package:flutter/material.dart';

import '../home/main_navigation_screen.dart';
import 'auth_screen.dart';

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
        ? MainNavigationScreen(
            farmer: _currentFarmer!,
            onLogout: _handleLogout,
          )
        : AuthScreen(
            onLoginSuccess: _handleLogin,
          );
  }
}