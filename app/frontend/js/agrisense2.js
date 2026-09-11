/**
 * AgriSense 2.0 Research Platform Frontend Controller
 * Connects frontend UI to PyTorch MM-SSNet (MobileNetV3), DBSCAN Spatial Clustering,
 * PyTorch Grad-CAM XAI, MAVLink Mission Planner, Closed-Loop Relays & SIL Digital Twin APIs.
 *
 * Explicitly displays scientific honesty disclaimers:
 * - "Synthetic-data prototype — real-world validation pending"
 * - "Lead-time estimate — synthetic simulation / not clinically or agriculturally validated"
 */

const AgriSense2 = {
    operatingMode: "SIMULATION", // "REAL_HARDWARE" or "SIMULATION"
    activeScenario: "HEALTHY_FIELD",
    wsConnection: null,

    init() {
        console.log("[AgriSense 2.0] Initializing Research Component Controller...");
        this.bindEvents();
        this.setOperatingMode(this.operatingMode);
        this.fetchSpatialHotspots();
        this.fetchActuatorStatus();
    },

    bindEvents() {
        const scenarioSelect = document.getElementById('silScenarioSelect');
        if (scenarioSelect) {
            scenarioSelect.addEventListener('change', (e) => {
                this.setSILScenario(e.target.value);
            });
        }

        const modeSelect = document.getElementById('v2OperatingModeSelect');
        if (modeSelect) {
            modeSelect.addEventListener('change', (e) => {
                this.setOperatingMode(e.target.value);
            });
        }
    },

    setOperatingMode(mode) {
        this.operatingMode = mode;
        console.log(`[AgriSense 2.0] Operating Mode set to: ${mode}`);

        const modeBadge = document.getElementById('v2OperatingModeBadge');
        if (modeBadge) {
            modeBadge.innerText = mode === "REAL_HARDWARE" ? "🔴 REAL HARDWARE PIPELINE" : "🧪 SIL SIMULATION MODE";
            modeBadge.className = mode === "REAL_HARDWARE" ?
                "px-3 py-1 rounded-full text-xs font-black bg-emerald-600 text-white animate-pulse" :
                "px-3 py-1 rounded-full text-xs font-black bg-purple-600 text-white";
        }

        if (mode === "REAL_HARDWARE") {
            this.connectRealHardwareWebSocket();
        } else {
            if (this.wsConnection) {
                this.wsConnection.close();
                this.wsConnection = null;
            }
            this.fetchSILTelemetry();
        }

        if (window.UI) window.UI.showToast(`Operating Mode switched to: ${mode}`, false);
    },

    connectRealHardwareWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/v1/telemetry`;

        try {
            this.wsConnection = new WebSocket(wsUrl);
            this.wsConnection.onmessage = (event) => {
                const data = JSON.parse(event.data);
                if (data.telemetry) {
                    const tel = {
                        temperature: data.telemetry.temperature_c || 25.0,
                        humidity: data.telemetry.humidity_pct || 60.0,
                        soil_moisture: data.telemetry.soil_moisture_vwc || 50.0,
                        smoke_ppm: data.telemetry.smoke_ppm || 80.0,
                        spectral: [0.15, 0.18, 0.20, 0.35, 0.65, 0.40, 0.25, 0.15, 0.70, 0.90],
                        scenario: "REAL_ESP32_TELEMETRY"
                    };
                    this.renderTelemetryUI(tel);
                    if (data.ai_diagnosis) {
                        this.renderAIResultsFromWebSocket(data.ai_diagnosis);
                    }
                }
            };
            this.wsConnection.onerror = (err) => {
                console.error("[AgriSense 2.0] Hardware WebSocket error", err);
            };
        } catch (e) {
            console.error("[AgriSense 2.0] Failed to open WebSocket connection", e);
        }
    },

    async setSILScenario(scenarioName) {
        try {
            const res = await fetch('/api/v2/simulation/digital-twin/set-scenario', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ scenario_name: scenarioName })
            });
            const data = await res.json();
            if (data.status === 'SUCCESS') {
                this.activeScenario = scenarioName;
                if (this.operatingMode === "SIMULATION") {
                    this.fetchSILTelemetry();
                }
            }
        } catch (e) {
            console.error("[AgriSense 2.0] Failed to set SIL scenario", e);
        }
    },

    async fetchSILTelemetry() {
        try {
            const res = await fetch('/api/v2/simulation/digital-twin/telemetry?node_id=NODE-01');
            const data = await res.json();
            if (data.status === 'SUCCESS' && data.simulated_telemetry) {
                const tel = data.simulated_telemetry;
                this.renderTelemetryUI(tel);
                this.runMMSSNetPrediction(tel);
            }
        } catch (e) {
            console.error("[AgriSense 2.0] Error fetching SIL telemetry", e);
        }
    },

    renderTelemetryUI(tel) {
        const elTemp = document.getElementById('v2TempDisplay');
        const elHum = document.getElementById('v2HumDisplay');
        const elSoil = document.getElementById('v2SoilDisplay');
        const elSmoke = document.getElementById('v2SmokeDisplay');
        const elScenarioBadge = document.getElementById('v2ScenarioBadge');

        if (elTemp) elTemp.innerText = `${tel.temperature.toFixed(1)}°C`;
        if (elHum) elHum.innerText = `${tel.humidity.toFixed(1)}%`;
        if (elSoil) elSoil.innerText = `${tel.soil_moisture.toFixed(1)}%`;
        if (elSmoke) elSmoke.innerText = `${tel.smoke_ppm.toFixed(1)} PPM`;
        if (elScenarioBadge) {
            elScenarioBadge.innerText = tel.scenario.replace(/_/g, ' ');
        }
    },

    async runMMSSNetPrediction(tel) {
        try {
            const payload = {
                spectral: tel.spectral || [0.15, 0.18, 0.20, 0.35, 0.65, 0.40, 0.25, 0.15, 0.70, 0.90],
                temperature: tel.temperature,
                humidity: tel.humidity,
                soil_moisture: tel.soil_moisture,
                smoke_ppm: tel.smoke_ppm
            };

            const res = await fetch('/api/v2/ai/predict', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            if (data.status === 'SUCCESS') {
                this.renderAIResults(data);
                this.fetchXAIExplanation(payload.spectral);
            }
        } catch (e) {
            console.error("[AgriSense 2.0] MM-SSNet prediction error", e);
        }
    },

    renderAIResultsFromWebSocket(diag) {
        const badge = document.getElementById('mmssnetConditionBadge');
        if (badge && diag.condition) {
            badge.innerText = diag.condition.replace(/_/g, ' ');
        }

        const elConf = document.getElementById('mmssnetConfidenceVal');
        const elSev = document.getElementById('mmssnetSeverityVal');
        const elLead = document.getElementById('mmssnetLeadTimeVal');

        if (elConf && diag.confidence) elConf.innerText = `${(diag.confidence * 100).toFixed(1)}%`;
        if (elSev && diag.severity_score) elSev.innerText = `${diag.severity_score.toFixed(1)} / 100`;
        if (elLead && diag.estimated_lead_time_hours) elLead.innerText = `${diag.estimated_lead_time_hours.toFixed(1)} Hours (Synthetic Lead Time)`;

        const traceBox = document.getElementById('fusionReasoningTrace');
        if (traceBox && diag.reasoning_trace) {
            traceBox.innerHTML = diag.reasoning_trace.map(r => `<div class="flex items-center space-x-2 text-slate-700"><i class="fa-solid fa-circle-check text-emerald-500"></i><span>${r}</span></div>`).join('');
        }
    },

    renderAIResults(data) {
        const pred = data.ai_prediction;
        const fused = data.fused_diagnosis;
        const ood = data.anomaly_analysis;

        const badge = document.getElementById('mmssnetConditionBadge');
        if (badge) {
            badge.innerText = fused.final_condition.replace(/_/g, ' ');
            let bgClass = "bg-emerald-100 text-emerald-800 border-emerald-300";
            if (fused.final_condition === "WATER_STRESS") bgClass = "bg-cyan-100 text-cyan-800 border-cyan-300";
            else if (fused.final_condition === "DISEASE") bgClass = "bg-purple-100 text-purple-800 border-purple-300";
            else if (fused.final_condition === "SEVERE_STRESS") bgClass = "bg-red-100 text-red-800 border-red-300 animate-pulse";
            else if (fused.final_condition === "PRE_SYMPTOMATIC_STRESS") bgClass = "bg-amber-100 text-amber-800 border-amber-300";
            else if (fused.final_condition === "UNKNOWN_ANOMALY") bgClass = "bg-rose-100 text-rose-800 border-rose-300";

            badge.className = `px-4 py-1.5 rounded-full text-xs font-black border ${bgClass}`;
        }

        const elConf = document.getElementById('mmssnetConfidenceVal');
        const elSev = document.getElementById('mmssnetSeverityVal');
        const elLead = document.getElementById('mmssnetLeadTimeVal');
        const elOOD = document.getElementById('mmssnetOODDistVal');

        if (elConf) elConf.innerText = `${(fused.disambiguated_confidence * 100).toFixed(1)}%`;
        if (elSev) elSev.innerText = `${fused.severity_score.toFixed(1)} / 100`;
        if (elLead) elLead.innerText = `${pred.estimated_lead_time_hours.toFixed(1)} Hours (Synthetic Model)`;
        if (elOOD) {
            if (ood.is_calibrated) {
                elOOD.innerText = `${ood.mahalanobis_distance.toFixed(2)} (Thresh: ${ood.anomaly_threshold})`;
            } else {
                elOOD.innerText = "NOT CALIBRATED";
            }
        }

        // Modality & Honesty Badges
        const elModalityBadge = document.getElementById('mmssnetModalityBadge');
        if (elModalityBadge) {
            const hasSpatial = pred.spatial_modality_available;
            if (hasSpatial) {
                elModalityBadge.innerText = "📷 Tri-Modal (Spatial RGB + Spectral + Env)";
                elModalityBadge.className = "px-3 py-1 rounded-full text-[10px] font-extrabold bg-emerald-100 text-emerald-800 border border-emerald-300";
            } else {
                elModalityBadge.innerText = "📷 RGB Image: Unavailable (Reduced-Modality Spectral + Env)";
                elModalityBadge.className = "px-3 py-1 rounded-full text-[10px] font-extrabold bg-purple-100 text-purple-800 border border-purple-300";
            }
        }

        const traceBox = document.getElementById('fusionReasoningTrace');
        if (traceBox && fused.reasoning_trace) {
            traceBox.innerHTML = fused.reasoning_trace.map(r => `<div class="flex items-center space-x-2 text-slate-700"><i class="fa-solid fa-circle-check text-emerald-500"></i><span>${r}</span></div>`).join('');
        }

        const probContainer = document.getElementById('softmaxProbBars');
        if (probContainer && pred.probabilities) {
            let html = '';
            for (const [cond, p] of Object.entries(pred.probabilities)) {
                const pct = (p * 100).toFixed(1);
                html += `
                    <div class="space-y-1 text-xs">
                        <div class="flex justify-between font-bold text-slate-700">
                            <span>${cond.replace(/_/g, ' ')}</span>
                            <span>${pct}%</span>
                        </div>
                        <div class="w-full h-2 bg-slate-100 rounded-full overflow-hidden">
                            <div class="h-full bg-agri-primary transition-all duration-500" style="width: ${pct}%"></div>
                        </div>
                    </div>
                `;
            }
            probContainer.innerHTML = html;
        }
    },

    async fetchXAIExplanation(spectral) {
        try {
            const res = await fetch('/api/v2/ai/xai', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ spectral: spectral })
            });
            const data = await res.json();
            if (data.status === 'SUCCESS') {
                this.renderXAI(data.xai_explanation);
            }
        } catch (e) {
            console.error("[AgriSense 2.0] XAI explanation error", e);
        }
    },

    renderXAI(xai) {
        const bandList = document.getElementById('spectralBandAttributionList');
        if (bandList && xai.spectral_band_importance) {
            let html = '';
            xai.spectral_band_importance.forEach(b => {
                html += `
                    <div class="p-2.5 rounded-xl bg-slate-50 border border-slate-200 flex items-center justify-between text-xs">
                        <div>
                            <div class="font-bold text-slate-900">${b.band_name}</div>
                            <div class="text-slate-500">Reflectance: ${b.reflectance_value}</div>
                        </div>
                        <div class="text-right">
                            <span class="px-2.5 py-1 rounded-lg font-black text-agri-dark bg-agri-mint">${b.importance_pct}% Impact</span>
                        </div>
                    </div>
                `;
            });
            bandList.innerHTML = html;
        }

        const canvas = document.getElementById('gradcamCanvas');
        const gradcamMsgBox = document.getElementById('gradcamMsgBox');

        if (canvas) {
            if (xai.xai_status === "UNAVAILABLE_MISSING_RGB" || !xai.gradcam_heatmap_grid) {
                canvas.style.display = 'none';
                if (gradcamMsgBox) {
                    gradcamMsgBox.style.display = 'flex';
                    gradcamMsgBox.innerHTML = `<i class="fa-solid fa-camera text-purple-500 text-xl"></i><span class="text-xs font-bold text-slate-600">RGB Image: Unavailable (No spatial camera payload in telemetry — Grad-CAM skipped)</span>`;
                }
            } else {
                canvas.style.display = 'block';
                if (gradcamMsgBox) gradcamMsgBox.style.display = 'none';
                const ctx = canvas.getContext('2d');
                const grid = xai.gradcam_heatmap_grid;
                const size = 64;
                const cellW = canvas.width / size;
                const cellH = canvas.height / size;

                for (let r = 0; r < size; r++) {
                    for (let c = 0; c < size; c++) {
                        const val = grid[r][c];
                        const red = Math.floor(val * 255);
                        const green = Math.floor((1 - val) * 180);
                        ctx.fillStyle = `rgba(${red}, ${green}, 40, ${val * 0.75})`;
                        ctx.fillRect(c * cellW, r * cellH, cellW, cellH);
                    }
                }
            }
        }
    },

    async fetchSpatialHotspots() {
        try {
            const res = await fetch('/api/v2/spatial/hotspots/simulation');
            const data = await res.json();
            if (data.status === 'SUCCESS' && data.spatial_clusters) {
                const clusters = data.spatial_clusters;
                const elArea = document.getElementById('v2AffectedAreaVal');
                const elCount = document.getElementById('v2HotspotCountVal');
                const list = document.getElementById('dbscanHotspotList');

                if (elArea) elArea.innerText = `${clusters.estimated_bounding_area_m2} m²`;
                if (elCount) elCount.innerText = `${clusters.total_hotspots} Clusters`;

                if (list && clusters.hotspots) {
                    list.innerHTML = clusters.hotspots.map(hs => `
                        <div class="p-3 rounded-xl bg-slate-50 border border-slate-200 flex items-center justify-between text-xs">
                            <div>
                                <div class="font-bold text-slate-900">${hs.hotspot_id} (Nodes: ${hs.affected_nodes.join(', ')})</div>
                                <div class="text-slate-500">Centroid: (${hs.centroid.lat}, ${hs.centroid.lng})</div>
                            </div>
                            <div class="text-right space-y-1">
                                <span class="px-2 py-0.5 rounded-full font-bold bg-amber-100 text-amber-800">${hs.estimated_bounding_area_m2} m²</span>
                                <div><button onclick="AgriSense2.planTargetedRevisit('${hs.hotspot_id}', ${hs.centroid.lat}, ${hs.centroid.lng})" class="text-[10px] font-bold text-agri-primary hover:underline">Target UAV Revisit</button></div>
                            </div>
                        </div>
                    `).join('');
                }
            }
        } catch (e) {
            console.error("[AgriSense 2.0] DBSCAN spatial fetch error", e);
        }
    },

    async generateLawnmowerMission() {
        try {
            const bounds = [
                { lat: 28.6135, lng: 77.2085 },
                { lat: 28.6145, lng: 77.2085 },
                { lat: 28.6145, lng: 77.2095 },
                { lat: 28.6135, lng: 77.2095 }
            ];
            const res = await fetch('/api/v2/uav/mission/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ boundary_coords: bounds, altitude_m: 15.0, spacing_m: 10.0 })
            });
            const data = await res.json();
            if (data.status === 'SUCCESS' && data.uav_mission) {
                const m = data.uav_mission;
                if (window.UI) window.UI.showToast(`✈️ ${m.execution_mode}: ${m.waypoint_count} Waypoints (${m.estimated_duration_minutes} min)`, false);
            }
        } catch (e) {
            console.error("[AgriSense 2.0] Lawnmower mission error", e);
        }
    },

    async planTargetedRevisit(hotspotId, lat, lng) {
        try {
            const res = await fetch('/api/v2/uav/mission/targeted-revisit', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ hotspot_id: hotspotId, centroid: { lat: lat, lng: lng } })
            });
            const data = await res.json();
            if (data.status === 'SUCCESS' && data.revisit_mission) {
                const r = data.revisit_mission;
                if (window.UI) window.UI.showToast(`🎯 Targeted UAV Revisit Scheduled for Hotspot ${hotspotId} (${r.execution_mode})`, false);
            }
        } catch (e) {
            console.error("[AgriSense 2.0] Targeted revisit error", e);
        }
    },

    async triggerActuator(zoneId, durationSec) {
        try {
            const res = await fetch('/api/v2/actuators/control', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ zone_id: zoneId, duration_sec: durationSec })
            });
            const data = await res.json();
            if (data.status === 'SUCCESS' && data.actuator_response) {
                const resp = data.actuator_response;
                if (resp.success) {
                    if (window.UI) window.UI.showToast(`💧 ${resp.message}`, false);
                    this.fetchActuatorStatus();
                } else {
                    if (window.UI) window.UI.showToast(`⚠️ ${resp.message}`, true);
                }
            }
        } catch (e) {
            console.error("[AgriSense 2.0] Actuator trigger error", e);
        }
    },

    async triggerEmergencyStop() {
        try {
            const res = await fetch('/api/v2/actuators/emergency-stop', { method: 'POST' });
            const data = await res.json();
            if (data.status === 'SUCCESS') {
                if (window.UI) window.UI.showToast('🚨 EMERGENCY KILL SWITCH ACTIVATED! Relays Powered OFF.', true);
                this.fetchActuatorStatus();
            }
        } catch (e) {
            console.error("[AgriSense 2.0] Emergency stop error", e);
        }
    },

    async fetchActuatorStatus() {
        try {
            const res = await fetch('/api/v2/actuators/status');
            const data = await res.json();
            if (data.status === 'SUCCESS' && data.actuator_status) {
                const st = data.actuator_status;
                const elState = document.getElementById('actuatorRelayStateBadge');
                const elCooldown = document.getElementById('actuatorCooldownBadge');

                if (elState) {
                    elState.innerText = `${st.relay_state} (${st.relay_mode})`;
                    elState.className = st.relay_state === 'ON' ?
                        'px-3 py-1 rounded-full text-xs font-black bg-emerald-500 text-white animate-pulse' :
                        'px-3 py-1 rounded-full text-xs font-black bg-slate-200 text-slate-800';
                }

                if (elCooldown) {
                    if (st.in_cooldown) {
                        elCooldown.innerText = `Cooldown (${st.cooldown_remaining_sec}s)`;
                        elCooldown.className = 'px-3 py-1 rounded-lg text-[10px] font-bold bg-amber-100 text-amber-800';
                    } else {
                        elCooldown.innerText = 'Ready (No Cooldown)';
                        elCooldown.className = 'px-3 py-1 rounded-lg text-[10px] font-bold bg-emerald-100 text-emerald-800';
                    }
                }
            }
        } catch (e) {
            console.error("[AgriSense 2.0] Actuator status error", e);
        }
    }
};

window.AgriSense2 = AgriSense2;

document.addEventListener('DOMContentLoaded', () => {
    AgriSense2.init();
});
