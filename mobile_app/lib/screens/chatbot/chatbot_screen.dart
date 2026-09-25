import 'dart:convert';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:geolocator/geolocator.dart';
import 'package:image_picker/image_picker.dart';
import '../../services/chatbot_service.dart';

class ChatbotScreen extends StatefulWidget {
  final Map<String, dynamic>? farmer;

  const ChatbotScreen({super.key, this.farmer});

  @override
  State<ChatbotScreen> createState() => _ChatbotScreenState();
}

class _ChatbotScreenState extends State<ChatbotScreen> {
  final ChatbotService _chatbotService = const ChatbotService();
  final TextEditingController _queryController = TextEditingController();
  final ScrollController _scrollController = ScrollController();
  final ImagePicker _imagePicker = ImagePicker();

  List<Map<String, dynamic>> _messages = [];
  List<Map<String, dynamic>> _supportedLanguages = [];
  List<String> _suggestions = [];

  String _selectedLangCode = "auto";
  String _selectedLangLabel = "🌐 Auto Language";
  bool _webSearchEnabled = true;
  bool _isLoading = false;

  String _userLocation = "India";
  double? _latitude;
  double? _longitude;
  String _cropType = "Wheat & Paddy";
  File? _attachedImageFile;
  String? _attachedImageBase64;

  @override
  void initState() {
    super.initState();
    if (widget.farmer != null) {
      _cropType = widget.farmer!['crop_type'] ?? 'Wheat & Paddy';
    }
    _initChatbot();
  }

  Future<void> _initChatbot() async {
    _detectLocation();
    _loadLanguages();
    _loadSuggestions();

    // Welcome message
    setState(() {
      _messages.add({
        'sender': 'bot',
        'text': '🙏 **Namaste & Welcome to AgriSense AI!**\n\nAsk me any question about crops, fertilizers, pest remedies, Mandi prices, or government schemes.\n\n*I speak all Indian languages & connect to live internet data!*',
        'citations': []
      });
    });
  }

  Future<void> _detectLocation() async {
    try {
      LocationPermission perm = await Geolocator.checkPermission();
      if (perm == LocationPermission.denied) {
        perm = await Geolocator.requestPermission();
      }
      if (perm == LocationPermission.whileInUse || perm == LocationPermission.always) {
        Position pos = await Geolocator.getCurrentPosition(timeLimit: const Duration(seconds: 4));
        if (mounted) {
          setState(() {
            _latitude = pos.latitude;
            _longitude = pos.longitude;
            _userLocation = "${pos.latitude.toStringAsFixed(2)}, ${pos.longitude.toStringAsFixed(2)}";
          });
        }
      }
    } catch (e) {
      print("[Chatbot Geolocation] Defaulting location: India");
    }
  }

  Future<void> _loadLanguages() async {
    final langs = await _chatbotService.fetchSupportedLanguages();
    if (mounted) {
      setState(() {
        _supportedLanguages = langs;
      });
    }
  }

  Future<void> _loadSuggestions() async {
    final sug = await _chatbotService.fetchSuggestions(location: _userLocation, crop: _cropType);
    if (mounted) {
      setState(() {
        _suggestions = sug;
      });
    }
  }

  Future<void> _pickCropImage() async {
    try {
      final XFile? file = await _imagePicker.pickImage(source: ImageSource.gallery, maxWidth: 1024);
      if (file != null) {
        final bytes = await file.readAsBytes();
        setState(() {
          _attachedImageFile = File(file.path);
          _attachedImageBase64 = "data:image/jpeg;base64,${base64Encode(bytes)}";
        });
      }
    } catch (e) {
      print("[Image Picker Error] $e");
    }
  }

  void _clearAttachedImage() {
    setState(() {
      _attachedImageFile = null;
      _attachedImageBase64 = null;
    });
  }

  Future<void> _sendMessage({String? customText}) async {
    final text = customText ?? _queryController.text.trim();
    if (text.isEmpty && _attachedImageBase64 == null) return;

    final userMsg = text.isNotEmpty ? text : "📷 Crop Disease Scan Image Attached";
    setState(() {
      _messages.add({
        'sender': 'user',
        'text': userMsg,
        'image': _attachedImageFile,
      });
      _isLoading = true;
    });

    _queryController.clear();
    _scrollToBottom();

    final imageToSend = _attachedImageBase64;
    _clearAttachedImage();

    int? farmId;
    if (widget.farmer != null) {
      farmId = widget.farmer!['farm_id'] is int ? widget.farmer!['farm_id'] : widget.farmer!['id'] as int?;
    }

    final response = await _chatbotService.sendChatMessage(
      query: text.isNotEmpty ? text : "Diagnose this crop leaf image for pests or diseases.",
      language: _selectedLangCode,
      location: _userLocation,
      latitude: _latitude,
      longitude: _longitude,
      cropType: _cropType,
      farmId: farmId,
      imageBase64: imageToSend,
      enableWebSearch: _webSearchEnabled,
    );

    if (mounted) {
      setState(() {
        _isLoading = false;
        _messages.add({
          'sender': 'bot',
          'text': response['answer'] ?? "⚠️ No answer received.",
          'citations': response['web_citations'] ?? [],
          'vision': response['vision_diagnosis'],
        });
      });
      _scrollToBottom();
    }
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  void _showLanguagePicker() {
    showModalBottomSheet(
      context: context,
      backgroundColor: const Color(0xFF1E293B),
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (context) {
        return Container(
          padding: const EdgeInsets.all(16),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Text(
                "Select Language / भाषा चुनें",
                style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 16),
              ),
              const SizedBox(height: 12),
              Expanded(
                child: ListView.builder(
                  shrinkWrap: true,
                  itemCount: _supportedLanguages.length,
                  itemBuilder: (context, idx) {
                    final item = _supportedLanguages[idx];
                    return ListTile(
                      leading: Text(item['flag'] ?? '🇮🇳', style: const TextStyle(fontSize: 20)),
                      title: Text("${item['native']} (${item['name']})", style: const TextStyle(color: Colors.white)),
                      trailing: _selectedLangCode == item['code'] ? const Icon(Icons.check_circle, color: Color(0xFF10B981)) : null,
                      onTap: () {
                        setState(() {
                          _selectedLangCode = item['code'];
                          _selectedLangLabel = "${item['flag']} ${item['native']}";
                        });
                        Navigator.pop(context);
                      },
                    );
                  },
                ),
              )
            ],
          ),
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0F172A),
      appBar: AppBar(
        backgroundColor: const Color(0xFF1E293B),
        elevation: 2,
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              "AgriSense Knowledge AI",
              style: TextStyle(color: Color(0xFF10B981), fontWeight: FontWeight.bold, fontSize: 16),

            ),
            Text(
              "📍 $_userLocation | Crop: $_cropType",
              style: const TextStyle(color: Color(0xFF94A3B8), fontSize: 11),
            ),
          ],
        ),
        actions: [
          // Language Selector Button
          TextButton.icon(
            onPressed: _showLanguagePicker,
            icon: const Icon(Icons.language, color: Colors.white, size: 16),
            label: Text(
              _selectedLangLabel,
              style: const TextStyle(color: Colors.white, fontSize: 12, fontWeight: FontWeight.bold),
            ),
          ),
          // Web Search Toggle
          IconButton(
            icon: Icon(
              _webSearchEnabled ? Icons.language_rounded : Icons.public_off_rounded,
              color: _webSearchEnabled ? const Color(0xFF10B981) : Colors.grey,
            ),
            tooltip: _webSearchEnabled ? "Live Web Search: ON" : "Live Web Search: OFF",
            onPressed: () {
              setState(() {
                _webSearchEnabled = !_webSearchEnabled;
              });
            },
          )
        ],
      ),
      body: Column(
        children: [
          // Suggestion Chips Header
          if (_suggestions.isNotEmpty)
            Container(
              height: 48,
              color: const Color(0xFF0B1329),
              child: ListView.builder(
                scrollDirection: Axis.horizontal,
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                itemCount: _suggestions.length,
                itemBuilder: (context, idx) {
                  final sug = _suggestions[idx];
                  return Padding(
                    padding: const EdgeInsets.only(right: 8),
                    child: ActionChip(
                      backgroundColor: const Color(0xFF1E293B),
                      side: const BorderSide(color: Color(0xFF0284C7)),
                      label: Text(
                        sug,
                        style: const TextStyle(color: Color(0xFF38BDF8), fontSize: 11),
                      ),
                      onPressed: () => _sendMessage(customText: sug),
                    ),
                  );
                },
              ),
            ),

          // Messages View
          Expanded(
            child: ListView.builder(
              controller: _scrollController,
              padding: const EdgeInsets.all(16),
              itemCount: _messages.length,
              itemBuilder: (context, idx) {
                final msg = _messages[idx];
                final isUser = msg['sender'] == 'user';
                final File? imgFile = msg['image'];
                final List citations = msg['citations'] ?? [];

                return Align(
                  alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
                  child: Container(
                    margin: const EdgeInsets.only(bottom: 12),
                    constraints: BoxConstraints(maxWidth: MediaQuery.of(context).size.width * 0.82),
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: isUser ? const Color(0xFF059669) : const Color(0xFF1E293B),
                      borderRadius: BorderRadius.only(
                        topLeft: const Radius.circular(12),
                        topRight: const Radius.circular(12),
                        bottomLeft: isUser ? const Radius.circular(12) : const Radius.circular(2),
                        bottomRight: isUser ? const Radius.circular(2) : const Radius.circular(12),
                      ),
                      border: isUser ? null : Border.all(color: const Color(0xFF334155)),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        if (imgFile != null)
                          Padding(
                            padding: const EdgeInsets.only(bottom: 8),
                            child: ClipRRect(
                              borderRadius: BorderRadius.circular(8),
                              child: Image.file(imgFile, height: 140, width: double.infinity, fit: BoxFit.cover),
                            ),
                          ),
                        Text(
                          msg['text'],
                          style: TextStyle(
                            color: isUser ? Colors.white : const Color(0xFFF1F5F9),
                            fontSize: 13,
                            height: 1.4,
                          ),
                        ),
                        if (citations.isNotEmpty) ...[
                          const SizedBox(height: 8),
                          const Divider(color: Color(0xFF334155)),
                          const Text("🌐 Web Citations:", style: TextStyle(color: Color(0xFF38BDF8), fontSize: 11, fontWeight: FontWeight.bold)),
                          ...citations.map((c) => Padding(
                                padding: const EdgeInsets.only(top: 2),
                                child: Text("• ${c['title']}: ${c['snippet']}", style: const TextStyle(color: Color(0xFF94A3B8), fontSize: 10)),
                              ))
                        ]
                      ],
                    ),
                  ),
                );
              },
            ),
          ),

          if (_isLoading)
            const Padding(
              padding: EdgeInsets.symmetric(vertical: 8),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2, color: Color(0xFF10B981))),
                  SizedBox(width: 10),
                  Text("AgriSense AI is thinking & retrieving data...", style: TextStyle(color: Color(0xFF94A3B8), fontSize: 12)),
                ],
              ),
            ),

          // Attached Image Preview Bar
          if (_attachedImageFile != null)
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              color: const Color(0xFF1E293B),
              child: Row(
                children: [
                  ClipRRect(
                    borderRadius: BorderRadius.circular(4),
                    child: Image.file(_attachedImageFile!, width: 36, height: 36, fit: BoxFit.cover),
                  ),
                  const SizedBox(width: 10),
                  const Expanded(
                    child: Text("Crop Image Attached for Vision AI Scan", style: TextStyle(color: Color(0xFF10B981), fontSize: 12)),
                  ),
                  IconButton(
                    icon: const Icon(Icons.close, color: Colors.redAccent, size: 18),
                    onPressed: _clearAttachedImage,
                  )
                ],
              ),
            ),

          // Input Toolbar
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 8),
            color: const Color(0xFF1E293B),
            child: Row(
              children: [
                IconButton(
                  icon: const Icon(Icons.add_a_photo_rounded, color: Color(0xFF10B981)),
                  tooltip: "Attach Crop Image for Disease Diagnosis",
                  onPressed: _pickCropImage,
                ),
                Expanded(
                  child: TextField(
                    controller: _queryController,
                    style: const TextStyle(color: Colors.white, fontSize: 13),
                    decoration: InputDecoration(
                      hintText: "Ask in Hindi, Tamil, Telugu, English...",
                      hintStyle: const TextStyle(color: Color(0xFF64748B), fontSize: 12),
                      filled: true,
                      fillColor: const Color(0xFF0F172A),
                      contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(20),
                        borderSide: const BorderSide(color: Color(0xFF475569)),
                      ),
                    ),
                    onSubmitted: (_) => _sendMessage(),
                  ),
                ),
                const SizedBox(width: 6),
                CircleAvatar(
                  backgroundColor: const Color(0xFF10B981),
                  child: IconButton(
                    icon: const Icon(Icons.send_rounded, color: Colors.white, size: 18),
                    onPressed: _sendMessage,
                  ),
                )
              ],
            ),
          )
        ],
      ),
    );
  }
}
