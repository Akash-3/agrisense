/**
 * AgriSense Multilingual Agricultural AI Chatbot Engine (Web)
 * Features: Multilingual (All Indian Languages), Location Context, Live Internet Search Retrieval, Vision Crop Diagnosis
 */

const AgriSenseChatbot = {
    selectedLanguage: "auto",
    webSearchEnabled: true,
    userLocation: "India",
    userCrop: "Wheat & Paddy",
    latitude: null,
    longitude: null,
    attachedImageBase64: null,
    speechRecognition: null,
    isListening: false,
    conversationHistory: [],

    init() {
        this.detectUserLocation();
        this.initSpeechRecognition();
        this.injectChatbotUI();
        this.loadLanguages();
        this.loadSuggestions();
    },

    detectUserLocation() {
        if ("geolocation" in navigator) {
            navigator.geolocation.getCurrentPosition(
                (pos) => {
                    this.latitude = pos.coords.latitude;
                    this.longitude = pos.coords.longitude;
                    const locLabel = document.getElementById("agri-chat-loc-label");
                    if (locLabel) {
                        locLabel.innerText = `📍 ${this.latitude.toFixed(2)}, ${this.longitude.toFixed(2)}`;
                    }
                },
                (err) => {
                    console.log("[Chatbot Geolocation] Using default location: India");
                },
                { timeout: 5000 }
            );
        }
    },

    initSpeechRecognition() {
        if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
            const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
            this.speechRecognition = new SpeechRec();
            this.speechRecognition.continuous = false;
            this.speechRecognition.interimResults = true;

            this.speechRecognition.onstart = () => {
                this.isListening = true;
                const voiceBtn = document.getElementById("agri-chat-voice-btn");
                const inputEl = document.getElementById("agri-chat-input");
                if (voiceBtn) {
                    voiceBtn.classList.add("listening-pulse");
                    voiceBtn.title = "Listening... Click to stop recording";
                }
                if (inputEl && !inputEl.value) {
                    inputEl.placeholder = "🎙️ Listening... speak now in your language";
                }
            };

            this.speechRecognition.onresult = (event) => {
                let interimTranscript = "";
                let finalTranscript = "";

                for (let i = event.resultIndex; i < event.results.length; i++) {
                    const transcript = event.results[i][0].transcript;
                    if (event.results[i].isFinal) {
                        finalTranscript += transcript;
                    } else {
                        interimTranscript += transcript;
                    }
                }

                const resultText = finalTranscript || interimTranscript;
                const inputEl = document.getElementById("agri-chat-input");
                if (inputEl && resultText) {
                    inputEl.value = resultText;
                }
            };

            this.speechRecognition.onerror = (err) => {
                console.warn("[Chatbot Voice Recognition Warning]", err.error);
                let msg = "Speech recognition error. Please try again.";
                if (err.error === "not-allowed" || err.error === "service-not-allowed") {
                    msg = "Microphone permission denied. Please allow microphone access in browser settings.";
                } else if (err.error === "no-speech") {
                    msg = "No speech detected. Please click the mic and speak clearly.";
                } else if (err.error === "network") {
                    msg = "Speech recognition network error. Please check your connection.";
                }
                this.showNotice(msg);
                this.stopListening();
            };

            this.speechRecognition.onend = () => {
                this.stopListening();
            };
        }
    },

    toggleVoiceInput() {
        if (!this.speechRecognition) {
            this.showNotice("Voice input is not supported by your browser. Please type your query.");
            return;
        }

        if (this.isListening) {
            try {
                this.speechRecognition.stop();
            } catch (e) {
                console.log("[Voice Stop Warning]", e);
            }
            this.stopListening();
        } else {
            const langMap = {
                "hi": "hi-IN", "ta": "ta-IN", "te": "te-IN", "kn": "kn-IN",
                "mr": "mr-IN", "bn": "bn-IN", "gu": "gu-IN", "pa": "pa-IN",
                "ml": "ml-IN", "or": "or-IN", "en": "en-IN"
            };

            let targetLang = langMap[this.selectedLanguage];
            if (!targetLang || this.selectedLanguage === "auto") {
                targetLang = navigator.language || "hi-IN";
            }

            try {
                this.speechRecognition.lang = targetLang;
                this.speechRecognition.start();
            } catch (err) {
                console.warn("[Voice Start Warning]", err);
                if (err.name === "InvalidStateError") {
                    this.stopListening();
                    try {
                        this.speechRecognition.start();
                    } catch (e) {
                        this.showNotice("Voice recognition starting. Please wait...");
                    }
                } else {
                    this.showNotice("Could not access microphone. Please check permissions.");
                }
            }
        }
    },

    stopListening() {
        this.isListening = false;
        const voiceBtn = document.getElementById("agri-chat-voice-btn");
        const inputEl = document.getElementById("agri-chat-input");
        if (voiceBtn) {
            voiceBtn.classList.remove("listening-pulse");
            voiceBtn.title = "Voice Input (Speak in Indian Language)";
        }
        if (inputEl && inputEl.placeholder.includes("Listening")) {
            inputEl.placeholder = "Ask in Hindi, Tamil, Telugu, English...";
        }
    },

    showNotice(text) {
        const msgContainer = document.getElementById("agri-chat-messages");
        if (!msgContainer) return;

        const noticeDiv = document.createElement("div");
        noticeDiv.className = "chat-msg bot-msg system-notice";
        noticeDiv.innerHTML = `<div class="msg-bubble" style="background:#334155; color:#F1F5F9; font-size:12px; font-style:italic;">⚠️ ${text}</div>`;
        msgContainer.appendChild(noticeDiv);
        msgContainer.scrollTop = msgContainer.scrollHeight;

        setTimeout(() => {
            if (noticeDiv.parentNode) {
                noticeDiv.parentNode.removeChild(noticeDiv);
            }
        }, 4000);
    },

    injectChatbotUI() {
        if (document.getElementById("agrisense-chatbot-container")) return;

        const container = document.createElement("div");
        container.id = "agrisense-chatbot-container";
        container.innerHTML = `
            <!-- FLOATING LAUNCH BUTTON -->
            <button id="agri-chat-launch-btn" class="agri-chat-fab" onclick="AgriSenseChatbot.toggleChatWindow()">
                <span class="fab-icon">🤖</span>
                <span class="fab-badge">AI</span>
            </button>

            <!-- CHAT MODAL / DRAWER -->
            <div id="agri-chat-window" class="agri-chat-card hidden">
                <!-- HEADER -->
                <div class="agri-chat-header">
                    <div class="agri-chat-title-group">
                        <div class="agri-bot-avatar">🌱</div>
                        <div>
                            <h4 class="agri-bot-name">AgriSense AI</h4>
                            <span id="agri-chat-loc-label" class="agri-chat-loc">📍 India</span>
                        </div>
                    </div>
                    <div class="agri-chat-controls">
                        <!-- LANGUAGE SELECTOR -->
                        <select id="agri-chat-lang-select" class="agri-chat-select" onchange="AgriSenseChatbot.onLanguageChange(this.value)">
                            <option value="auto">🌐 Auto</option>
                            <option value="hi">🇮🇳 हिंदी (Hindi)</option>
                            <option value="en">🇬🇧 English</option>
                            <option value="ta">🇮🇳 தமிழ் (Tamil)</option>
                            <option value="te">🇮🇳 తెలుగు (Telugu)</option>
                            <option value="kn">🇮🇳 ಕನ್ನಡ (Kannada)</option>
                            <option value="mr">🇮🇳 मराठी (Marathi)</option>
                            <option value="bn">🇮🇳 বাংলা (Bengali)</option>
                            <option value="gu">🇮🇳 ગુજરાતી (Gujarati)</option>
                            <option value="pa">🇮🇳 ਪੰਜਾਬੀ (Punjabi)</option>
                            <option value="ml">🇮🇳 മലയാളം (Malayalam)</option>
                            <option value="or">🇮🇳 ଓଡ଼ିଆ (Odia)</option>
                        </select>

                        <!-- WEB SEARCH TOGGLE -->
                        <button id="agri-web-toggle-btn" class="agri-chat-icon-btn active" title="Toggle Real-Time Internet Search" onclick="AgriSenseChatbot.toggleWebSearch()">
                            🌐 Internet
                        </button>
                        <button class="agri-chat-icon-btn" onclick="AgriSenseChatbot.toggleChatWindow()">✖</button>
                    </div>
                </div>

                <!-- SUGGESTION CHIPS -->
                <div id="agri-chat-chips" class="agri-chat-chips-scroll"></div>

                <!-- MESSAGES BODY -->
                <div id="agri-chat-messages" class="agri-chat-body">
                    <div class="chat-msg bot-msg">
                        <div class="msg-bubble">
                            <div class="agri-welcome-title">🙏 <strong>Namaste & Welcome to AgriSense AI!</strong></div>
                            <div class="agri-welcome-desc">Ask me any question about crops, fertilizers, pest control, Mandi market rates, or government schemes.</div>
                            <div class="agri-welcome-lang">I speak all major Indian languages & can search the live internet for you!</div>
                        </div>
                    </div>
                </div>

                <!-- IMAGE ATTACHMENT PREVIEW -->
                <div id="agri-chat-img-preview" class="agri-img-preview-bar hidden">
                    <img id="agri-preview-thumb" src="" alt="Crop leaf attachment"/>
                    <span class="preview-text">Plant Disease Image Attached</span>
                    <button class="remove-img-btn" onclick="AgriSenseChatbot.clearImageAttachment()">✖</button>
                </div>

                <!-- INPUT TOOLBAR -->
                <div class="agri-chat-footer">
                    <label class="agri-attach-btn" title="Upload Crop Image for AI Diagnosis">
                        📷
                        <input type="file" id="agri-chat-file-input" accept="image/*" onchange="AgriSenseChatbot.handleImageSelect(event)"/>
                    </label>
                    <button id="agri-chat-voice-btn" class="agri-voice-btn" title="Voice Input (Speak in Indian Language)" onclick="AgriSenseChatbot.toggleVoiceInput()">🎤</button>
                    <input type="text" id="agri-chat-input" class="agri-chat-input-field" placeholder="Ask in Hindi, Tamil, Telugu, English..." onkeypress="if(event.key==='Enter') AgriSenseChatbot.sendMessage()"/>
                    <button class="agri-chat-send-btn" onclick="AgriSenseChatbot.sendMessage()">🚀</button>
                </div>
            </div>
        `;
        document.body.appendChild(container);
        this.injectCSS();

        const chipsEl = document.getElementById("agri-chat-chips");
        if (chipsEl) {
            chipsEl.addEventListener("wheel", (e) => {
                if (e.deltaY !== 0) {
                    e.preventDefault();
                    chipsEl.scrollLeft += e.deltaY;
                }
            }, { passive: false });
        }
    },

    injectCSS() {
        if (document.getElementById("agrisense-chatbot-css")) return;
        const style = document.createElement("style");
        style.id = "agrisense-chatbot-css";
        style.innerHTML = `
            .agri-chat-fab {
                position: fixed;
                bottom: 24px;
                right: 24px;
                width: 60px;
                height: 60px;
                border-radius: 50%;
                background: linear-gradient(135deg, #10B981, #059669);
                color: white;
                border: none;
                box-shadow: 0 8px 24px rgba(16, 185, 129, 0.4);
                cursor: pointer;
                z-index: 99999;
                display: flex;
                align-items: center;
                justify-content: center;
                transition: transform 0.2s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            }
            .agri-chat-fab:hover { transform: scale(1.08); }
            .fab-icon { font-size: 28px; }
            .fab-badge {
                position: absolute;
                top: -2px;
                right: -2px;
                background: #F59E0B;
                color: #000;
                font-size: 10px;
                font-weight: bold;
                padding: 2px 6px;
                border-radius: 10px;
                border: 2px solid white;
            }

            .agri-chat-card {
                position: fixed;
                bottom: 96px;
                right: 24px;
                width: 420px;
                max-width: calc(100vw - 32px);
                height: 580px;
                max-height: calc(100vh - 120px);
                background: #0F172A;
                color: #F8FAFC;
                border: 1px solid #1E293B;
                border-radius: 16px;
                box-shadow: 0 20px 40px rgba(0,0,0,0.6);
                display: flex;
                flex-direction: column;
                z-index: 99999;
                overflow: hidden !important;
                box-sizing: border-box !important;
                font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            }
            .agri-chat-card * {
                box-sizing: border-box;
            }
            .agri-chat-card.hidden { display: none !important; }

            @media (max-width: 480px) {
                .agri-chat-card {
                    bottom: 0 !important;
                    right: 0 !important;
                    left: 0 !important;
                    top: 0 !important;
                    width: 100vw !important;
                    height: 100vh !important;
                    max-width: 100vw !important;
                    max-height: 100vh !important;
                    border-radius: 0 !important;
                    border: none !important;
                }
            }

            .agri-chat-header {
                padding: 10px 12px;
                background: #1E293B;
                display: flex;
                align-items: center;
                justify-content: space-between;
                border-bottom: 1px solid #334155;
                flex-shrink: 0;
                width: 100%;
                min-width: 0;
                gap: 8px;
            }
            .agri-chat-title-group {
                display: flex;
                align-items: center;
                gap: 8px;
                min-width: 0;
                flex: 1 1 auto;
            }
            .agri-bot-avatar {
                font-size: 18px;
                background: #065F46;
                width: 32px;
                height: 32px;
                display: flex;
                align-items: center;
                justify-content: center;
                border-radius: 50%;
                flex-shrink: 0;
            }
            .agri-bot-name {
                margin: 0;
                font-size: 13.5px;
                font-weight: 700;
                color: #10B981;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
                line-height: 1.2;
            }
            .agri-chat-loc {
                font-size: 10.5px;
                color: #94A3B8;
                display: block;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
            }

            .agri-chat-controls { display: flex; align-items: center; gap: 5px; flex-shrink: 0; }
            .agri-chat-select {
                background: #0F172A;
                color: #E2E8F0;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 4px 6px;
                font-size: 11px;
                max-width: 112px;
                cursor: pointer;
                outline: none;
                text-overflow: ellipsis;
            }
            .agri-chat-select:focus {
                border-color: #10B981;
            }
            .agri-chat-icon-btn {
                background: #334155;
                color: #E2E8F0;
                border: none;
                border-radius: 6px;
                padding: 4px 7px;
                font-size: 11px;
                cursor: pointer;
                white-space: nowrap;
                transition: background 0.15s ease;
            }
            .agri-chat-icon-btn:hover { background: #475569; }
            .agri-chat-icon-btn.active { background: #059669; color: white; font-weight: bold; }

            .agri-chat-chips-scroll {
                display: flex;
                gap: 8px;
                padding: 9px 12px;
                background: #0B1329;
                overflow-x: auto !important;
                overflow-y: hidden !important;
                white-space: nowrap;
                border-bottom: 1px solid #1E293B;
                flex-shrink: 0;
                width: 100%;
                scrollbar-width: none !important;
                -ms-overflow-style: none !important;
            }
            .agri-chat-chips-scroll::-webkit-scrollbar {
                display: none !important;
                width: 0 !important;
                height: 0 !important;
            }
            .agri-chip {
                background: #1E293B;
                color: #38BDF8;
                border: 1px solid #0284C7;
                border-radius: 12px;
                padding: 4px 10px;
                font-size: 11px;
                cursor: pointer;
                white-space: nowrap;
                flex-shrink: 0;
                transition: background 0.15s ease, color 0.15s ease;
            }
            .agri-chip:hover { background: #0284C7; color: white; }

            .agri-chat-body {
                flex: 1;
                padding: 14px;
                overflow-y: auto !important;
                overflow-x: hidden !important;
                display: flex;
                flex-direction: column;
                gap: 12px;
                width: 100%;
                word-break: break-word !important;
                overflow-wrap: break-word !important;
                scrollbar-width: thin !important;
                scrollbar-color: #334155 transparent !important;
            }
            .agri-chat-body::-webkit-scrollbar {
                width: 6px !important;
            }
            .agri-chat-body::-webkit-scrollbar-track {
                background: transparent !important;
            }
            .agri-chat-body::-webkit-scrollbar-thumb {
                background: #334155 !important;
                border-radius: 9999px !important;
            }
            .agri-chat-body::-webkit-scrollbar-thumb:hover {
                background: #10B981 !important;
            }

            .chat-msg { display: flex; flex-direction: column; max-width: 100%; width: 100%; }
            .bot-msg { align-items: flex-start; text-align: left; }
            .user-msg { align-items: flex-end; text-align: left; }
            .msg-bubble {
                max-width: 90%;
                padding: 11px 15px;
                border-radius: 14px;
                font-size: 13.5px;
                line-height: 1.55;
                text-align: left !important;
                overflow-wrap: break-word !important;
                word-break: break-word !important;
                hyphens: none !important;
                -webkit-hyphens: none !important;
            }
            .agri-welcome-title {
                font-size: 14px;
                font-weight: 700;
                color: #10B981;
                margin-bottom: 6px;
                line-height: 1.4;
                text-align: left;
            }
            .agri-welcome-desc {
                font-size: 13px;
                color: #F1F5F9;
                line-height: 1.5;
                margin-bottom: 6px;
                text-align: left;
            }
            .agri-welcome-lang {
                font-size: 12px;
                color: #94A3B8;
                font-style: italic;
                line-height: 1.4;
                text-align: left;
            }
            .msg-bubble a {
                color: #38BDF8;
                word-break: break-all !important;
                text-decoration: underline;
            }
            .msg-bubble pre, .msg-bubble code {
                max-width: 100%;
                white-space: pre-wrap;
                word-break: break-word !important;
                overflow-x: auto;
            }
            .bot-msg .msg-bubble { background: #1E293B; color: #F1F5F9; border-top-left-radius: 2px; border: 1px solid #334155; }
            .user-msg .msg-bubble { background: #059669; color: white; border-top-right-radius: 2px; }

            .agri-img-preview-bar {
                display: flex;
                align-items: center;
                gap: 8px;
                padding: 6px 12px;
                background: #1E293B;
                border-top: 1px solid #334155;
                flex-shrink: 0;
                width: 100%;
            }
            .agri-img-preview-bar.hidden { display: none; }
            #agri-preview-thumb { width: 32px; height: 32px; border-radius: 4px; object-fit: cover; }
            .preview-text { font-size: 12px; color: #10B981; flex: 1; }
            .remove-img-btn { background: none; border: none; color: #EF4444; font-size: 14px; cursor: pointer; }

            .agri-chat-footer {
                padding: 10px 12px;
                background: #1E293B;
                display: flex;
                align-items: center;
                gap: 8px;
                border-top: 1px solid #334155;
                flex-shrink: 0;
                width: 100%;
            }
            .agri-attach-btn { cursor: pointer; font-size: 18px; padding: 4px; flex-shrink: 0; }
            .agri-attach-btn input { display: none; }
            .agri-voice-btn { background: none; border: none; font-size: 18px; cursor: pointer; padding: 4px; flex-shrink: 0; }
            .agri-voice-btn.listening-pulse { animation: pulse-red 1s infinite; }
            @keyframes pulse-red { 0% { transform: scale(1); } 50% { transform: scale(1.3); } 100% { transform: scale(1); } }

            .agri-chat-input-field {
                flex: 1;
                min-width: 0;
                background: #0F172A;
                border: 1px solid #475569;
                border-radius: 8px;
                padding: 8px 12px;
                color: white;
                font-size: 13px;
            }
            .agri-chat-send-btn {
                background: #10B981;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 12px;
                cursor: pointer;
                font-size: 14px;
                flex-shrink: 0;
            }
        `;
        document.head.appendChild(style);
    },

    openChatWindow() {
        let win = document.getElementById("agri-chat-window");
        if (!win) {
            this.init();
            win = document.getElementById("agri-chat-window");
        }
        if (win) {
            win.classList.remove("hidden");
            const inputEl = document.getElementById("agri-chat-input");
            if (inputEl) inputEl.focus();
        }
    },

    closeChatWindow() {
        const win = document.getElementById("agri-chat-window");
        if (win) win.classList.add("hidden");
        if (typeof UI !== "undefined" && UI.currentView) {
            document.querySelectorAll('.nav-link').forEach(link => {
                link.classList.remove('nav-item-active');
                if (link.dataset.view === UI.currentView) {
                    link.classList.add('nav-item-active');
                }
            });
        }
    },

    toggleChatWindow() {
        const win = document.getElementById("agri-chat-window");
        if (win) {
            if (win.classList.contains("hidden")) {
                this.openChatWindow();
            } else {
                this.closeChatWindow();
            }
        }
    },

    toggleWebSearch() {
        this.webSearchEnabled = !this.webSearchEnabled;
        const btn = document.getElementById("agri-web-toggle-btn");
        if (btn) {
            btn.classList.toggle("active", this.webSearchEnabled);
            btn.innerText = this.webSearchEnabled ? "🌐 Internet: ON" : "🌐 Internet: OFF";
        }
    },

    onLanguageChange(lang) {
        this.selectedLanguage = lang;
        this.loadSuggestions();
    },

    async loadLanguages() {
        try {
            const res = await fetch("/api/v1/chatbot/languages");
            const data = await res.json();
            if (data.status === "success" && data.languages) {
                const selectEl = document.getElementById("agri-chat-lang-select");
                if (selectEl) {
                    const autoOption = `<option value="auto">🌐 Auto</option>`;
                    selectEl.innerHTML = autoOption + data.languages.map(l =>
                        `<option value="${l.code}">${l.flag} ${l.native} (${l.name})</option>`
                    ).join("");
                    selectEl.value = this.selectedLanguage || "auto";
                }
            }
        } catch (e) {
            console.log("[Chatbot Languages Error]", e);
        }
    },

    async loadSuggestions() {
        try {
            const res = await fetch(`/api/v1/chatbot/suggestions?location=${encodeURIComponent(this.userLocation)}&crop=${encodeURIComponent(this.userCrop)}`);
            const data = await res.json();
            if (data.status === "success" && data.suggestions) {
                const container = document.getElementById("agri-chat-chips");
                if (container) {
                    container.innerHTML = data.suggestions.map(s =>
                        `<span class="agri-chip" onclick="AgriSenseChatbot.clickSuggestion('${s.replace(/'/g, "\\'")}')">${s}</span>`
                    ).join("");
                }
            }
        } catch (e) {
            console.log("[Chatbot Suggestions Error]", e);
        }
    },

    clickSuggestion(text) {
        const inputEl = document.getElementById("agri-chat-input");
        if (inputEl) {
            inputEl.value = text;
            this.sendMessage();
        }
    },

    handleImageSelect(event) {
        const file = event.target.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = (e) => {
                this.attachedImageBase64 = e.target.result;
                const thumb = document.getElementById("agri-preview-thumb");
                const previewBar = document.getElementById("agri-chat-img-preview");
                if (thumb && previewBar) {
                    thumb.src = this.attachedImageBase64;
                    previewBar.classList.remove("hidden");
                }
            };
            reader.readAsDataURL(file);
        }
    },

    clearImageAttachment() {
        this.attachedImageBase64 = null;
        const previewBar = document.getElementById("agri-chat-img-preview");
        const fileInput = document.getElementById("agri-chat-file-input");
        if (previewBar) previewBar.classList.add("hidden");
        if (fileInput) fileInput.value = "";
    },

    async sendMessage() {
        const inputEl = document.getElementById("agri-chat-input");
        const query = inputEl ? inputEl.value.trim() : "";
        if (!query && !this.attachedImageBase64) return;

        // Append User Message
        this.appendMessage(query || "📷 Crop Disease Diagnosis Image", "user");
        if (inputEl) inputEl.value = "";

        // Show Typing Indicator
        const typingId = this.appendMessage("⏳ Thinking & fetching agricultural knowledge...", "bot");

        try {
            const headers = { "Content-Type": "application/json" };
            const token = (typeof AuthService !== "undefined" && AuthService.getToken)
                ? AuthService.getToken()
                : localStorage.getItem("agrisense_session_token");
            if (token) {
                headers["Authorization"] = `Bearer ${token}`;
            }

            if (!this.conversationHistory) this.conversationHistory = [];

            const activeFarmId = (typeof AgriState !== "undefined" && AgriState.activeFarmId)
                ? AgriState.activeFarmId
                : null;

            const payload = {
                query: query || "Diagnose this crop leaf image for pests or diseases.",
                language: this.selectedLanguage,
                location: this.userLocation,
                latitude: this.latitude,
                longitude: this.longitude,
                crop_type: this.userCrop,
                farm_id: activeFarmId,
                image_base64: this.attachedImageBase64,
                enable_web_search: this.webSearchEnabled,
                history: this.conversationHistory.slice(-6)
            };

            const response = await fetch("/api/v1/chatbot/chat", {
                method: "POST",
                headers: headers,
                body: JSON.stringify(payload)
            });

            if (response.status === 401) {
                this.removeMessage(typingId);
                this.clearImageAttachment();
                this.appendMessage("⚠️ Authentication required or session expired. Please sign in to use AgriSense AI Chatbot.", "bot");
                return;
            }

            if (!response.ok) {
                this.removeMessage(typingId);
                this.clearImageAttachment();
                let detailMsg = `HTTP ${response.status} ${response.statusText}`;
                try {
                    const errData = await response.json();
                    detailMsg = errData.detail || errData.message || detailMsg;
                } catch (_) {}
                this.appendMessage(`⚠️ Server error (${response.status}): ${detailMsg}`, "bot");
                return;
            }

            const data = await response.json();
            this.removeMessage(typingId);
            this.clearImageAttachment();

            if (data.status === "success") {
                if (query) {
                    this.conversationHistory.push({ role: "user", content: query });
                }
                this.conversationHistory.push({ role: "assistant", content: data.answer });
                if (this.conversationHistory.length > 12) {
                    this.conversationHistory = this.conversationHistory.slice(-12);
                }
                this.appendMessage(data.answer, "bot");
            } else {
                const errorMsg = data.detail || data.message || "Sorry, I could not process your query at this moment. Please try again.";
                this.appendMessage(`⚠️ ${errorMsg}`, "bot");
            }
        } catch (err) {
            console.error("[AgriSense Chatbot Error]", err);
            this.removeMessage(typingId);
            if (err instanceof TypeError && err.message.includes("fetch")) {
                this.appendMessage("📡 Network Connection Error: Unable to reach AgriSense server at /api/v1/chatbot/chat. Please check your network connection.", "bot");
            } else {
                this.appendMessage(`❌ Client Error: ${err.message || String(err)}`, "bot");
            }
        }
    },

    appendMessage(text, sender) {
        const msgContainer = document.getElementById("agri-chat-messages");
        if (!msgContainer) return null;

        const id = "msg-" + Date.now() + "-" + Math.random().toString(36).substr(2, 4);
        const msgDiv = document.createElement("div");
        msgDiv.id = id;
        msgDiv.className = `chat-msg ${sender}-msg`;

        // Format markdown basic bold/newlines and clean whitespace
        const cleanText = (text || "").trim();
        const formattedText = cleanText
            .replace(/\r\n/g, '\n')
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\[(.*?)\]\((.*?)\)/g, '<a href="$2" target="_blank" style="color: #38BDF8; text-decoration: underline;">$1</a>')
            .replace(/\n/g, '<br/>');

        msgDiv.innerHTML = `<div class="msg-bubble">${formattedText}</div>`;
        msgContainer.appendChild(msgDiv);
        msgContainer.scrollTop = msgContainer.scrollHeight;
        return id;
    },

    removeMessage(id) {
        if (!id) return;
        const el = document.getElementById(id);
        if (el) el.remove();
    }
};

window.AgriSenseChatbot = AgriSenseChatbot;
console.info('[AgriSense Chatbot] loaded build: CHATBOT-FIX-20260926_01');

// AUTO INITIALIZE CHATBOT ON DOM LOAD OR IMMEDIATELY IF ALREADY LOADED
if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => {
        AgriSenseChatbot.init();
    });
} else {
    AgriSenseChatbot.init();
}
