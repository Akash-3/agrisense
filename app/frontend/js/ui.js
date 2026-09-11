/**
 * AgriSense UI Controller & SPA View Navigation Manager
 * Connected to FastAPI SQLite Database & Live Hardware Ingest
 */
const UI = {
    currentView: "dashboard",

    init() {
        this.bindEvents();
        this.renderAll();
        
        // Trigger smooth entrance animation on initial page load / refresh
        const authScreen = document.getElementById('authScreen');
        const loginCard = document.getElementById('loginCard');
        const activeDash = document.getElementById('pageDashboard');

        if (authScreen && !authScreen.classList.contains('hidden') && loginCard) {
            loginCard.classList.remove('animate-view-entrance');
            void loginCard.offsetWidth;
            loginCard.classList.add('animate-view-entrance');
        } else if (activeDash) {
            activeDash.classList.remove('animate-view-entrance');
            void activeDash.offsetWidth;
            activeDash.classList.add('animate-view-entrance');
        }

        // Start live telemetry simulation ticker
        window.AgriState.startLiveTelemetryLoop((t) => {
            this.renderTelemetryValues(t);
        });

        // Subscribe to Drone Status updates
        window.DroneService.subscribe((drone) => {
            this.renderDroneState(drone);
        });
    },

    bindEvents() {
        // Mobile Sidebar Toggle
        const menuBtn = document.getElementById('mobileMenuBtn');
        const sidebar = document.getElementById('sidebar');
        const overlay = document.getElementById('sidebarOverlay');

        if (menuBtn && sidebar && overlay) {
            menuBtn.addEventListener('click', () => {
                sidebar.classList.remove('-translate-x-full');
                overlay.classList.remove('hidden');
            });

            overlay.addEventListener('click', () => {
                sidebar.classList.add('-translate-x-full');
                overlay.classList.add('hidden');
            });
        }
    },

    switchAuthTab(tab) {
        const loginCard = document.getElementById('loginCard');
        const regCard = document.getElementById('registerCard');
        const btnLogin = document.getElementById('authTabLogin');
        const btnReg = document.getElementById('authTabReg');

        if (tab === 'login') {
            loginCard.classList.remove('hidden');
            regCard.classList.add('hidden');
            btnLogin.className = 'flex-1 py-2.5 rounded-lg text-xs font-bold btn-agri-primary transition';
            btnReg.className = 'flex-1 py-2.5 rounded-lg text-xs font-bold text-slate-600 hover:text-slate-900 transition';
        } else {
            loginCard.classList.add('hidden');
            regCard.classList.remove('hidden');
            btnReg.className = 'flex-1 py-2.5 rounded-lg text-xs font-bold btn-agri-primary transition';
            btnLogin.className = 'flex-1 py-2.5 rounded-lg text-xs font-bold text-slate-600 hover:text-slate-900 transition';
        }
    },

    togglePassVisibility() {
        const input = document.getElementById('loginPassInput');
        const icon = document.getElementById('eyeIcon');
        if (input.type === 'password') {
            input.type = 'text';
            icon.className = 'fa-solid fa-eye text-sm';
        } else {
            input.type = 'password';
            icon.className = 'fa-solid fa-eye-slash text-sm';
        }
    },

    // ==================== AUTHENTICATION DELEGATION TO AUTHSERVICE ====================
    async submitLogin() {
        const idInput = document.getElementById('loginIdInput').value.trim();
        const passInput = document.getElementById('loginPassInput').value.trim();

        if (!idInput || !passInput) {
            this.showToast('Please enter your email/phone and password.', true);
            return;
        }

        this.showToast('Verifying credentials against database...', false);
        const data = await window.AuthService.login(idInput, passInput);

        if (data.status === 'success' && data.farmer) {
            const farmer = data.farmer;
            window.AgriState.currentUser = {
                id: farmer.id || 1,
                isDemoMode: false,
                name: farmer.full_name || idInput,
                email: farmer.phone_or_email || idInput,
                phone: farmer.phone || "+1 (555) 019-2834",
                country: farmer.country || "United States",
                country_code: farmer.country_code || "+1",
                address: farmer.address || "",
                city: farmer.city || "",
                state: farmer.state || "",
                postal_code: farmer.postal_code || "",
                farmName: farmer.farm_name || "Green Valley Field Plot",
                farmSize: farmer.farm_acres || 15.0,
                location: "Lat: 20.2961, Lon: 85.8245",
                avatar: farmer.full_name ? farmer.full_name.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase() : "AV"
            };

            this.renderUser();
            this.switchView('dashboard');
            this.showToast(`✅ Welcome back, ${window.AgriState.currentUser.name}!`, false);
        } else {
            this.showToast(data.detail || data.message || 'Invalid credentials or locked account.', true);
        }
    },

    async submitDemoLogin() {
        this.showToast('🚜 Initializing AgriSense Demo Session...', false);
        const data = await window.AuthService.demoLogin();

        if (data.status === 'success' && data.farmer) {
            const farmer = data.farmer;
            window.AgriState.currentUser = {
                id: farmer.id || 1,
                isDemoMode: true,
                name: farmer.full_name || "Alex Vance",
                email: farmer.phone_or_email || "demo.farmer@agrisense.io",
                phone: "+1 (555) 019-2834",
                country: farmer.country || "United States",
                country_code: farmer.country_code || "+1",
                address: farmer.address || "",
                city: farmer.city || "",
                state: farmer.state || "",
                postal_code: farmer.postal_code || "",
                farmName: farmer.farm_name || "Green Valley Field Plot",
                farmSize: farmer.farm_acres || 15.0,
                location: "Lat: 20.2961, Lon: 85.8245",
                avatar: "AV"
            };

            this.renderUser();
            this.switchView('dashboard');
            this.showToast(`🚜 Welcome to AgriSense! Demo account active.`, false);
        }
    },

    async submitRegister() {
        const name = document.getElementById('regName').value.trim();
        const email = document.getElementById('regEmail').value.trim();
        const farm = document.getElementById('regFarm').value.trim();
        const acres = parseFloat(document.getElementById('regAcres').value) || 10.0;
        const pass = document.getElementById('regPass').value.trim();

        if (!name || !email || !pass) {
            this.showToast('Please fill in all required fields.', true);
            return;
        }

        this.showToast('Registering farmer in SQLite database...', false);
        const data = await window.AuthService.register({
            full_name: name,
            phone_or_email: email,
            farm_name: farm || "Main Farm Plot",
            farm_acres: acres,
            password: pass,
            crop_type: "Wheat & Paddy"
        });

        if (data.status === 'success') {
            this.showToast('✅ Account registered successfully! Signing in...', false);
            document.getElementById('loginIdInput').value = email;
            document.getElementById('loginPassInput').value = pass;
            this.submitLogin();
        } else {
            this.showToast(data.detail || data.message || 'Registration failed.', true);
        }
    },

    currentSSOProvider: "google",

    submitSSO(provider) {
        this.openSSOModal(provider);
    },

    openSSOModal(provider = "google") {
        this.currentSSOProvider = provider;
        const modal = document.getElementById('ssoModal');
        const icon = document.getElementById('ssoProviderIcon');
        const title = document.getElementById('ssoModalTitle');
        const subtitle = document.getElementById('ssoModalSubtitle');
        const btnText = document.getElementById('ssoBtnText');
        const emailInput = document.getElementById('ssoEmailInput');
        const nameInput = document.getElementById('ssoNameInput');

        const isGoogle = provider.toLowerCase() === 'google';
        if (icon) {
            icon.className = isGoogle ? "fa-brands fa-google text-red-500" : "fa-brands fa-microsoft text-blue-500";
        }
        if (title) title.innerText = isGoogle ? "Sign in with Google" : "Sign in with Microsoft";
        if (subtitle) subtitle.innerText = isGoogle ? "Select or enter your Gmail address to register or sign in" : "Select or enter your Microsoft / Outlook email address";
        if (btnText) btnText.innerText = isGoogle ? "Continue with Google" : "Continue with Microsoft";

        const loginVal = document.getElementById('loginIdInput') ? document.getElementById('loginIdInput').value.trim() : "";
        const regEmailVal = document.getElementById('regEmail') ? document.getElementById('regEmail').value.trim() : "";
        
        if (emailInput) {
            emailInput.value = loginVal || regEmailVal || "";
            if (isGoogle && !emailInput.value.includes('@')) {
                emailInput.placeholder = "user@gmail.com";
            } else if (!isGoogle && !emailInput.value.includes('@')) {
                emailInput.placeholder = "user@outlook.com";
            }
        }
        if (nameInput) {
            const regNameVal = document.getElementById('regName') ? document.getElementById('regName').value.trim() : "";
            nameInput.value = regNameVal || "";
        }

        if (modal) modal.classList.remove('hidden');
        if (emailInput) setTimeout(() => emailInput.focus(), 100);
    },

    closeSSOModal() {
        const modal = document.getElementById('ssoModal');
        if (modal) modal.classList.add('hidden');
    },

    async submitSSOModal() {
        const email = document.getElementById('ssoEmailInput').value.trim();
        const fullName = document.getElementById('ssoNameInput').value.trim();
        const provider = this.currentSSOProvider || "google";

        if (!email || !email.includes('@')) {
            this.showToast('Please enter a valid email address e.g. user@gmail.com', true);
            return;
        }

        this.showToast(`Connecting to ${provider.toUpperCase()} SSO as ${email}...`, false);
        const data = await window.AuthService.sso(provider, email, fullName);

        if (data.status === 'success') {
            const farmer = data.farmer || {};
            window.AgriState.currentUser = {
                id: farmer.id || 1,
                isDemoMode: false,
                name: farmer.full_name || (fullName || email.split('@')[0].toUpperCase()),
                email: farmer.phone_or_email || email,
                phone: farmer.phone || "+1 (555) 019-2834",
                country: farmer.country || "United States",
                country_code: farmer.country_code || "+1",
                address: farmer.address || "",
                city: farmer.city || "",
                state: farmer.state || "",
                postal_code: farmer.postal_code || "",
                farmName: farmer.farm_name || "Green Valley Field Plot",
                farmSize: farmer.farm_acres || 10.0,
                location: "Lat: 20.2961, Lon: 85.8245",
                avatar: farmer.full_name ? farmer.full_name.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase() : "AV"
            };

            this.closeSSOModal();
            this.renderUser();
            this.switchView('dashboard');
            this.showToast(`✅ Authenticated as ${email} via ${provider.toUpperCase()} SSO!`, false);
        } else {
            this.showToast(data.detail || data.message || 'SSO authentication failed.', true);
        }
    },

    updatePhoneCountryCode() {
        const countrySelect = document.getElementById('profCountry');
        const phoneInput = document.getElementById('profPhone');
        if (!countrySelect || !phoneInput) return;

        const selectedOption = countrySelect.options[countrySelect.selectedIndex];
        const dialCode = selectedOption ? selectedOption.getAttribute('data-code') || '+1' : '+1';

        let currentPhone = phoneInput.value.trim();
        // Strip out existing dial code if present (e.g. +1, +91, +44, etc.)
        currentPhone = currentPhone.replace(/^\+\d{1,4}\s*/, '');

        if (currentPhone) {
            phoneInput.value = `${dialCode} ${currentPhone}`;
        } else {
            phoneInput.value = `${dialCode} `;
        }
    },

    // ==================== REAL DATABASE PROFILE UPDATE ====================
    async submitProfileUpdate() {
        const name = document.getElementById('profName').value.trim();
        const email = document.getElementById('profEmail').value.trim();
        const phone = document.getElementById('profPhone').value.trim();

        const countrySelect = document.getElementById('profCountry');
        const country = countrySelect ? countrySelect.value : "United States";
        const selectedOpt = countrySelect ? countrySelect.options[countrySelect.selectedIndex] : null;
        const countryCode = selectedOpt ? (selectedOpt.getAttribute('data-code') || "+1") : "+1";

        const address = document.getElementById('profAddress') ? document.getElementById('profAddress').value.trim() : "";
        const city = document.getElementById('profCity') ? document.getElementById('profCity').value.trim() : "";
        const state = document.getElementById('profState') ? document.getElementById('profState').value.trim() : "";
        const postalCode = document.getElementById('profPostalCode') ? document.getElementById('profPostalCode').value.trim() : "";

        const farmName = document.getElementById('profFarmName').value.trim();
        const farmAcres = parseFloat(document.getElementById('profFarmAcres').value) || 15.0;
        const cropType = document.getElementById('profCropType').value.trim();
        const location = document.getElementById('profLocation').value.trim();

        if (!name || !email) {
            this.showToast('Full name and email are required.', true);
            return;
        }

        try {
            this.showToast('Saving profile updates...', false);
            const res = await fetch('/api/v1/auth/profile/update', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    farmer_id: window.AgriState.currentUser.id || 1,
                    full_name: name,
                    phone_or_email: email,
                    phone: phone,
                    country: country,
                    country_code: countryCode,
                    address: address,
                    city: city,
                    state: state,
                    postal_code: postalCode,
                    farm_name: farmName,
                    farm_acres: farmAcres,
                    crop_type: cropType,
                    location: location
                })
            });

            const data = await res.json();
            if (res.ok && data.status === 'success') {
                // Update local state
                window.AgriState.currentUser.name = name;
                window.AgriState.currentUser.email = email;
                window.AgriState.currentUser.phone = phone;
                window.AgriState.currentUser.country = country;
                window.AgriState.currentUser.country_code = countryCode;
                window.AgriState.currentUser.address = address;
                window.AgriState.currentUser.city = city;
                window.AgriState.currentUser.state = state;
                window.AgriState.currentUser.postal_code = postalCode;
                window.AgriState.currentUser.farmName = farmName;
                window.AgriState.currentUser.farmSize = farmAcres;
                window.AgriState.currentUser.location = location;
                window.AgriState.currentUser.avatar = name.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase();

                // Update primary farm in array
                const farm = window.AgriState.farms[0];
                if (farm) {
                    farm.name = farmName;
                    farm.acres = farmAcres;
                    farm.cropType = cropType;
                }

                this.renderUser();
                this.renderFarmsList();
                this.showToast('✅ Profile & Address details updated in database!', false);
            } else {
                this.showToast(data.detail || data.message || 'Profile update failed.', true);
            }
        } catch (_) {
            // Fallback state update
            window.AgriState.currentUser.name = name;
            window.AgriState.currentUser.email = email;
            window.AgriState.currentUser.phone = phone;
            window.AgriState.currentUser.country = country;
            window.AgriState.currentUser.country_code = countryCode;
            window.AgriState.currentUser.address = address;
            window.AgriState.currentUser.city = city;
            window.AgriState.currentUser.state = state;
            window.AgriState.currentUser.postal_code = postalCode;
            window.AgriState.currentUser.farmName = farmName;
            window.AgriState.currentUser.farmSize = farmAcres;
            this.renderUser();
            this.showToast('✅ Profile updated locally!', false);
        }
    },

    // ==================== CSV EXPORT FOR TELEMETRY ====================
    exportTelemetryCSV() {
        const t = window.AgriState.telemetry;
        const now = new Date().toISOString();
        
        let csvContent = "data:text/csv;charset=utf-8,";
        csvContent += "Timestamp,Device_ID,Soil_Moisture_VWC_Pct,Soil_Status,Temperature_C,DHT_Status,Humidity_Pct,Air_Quality_MQ135_PPM,MQ135_Status,Pathogen_Risk_Pct,CHI_Score,SNIR_Ratio,Clear_Channel,NIR_885nm_Counts\n";
        csvContent += `"${now}","ESP32_AgriSense_01",${t.soilMoisture.toFixed(2)},"${t.soilStatus}",${t.temperatureC.toFixed(2)},"${t.dhtStatus}",${t.humidity.toFixed(2)},${Math.round(t.airQualityPpm)},"${t.mq135Status}",${t.pathogenRiskPct.toFixed(2)},${t.chiScore.toFixed(2)},${t.snirRatio.toFixed(2)},${t.clearChannel},${t.as7341Channels[9] || 6893}\n`;

        const encodedUri = encodeURI(csvContent);
        const link = document.createElement("a");
        link.setAttribute("href", encodedUri);
        link.setAttribute("download", `AgriSense_Telemetry_Export_${Date.now()}.csv`);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);

        this.showToast('📥 Telemetry dataset downloaded to CSV!', false);
    },

    switchView(viewName) {
        this.currentView = viewName;
        this.closeFieldDetailPanel();

        const pages = [
            'pageDashboard', 'pageMap', 'pageDroneStation', 'pageMissionPlanner',
            'pageAnalytics', 'pageScenarios', 'pageTelemetry', 'pageAlerts',
            'pageSettings', 'pageProfile', 'pageFarms'
        ];

        if (viewName === 'auth') {
            document.getElementById('authScreen').classList.remove('hidden');
            document.getElementById('mainAppScreen').classList.add('hidden');
            return;
        }

        document.getElementById('authScreen').classList.add('hidden');
        document.getElementById('mainAppScreen').classList.remove('hidden');

        pages.forEach(p => {
            const el = document.getElementById(p);
            if (el) el.classList.add('hidden');
        });

        // Show active page with smooth entrance keyframe animation & staggered cards
        const activePageId = 'page' + viewName.charAt(0).toUpperCase() + viewName.slice(1);
        const activeEl = document.getElementById(activePageId);
        if (activeEl) {
            activeEl.classList.remove('hidden');
            activeEl.classList.remove('animate-view-entrance');
            void activeEl.offsetWidth; // Force reflow to re-trigger animation
            activeEl.classList.add('animate-view-entrance');

            // Apply staggered entrance animation to cards inside active view
            const cards = activeEl.querySelectorAll('.card-agri');
            cards.forEach((card, idx) => {
                const staggerClass = `stagger-card-${(idx % 4) + 1}`;
                card.classList.remove('stagger-card-1', 'stagger-card-2', 'stagger-card-3', 'stagger-card-4');
                void card.offsetWidth;
                card.classList.add(staggerClass);
            });
        }

        // Update sidebar active nav highlights
        document.querySelectorAll('.nav-link').forEach(link => {
            link.classList.remove('nav-item-active');
            if (link.dataset.view === viewName) {
                link.classList.add('nav-item-active');
            }
        });

        // Trigger view-specific initializations
        if (viewName === 'dashboard') {
            window.ChartService.initDashboardSparklines();
            window.ChartService.initDashboardFieldTrends('dashboardTrendChart');
        } else if (viewName === 'map') {
            window.MapService.init('mapContainer');
        } else if (viewName === 'analytics') {
            window.ChartService.initAnalyticsTrends('analyticsTrendChart');
            window.ChartService.initAnalyticsSoilTemp('analyticsSoilTempChart');
        } else if (viewName === 'scenarios') {
            window.ChartService.initScenarioChart('scenarioSimChart', window.AgriState.activeScenario);
        } else if (viewName === 'missionPlanner') {
            window.MapService.init('plannerMapContainer');
        } else if (viewName === 'telemetry') {
            this.renderTelemetryTable();
        } else if (viewName === 'profile') {
            this.populateProfileForm();
        }

        // Close mobile drawer if open
        const sidebar = document.getElementById('sidebar');
        const overlay = document.getElementById('sidebarOverlay');
        if (sidebar && overlay) {
            sidebar.classList.add('-translate-x-full');
            overlay.classList.add('hidden');
        }

        window.scrollTo(0, 0);
    },

    populateProfileForm() {
        const u = window.AgriState.currentUser;
        if (document.getElementById('profName')) document.getElementById('profName').value = u.name || "Alex Vance";
        if (document.getElementById('profEmail')) document.getElementById('profEmail').value = u.email || "farmer@agrisense.io";
        if (document.getElementById('profPhone')) document.getElementById('profPhone').value = u.phone || "+1 (555) 019-2834";
        if (document.getElementById('profCountry') && u.country) document.getElementById('profCountry').value = u.country;
        if (document.getElementById('profAddress')) document.getElementById('profAddress').value = u.address || "";
        if (document.getElementById('profCity')) document.getElementById('profCity').value = u.city || "";
        if (document.getElementById('profState')) document.getElementById('profState').value = u.state || "";
        if (document.getElementById('profPostalCode')) document.getElementById('profPostalCode').value = u.postal_code || "";
        if (document.getElementById('profFarmName')) document.getElementById('profFarmName').value = u.farmName || "Green Valley Field Plot";
        if (document.getElementById('profFarmAcres')) document.getElementById('profFarmAcres').value = u.farmSize || 15.0;
        if (document.getElementById('profCropType')) document.getElementById('profCropType').value = "Wheat & Paddy";
        if (document.getElementById('profLocation')) document.getElementById('profLocation').value = u.location || "Sector A-14, Odisha (Lat: 20.2961, Lon: 85.8245)";

        const lastChangedEl = document.getElementById('profLastChangedText');
        if (lastChangedEl) {
            if (u.password_updated_at) {
                const dt = new Date(u.password_updated_at * 1000);
                lastChangedEl.innerText = `Last changed: ${dt.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}`;
            } else {
                lastChangedEl.innerText = `Last changed: Never`;
            }
        }
    },

    renderAll() {
        this.renderUser();
        this.renderTelemetryValues(window.AgriState.telemetry);
        this.renderDroneState(window.DroneService.getPrimaryDrone());
        this.renderNotifications();
        this.renderFarmsList();
        this.renderHardwareStatus();
    },

    renderHardwareStatus() {
        const isOnline = window.AgriState.hardwareStatus === "ONLINE";
        
        // Top Bar Badge
        const topBadge = document.getElementById('topTelemetryBadge');
        if (topBadge) {
            if (isOnline) {
                topBadge.innerHTML = `<span class="w-2 h-2 rounded-full bg-emerald-500 animate-ping"></span><span>LIVE SENSORS STREAM</span>`;
                topBadge.className = 'px-3 py-1 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800 border border-emerald-300 flex items-center space-x-1.5 cursor-pointer';
            } else {
                topBadge.innerHTML = `<span class="w-2 h-2 rounded-full bg-red-500"></span><span>⚠️ SENSORS OFFLINE</span>`;
                topBadge.className = 'px-3 py-1 rounded-full text-xs font-bold bg-red-100 text-red-800 border border-red-300 flex items-center space-x-1.5 cursor-pointer';
            }
        }

        // Offline Alert Banner on Dashboard
        const dashAlert = document.getElementById('dashHardwareAlert');
        if (dashAlert) {
            if (isOnline) dashAlert.classList.add('hidden');
            else dashAlert.classList.remove('hidden');
        }

        // Telemetry Page Hardware Status Badge
        const telemBadge = document.getElementById('telemHardwareStatusBadge');
        if (telemBadge) {
            if (isOnline) {
                telemBadge.innerHTML = `<span class="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse"></span><span>100% ONLINE</span>`;
                telemBadge.className = 'text-xl font-black text-emerald-600 flex items-center space-x-2';
            } else {
                telemBadge.innerHTML = `<span class="w-2.5 h-2.5 rounded-full bg-red-500"></span><span>OFFLINE (NO SENSOR DATA)</span>`;
                telemBadge.className = 'text-xl font-black text-red-600 flex items-center space-x-2';
            }
        }
    },

    renderUser() {
        const u = window.AgriState.currentUser;
        document.querySelectorAll('.user-name').forEach(el => el.innerText = u.name);
        document.querySelectorAll('.user-email').forEach(el => el.innerText = u.email);
        document.querySelectorAll('.user-avatar').forEach(el => el.innerText = u.avatar);
        document.querySelectorAll('.user-farm').forEach(el => el.innerText = `${u.farmName} (${u.farmSize} Acres)`);

        const demoBadge = document.getElementById('headerDemoBadge');
        if (demoBadge) {
            if (u.isDemoMode) {
                demoBadge.innerHTML = `<span class="w-2 h-2 rounded-full bg-amber-500 animate-ping"></span><span>● DEMO MODE</span>`;
                demoBadge.className = 'flex items-center space-x-1.5 px-3 py-1 rounded-full bg-amber-50 border border-amber-300 text-amber-800 text-xs font-black tracking-wider';
            } else {
                demoBadge.innerHTML = `<span class="w-2 h-2 rounded-full bg-emerald-500"></span><span>● LIVE SESSION</span>`;
                demoBadge.className = 'flex items-center space-x-1.5 px-3 py-1 rounded-full bg-emerald-50 border border-emerald-300 text-emerald-800 text-xs font-black tracking-wider';
            }
        }
    },

    renderTelemetryValues(t) {
        // Soil Moisture
        const soilVal = document.getElementById('soilVal');
        if (soilVal) soilVal.innerText = `${t.soilMoisture.toFixed(1)}%`;

        // Temperature
        const tempVal = document.getElementById('tempVal');
        if (tempVal) tempVal.innerText = window.AgriState.getFormattedTemp(t.temperatureC);

        // Air Quality
        const airVal = document.getElementById('airVal');
        if (airVal) airVal.innerText = `${Math.round(t.airQualityPpm)} PPM`;

        // Pathogen Risk
        const riskVal = document.getElementById('riskVal');
        if (riskVal) riskVal.innerText = `${t.pathogenRiskPct.toFixed(1)}%`;

        // Crop Condition Card
        const condition = window.AgriState.getCropConditionState();
        const condBadge = document.getElementById('cropConditionBadge');
        if (condBadge) {
            condBadge.innerText = condition.label;
            condBadge.style.backgroundColor = condition.bg;
            condBadge.style.color = condition.color;
        }

        const condAdv = document.getElementById('cropConditionAdvice');
        if (condAdv) condAdv.innerText = t.recommendedAction;

        const chiVal = document.getElementById('chiVal');
        if (chiVal) chiVal.innerText = `${t.chiScore.toFixed(1)} / 100`;

        const leadVal = document.getElementById('leadVal');
        if (leadVal) leadVal.innerText = `${t.leadTimeDays} Days Early`;

        // Live update Telemetry table if active
        if (this.currentView === 'telemetry') {
            this.renderTelemetryTable();
        }
    },

    renderTelemetryTable() {
        const t = window.AgriState.telemetry;
        
        // Soil Row
        const tSoil = document.getElementById('tSoilVal');
        if (tSoil) tSoil.innerText = `${t.soilMoisture.toFixed(1)}% VWC`;

        // Temp Row
        const tTemp = document.getElementById('tTempVal');
        if (tTemp) tTemp.innerText = window.AgriState.getFormattedTemp(t.temperatureC);

        // Humidity Row
        const tHum = document.getElementById('tHumVal');
        if (tHum) tHum.innerText = `${t.humidity.toFixed(1)}%`;

        // Smoke Row
        const tSmoke = document.getElementById('tSmokeVal');
        if (tSmoke) tSmoke.innerText = `${Math.round(t.airQualityPpm)} PPM`;

        // Pathogen Risk Row
        const tRisk = document.getElementById('tRiskVal');
        if (tRisk) tRisk.innerText = `${t.pathogenRiskPct.toFixed(1)}%`;

        // CHI Row
        const tChi = document.getElementById('tChiVal');
        if (tChi) tChi.innerText = `${t.chiScore.toFixed(1)} / 100`;

        // Clear Lux Row
        const tClear = document.getElementById('tClearVal');
        if (tClear) tClear.innerText = `${t.clearChannel.toLocaleString()} Lux`;

        // NIR Row
        const tNir = document.getElementById('tNirVal');
        if (tNir) tNir.innerText = `${(t.as7341Channels[9] || 6893).toLocaleString()} counts`;
    },

    renderDroneState(drone) {
        const badge = document.getElementById('headerDroneStatus');
        if (badge) {
            badge.innerText = `${drone.id} • ${drone.status} (${drone.battery}%)`;
            if (drone.status === "MISSION_ACTIVE") {
                badge.className = "px-3 py-1 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800 border border-emerald-300 animate-pulse";
            } else if (drone.status === "ERROR") {
                badge.className = "px-3 py-1 rounded-full text-xs font-bold bg-red-100 text-red-800 border border-red-300";
            } else {
                badge.className = "px-3 py-1 rounded-full text-xs font-bold bg-slate-100 text-slate-700 border border-slate-200";
            }
        }

        // Drone Station Tab Updates
        const statusEl = document.getElementById('droneStateText');
        if (statusEl) statusEl.innerText = drone.status;

        const battEl = document.getElementById('droneBattText');
        if (battEl) battEl.innerText = `${Math.round(drone.battery)}%`;

        const altEl = document.getElementById('droneAltText');
        if (altEl) altEl.innerText = `${drone.altitude.toFixed(1)} m`;

        const speedEl = document.getElementById('droneSpeedText');
        if (speedEl) speedEl.innerText = `${drone.speed.toFixed(1)} m/s`;

        const progEl = document.getElementById('droneProgText');
        if (progEl) progEl.innerText = `${drone.missionProgress}%`;

        const progBar = document.getElementById('droneProgBar');
        if (progBar) progBar.style.width = `${drone.missionProgress}%`;
    },

    renderNotifications() {
        const container = document.getElementById('notificationsList');
        if (!container) return;

        const unreadCount = window.AgriState.notifications.filter(n => !n.read).length;
        document.querySelectorAll('.unread-badge-count').forEach(b => {
            b.innerText = unreadCount;
            if (unreadCount === 0) b.classList.add('hidden');
            else b.classList.remove('hidden');
        });

        container.innerHTML = window.AgriState.notifications.map(n => `
            <div class="p-4 rounded-xl border ${n.read ? 'bg-white border-slate-200' : 'bg-emerald-50/50 border-emerald-200'} flex items-start justify-between space-x-3">
                <div class="flex items-start space-x-3">
                    <div class="w-8 h-8 rounded-lg ${n.severity === 'success' ? 'bg-emerald-100 text-emerald-700' : n.severity === 'warning' ? 'bg-amber-100 text-amber-700' : 'bg-blue-100 text-blue-700'} flex items-center justify-center font-bold text-sm shrink-0">
                        <i class="fa-solid ${n.severity === 'success' ? 'fa-circle-check' : n.severity === 'warning' ? 'fa-triangle-exclamation' : 'fa-bell'}"></i>
                    </div>
                    <div>
                        <div class="font-bold text-sm text-slate-900">${n.title}</div>
                        <div class="text-xs text-slate-600 mt-0.5">${n.message}</div>
                        <div class="text-[10px] text-slate-400 font-medium mt-1">${n.field} • ${n.timestamp}</div>
                    </div>
                </div>
                <button onclick="UI.markNotificationRead(${n.id})" class="text-xs text-slate-400 hover:text-emerald-600 font-bold">
                    ${n.read ? 'Read' : 'Mark Read'}
                </button>
            </div>
        `).join('');
    },

    markNotificationRead(id) {
        const item = window.AgriState.notifications.find(n => n.id === id);
        if (item) {
            item.read = true;
            this.renderNotifications();
            this.showToast('Notification updated.', false);
        }
    },

    markAllNotificationsRead() {
        window.AgriState.notifications.forEach(n => n.read = true);
        this.renderNotifications();
        this.showToast('All notifications marked as read.', false);
    },

    renderFarmsList() {
        const select = document.getElementById('farmSelect');
        if (!select) return;

        select.innerHTML = window.AgriState.farms.map(f => `
            <option value="${f.id}" ${f.id === window.AgriState.activeFarmId ? 'selected' : ''}>
                ${f.name} (${f.acres} Acres)
            </option>
        `).join('');
    },

    switchFarm(farmId) {
        window.AgriState.activeFarmId = parseInt(farmId);
        const f = window.AgriState.getActiveFarm();
        window.AgriState.currentUser.farmName = f.name;
        window.AgriState.currentUser.farmSize = f.acres;
        this.renderUser();
        this.showToast(`Switched active farm to ${f.name}.`, false);

        if (this.currentView === 'map') {
            window.MapService.init('mapContainer');
        }
    },

    showToast(message, isError = false) {
        const container = document.getElementById('toastContainer');
        const msgEl = document.getElementById('toastMessage');
        const iconBg = document.getElementById('toastIconBg');
        const icon = document.getElementById('toastIcon');

        if (!container || !msgEl) return;

        msgEl.innerText = message;
        if (isError) {
            iconBg.className = 'p-2.5 rounded-xl bg-red-500/20 text-red-400';
            icon.className = 'fa-solid fa-circle-exclamation text-lg';
        } else {
            iconBg.className = 'p-2.5 rounded-xl bg-emerald-500/20 text-emerald-400';
            icon.className = 'fa-solid fa-circle-check text-lg';
        }

        container.classList.remove('hidden');
        setTimeout(() => container.classList.add('hidden'), 4000);
    },

    showFieldDetailPanel(field, polygon) {
        const panel = document.getElementById('fieldDetailPanel');
        const backdrop = document.getElementById('fieldDetailBackdrop');
        if (!panel) return;

        // Set Values with fallback for data availability
        const nameEl = document.getElementById('panelFieldName');
        if (nameEl) nameEl.innerText = field.name || "Field Plot";

        const acresEl = document.getElementById('panelFieldAcres');
        if (acresEl) acresEl.innerText = field.acres ? `${field.acres} Acres` : "Not available";

        const cropEl = document.getElementById('panelFieldCrop');
        if (cropEl) cropEl.innerText = field.crop || "Not available";

        const acresMeta = document.getElementById('panelFieldAcresMeta');
        if (acresMeta) acresMeta.innerText = field.acres ? `${field.acres} Acres` : "Not available";

        const cropMeta = document.getElementById('panelFieldCropMeta');
        if (cropMeta) cropMeta.innerText = field.crop || "Not available";

        const healthEl = document.getElementById('panelFieldHealth');
        if (healthEl) healthEl.innerText = field.health !== undefined ? `${field.health.toFixed(1)} / 100` : "Not available";

        const hydEl = document.getElementById('panelFieldHydration');
        if (hydEl) hydEl.innerText = field.hydration !== undefined ? `${field.hydration.toFixed(1)}%` : "Not available";

        const riskEl = document.getElementById('panelFieldRisk');
        if (riskEl) riskEl.innerText = field.risk !== undefined ? `${field.risk.toFixed(1)}%` : "Not available";

        // Badges
        const healthBadge = document.getElementById('panelFieldHealthBadge');
        if (healthBadge && field.health !== undefined) {
            if (field.health >= 80) {
                healthBadge.innerText = "Excellent";
                healthBadge.className = "px-2.5 py-1 rounded-full bg-emerald-100 text-emerald-800 font-bold text-[11px]";
            } else if (field.health >= 60) {
                healthBadge.innerText = "Moderate";
                healthBadge.className = "px-2.5 py-1 rounded-full bg-amber-100 text-amber-800 font-bold text-[11px]";
            } else {
                healthBadge.innerText = "Attention Needed";
                healthBadge.className = "px-2.5 py-1 rounded-full bg-red-100 text-red-800 font-bold text-[11px]";
            }
        }

        const hydBadge = document.getElementById('panelFieldHydrationBadge');
        if (hydBadge && field.hydration !== undefined) {
            if (field.hydration >= 35) {
                hydBadge.innerText = "Optimal";
                hydBadge.className = "px-2.5 py-1 rounded-full bg-cyan-100 text-cyan-800 font-bold text-[11px]";
            } else {
                hydBadge.innerText = "Low VWC";
                hydBadge.className = "px-2.5 py-1 rounded-full bg-amber-100 text-amber-800 font-bold text-[11px]";
            }
        }

        const riskBadge = document.getElementById('panelFieldRiskBadge');
        if (riskBadge && field.risk !== undefined) {
            if (field.risk < 15) {
                riskBadge.innerText = "Low Risk";
                riskBadge.className = "px-2.5 py-1 rounded-full bg-emerald-100 text-emerald-800 font-bold text-[11px]";
            } else {
                riskBadge.innerText = "Elevated Risk";
                riskBadge.className = "px-2.5 py-1 rounded-full bg-rose-100 text-rose-800 font-bold text-[11px]";
            }
        }

        // Display panel & backdrop
        if (backdrop) {
            backdrop.classList.remove('opacity-0', 'pointer-events-none');
            backdrop.classList.add('opacity-100', 'pointer-events-auto');
        }

        panel.classList.remove('hidden');
        setTimeout(() => {
            panel.classList.remove('translate-y-full', 'md:translate-x-full');
            panel.classList.add('translate-y-0', 'md:translate-x-0');
        }, 10);
    },

    closeFieldDetailPanel() {
        const panel = document.getElementById('fieldDetailPanel');
        const backdrop = document.getElementById('fieldDetailBackdrop');

        if (panel) {
            panel.classList.remove('translate-y-0', 'md:translate-x-0');
            panel.classList.add('translate-y-full', 'md:translate-x-full');
        }
        if (backdrop) {
            backdrop.classList.remove('opacity-100', 'pointer-events-auto');
            backdrop.classList.add('opacity-0', 'pointer-events-none');
        }

        setTimeout(() => {
            if (panel) panel.classList.add('hidden');
        }, 300);

        if (window.MapService) {
            window.MapService.clearSelectedPolygon();
        }
    },

    closeAllModalsAndDrawers() {
        this.closeFieldDetailPanel();
        this.closeAddFarmModal();
        this.closeOTPAuthModal();
    },

    onPlannerFieldSelect(fieldId) {
        const id = parseInt(fieldId) || 1;
        if (window.MapService) {
            window.MapService.selectFieldById(id, false);
        }
    },

    openAddFarmModal() {
        document.getElementById('addFarmModal').classList.remove('hidden');
    },

    closeAddFarmModal() {
        document.getElementById('addFarmModal').classList.add('hidden');
    },

    async submitAddFarm() {
        const name = document.getElementById('newFarmName').value;
        const acres = parseFloat(document.getElementById('newFarmAcres').value);
        const crop = document.getElementById('newFarmCrop').value;

        if (!name || !acres) {
            this.showToast('Please enter a valid farm name and size.', true);
            return;
        }

        try {
            const res = await fetch('/api/v1/farms/add', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    farmer_id: window.AgriState.currentUser.id || 1,
                    farm_name: name,
                    farm_acres: acres,
                    crop_type: crop || "Wheat Plot"
                })
            });
            const data = await res.json();
            const newId = data.farm_id || (window.AgriState.farms.length + 1);

            window.AgriState.farms.push({
                id: newId,
                name: name,
                acres: acres,
                cropType: crop || "Wheat Plot",
                location: "Registered Plot",
                center: [20.2961, 85.8245],
                status: "Optimal",
                droneCoverage: "Scheduled"
            });

            this.switchFarm(newId);
            this.renderFarmsList();
            this.closeAddFarmModal();
            this.showToast(`Farm '${name}' registered in database!`, false);
        } catch (_) {
            const newId = window.AgriState.farms.length + 1;
            window.AgriState.farms.push({
                id: newId,
                name: name,
                acres: acres,
                cropType: crop || "Wheat Plot",
                location: "Registered Plot",
                center: [20.2961, 85.8245],
                status: "Optimal",
                droneCoverage: "Scheduled"
            });
            this.switchFarm(newId);
            this.renderFarmsList();
            this.closeAddFarmModal();
            this.showToast(`Farm '${name}' added!`, false);
        }
    },

    toggleTempUnit() {
        window.AgriState.settings.tempUnit = window.AgriState.settings.tempUnit === "C" ? "F" : "C";
        document.querySelectorAll('.temp-unit-label').forEach(el => el.innerText = `°${window.AgriState.settings.tempUnit}`);
        this.renderTelemetryValues(window.AgriState.telemetry);
        this.showToast(`Temperature unit set to °${window.AgriState.settings.tempUnit}.`, false);
    },

    // ==================== EMAIL OTP & ACCOUNT SECURITY FLOWS ====================
    otpState: {
        mode: 'change_password', // 'change_password' | 'forgot_password'
        email: '',
        fullName: '',
        step: 1,
        verifiedOtp: null,
        resendTimer: null,
        resendSeconds: 45
    },

    openChangePasswordModal() {
        const u = window.AgriState.currentUser;
        this.otpState = {
            mode: 'change_password',
            email: u.email || 'demo.farmer@agrisense.io',
            fullName: u.name || 'Farmer',
            step: 1,
            verifiedOtp: null,
            resendTimer: null,
            resendSeconds: 45
        };

        document.getElementById('otpModalTitle').innerText = 'Account Security Verification';
        document.getElementById('otpModalSubtitle').innerText = 'Verify email to modify account password';
        document.getElementById('otpDestinationLabel').innerText = 'Verification Code Destination';
        document.getElementById('otpMaskedEmailBox').classList.remove('hidden');
        document.getElementById('otpMaskedEmailBox').innerText = window.EmailOTPService.maskEmail(this.otpState.email);
        document.getElementById('otpUnmaskedEmailInput').classList.add('hidden');

        this.showOTPStep(1);
        document.getElementById('otpAuthModal').classList.remove('hidden');
    },

    openForgotPasswordModal() {
        const prefilledEmail = document.getElementById('loginIdInput')?.value.trim() || '';
        this.otpState = {
            mode: 'forgot_password',
            email: prefilledEmail,
            fullName: 'Farmer',
            step: 1,
            verifiedOtp: null,
            resendTimer: null,
            resendSeconds: 45
        };

        document.getElementById('otpModalTitle').innerText = 'Reset Forgotten Password';
        document.getElementById('otpModalSubtitle').innerText = 'Enter your registered email address to receive an OTP';
        document.getElementById('otpDestinationLabel').innerText = 'Registered Email Address';
        document.getElementById('otpMaskedEmailBox').classList.add('hidden');
        const emailInput = document.getElementById('otpUnmaskedEmailInput');
        emailInput.classList.remove('hidden');
        emailInput.value = prefilledEmail;

        this.showOTPStep(1);
        document.getElementById('otpAuthModal').classList.remove('hidden');
    },

    closeOTPAuthModal() {
        document.getElementById('otpAuthModal').classList.add('hidden');
        if (this.otpState.resendTimer) {
            clearInterval(this.otpState.resendTimer);
            this.otpState.resendTimer = null;
        }
    },

    showOTPStep(stepNum) {
        this.otpState.step = stepNum;
        [1, 2, 3, 4].forEach(s => {
            const el = document.getElementById(`otpStep${s}`);
            if (el) el.classList.toggle('hidden', s !== stepNum);
        });
    },

    async sendOTPCode() {
        if (this.otpState.mode === 'forgot_password') {
            const emailInput = document.getElementById('otpUnmaskedEmailInput').value.trim();
            if (!emailInput) {
                this.showToast('Please enter your registered email address.', true);
                return;
            }
            this.otpState.email = emailInput;
        }

        this.showToast('Sending OTP verification code to email...', false);

        let res;
        if (this.otpState.mode === 'change_password') {
            res = await window.EmailOTPService.sendPasswordChangeOTP(this.otpState.email, this.otpState.fullName);
        } else {
            res = await window.EmailOTPService.sendForgotPasswordOTP(this.otpState.email);
        }

        if (res.status === 'success') {
            this.showToast('✅ OTP code sent! Please check your email inbox.', false);
            this.showOTPStep(2);
            this.startResendTimer();
        } else {
            this.showToast(res.message, true);
        }
    },

    async resendOTPCode() {
        if (this.otpState.resendSeconds > 0) return;
        this.showToast('Resending OTP verification code...', false);
        await this.sendOTPCode();
    },

    startResendTimer() {
        if (this.otpState.resendTimer) clearInterval(this.otpState.resendTimer);
        this.otpState.resendSeconds = 45;

        const timerSecEl = document.getElementById('otpTimerSeconds');
        const resendBtn = document.getElementById('btnResendOTP');
        const countdownText = document.getElementById('otpCountdownText');

        if (timerSecEl) timerSecEl.innerText = '45';
        if (resendBtn) resendBtn.disabled = true;
        if (countdownText) countdownText.classList.remove('hidden');

        this.otpState.resendTimer = setInterval(() => {
            this.otpState.resendSeconds--;
            if (timerSecEl) timerSecEl.innerText = this.otpState.resendSeconds;

            if (this.otpState.resendSeconds <= 0) {
                clearInterval(this.otpState.resendTimer);
                this.otpState.resendTimer = null;
                if (resendBtn) resendBtn.disabled = false;
                if (countdownText) countdownText.classList.add('hidden');
            }
        }, 1000);
    },

    async verifyOTPCode() {
        const code = document.getElementById('otpCodeInput').value.trim();
        if (!code || code.length < 6) {
            this.showToast('Please enter the 6-digit OTP code.', true);
            return;
        }

        this.showToast('Verifying OTP code...', false);
        const res = await window.EmailOTPService.verifyOTP(this.otpState.email, code);

        if (res.status === 'success') {
            this.otpState.verifiedOtp = code;
            this.showToast('✅ OTP verified successfully!', false);
            this.showOTPStep(3);
        } else {
            this.showToast(res.message, true);
        }
    },

    checkPasswordStrength() {
        const pass = document.getElementById('otpNewPasswordInput').value;
        const evalRes = window.EmailOTPService.evaluatePasswordStrength(pass);

        const labelEl = document.getElementById('otpStrengthLabel');
        const barEl = document.getElementById('otpStrengthBar');

        if (labelEl) {
            labelEl.innerText = evalRes.label;
            labelEl.className = `font-bold ${evalRes.color}`;
        }
        if (barEl) {
            barEl.style.width = `${evalRes.score}%`;
            barEl.className = `h-full ${evalRes.barColor} transition-all duration-300`;
        }
    },

    toggleOTPPassVisibility(inputId, iconId) {
        const input = document.getElementById(inputId);
        const icon = document.getElementById(iconId);
        if (input && icon) {
            if (input.type === 'password') {
                input.type = 'text';
                icon.className = 'fa-solid fa-eye text-xs text-agri-primary';
            } else {
                input.type = 'password';
                icon.className = 'fa-solid fa-eye-slash text-xs text-slate-400';
            }
        }
    },

    async submitNewPassword() {
        const newPass = document.getElementById('otpNewPasswordInput').value;
        const confPass = document.getElementById('otpConfirmPasswordInput').value;

        if (!newPass || newPass.length < 6) {
            this.showToast('Password must be at least 6 characters long.', true);
            return;
        }
        if (newPass !== confPass) {
            this.showToast('New passwords do not match.', true);
            return;
        }

        this.showToast('Updating account password in database...', false);
        const res = await window.EmailOTPService.resetPassword(this.otpState.email, this.otpState.verifiedOtp, newPass);

        if (res.status === 'success') {
            if (res.password_updated_at) {
                window.AgriState.currentUser.password_updated_at = res.password_updated_at;
            } else {
                window.AgriState.currentUser.password_updated_at = Date.now() / 1000;
            }

            this.showToast('✅ Password updated successfully!', false);
            this.showOTPStep(4);
        } else {
            this.showToast(res.message, true);
        }
    },

    finishOTPPasswordFlow() {
        this.closeOTPAuthModal();
        if (this.otpState.mode === 'change_password') {
            this.populateProfileForm();
        } else {
            // Return to login screen
            this.switchView('auth');
            document.getElementById('loginIdInput').value = this.otpState.email;
            document.getElementById('loginPassInput').value = '';
            document.getElementById('loginPassInput').focus();
        }
    },

    async sendRealHardwareIngestPayload(moisture = 44.2, temp = 25.8, humidity = 65.0, smoke = 82.0) {
        try {
            const res = await fetch('/api/v1/telemetry/ingest', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    device_id: "ESP32_SOIL_NODE_01",
                    soil_moisture: moisture,
                    temperature: temp,
                    humidity: humidity,
                    smoke_ppm: smoke,
                    soil_status: "ONLINE",
                    dht_status: "ONLINE",
                    mq135_status: "ONLINE"
                })
            });
            if (res.ok) {
                window.AgriState.hardwareStatus = "ONLINE";
                window.AgriState.telemetry.soilMoisture = moisture;
                window.AgriState.telemetry.temperatureC = temp;
                window.AgriState.telemetry.humidity = humidity;
                window.AgriState.telemetry.airQualityPpm = smoke;
                window.AgriState.telemetry.isRealHardware = true;
                this.renderAll();
                this.showToast(`📡 Real Hardware Telemetry Ingested from ESP32_SOIL_NODE_01!`, false);
            }
        } catch (err) {
            this.showToast(`Hardware Ingest Exception: ${err}`, true);
        }
    }
};

window.UI = UI;

document.addEventListener('DOMContentLoaded', () => {
    window.UI.init();

    // Global ESC key listener to close open modals and drawers
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' || e.key === 'Esc') {
            if (window.UI) window.UI.closeAllModalsAndDrawers();
        }
    });
});
