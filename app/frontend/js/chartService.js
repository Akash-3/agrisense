/**
 * AgriSense Data Visualization & Chart Engine (Chart.js)
 */
const ChartService = {
    charts: {},

    initDashboardSparklines() {
        this.renderSparkline('soilSparkline', [40, 41, 41.5, 42.0, 42.5], '#249EAF');
        this.renderSparkline('tempSparkline', [25.5, 25.8, 26.0, 26.1], '#F4A019');
        this.renderSparkline('airSparkline', [75, 78, 80, 82, 80], '#079A70');
        this.renderSparkline('riskSparkline', [14, 12, 11, 10, 9.9], '#EF5B67');
    },

    renderSparkline(canvasId, dataPoints, strokeColor) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return;

        if (this.charts[canvasId]) {
            this.charts[canvasId].destroy();
        }

        this.charts[canvasId] = new Chart(ctx, {
            type: 'line',
            data: {
                labels: dataPoints.map((_, i) => i),
                datasets: [{
                    data: dataPoints,
                    borderColor: strokeColor,
                    borderWidth: 2,
                    pointRadius: 0,
                    tension: 0.4,
                    fill: false
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false }, tooltip: { enabled: false } },
                scales: { x: { display: false }, y: { display: false } }
            }
        });
    },

    initSpectrometryChart(canvasId, channelsData) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return;

        if (this.charts[canvasId]) {
            this.charts[canvasId].destroy();
        }

        const defaultChannels = channelsData || [450, 680, 920, 1450, 2800, 1600, 980, 520, 12400, 6893];

        this.charts[canvasId] = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: ['Violet 415nm', 'Blue 445nm', 'Cyan 480nm', 'Green 515nm', 'Yellow 555nm', 'Amber 590nm', 'Red 630nm', 'Deep Red 680nm', 'Visible Clear', 'NIR 885nm'],
                datasets: [{
                    label: 'Reflectance Intensity (Counts)',
                    data: defaultChannels,
                    backgroundColor: '#079A70',
                    borderRadius: 8,
                    hoverBackgroundColor: '#159B7A'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: '#0D172B',
                        padding: 12,
                        cornerRadius: 12,
                        titleFont: { family: 'Inter', size: 12, weight: 'bold' }
                    }
                },
                scales: {
                    x: {
                        grid: { display: false },
                        ticks: { font: { family: 'Inter', size: 11, weight: 'bold' }, color: '#64748B' }
                    },
                    y: {
                        grid: { color: '#F1F5F9' },
                        ticks: { font: { family: 'Inter', size: 11 }, color: '#94A3B8' }
                    }
                }
            }
        });
    },

    initAnalyticsTrends(canvasId) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return;

        if (this.charts[canvasId]) {
            this.charts[canvasId].destroy();
        }

        this.charts[canvasId] = new Chart(ctx, {
            type: 'line',
            data: {
                labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
                datasets: [
                    {
                        label: 'Crop Health Index (CHI / 100)',
                        data: [82, 84, 85, 86, 85, 87, 88],
                        borderColor: '#079A70',
                        backgroundColor: 'rgba(7, 154, 112, 0.1)',
                        fill: true,
                        tension: 0.3
                    },
                    {
                        label: 'Pathogen Risk (%)',
                        data: [15, 13, 11, 10, 9.9, 8.5, 7.8],
                        borderColor: '#EF5B67',
                        borderDash: [5, 5],
                        fill: false,
                        tension: 0.3
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'top', labels: { font: { family: 'Inter', size: 12, weight: '600' } } },
                    tooltip: { backgroundColor: '#0D172B' }
                },
                scales: {
                    x: { grid: { display: false } },
                    y: { grid: { color: '#F1F5F9' } }
                }
            }
        });
    },

    initScenarioChart(canvasId, scenarioKey) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return;

        if (this.charts[canvasId]) {
            this.charts[canvasId].destroy();
        }

        let chiPoints = [85, 85, 85, 85, 85];
        let riskPoints = [10, 9.9, 9.5, 9.0, 8.5];

        if (scenarioKey === "FUNGAL") {
            chiPoints = [85, 78, 65, 58, 54.2];
            riskPoints = [10, 22, 38, 44, 48.2];
        } else if (scenarioKey === "DROUGHT") {
            chiPoints = [85, 72, 58, 46, 41.0];
            riskPoints = [10, 12, 15, 17, 18.5];
        } else if (scenarioKey === "FIRE") {
            chiPoints = [85, 68, 45, 38, 32.5];
            riskPoints = [10, 15, 18, 20, 22.0];
        }

        this.charts[canvasId] = new Chart(ctx, {
            type: 'line',
            data: {
                labels: ['Day 1', 'Day 2', 'Day 3', 'Day 4', 'Day 5'],
                datasets: [
                    {
                        label: 'CHI Score',
                        data: chiPoints,
                        borderColor: '#079A70',
                        backgroundColor: 'rgba(7, 154, 112, 0.15)',
                        fill: true,
                        tension: 0.3
                    },
                    {
                        label: 'Pathogen Risk (%)',
                        data: riskPoints,
                        borderColor: '#EF5B67',
                        borderWidth: 2,
                        tension: 0.3
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { position: 'top' } },
                scales: { x: { grid: { display: false } }, y: { grid: { color: '#F1F5F9' } } }
            }
        });
    },

    initAnalyticsSoilTemp(canvasId) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return;

        if (this.charts[canvasId]) {
            this.charts[canvasId].destroy();
        }

        this.charts[canvasId] = new Chart(ctx, {
            type: 'line',
            data: {
                labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
                datasets: [
                    {
                        label: 'Soil Moisture (% VWC)',
                        data: [40, 41, 41.5, 42, 42.5, 43, 42.8],
                        borderColor: '#249EAF',
                        backgroundColor: 'rgba(36, 158, 175, 0.12)',
                        fill: true,
                        tension: 0.3,
                        yAxisID: 'y'
                    },
                    {
                        label: 'Air Temp (°C)',
                        data: [25.5, 25.8, 26, 26.1, 25.9, 25.4, 25.2],
                        borderColor: '#F4A019',
                        borderDash: [4, 4],
                        fill: false,
                        tension: 0.3,
                        yAxisID: 'y1'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'top', labels: { font: { family: 'Inter', size: 12, weight: '600' } } },
                    tooltip: { backgroundColor: '#0D172B', cornerRadius: 12 }
                },
                scales: {
                    x: { grid: { display: false } },
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        grid: { color: '#F1F5F9' },
                        title: { display: true, text: 'Soil VWC %', font: { family: 'Inter', size: 11, weight: 'bold' } }
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        grid: { drawOnChartArea: false },
                        title: { display: true, text: 'Temp °C', font: { family: 'Inter', size: 11, weight: 'bold' } }
                    }
                }
            }
        });
    },

    initDashboardFieldTrends(canvasId) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return;

        if (this.charts[canvasId]) {
            this.charts[canvasId].destroy();
        }

        this.charts[canvasId] = new Chart(ctx, {
            type: 'line',
            data: {
                labels: ['00:00', '04:00', '08:00', '12:00', '16:00', '20:00', '24:00'],
                datasets: [
                    {
                        label: 'Soil Moisture (% VWC)',
                        data: [41.2, 41.8, 42.5, 43.1, 42.8, 42.3, 42.5],
                        borderColor: '#249EAF',
                        backgroundColor: 'rgba(36, 158, 175, 0.12)',
                        fill: true,
                        tension: 0.35,
                        yAxisID: 'y'
                    },
                    {
                        label: 'Canopy Temp (°C)',
                        data: [21.5, 20.8, 24.2, 28.5, 27.1, 23.4, 22.0],
                        borderColor: '#F4A019',
                        borderDash: [3, 3],
                        fill: false,
                        tension: 0.35,
                        yAxisID: 'y1'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'top', labels: { font: { family: 'Inter', size: 12, weight: '600' } } },
                    tooltip: { backgroundColor: '#0D172B', cornerRadius: 10 }
                },
                scales: {
                    x: { grid: { display: false } },
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        grid: { color: '#F1F5F9' },
                        title: { display: true, text: 'Soil VWC %', font: { family: 'Inter', size: 11, weight: 'bold' } }
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        grid: { drawOnChartArea: false },
                        title: { display: true, text: 'Temp °C', font: { family: 'Inter', size: 11, weight: 'bold' } }
                    }
                }
            }
        });
    }
};

window.ChartService = ChartService;
