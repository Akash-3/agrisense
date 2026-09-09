/**
 * AgriSense UI Controller & SPA View Navigation Manager
 */
const UI = {
    currentView: "dashboard",

    init() {
        this.bindEvents();
        this.renderAll();
        
        // Start telemetry simulation ticker
        window.AgriState.startLiveTelemetryLoop((t) => {
            this.renderTelemetryValues(t);
        });

        // Initialize Drone Status update listener
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

    switchView(viewName) {
        this.currentView = viewName;

        // Hide all page containers
        const views = [
            'authScreen', 'mainAppScreen'
        ];

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

        // Show active page
        const activePageId = 'page' + viewName.charAt(0).toUpperCase() + viewName.slice(1);
        const activeEl = document.getElementById(activePageId);
        if (activeEl) activeEl.classList.remove('hidden');

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
            window.ChartService.initSpectrometryChart('dashboardSpectralChart');
        } else if (viewName === 'map') {
            window.MapService.init('mapContainer');
        } else if (viewName === 'analytics') {
            window.ChartService.initAnalyticsTrends('analyticsTrendChart');
            window.ChartService.initSpectrometryChart('analyticsSpectralChart');
        } else if (viewName === 'scenarios') {
            window.ChartService.initScenarioChart('scenarioSimChart', window.AgriState.activeScenario);
        } else if (viewName === 'missionPlanner') {
            window.MapService.init('plannerMapContainer');
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

    renderAll() {
        this.renderUser();
        this.renderTelemetryValues(window.AgriState.telemetry);
        this.renderDroneState(window.DroneService.getPrimaryDrone());
        this.renderNotifications();
        this.renderFarmsList();
    },

    renderUser() {
        const u = window.AgriState.currentUser;
        document.querySelectorAll('.user-name').forEach(el => el.innerText = u.name);
        document.querySelectorAll('.user-email').forEach(el => el.innerText = u.email);
        document.querySelectorAll('.user-avatar').forEach(el => el.innerText = u.avatar);
        document.querySelectorAll('.user-farm').forEach(el => el.innerText = `${u.farmName} (${u.farmSize} Acres)`);
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

    showFieldDetailModal(field) {
        const modal = document.getElementById('fieldDetailModal');
        if (!modal) return;

        document.getElementById('modalFieldName').innerText = field.name;
        document.getElementById('modalFieldAcres').innerText = `${field.acres} Acres`;
        document.getElementById('modalFieldCrop').innerText = field.crop;
        document.getElementById('modalFieldHealth').innerText = `${field.health.toFixed(1)} / 100`;
        document.getElementById('modalFieldHydration').innerText = `${field.hydration.toFixed(1)}%`;
        document.getElementById('modalFieldRisk').innerText = `${field.risk.toFixed(1)}%`;

        modal.classList.remove('hidden');
    },

    closeFieldDetailModal() {
        const modal = document.getElementById('fieldDetailModal');
        if (modal) modal.classList.add('hidden');
    },

    openAddFarmModal() {
        document.getElementById('addFarmModal').classList.remove('hidden');
    },

    closeAddFarmModal() {
        document.getElementById('addFarmModal').classList.add('hidden');
    },

    submitAddFarm() {
        const name = document.getElementById('newFarmName').value;
        const acres = parseFloat(document.getElementById('newFarmAcres').value);
        const crop = document.getElementById('newFarmCrop').value;

        if (!name || !acres) {
            this.showToast('Please enter a valid farm name and size.', true);
            return;
        }

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
        this.showToast(`Farm '${name}' added successfully!`, false);
    },

    toggleTempUnit() {
        window.AgriState.settings.tempUnit = window.AgriState.settings.tempUnit === "C" ? "F" : "C";
        document.querySelectorAll('.temp-unit-label').forEach(el => el.innerText = `°${window.AgriState.settings.tempUnit}`);
        this.renderTelemetryValues(window.AgriState.telemetry);
        this.showToast(`Temperature unit set to °${window.AgriState.settings.tempUnit}.`, false);
    }
};

window.UI = UI;

document.addEventListener('DOMContentLoaded', () => {
    window.UI.init();
});
