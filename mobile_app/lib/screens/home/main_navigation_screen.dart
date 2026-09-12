import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter/foundation.dart';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:http/http.dart' as http;

import '../../config/app_config.dart';
import '../../models/telemetry_models.dart';
import '../../services/websocket_service.dart';
import '../../widgets/agri_logo_badge.dart';
import '../../widgets/app_drawer.dart';
import '../../widgets/farmer_avatar_widget.dart';
import '../../widgets/top_capsule_notification.dart';
import '../dashboard/farmer_dashboard.dart';
import '../map/farm_layout_map_screen.dart';
import '../drone/drone_flight_control_screen.dart';
import '../settings/settings_and_profile_screen.dart';
import '../auth/farm_setup_wizard_screen.dart';

class MainNavigationScreen extends StatefulWidget {
  final Map<String, dynamic> farmer;
  final VoidCallback onLogout;

  const MainNavigationScreen({super.key, required this.farmer, required this.onLogout});

  @override
  State<MainNavigationScreen> createState() => _MainNavigationScreenState();
}

class _MainNavigationScreenState extends State<MainNavigationScreen> {
  final GlobalKey<ScaffoldState> _scaffoldKey = GlobalKey<ScaffoldState>();
  final GlobalKey<FarmerDashboardState> _farmerDashboardKey = GlobalKey<FarmerDashboardState>();
  int _currentIndex = 0;
  late Map<String, dynamic> _farmerData;
  late List<Map<String, dynamic>> _farms;
  int _selectedFarmIdx = 0;

  final WebSocketService _wsService = WebSocketService();
  TelemetryPacket? _latestPacket;
  bool _isConnected = false;

  final String _currentAppVersion = "1.7.8";
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
                        final String downloadUrl = rawUrl.startsWith('http')
                            ? rawUrl
                            : '${AppConfig.backendHttpUrl}$rawUrl';

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
                        Flexible(
                          child: InkWell(
                            onTap: _showExtendedFarmSelectorDialog,
                            borderRadius: BorderRadius.circular(25),
                            child: Container(
                              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                              decoration: BoxDecoration(
                                color: const Color(0xFF047857),
                                borderRadius: BorderRadius.circular(25),
                                boxShadow: [BoxShadow(color: const Color(0xFF047857).withOpacity(0.35), blurRadius: 8)],
                              ),
                              child: Row(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  const Icon(Icons.landscape_rounded, color: Colors.white, size: 18),
                                  const SizedBox(width: 6),
                                  Flexible(
                                    child: Column(
                                      mainAxisSize: MainAxisSize.min,
                                      crossAxisAlignment: CrossAxisAlignment.start,
                                      children: [
                                        Text(
                                          activeFarm['farm_name'] ?? 'Main Farm',
                                          style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 12.5),
                                          overflow: TextOverflow.ellipsis,
                                          maxLines: 1,
                                        ),
                                        Text(
                                          '${activeFarm['farm_acres'] ?? 15.0} Acres',
                                          style: const TextStyle(color: Colors.white70, fontSize: 9.5, fontWeight: FontWeight.w500),
                                          overflow: TextOverflow.ellipsis,
                                          maxLines: 1,
                                        ),
                                      ],
                                    ),
                                  ),
                                  const SizedBox(width: 4),
                                  const Icon(Icons.keyboard_arrow_down_rounded, color: Colors.white, size: 18),
                                  const SizedBox(width: 4),
                                  Container(height: 14, width: 1, color: Colors.white30),
                                  const SizedBox(width: 4),
                                  Container(
                                    padding: const EdgeInsets.all(3),
                                    decoration: const BoxDecoration(color: Colors.white24, shape: BoxShape.circle),
                                    child: const Icon(Icons.add_rounded, color: Colors.white, size: 13),
                                  ),
                                ],
                              ),
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
