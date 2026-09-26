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
            this.speechRecognition.interimResults = false;

            this.speechRecognition.onresult = (event) => {
                const transcript = event.results[0][0].transcript;
                const inputEl = document.getElementById("agri-chat-input");
                if (inputEl) {
                    inputEl.value = transcript;
                }
                this.stopListening();
            };

            this.speechRecognition.onerror = (err) => {
                console.error("[Speech Error]", err);
                this.stopListening();
            };

            this.speechRecognition.onend = () => {
                this.stopListening();
            };
        }
    },

    toggleVoiceInput() {
        if (!this.speechRecognition) {
            alert("Voice input is not supported by your browser. Please type your message.");
            return;
        }

        const voiceBtn = document.getElementById("agri-chat-voice-btn");
        if (this.isListening) {
            this.speechRecognition.stop();
            this.stopListening();
        } else {
            // Set speech language mapping
            const langMap = {
                "hi": "hi-IN", "ta": "ta-IN", "te": "te-IN", "kn": "kn-IN",
                "mr": "mr-IN", "bn": "bn-IN", "gu": "gu-IN", "pa": "pa-IN",
                "ml": "ml-IN", "or": "or-IN", "en": "en-IN"
            };
            this.speechRecognition.lang = langMap[this.selectedLanguage] || "hi-IN";
            this.speechRecognition.start();
            this.isListening = true;
            if (voiceBtn) voiceBtn.classList.add("listening-pulse");
        }
    },

    stopListening() {
        this.isListening = false;
        const voiceBtn = document.getElementById("agri-chat-voice-btn");
        if (voiceBtn) voiceBtn.classList.remove("listening-pulse");
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
                            <h4 class="agri-bot-name">AgriSense Knowledge AI</h4>
                            <span id="agri-chat-loc-label" class="agri-chat-loc">📍 India</span>
                        </div>
                    </div>
                    <div class="agri-chat-controls">
                        <!-- LANGUAGE SELECTOR -->
                        <select id="agri-chat-lang-select" class="agri-chat-select" onchange="AgriSenseChatbot.onLanguageChange(this.value)">
                            <option value="auto">🌐 Auto Language</option>
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
                            🙏 <strong>Namaste & Welcome to AgriSense AI!</strong><br/>
                            Ask me any question about crops, fertilizers, pest control, Mandi market rates, or government schemes.<br/>
                            <em>I speak all major Indian languages & can search the live internet for you!</em>
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
                width: 400px;
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
                overflow: hidden;
                font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            }
            .agri-chat-card.hidden { display: none !important; }

            .agri-chat-header {
                padding: 12px 16px;
                background: #1E293B;
                display: flex;
                align-items: center;
                justify-content: space-between;
                border-bottom: 1px solid #334155;
            }
            .agri-chat-title-group { display: flex; align-items: center; gap: 10px; }
            .agri-bot-avatar { font-size: 24px; background: #065F46; padding: 6px; border-radius: 50%; }
            .agri-bot-name { margin: 0; font-size: 15px; font-weight: 600; color: #10B981; }
            .agri-chat-loc { font-size: 11px; color: #94A3B8; }

            .agri-chat-controls { display: flex; align-items: center; gap: 6px; }
            .agri-chat-select {
                background: #0F172A;
                color: #E2E8F0;
                border: 1px solid #475569;
                border-radius: 6px;
                padding: 4px 6px;
                font-size: 12px;
            }
            .agri-chat-icon-btn {
                background: #334155;
                color: #E2E8F0;
                border: none;
                border-radius: 6px;
                padding: 4px 8px;
                font-size: 12px;
                cursor: pointer;
            }
            .agri-chat-icon-btn.active { background: #059669; color: white; font-weight: bold; }

            .agri-chat-chips-scroll {
                display: flex;
                gap: 8px;
                padding: 8px 12px;
                background: #0B1329;
                overflow-x: auto;
                white-space: nowrap;
                border-bottom: 1px solid #1E293B;
            }
            .agri-chip {
                background: #1E293B;
                color: #38BDF8;
                border: 1px solid #0284C7;
                border-radius: 12px;
                padding: 4px 10px;
                font-size: 11px;
                cursor: pointer;
            }
            .agri-chip:hover { background: #0284C7; color: white; }

            .agri-chat-body {
                flex: 1;
                padding: 16px;
                overflow-y: auto;
                display: flex;
                flex-direction: column;
                gap: 12px;
            }
            .chat-msg { display: flex; flex-direction: column; }
            .bot-msg { align-items: flex-start; }
            .user-msg { align-items: flex-end; }
            .msg-bubble {
                max-width: 85%;
                padding: 10px 14px;
                border-radius: 12px;
                font-size: 13px;
                line-height: 1.5;
                white-space: pre-wrap;
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
            }
            .agri-img-preview-bar.hidden { display: none; }
            #agri-preview-thumb { width: 32px; height: 32px; border-radius: 4px; object-fit: cover; }
            .preview-text { font-size: 12px; color: #10B981; flex: 1; }
            .remove-img-btn { background: none; border: none; color: #EF4444; font-size: 14px; cursor: pointer; }

            .agri-chat-footer {
                padding: 10px;
                background: #1E293B;
                display: flex;
                align-items: center;
                gap: 8px;
                border-top: 1px solid #334155;
            }
            .agri-attach-btn { cursor: pointer; font-size: 18px; padding: 4px; }
            .agri-attach-btn input { display: none; }
            .agri-voice-btn { background: none; border: none; font-size: 18px; cursor: pointer; padding: 4px; }
            .agri-voice-btn.listening-pulse { animation: pulse-red 1s infinite; }
            @keyframes pulse-red { 0% { transform: scale(1); } 50% { transform: scale(1.3); } 100% { transform: scale(1); } }

            .agri-chat-input-field {
                flex: 1;
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
            }
        `;
        document.head.appendChild(style);
    },

    openChatWindow() {
        const win = document.getElementById("agri-chat-window");
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
                    selectEl.innerHTML = data.languages.map(l => 
                        `<option value="${l.code}">${l.flag} ${l.native}</option>`
                    ).join("");
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

            const activeFarmId = window.AgriState ? window.AgriState.activeFarmId : null;

            const payload = {
                query: query || "Diagnose this crop leaf image for pests or diseases.",
                language: this.selectedLanguage,
                location: this.userLocation,
                latitude: this.latitude,
                longitude: this.longitude,
                crop_type: this.userCrop,
                farm_id: activeFarmId,
                image_base64: this.attachedImageBase64,
                enable_web_search: this.webSearchEnabled
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

            const data = await response.json();
            this.removeMessage(typingId);
            this.clearImageAttachment();

            if (data.status === "success") {
                this.appendMessage(data.answer, "bot");
            } else {
                const errorMsg = data.detail || "Sorry, I could not process your query at this moment. Please try again.";
                this.appendMessage(`⚠️ ${errorMsg}`, "bot");
            }
        } catch (err) {
            this.removeMessage(typingId);
            this.appendMessage("❌ Network error connecting to AgriSense AI. Please check your internet connection.", "bot");
        }
    },

    appendMessage(text, sender) {
        const msgContainer = document.getElementById("agri-chat-messages");
        if (!msgContainer) return null;

        const id = "msg-" + Date.now() + "-" + Math.random().toString(36).substr(2, 4);
        const msgDiv = document.createElement("div");
        msgDiv.id = id;
        msgDiv.className = `chat-msg ${sender}-msg`;

        // Format markdown basic bold/newlines
        const formattedText = text
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\[(.*?)\]\((.*?)\)/g, '<a href="$2" target="_blank" style="color: #38BDF8; text-decoration: underline;">$1</a>');

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

// AUTO INITIALIZE CHATBOT ON DOM LOAD
document.addEventListener("DOMContentLoaded", () => {
    AgriSenseChatbot.init();
});
