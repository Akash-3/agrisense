import 'package:flutter/material.dart';

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
