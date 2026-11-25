/**
 * Mock Data for AgriTwin-RAG Dashboard
 * Provides realistic dummy data for all dashboard components
 * Backend APIs will replace these functions later
 */

const mockData = {
  // Current logged-in user
  currentUser: {
    id: "USR-001",
    name: "Rajesh Kumar",
    email: "rajesh.kumar@agritwin.com",
    phone: "+91 98765 43210",
    role: "Farmer",
    avatar: "R",
    profileImage: null,
    location: null,
  },

  // Farm Information
  farm: {
    id: "FARM-001",
    name: "Precision Farm",
    location: null,
    latitude: null,
    longitude: null,
    area: 5, // acres
    areaInHectares: 2.02,
    crop: "Rice (Paddy)",
    variety: "MTU-1010",
    sowingDate: "2024-07-15",
    cropAge: 45, // days
    growthStage: "Flowering Stage",
    expectedHarvestDate: "2024-11-15",
    lastUpdated: "Just now",
    healthScore: 72, // out of 100
    status: "Healthy with Water Stress Alert",
    soilHealth: 68,
    cropHealth: 74,
    waterAvailability: 28,
    climateRisk: 72
  },

  // Current Weather Data
  weather: {
    current: {
      temperature: 32.8, // °C
      feelsLike: 32.8,
      humidity: 36, // %
      rainfall: 0, // mm
      windSpeed: 9.29, // m/s
      windDirection: "SSW",
      pressure: 1006, // hPa
      condition: "Overcast Clouds",
      conditionCategory: "Partly Cloudy",
      icon: "cloud-sun",
      uvIndex: 7.2,
    },

    // Historical weather data for trends (last 7 days)
    historicalData: [
      { date: "2024-09-06", temperature: 30.2, temp: 30.2, humidity: 42, rainfall: 0, soilMoisture: 35 },
      { date: "2024-09-07", temperature: 31.5, temp: 31.5, humidity: 39, rainfall: 0, soilMoisture: 33 },
      { date: "2024-09-08", temperature: 32.1, temp: 32.1, humidity: 38, rainfall: 2.5, soilMoisture: 36 },
      { date: "2024-09-09", temperature: 33.2, temp: 33.2, humidity: 35, rainfall: 0, soilMoisture: 32 },
      { date: "2024-09-10", temperature: 32.9, temp: 32.9, humidity: 36, rainfall: 0, soilMoisture: 30 },
      { date: "2024-09-11", temperature: 32.5, temp: 32.5, humidity: 37, rainfall: 0, soilMoisture: 29 },
      { date: "2024-09-12", temperature: 32.8, temp: 32.8, humidity: 36, rainfall: 0, soilMoisture: 28 },
    ],

    // 7-day weather forecast
    forecast: [
      {
        date: "2024-09-13",
        dayName: "Fri",
        fullDay: "Friday",
        tempHigh: 33.2,
        tempLow: 26.5,
        condition: "Partly Cloudy",
        icon: "cloud-sun",
        rainfall: 0,
        humidity: 35,
        windSpeed: 9.5,
      },
      {
        date: "2024-09-14",
        dayName: "Sat",
        fullDay: "Saturday",
        tempHigh: 34.1,
        tempLow: 27.2,
        condition: "Sunny",
        icon: "sun",
        rainfall: 0,
        humidity: 33,
        windSpeed: 8.9,
      },
      {
        date: "2024-09-15",
        dayName: "Sun",
        fullDay: "Sunday",
        tempHigh: 33.8,
        tempLow: 26.9,
        condition: "Partly Cloudy",
        icon: "cloud-sun",
        rainfall: 0,
        humidity: 34,
        windSpeed: 9.1,
      },
      {
        date: "2024-09-16",
        dayName: "Mon",
        fullDay: "Monday",
        tempHigh: 32.5,
        tempLow: 26.1,
        condition: "Scattered Rain",
        icon: "cloud-rain",
        rainfall: 12.5,
        humidity: 65,
        windSpeed: 15.3,
      },
      {
        date: "2024-09-17",
        dayName: "Tue",
        fullDay: "Tuesday",
        tempHigh: 31.2,
        tempLow: 25.8,
        condition: "Moderate Rain",
        icon: "cloud-showers-heavy",
        rainfall: 18.2,
        humidity: 72,
        windSpeed: 16.8,
      },
      {
        date: "2024-09-18",
        dayName: "Wed",
        fullDay: "Wednesday",
        tempHigh: 31.8,
        tempLow: 26.3,
        condition: "Partly Cloudy",
        icon: "cloud-sun",
        rainfall: 2.1,
        humidity: 56,
        windSpeed: 11.2,
      },
      {
        date: "2024-09-19",
        dayName: "Thu",
        fullDay: "Thursday",
        tempHigh: 33.5,
        tempLow: 27.1,
        condition: "Clear Sky",
        icon: "sun",
        rainfall: 0,
        humidity: 32,
        windSpeed: 8.7,
      },
    ],
  },

  // Soil Data
  soil: {
    ph: 6.5,
    nitrogen: 80, // kg/ha
    phosphorus: 40, // kg/ha
    potassium: 50, // kg/ha
    organicCarbon: 1.2, // %
    moisture: 28, // %
    soilType: "Clay Loam",
    texture: "Clay Loam (60% Clay, 25% Sand, 15% Silt)",
    salinity: 0.35, // ds/m (Electrical Conductivity)
    classification: "Good",
    lastTestedDate: "2024-08-20",
    recommendations: [
      "Nitrogen levels are adequate for current growth stage",
      "Consider adding phosphorus next season",
      "Maintain current moisture level with drip irrigation",
    ],
  },

  // Satellite/NDVI Data
  ndvi: {
    value: 0.42,
    trend: "increasing",
    trendPercent: 8.5,
    classification: "Moderate vegetation health",
    lastUpdated: "2 days ago",
    historicalData: [
      { date: "2024-08-19", ndvi: 0.28, value: 0.28 },
      { date: "2024-08-26", ndvi: 0.32, value: 0.32 },
      { date: "2024-09-02", ndvi: 0.38, value: 0.38 },
      { date: "2024-09-09", ndvi: 0.40, value: 0.40 },
      { date: "2024-09-12", ndvi: 0.42, value: 0.42 },
    ],
    status: "Healthy",
  },

  // AI Prediction Data
  prediction: {
    mainRisk: "Crop Water Stress",
    riskScore: 82, // out of 100
    riskLevel: "HIGH RISK",
    riskColor: "danger",
    confidence: 0.91, // 91%
    modelEngine: "AgriTwin Prediction Engine (XGBoost + LSTM)",
    predictions: [
      {
        name: "Water Stress Risk",
        score: 82,
        level: "HIGH",
        color: "danger",
      },
      {
        name: "Disease Risk",
        score: 25,
        level: "LOW",
        color: "success",
      },
      {
        name: "Pest Infestation",
        score: 45,
        level: "MEDIUM",
        color: "warning",
      },
      {
        name: "Nutrient Deficiency",
        score: 35,
        level: "MEDIUM",
        color: "warning",
      },
    ],

    // Input features used for prediction
    inputFeatures: {
      temperature: 32.8,
      humidity: 36,
      rainfall: 0,
      soilMoisture: 28,
      ndvi: 0.42,
      cropGrowthStage: "Flowering",
      daysToHarvest: 65,
    },

    // Model Information
    model: {
      name: "AgriTwin Prediction Engine",
      type: "Machine Learning (XGBoost + LSTM)",
      version: "2.4",
      status: "Active",
      lastTrained: "2024-09-01",
      accuracy: 0.91,
      description: "Hybrid precision model combining CNN, Bi-LSTM, and Gradient Boosting for precision agriculture.",
    },

    // Prediction history
    historyData: [
      { date: "2024-09-06", score: 68, riskLevel: 68 },
      { date: "2024-09-07", score: 70, riskLevel: 70 },
      { date: "2024-09-08", score: 75, riskLevel: 75 },
      { date: "2024-09-09", score: 78, riskLevel: 78 },
      { date: "2024-09-10", score: 80, riskLevel: 80 },
      { date: "2024-09-11", score: 81, riskLevel: 81 },
      { date: "2024-09-12", score: 82, riskLevel: 82 },
    ],
  },

  // Explainable AI (SHAP) Data
  explainableAI: {
    mainPrediction: "High crop water stress risk detected",
    mainScore: 82,
    explanation:
      "The model predicts high water-stress risk (82%) mainly because of elevated canopy temperature (32.8°C), critically low soil moisture (28%), rainfall deficit (0 mm), and moderate vegetation index (0.42).",
    featureImportance: [
      {
        feature: "Temperature",
        contribution: 0.32,
        percent: 32,
        type: "positive",
        value: 32.8,
        unit: "°C",
        impact: "High temperature increases evapotranspiration demand",
      },
      {
        feature: "Soil Moisture",
        contribution: 0.28,
        percent: 28,
        type: "negative",
        value: 28,
        unit: "%",
        impact: "Low soil moisture reduces root water intake",
      },
      {
        feature: "Rainfall",
        contribution: 0.19,
        percent: 19,
        type: "negative",
        value: 0,
        unit: "mm",
        impact: "No precipitation in last 4 days accelerates soil dryness",
      },
      {
        feature: "NDVI",
        contribution: 0.13,
        percent: 13,
        type: "negative",
        value: 0.42,
        unit: "index",
        impact: "Canopy stress detected in multispectral infrared reflectance",
      },
      {
        feature: "Humidity",
        contribution: 0.08,
        percent: 8,
        type: "negative",
        value: 36,
        unit: "%",
        impact: "Dry ambient air elevates vapor pressure deficit (VPD)",
      },
    ],
  },

  // AI Recommendations
  recommendations: [
    {
      id: 1,
      priority: "HIGH",
      icon: "droplet",
      title: "Monitor soil moisture & increase irrigation",
      description: "Current moisture (28%) is below the preferred range (40-50%) for the rice flowering stage.",
      reason: "Current soil moisture (28%) is below optimal level. Evapotranspiration is elevated due to 32.8°C ambient heat.",
      action: "Schedule irrigation for 3-4 hours today",
      timestamp: "2 hours ago",
      status: "Active",
    },
    {
      id: 2,
      priority: "MEDIUM",
      icon: "cloud-rain",
      title: "Monitor rainfall & weather outlook",
      description: "Weather conditions indicate limited rainfall over next 3 days, followed by showers on Sep 16-17.",
      reason: "Expected rainfall 12.5-18.2 mm will help replenish soil moisture. Plan fertigation schedule accordingly.",
      action: "Coordinate irrigation with forecasted rain to optimize water usage",
      timestamp: "5 hours ago",
      status: "Active",
    },
    {
      id: 3,
      priority: "LOW",
      icon: "satellite",
      title: "Monitor NDVI vegetation index",
      description: "Vegetation health should be monitored during the next Sentinel-2 satellite update in 2 days.",
      reason: "NDVI trend is increasing (+8.5%), indicating positive response to current crop management.",
      action: "Check leaf color and multispectral reflectance",
      timestamp: "8 hours ago",
      status: "Active",
    },
    {
      id: 4,
      priority: "LOW",
      icon: "seedling",
      title: "Plan post-flowering nutrient application",
      description: "Rice is at 45 days (flowering stage). Plan potassium and phosphorus boost for grain filling.",
      reason: "Proper nutrition during grain filling stage ensures high milling yield and prevents lodging.",
      action: "Apply potassium top-dressing in 2 weeks",
      timestamp: "12 hours ago",
      status: "Active",
    },
  ],

  // Farm Alerts & Notifications
  alerts: [
    {
      id: 1,
      severity: "danger",
      type: "alert",
      title: "Water stress detected",
      description: "AI Prediction Engine flagged 82% water stress risk in Field Zone A.",
      time: "2 hours ago",
      unread: true,
    },
    {
      id: 2,
      severity: "warning",
      type: "warning",
      title: "Low soil moisture below 30%",
      description: "Sensor S-02 recorded 28% volumetric water content.",
      time: "5 hours ago",
      unread: true,
    },
    {
      id: 3,
      severity: "success",
      type: "sync",
      title: "Weather data synchronized",
      description: "Automated hyper-local meteorological station feed refreshed.",
      time: "Today at 06:00 AM",
      unread: false,
    },
    {
      id: 4,
      severity: "info",
      type: "satellite",
      title: "Sentinel-2 NDVI updated",
      description: "Mean NDVI calculated at 0.42 (+8.5% over 7 days).",
      time: "2 days ago",
      unread: false,
    }
  ],

  // Chat Bot Messages (Mock Conversations)
  chatMessages: [
    {
      id: 1,
      type: "user",
      message: "What is the current condition of my crop?",
      timestamp: "10:15 AM",
    },
    {
      id: 2,
      type: "bot",
      message:
        "Your rice crop (MTU-1010, 5 acres) is currently at Day 45 (Flowering stage). The overall Farm Health Score is 72/100. However, the AI Prediction Engine has identified an **82% Water Stress Risk** due to current soil moisture at 28% and ambient temperature at 32.8°C. Immediate 3-4 hour irrigation is recommended today.",
      timestamp: "10:15 AM",
    },
    {
      id: 3,
      type: "user",
      message: "Should I irrigate today?",
      timestamp: "10:18 AM",
    },
    {
      id: 4,
      type: "bot",
      message:
        "**Yes, irrigation is strongly recommended today.**\n\n• **Current Soil Moisture:** 28% (Target: 40-50% for flowering rice)\n• **Weather:** 32.8°C with 36% humidity (high evapotranspiration)\n• **Forecast:** Rain is not expected until September 16th (3 days away).\n\n💡 **Recommended Action:** Initiate 3 to 4 hours of irrigation to bring root-zone moisture above 38%.",
      timestamp: "10:18 AM",
    },
  ],

  // Suggested Questions for Chatbot
  suggestedQuestions: [
    "Why is my crop stressed?",
    "Should I irrigate today?",
    "How can I improve soil health?",
    "What is the 7-day rainfall outlook?",
    "Explain the 82% water risk SHAP values"
  ],

  // Reports Data
  reports: {
    weatherReport: {
      title: "Weather Analysis Report",
      dateGenerated: new Date().toLocaleDateString(),
      summary:
        "Last 7 days show consistent high temperatures (30.2–33.2°C) with low humidity (35–42%). Rainfall was minimal with only 2.5mm recorded. Forecast indicates high likelihood of significant showers on 16–17 September.",
      details: {
        avgTemperature: 32.1,
        maxTemperature: 33.2,
        minTemperature: 30.2,
        totalRainfall: 2.5,
        avgHumidity: 37,
        avgWindSpeed: 9.3,
      },
    },
    cropHealthReport: {
      title: "Crop Health Analysis Report",
      dateGenerated: new Date().toLocaleDateString(),
      summary:
        "Rice crop at 45 days is in peak flowering stage. Health score is 72/100. NDVI shows moderate vegetation vigor (0.42) with an upward +8.5% trend. Water stress is the primary limiting factor.",
      details: {
        healthScore: 72,
        ndvi: 0.42,
        cropAge: 45,
        stage: "Flowering",
        mainIssue: "Water Stress (82%)",
      },
    },
    soilReport: {
      title: "Soil Analysis Report",
      dateGenerated: new Date().toLocaleDateString(),
      summary:
        "Soil type is Clay Loam with excellent nutrient retention capacity. pH is 6.5 (optimal). N-P-K levels are 80-40-50 kg/ha. Soil moisture is at 28%, which is below the 40% optimal threshold for rice.",
      details: {
        ph: 6.5,
        nitrogen: 80,
        phosphorus: 40,
        potassium: 50,
        moisture: 28,
        organicCarbon: 1.2,
      },
    },
  },

  // Settings
  settings: {
    notifications: {
      emailAlerts: true,
      weatherAlerts: true,
      irrigationReminders: true,
      healthWarnings: true,
      predictionUpdates: true,
    },
    preferences: {
      language: "English",
      units: "Metric (°C, mm, m/s)",
      theme: "Light (AgriTech Emerald)",
      refreshInterval: "5 minutes"
    }
  }
};

// Aliases for backwards compatibility with all scripts
mockData.weather.historical = mockData.weather.historicalData;
mockData.ndvi.historical = mockData.ndvi.historicalData;
mockData.prediction.history = mockData.prediction.historyData;
