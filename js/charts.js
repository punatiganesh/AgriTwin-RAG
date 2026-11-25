// AgriTwin-RAG Dashboard - Chart.js Initialization and Management
// Real-Time Precision AgriTech Data Visualizations strictly driven by live telemetry

const chartColors = {
  forest: "#133e24",
  primary: "#1b4d2e",
  emerald: "#2d6a4f",
  accent: "#52b788",
  accentLight: "rgba(82, 183, 136, 0.15)",
  info: "#2563eb",
  infoLight: "rgba(37, 99, 235, 0.12)",
  warning: "#d97706",
  warningLight: "rgba(217, 119, 6, 0.12)",
  danger: "#dc2626",
  dangerLight: "rgba(220, 38, 38, 0.12)",
  grid: "rgba(0, 0, 0, 0.04)",
  textMuted: "#64748b",
};

const charts = {
  dashboardNDVI: null,
  dashboardEnv: null,
  weatherTemp: null,
  weatherHumidity: null,
  weatherRainfall: null,
  ndviTrend: null,
  predictionHistory: null,
};

function getCommonChartOptions(options = {}) {
  return {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: options.legend ?? true,
        position: "top",
        align: "end",
        labels: {
          usePointStyle: true,
          pointStyle: "circle",
          boxWidth: 8,
          boxHeight: 8,
          padding: 12,
          font: { family: "'Plus Jakarta Sans', sans-serif", size: 11, weight: "600" },
          color: "#334155",
        },
      },
      tooltip: {
        backgroundColor: "rgba(15, 23, 42, 0.9)",
        titleFont: { family: "'Plus Jakarta Sans', sans-serif", size: 12, weight: "700" },
        bodyFont: { family: "'Plus Jakarta Sans', sans-serif", size: 11, weight: "500" },
        padding: 10,
        cornerRadius: 8,
        displayColors: true,
      },
    },
    scales: {
      x: {
        grid: { display: false, drawBorder: false },
        ticks: {
          font: { family: "'Plus Jakarta Sans', sans-serif", size: 10 },
          color: chartColors.textMuted,
        },
      },
      y: {
        grid: { color: chartColors.grid, drawBorder: false },
        ticks: {
          font: { family: "'Plus Jakarta Sans', sans-serif", size: 10 },
          color: chartColors.textMuted,
          padding: 6,
        },
        ...options.yAxis,
      },
    },
  };
}

// 1. Dashboard Left Chart: Sentinel-2 Canopy Vigor (NDVI & Reflectance)
function createDashboardNDVIChart(canvasId = "dashboardNDVIChart") {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;

  if (charts.dashboardNDVI) {
    charts.dashboardNDVI.destroy();
  }

  const state = typeof FarmState !== "undefined" ? FarmState.get() : null;
  const ndviVal = state?.satellite?.ndvi !== null && state?.satellite?.ndvi !== undefined ? state.satellite.ndvi : null;
  const redVal = state?.satellite?.b04 !== null && state?.satellite?.b04 !== undefined ? state.satellite.b04 : null;
  const nirVal = state?.satellite?.b08 !== null && state?.satellite?.b08 !== undefined ? state.satellite.b08 : null;
  const acqDate = state?.satellite?.acquisitionDate || "Latest Pass";

  let labels = ["Red (B04)", "NIR (B08)", "NDVI Index"];
  let dataPoints = [redVal || 0, nirVal || 0, ndviVal || 0];

  const badgeEl = document.getElementById("chartNdviBadge");
  if (badgeEl) {
    badgeEl.textContent = ndviVal !== null ? `NDVI: ${ndviVal.toFixed(4)} (${acqDate})` : "Awaiting Sentinel-2 Telemetry";
  }

  charts.dashboardNDVI = new Chart(ctx, {
    type: "bar",
    data: {
      labels: labels,
      datasets: [
        {
          label: "Reflectance & Index",
          data: dataPoints,
          backgroundColor: [
            "rgba(220, 38, 38, 0.7)",  // Red band
            "rgba(37, 99, 235, 0.7)",  // NIR band
            "rgba(45, 106, 79, 0.85)", // NDVI
          ],
          borderColor: [
            chartColors.danger,
            chartColors.info,
            chartColors.emerald,
          ],
          borderWidth: 1.5,
          borderRadius: 6,
        },
      ],
    },
    options: getCommonChartOptions({
      yAxis: {
        min: 0,
        max: 1.0,
        ticks: {
          stepSize: 0.2,
          callback: (v) => v.toFixed(2),
        },
      },
    }),
  });
}

// 2. Dashboard Right Chart: Microclimate & Soil Telemetry Readings
function createDashboardEnvChart(canvasId = "dashboardEnvChart") {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;

  if (charts.dashboardEnv) {
    charts.dashboardEnv.destroy();
  }

  const state = typeof FarmState !== "undefined" ? FarmState.get() : null;
  const temp = state?.weather?.temperature !== null && state?.weather?.temperature !== undefined ? state.weather.temperature : null;
  const humid = state?.weather?.humidity !== null && state?.weather?.humidity !== undefined ? state.weather.humidity : null;
  const moist = state?.soil?.moisture !== null && state?.soil?.moisture !== undefined ? state.soil.moisture : null;
  const rain = state?.weather?.rainfall !== null && state?.weather?.rainfall !== undefined ? state.weather.rainfall : 0;

  const labels = ["Temp (°C)", "Humidity (%)", "Soil Moisture (%)", "Rainfall (mm)"];
  const values = [temp || 0, humid || 0, moist || 0, rain || 0];

  charts.dashboardEnv = new Chart(ctx, {
    type: "bar",
    data: {
      labels: labels,
      datasets: [
        {
          label: "Live Telemetry Value",
          data: values,
          backgroundColor: [
            "rgba(217, 119, 6, 0.75)",  // Temp (Amber)
            "rgba(2, 132, 199, 0.75)",  // Humidity (Sky)
            "rgba(20, 184, 166, 0.75)", // Soil Moisture (Teal)
            "rgba(37, 99, 235, 0.75)",  // Rain (Blue)
          ],
          borderColor: [
            chartColors.warning,
            "#0284c7",
            "#14b8a6",
            chartColors.info,
          ],
          borderWidth: 1.5,
          borderRadius: 6,
        },
      ],
    },
    options: getCommonChartOptions({
      yAxis: {
        beginAtZero: true,
      },
    }),
  });
}

// Hook called whenever FarmState updates to dynamically sync charts
function updateDashboardCharts(state) {
  if (!state) return;
  if (charts.dashboardNDVI) {
    createDashboardNDVIChart("dashboardNDVIChart");
  }
  if (charts.dashboardEnv) {
    createDashboardEnvChart("dashboardEnvChart");
  }
}

// Destroy charts on transition
function destroyAllCharts() {
  Object.keys(charts).forEach((key) => {
    if (charts[key]) {
      charts[key].destroy();
      charts[key] = null;
    }
  });
}
