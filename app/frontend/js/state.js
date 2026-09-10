/**
 * AgriSense Global State & Telemetry Simulation Layer
 */
const AgriState = {
    // Current Authenticated User State
    currentUser: {
        isAuthenticated: true,
        isDemoMode: true,
        name: "Alex Vance",
        email: "demo.farmer@agrisense.io",
        phone: "+1 (555) 019-2834",
        farmName: "Green Valley Field Plot",
        farmSize: 15.0,
        location: "Lat: 20.2961, Lon: 85.8245",
        avatar: "AV"
    },

    // Hardware Connection & Sensor Diagnostic State
    hardwareStatus: "OFFLINE", // "ONLINE" or "OFFLINE"

    toggleHardwareStatus() {
        this.hardwareStatus = this.hardwareStatus === "ONLINE" ? "OFFLINE" : "ONLINE";
        if (window.UI) {
            window.UI.renderHardwareStatus();
            window.UI.showToast(`Hardware Sensor Status: ${this.hardwareStatus}`, false);
        }
        return this.hardwareStatus;
    },

    // Settings Configuration
    settings: {
        tempUnit: "C", // "C" or "F"
        telemetryRefreshInterval: 5, // seconds
        defaultMapLayer: "satellite",
        notificationsEnabled: true,
        theme: "light"
    },

    // Active Selected Farm Index
    activeFarmId: 1,

    // Registered Farms List
    farms: [
        {
            id: 1,
            name: "Green Valley Field Plot",
            acres: 15.0,
            cropType: "Wheat & Paddy",
            location: "Sector A-14, Valley Basin",
            center: [20.2961, 85.8245],
            status: "Optimal",
            droneCoverage: "100% Completed"
        },
        {
            id: 2,
            name: "North Sector Plot",
            acres: 22.4,
            cropType: "Corn Canopy",
            location: "North Ridge 09",
            center: [20.3010, 85.8290],
            status: "Good",
            droneCoverage: "Scheduled Today"
        },
        {
            id: 3,
            name: "East Sector Plot",
            acres: 18.5,
            cropType: "Soybean",
            location: "East Border Plot B",
            center: [20.2915, 85.8350],
            status: "Optimal",
            droneCoverage: "85% Scanned"
        }
    ],

    // Live Telemetry Payload
    telemetry: {
        soilMoisture: 42.5, // %
        temperatureC: 26.1, // °C
        humidity: 68.4, // %
        airQualityPpm: 80, // PPM
        pathogenRiskPct: 9.9, // %
        chiScore: 85.0, // Crop Health Index out of 100
        leadTimeDays: 5.4, // Days early lead warning
        snirRatio: 6.89, // S_NIR NIR reflectance ratio
        clearChannel: 12400, // Lux light intensity
        soilStatus: "Optimal",
        dhtStatus: "Normal",
        mq135Status: "Clean Air",
        recommendedAction: "Optimal Crop Health: Leaf canopy NIR scattering & soil hydration levels are within target ranges.",
        as7341Channels: [450, 680, 920, 1450, 2800, 1600, 980, 520, 12400, 6893], // F1-F8, Clear, NIR
        lastUpdated: new Date()
    },

    // Crop Health Active Scenario
    activeScenario: "HEALTHY", // "HEALTHY", "FUNGAL", "DROUGHT", "FIRE"

    // Notifications List
    notifications: [
        {
            id: 1,
            severity: "success",
            title: "Crop Health Optimal",
            message: "Green Valley Field canopy NIR scattering & moisture levels are ideal.",
            timestamp: "10 mins ago",
            read: false,
            field: "Green Valley Field"
        },
        {
            id: 2,
            severity: "warning",
            title: "Soil Hydration Dropping",
            message: "Soil VWC in North Sector Plot dropped from 38% to 24%.",
            timestamp: "45 mins ago",
            read: false,
            field: "North Sector Plot"
        },
        {
            id: 3,
            severity: "info",
            title: "Autonomous Drone Mission Completed",
            message: "AGRIDRONE-01 completed multispectral scan of Plot A-14.",
            timestamp: "2 hours ago",
            read: true,
            field: "Green Valley Field"
        },
        {
            id: 4,
            severity: "warning",
            title: "Pre-Symptomatic Fungal Alert",
            message: "MM-SSNet model flagged subtle 480nm reflectance shift in Sector B.",
            timestamp: "5 hours ago",
            read: true,
            field: "East Sector Plot"
        }
    ],

    // Simulation Ticker handle
    simInterval: null,

    // Methods
    getFormattedTemp(celsiusVal) {
        if (this.settings.tempUnit === "F") {
            const f = (celsiusVal * 9/5) + 32;
            return `${f.toFixed(1)}°F`;
        }
        return `${celsiusVal.toFixed(1)}°C`;
    },

    getActiveFarm() {
        return this.farms.find(f => f.id === this.activeFarmId) || this.farms[0];
    },

    getCropConditionState() {
        const risk = this.telemetry.pathogenRiskPct;
        const soil = this.telemetry.soilMoisture;
        if (risk < 15 && soil > 35) return { label: "EXCELLENT", color: "#079A70", icon: "fa-circle-check", bg: "#EFFAF6" };
        if (risk < 25 && soil > 25) return { label: "GOOD", color: "#159B7A", icon: "fa-circle-check", bg: "#DDF4EC" };
        if (risk < 40) return { label: "MODERATE", color: "#F4A019", icon: "fa-triangle-exclamation", bg: "#FFF3DD" };
        if (risk < 60) return { label: "AT RISK", color: "#EF5B67", icon: "fa-circle-exclamation", bg: "#FDEBED" };
        return { label: "CRITICAL", color: "#B91C1C", icon: "fa-skull-crossbones", bg: "#FEE2E2" };
    },

    triggerScenario(scenarioKey) {
        this.activeScenario = scenarioKey;
        if (scenarioKey === "HEALTHY") {
            this.telemetry.pathogenRiskPct = 3.2;
            this.telemetry.soilMoisture = 42.5;
            this.telemetry.temperatureC = 26.1;
            this.telemetry.airQualityPpm = 80;
            this.telemetry.chiScore = 85.0;
            this.telemetry.recommendedAction = "✅ Optimal Crop Health: Leaf canopy NIR scattering & soil hydration levels are within ideal target ranges.";
            this.telemetry.as7341Channels = [450, 680, 920, 1450, 2800, 1600, 980, 520, 12400, 6893];
        } else if (scenarioKey === "FUNGAL") {
            this.telemetry.pathogenRiskPct = 48.2;
            this.telemetry.soilMoisture = 38.0;
            this.telemetry.temperatureC = 28.4;
            this.telemetry.airQualityPpm = 95;
            this.telemetry.chiScore = 54.2;
            this.telemetry.recommendedAction = "⚠️ Early Fungal Stress Detected: High pathogen risk. Recommended targeted copper fungicide drone spray at Sector B.";
            this.telemetry.as7341Channels = [780, 1120, 1890, 2400, 1950, 1200, 850, 410, 11200, 3100];
        } else if (scenarioKey === "DROUGHT") {
            this.telemetry.pathogenRiskPct = 18.5;
            this.telemetry.soilMoisture = 14.2;
            this.telemetry.temperatureC = 36.5;
            this.telemetry.airQualityPpm = 110;
            this.telemetry.chiScore = 41.0;
            this.telemetry.recommendedAction = "☀️ Severe Drought Stress: Sub-surface moisture below 15%. Automated drip irrigation valve trigger required immediately.";
            this.telemetry.as7341Channels = [320, 510, 710, 1100, 1400, 1100, 700, 390, 8900, 2400];
        } else if (scenarioKey === "FIRE") {
            this.telemetry.pathogenRiskPct = 22.0;
            this.telemetry.soilMoisture = 22.0;
            this.telemetry.temperatureC = 39.8;
            this.telemetry.airQualityPpm = 485;
            this.telemetry.chiScore = 32.5;
            this.telemetry.recommendedAction = "🚨 Stubble Fire Hazard: MQ-135 sensor array detected smoke PPM > 450. Emergency alert sent to local fire station.";
            this.telemetry.as7341Channels = [210, 340, 490, 890, 1100, 950, 600, 310, 7500, 1800];
        }
        this.telemetry.lastUpdated = new Date();
    },

    startLiveTelemetryLoop(callback) {
        if (this.simInterval) clearInterval(this.simInterval);

        const fetchLatest = async () => {
            try {
                const res = await fetch('/api/v1/telemetry/latest');
                if (res.ok) {
                    const data = await res.json();
                    if (data && data.telemetry) {
                        const t = data.telemetry;
                        this.telemetry.soilMoisture = t.soil_moisture_vwc !== null ? t.soil_moisture_vwc : 42.5;
                        this.telemetry.temperatureC = t.temperature_c !== null ? t.temperature_c : 26.1;
                        this.telemetry.humidity = t.humidity_pct !== null ? t.humidity_pct : 68.4;
                        this.telemetry.airQualityPpm = t.smoke_ppm !== null ? t.smoke_ppm : 80.0;
                        this.telemetry.isRealHardware = t.is_real_hardware || false;

                        if (t.is_real_hardware) {
                            this.hardwareStatus = "ONLINE";
                        }

                        if (typeof callback === 'function') callback(this.telemetry);
                    }
                }
            } catch (_) {
                if (typeof callback === 'function') callback(this.telemetry);
            }
        };

        fetchLatest();
        this.simInterval = setInterval(fetchLatest, this.settings.telemetryRefreshInterval * 1000);
    }
};

window.AgriState = AgriState;
