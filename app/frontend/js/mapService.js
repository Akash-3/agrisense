/**
 * AgriSense Satellite Map Engine Service (Leaflet.js)
 * Supports Satellite, Terrain, Street basemaps + Crop Health, Hydration & Pathogen Risk overlays
 */
const MapService = {
    map: null,
    tileLayers: {},
    activeOverlay: "cropHealth", // "cropHealth", "hydration", "pathogen"
    fieldPolygons: [],
    droneMarker: null,
    sensorMarkers: [],

    init(containerId) {
        const container = document.getElementById(containerId);
        if (!container) return;

        // Clean existing instance if re-initializing
        if (this.map) {
            this.map.remove();
            this.map = null;
        }

        const centerLat = 20.2961;
        const centerLng = 85.8245;

        // Initialize Leaflet Map
        this.map = L.map(containerId, {
            center: [centerLat, centerLng],
            zoom: 15,
            zoomControl: false
        });

        // Custom Zoom Position
        L.control.zoom({ position: 'topright' }).addTo(this.map);

        // Tile Layers
        this.tileLayers.satellite = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
            attribution: 'Esri, Maxar, Earthstar Geographics',
            maxZoom: 19
        });

        this.tileLayers.street = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors',
            maxZoom: 19
        });

        this.tileLayers.terrain = L.tileLayer('https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenTopoMap',
            maxZoom: 17
        });

        // Default to Satellite
        this.tileLayers.satellite.addTo(this.map);

        // Render Field Polygons
        this.renderFields();

        // Render Drone & Sensor Markers
        this.renderMarkers();

        // Subscribe to Drone Telemetry Updates
        if (window.DroneService) {
            window.DroneService.subscribe((droneData) => {
                this.updateDroneMarker(droneData);
            });
        }

        // Force Map Invalidate Size after DOM render
        setTimeout(() => {
            if (this.map) this.map.invalidateSize();
        }, 300);
    },

    setBaseLayer(layerType) {
        if (!this.map) return;
        Object.keys(this.tileLayers).forEach(k => {
            this.map.removeLayer(this.tileLayers[k]);
        });
        if (this.tileLayers[layerType]) {
            this.tileLayers[layerType].addTo(this.map);
        }
    },

    setOverlayMode(mode) {
        this.activeOverlay = mode;
        this.renderFields();
    },

    selectedPolygon: null,

    clearSelectedPolygon() {
        if (this.selectedPolygon) {
            if (this.selectedPolygon.defaultStyle) {
                this.selectedPolygon.setStyle(this.selectedPolygon.defaultStyle);
            }
            this.selectedPolygon = null;
        }
    },

    setSelectedPolygon(polygon) {
        this.clearSelectedPolygon();
        this.selectedPolygon = polygon;
        if (polygon) {
            polygon.setStyle({
                color: '#059669',
                weight: 4,
                fillColor: '#059669',
                fillOpacity: 0.55
            });
            polygon.bringToFront();
        }
    },

    renderFields() {
        if (!this.map) return;

        // Remove existing polygons
        this.fieldPolygons.forEach(p => this.map.removeLayer(p));
        this.fieldPolygons = [];
        this.selectedPolygon = null;

        const fieldData = [
            {
                id: 1,
                name: "Green Valley Field Plot",
                acres: 15.0,
                crop: "Wheat & Paddy",
                coords: [
                    [20.2945, 85.8220],
                    [20.2980, 85.8220],
                    [20.2980, 85.8270],
                    [20.2945, 85.8270]
                ],
                health: 85.0,
                hydration: 42.5,
                risk: 9.9,
                color: "#079A70"
            },
            {
                id: 2,
                name: "North Sector Plot",
                acres: 22.4,
                crop: "Corn Canopy",
                coords: [
                    [20.2990, 85.8260],
                    [20.3030, 85.8260],
                    [20.3030, 85.8320],
                    [20.2990, 85.8320]
                ],
                health: 72.0,
                hydration: 28.0,
                risk: 28.4,
                color: "#F4A019"
            },
            {
                id: 3,
                name: "East Sector Plot",
                acres: 18.5,
                crop: "Soybean",
                coords: [
                    [20.2900, 85.8320],
                    [20.2940, 85.8320],
                    [20.2940, 85.8380],
                    [20.2900, 85.8380]
                ],
                health: 91.0,
                hydration: 48.0,
                risk: 4.2,
                color: "#159B7A"
            }
        ];

        fieldData.forEach(field => {
            let fillColor = field.color;

            if (this.activeOverlay === "hydration") {
                fillColor = field.hydration > 35 ? "#249EAF" : "#F4A019";
            } else if (this.activeOverlay === "pathogen") {
                fillColor = field.risk > 20 ? "#EF5B67" : "#079A70";
            }

            const defaultStyle = {
                color: fillColor,
                weight: 2,
                fillColor: fillColor,
                fillOpacity: 0.35
            };

            const polygon = L.polygon(field.coords, defaultStyle).addTo(this.map);
            polygon.defaultStyle = defaultStyle;

            polygon.bindTooltip(`<b>${field.name}</b><br>${field.acres} Acres • ${field.crop}`, {
                permanent: false,
                direction: 'center',
                className: 'bg-slate-900 text-white font-sans text-xs px-2 py-1 rounded shadow-lg border-0'
            });

            polygon.on('click', () => {
                this.setSelectedPolygon(polygon);
                if (this.map) {
                    this.map.fitBounds(polygon.getBounds(), { padding: [60, 60], maxZoom: 16, animate: true });
                }
                if (window.UI) {
                    window.UI.showFieldDetailPanel(field, polygon);
                }
            });

            this.fieldPolygons.push(polygon);
        });
    },

    renderMarkers() {
        if (!this.map) return;

        // Custom Icon for Drone
        const droneIcon = L.divIcon({
            className: 'custom-drone-icon',
            html: `<div class="w-10 h-10 rounded-full bg-slate-900 border-2 border-emerald-400 text-emerald-400 flex items-center justify-center shadow-2xl pulse-emerald">
                        <i class="fa-solid fa-plane-up text-sm"></i>
                   </div>`,
            iconSize: [40, 40],
            iconAnchor: [20, 20]
        });

        const primaryDrone = window.DroneService ? window.DroneService.getPrimaryDrone() : { lat: 20.2961, lng: 85.8245 };
        this.droneMarker = L.marker([primaryDrone.lat, primaryDrone.lng], { icon: droneIcon }).addTo(this.map);
        this.droneMarker.bindPopup(`<b>AGRIDRONE-01</b><br>Autonomous Spectrometry Scanner`);

        // Sensor Nodes
        const sensors = [
            { name: "Node-01 (Soil Capacitive)", lat: 20.2960, lng: 85.8240 },
            { name: "Node-02 (DHT22 Canopy)", lat: 20.2972, lng: 85.8250 },
            { name: "Node-03 (MQ-135 Air)", lat: 20.3015, lng: 85.8280 }
        ];

        sensors.forEach(s => {
            const sensorIcon = L.divIcon({
                className: 'custom-sensor-icon',
                html: `<div class="w-7 h-7 rounded-full bg-emerald-600 text-white flex items-center justify-center shadow-md border-2 border-white">
                            <i class="fa-solid fa-tower-cell text-xs"></i>
                       </div>`,
                iconSize: [28, 28],
                iconAnchor: [14, 14]
            });

            const m = L.marker([s.lat, s.lng], { icon: sensorIcon }).addTo(this.map);
            m.bindTooltip(`IoT Sensor: ${s.name}`, { permanent: false, direction: 'top' });
            this.sensorMarkers.push(m);
        });
    },

    updateDroneMarker(droneData) {
        if (this.droneMarker && droneData.lat && droneData.lng) {
            this.droneMarker.setLatLng([droneData.lat, droneData.lng]);
        }
    }
};

window.MapService = MapService;
