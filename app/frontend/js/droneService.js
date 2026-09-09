/**
 * AgriSense Autonomous Drone Service & State Machine Simulator
 * Supports MAVLink / ROS 2 / REST API Integration Abstraction
 */
const DroneService = {
    // Fleet State
    drones: [
        {
            id: "AGRIDRONE-01",
            name: "AgriVision Pro Drone Alpha",
            status: "IDLE", // IDLE, ARMING, TAKEOFF, MISSION_ACTIVE, PAUSED, RETURNING, LANDING, CHARGING, ERROR
            battery: 87, // %
            altitude: 0.0, // meters
            speed: 0.0, // m/s
            gpsSatellites: 14,
            signalRssi: 98, // %
            currentField: "Green Valley Field",
            missionProgress: 0, // %
            flightTimeSec: 0,
            payload: "Multispectral Crop Health Sensor",
            lat: 20.2961,
            lng: 85.8245
        },
        {
            id: "AGRIDRONE-02",
            name: "SpectraScan Hexacopter Beta",
            status: "CHARGING",
            battery: 42,
            altitude: 0.0,
            speed: 0.0,
            gpsSatellites: 12,
            signalRssi: 94,
            currentField: "North Sector Plot",
            missionProgress: 100,
            flightTimeSec: 1450,
            payload: "NDVI Multispectral Camera",
            lat: 20.3010,
            lng: 85.8290
        },
        {
            id: "AGRIDRONE-03",
            name: "SprayMaster Quadcopter Gamma",
            status: "IDLE",
            battery: 95,
            altitude: 0.0,
            speed: 0.0,
            gpsSatellites: 16,
            signalRssi: 99,
            currentField: "East Sector Plot",
            missionProgress: 0,
            flightTimeSec: 0,
            payload: "Precision Targeted Nozzle Spray",
            lat: 20.2915,
            lng: 85.8350
        }
    ],

    // Active Mission Plan
    activeMissionPlan: {
        fieldId: 1,
        fieldName: "Green Valley Field Plot",
        pattern: "Grid Lawnmover",
        altitude: 25, // meters
        speed: 8, // m/s
        overlap: 75, // %
        scanType: "Multispectral Crop Health Sensor",
        estimatedDistKm: 2.4,
        estimatedTimeMin: 14,
        estimatedBatteryPct: 32,
        waypoints: [
            [20.2950, 85.8235],
            [20.2970, 85.8235],
            [20.2970, 85.8255],
            [20.2950, 85.8255],
            [20.2950, 85.8235]
        ]
    },

    // Simulation Loop Handle
    timer: null,
    listeners: [],

    subscribe(listener) {
        if (typeof listener === 'function') {
            this.listeners.push(listener);
        }
    },

    notify() {
        this.listeners.forEach(fn => fn(this.drones[0]));
    },

    getPrimaryDrone() {
        return this.drones[0];
    },

    launchMission(missionConfig) {
        const d = this.drones[0];
        if (d.status !== "IDLE" && d.status !== "CHARGING") {
            return { success: false, message: `Drone ${d.id} is currently ${d.status}. Cannot launch.` };
        }

        if (missionConfig) {
            this.activeMissionPlan = { ...this.activeMissionPlan, ...missionConfig };
        }

        d.status = "ARMING";
        d.missionProgress = 0;
        d.flightTimeSec = 0;
        this.notify();

        // State machine progression simulation
        setTimeout(() => {
            if (d.status === "ARMING") {
                d.status = "TAKEOFF";
                d.altitude = 5.0;
                d.speed = 1.2;
                this.notify();
            }
        }, 2000);

        setTimeout(() => {
            if (d.status === "TAKEOFF") {
                d.status = "MISSION_ACTIVE";
                d.altitude = this.activeMissionPlan.altitude || 25.0;
                d.speed = this.activeMissionPlan.speed || 8.0;
                this.notify();
                this.startFlightSimulation();
            }
        }, 4500);

        return { success: true, message: `Mission initiated for ${d.id}! Motors arming...` };
    },

    pauseMission() {
        const d = this.drones[0];
        if (d.status === "MISSION_ACTIVE") {
            d.status = "PAUSED";
            d.speed = 0.0;
            this.notify();
            return { success: true, message: `Mission paused. ${d.id} hovering at ${d.altitude}m.` };
        }
        return { success: false, message: "Drone is not currently active in a mission." };
    },

    resumeMission() {
        const d = this.drones[0];
        if (d.status === "PAUSED") {
            d.status = "MISSION_ACTIVE";
            d.speed = this.activeMissionPlan.speed || 8.0;
            this.notify();
            this.startFlightSimulation();
            return { success: true, message: `Mission resumed for ${d.id}.` };
        }
        return { success: false, message: "Drone mission is not paused." };
    },

    returnToBase() {
        const d = this.drones[0];
        d.status = "RETURNING";
        d.speed = 10.0;
        this.notify();

        setTimeout(() => {
            if (d.status === "RETURNING") {
                d.status = "LANDING";
                d.altitude = 3.0;
                d.speed = 0.8;
                this.notify();
            }
        }, 4000);

        setTimeout(() => {
            if (d.status === "LANDING") {
                d.status = "IDLE";
                d.altitude = 0.0;
                d.speed = 0.0;
                d.missionProgress = 100;
                this.notify();
                if (this.timer) clearInterval(this.timer);
            }
        }, 7000);

        return { success: true, message: `Return-To-Home initiated for ${d.id}. Returning to base...` };
    },

    emergencyStop() {
        const d = this.drones[0];
        d.status = "ERROR";
        d.speed = 0.0;
        if (this.timer) clearInterval(this.timer);
        this.notify();
        return { success: true, message: `🚨 EMERGENCY STOP EXECUTED! Motors kill signal transmitted to ${d.id}.` };
    },

    startFlightSimulation() {
        if (this.timer) clearInterval(this.timer);
        const d = this.drones[0];

        this.timer = setInterval(() => {
            if (d.status !== "MISSION_ACTIVE") {
                clearInterval(this.timer);
                return;
            }

            d.flightTimeSec += 2;
            d.missionProgress = Math.min(100, d.missionProgress + 3);
            d.battery = Math.max(10, d.battery - 0.4);

            // Animate lat/lng position along flight waypoints
            const waypoints = this.activeMissionPlan.waypoints;
            const stepIndex = Math.floor((d.missionProgress / 100) * (waypoints.length - 1));
            const targetWp = waypoints[stepIndex] || waypoints[0];
            
            d.lat = targetWp[0] + (Math.random() - 0.5) * 0.0002;
            d.lng = targetWp[1] + (Math.random() - 0.5) * 0.0002;

            if (d.missionProgress >= 100) {
                clearInterval(this.timer);
                this.returnToBase();
            }

            this.notify();
        }, 1500);
    }
};

window.DroneService = DroneService;
