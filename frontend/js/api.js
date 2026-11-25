/**
 * API Integration Layer for AgriTwin-RAG
 * Connects frontend modules to Flask backend endpoints
 */

const API_BASE_URL = (
  window.AGRITWIN_CONFIG?.apiBaseUrl ||
  localStorage.getItem("agritwin_api_base_url") ||
  "http://127.0.0.1:5000"
).replace(/\/$/, "");

function apiUrl(path) {
  return `${API_BASE_URL}${path.startsWith("/") ? "" : "/"}${path}`;
}

function apiFetch(path, options = {}) {
  return fetch(apiUrl(path), { ...options, credentials: "include" });
}

window.apiFetch = apiFetch;
window.apiUrl = apiUrl;

let activeFarmContext = null;
let farmContextRequest = null;

function clearFarmContextCache() {
  activeFarmContext = null;
  farmContextRequest = null;
}
window.clearFarmContextCache = clearFarmContextCache;

async function loadFarmContext(forceRefresh = false) {
  if (forceRefresh) {
    activeFarmContext = null;
    farmContextRequest = null;
  }
  if (!forceRefresh && activeFarmContext) {
    return { success: true, data: activeFarmContext };
  }
  if (!forceRefresh && farmContextRequest) return farmContextRequest;

  farmContextRequest = (async () => {
    try {
      const response = await apiFetch("/api/farm-context");
      const payload = await response.json().catch(() => ({}));
      const context = payload.farm_context || payload.farm || payload;
      const location = context?.location || {};
      const rawLatitude = location.latitude ?? context.latitude;
      const rawLongitude = location.longitude ?? context.longitude;
      const latitude = Number(rawLatitude);
      const longitude = Number(rawLongitude);

      if (!response.ok || payload.success === false) {
        throw new Error(
          payload.error || `Farm context request failed (${response.status}).`,
        );
      }
      if (
        rawLatitude == null ||
        rawLatitude === "" ||
        rawLongitude == null ||
        rawLongitude === "" ||
        !Number.isFinite(latitude) ||
        !Number.isFinite(longitude)
      ) {
        throw new Error(
          "Backend FarmContext did not include valid farm coordinates.",
        );
      }

      location.latitude = latitude;
      location.longitude = longitude;
      context.location = location;
      activeFarmContext = context;

      if (typeof FarmState !== "undefined" && FarmState.setFromBackend) {
        FarmState.setFromBackend(context);
      }

      // Keep legacy display integrations synchronized, but never read these as authority.
      try {
        const name =
          location.locality ||
          location.city ||
          location.place_name ||
          (Number.isFinite(latitude) && Number.isFinite(longitude)
            ? `Farm (${latitude.toFixed(4)}, ${longitude.toFixed(4)})`
            : "Farm Location");
        localStorage.setItem("farmLatitude", String(latitude));
        localStorage.setItem("farmLongitude", String(longitude));
        localStorage.setItem("farmLocationName", name);
        localStorage.setItem(
          "farmLocation",
          JSON.stringify({
            latitude,
            longitude,
            name,
            display_name: location.place_name || name,
            source: location.source || "Backend FarmContext",
            confirmed: true,
          }),
        );
      } catch (storageError) {
        console.warn("Farm location cache update failed:", storageError);
      }

      return { success: true, data: context };
    } catch (error) {
      return {
        success: false,
        error: error.message || "Unable to load farm context.",
      };
    } finally {
      farmContextRequest = null;
    }
  })();

  return farmContextRequest;
}

window.loadFarmContext = loadFarmContext;

async function updateFarmLocation(lat, lon, placeName = null, source = "Device GPS", accuracy = null) {
  clearFarmContextCache();
  try {
    const response = await apiFetch("/api/farm/context/location", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        location: {
          latitude: lat,
          longitude: lon,
          place_name: placeName,
          source: source,
          accuracy: accuracy,
          accuracy_m: accuracy,
        },
      }),
    });
    const payload = await response.json().catch(() => ({}));
    clearFarmContextCache();
    return payload;
  } catch (err) {
    console.error("updateFarmLocation error:", err);
    return { success: false, error: err.message };
  }
}
window.updateFarmLocation = updateFarmLocation;

function getFarmCoordinates() {
  const location = activeFarmContext?.location;
  if (!location || location.latitude == null || location.longitude == null) {
    return null;
  }
  return { latitude: location.latitude, longitude: location.longitude };
}

async function getLiveWeather(lat = null, lon = null) {
  let targetLat = lat;
  let targetLon = lon;

  if (targetLat === null || targetLon === null) {
    if (typeof FarmState !== "undefined") {
      const loc = FarmState.get().location;
      if (loc && loc.latitude !== null && loc.longitude !== null) {
        targetLat = loc.latitude;
        targetLon = loc.longitude;
      }
    }
  }

  if (targetLat === null || targetLon === null) {
    const farm = await loadFarmContext();
    if (farm.success) {
      const coords = getFarmCoordinates();
      if (coords) {
        targetLat = coords.latitude;
        targetLon = coords.longitude;
      }
    }
  }

  if (targetLat === null || targetLon === null) {
    return {
      success: false,
      error: "Please set your farm location first.",
    };
  }

  try {
    const response = await apiFetch(
      `/api/weather?lat=${encodeURIComponent(targetLat)}&lon=${encodeURIComponent(targetLon)}`,
    );

    if (!response.ok) {
      let payload = {};
      try {
        payload = await response.json();
      } catch (error) {
        payload = {};
      }
      return {
        success: false,
        error: payload.error || "Unable to load live weather data.",
      };
    }

    const data = await response.json();
    if (!data || data.success === false) {
      return {
        success: false,
        error: data?.error || "Unable to load live weather data.",
      };
    }

    return data;
  } catch (error) {
    return {
      success: false,
      error: "Unable to load live weather data.",
    };
  }
}

async function getLiveSoilData(lat = null, lon = null) {
  let targetLat = lat;
  let targetLon = lon;

  if (targetLat === null || targetLon === null) {
    if (typeof FarmState !== "undefined") {
      const loc = FarmState.get().location;
      if (loc && loc.latitude !== null && loc.longitude !== null) {
        targetLat = loc.latitude;
        targetLon = loc.longitude;
      }
    }
  }

  if (targetLat === null || targetLon === null) {
    const farm = await loadFarmContext();
    if (farm.success) {
      const coords = getFarmCoordinates();
      if (coords) {
        targetLat = coords.latitude;
        targetLon = coords.longitude;
      }
    }
  }

  if (targetLat === null || targetLon === null) {
    return {
      success: false,
      error: "Please set your farm location first.",
    };
  }

  try {
    const response = await apiFetch(
      `/api/soil?lat=${encodeURIComponent(targetLat)}&lon=${encodeURIComponent(targetLon)}`,
    );

    if (!response.ok) {
      let payload = {};
      try {
        payload = await response.json();
      } catch (error) {
        payload = {};
      }
      return {
        success: false,
        error: payload.error || "Unable to load live soil telemetry.",
      };
    }

    const data = await response.json();
    if (!data || data.success === false) {
      return {
        success: false,
        error: data?.error || "Unable to load live soil telemetry.",
      };
    }

    return data;
  } catch (error) {
    return {
      success: false,
      error: "Unable to connect to soil intelligence service.",
    };
  }
}

async function getLatestNDVIData(maxCloud = 30, lat = null, lon = null) {
  let targetLat = lat;
  let targetLon = lon;

  if (targetLat === null || targetLon === null) {
    if (typeof FarmState !== "undefined") {
      const loc = FarmState.get().location;
      if (loc && loc.latitude !== null && loc.longitude !== null) {
        targetLat = loc.latitude;
        targetLon = loc.longitude;
      }
    }
  }

  if (targetLat === null || targetLon === null) {
    const farm = await loadFarmContext();
    if (farm.success) {
      const coords = getFarmCoordinates();
      if (coords) {
        targetLat = coords.latitude;
        targetLon = coords.longitude;
      }
    }
  }

  if (targetLat === null || targetLon === null) {
    return {
      success: false,
      error: "Please set your farm location first.",
    };
  }

  try {
    const response = await apiFetch(
      `/api/ndvi?lat=${encodeURIComponent(targetLat)}&lon=${encodeURIComponent(targetLon)}&max_cloud=${encodeURIComponent(maxCloud)}`,
    );

    if (!response.ok) {
      let payload = {};
      try {
        payload = await response.json();
      } catch (error) {
        payload = {};
      }
      return {
        success: false,
        error: payload.error || "Unable to load Sentinel-2 NDVI observation.",
      };
    }

    const data = await response.json();
    if (!data || data.success === false) {
      return {
        success: false,
        error: data?.error || "Unable to load Sentinel-2 NDVI observation.",
      };
    }

    return data;
  } catch (error) {
    return {
      success: false,
      error: "Unable to connect to satellite remote sensing service.",
    };
  }
}

async function searchLocation(query) {
  if (!query || !query.trim()) {
    return {
      success: false,
      error: "Please enter a location name, village, or town to search.",
    };
  }

  try {
    const response = await apiFetch(
      `/api/location/search?q=${encodeURIComponent(query.trim())}`,
    );
    const data = await response.json();

    if (!response.ok || data.success === false) {
      return {
        success: false,
        error: data?.error || "Location search failed. Please try again.",
      };
    }

    return data;
  } catch (error) {
    return {
      success: false,
      error:
        "Unable to connect to location search service. Please check your network.",
    };
  }
}

async function reverseGeocode(lat, lon) {
  if (lat === undefined || lat === null || lon === undefined || lon === null) {
    return {
      success: false,
      error: "Latitude and longitude are required for address lookup.",
    };
  }

  try {
    const response = await apiFetch(
      `/api/location/reverse?lat=${encodeURIComponent(lat)}&lon=${encodeURIComponent(lon)}`,
    );
    const data = await response.json();

    if (!response.ok || data.success === false) {
      return {
        success: false,
        error: data?.error || "Unable to determine address from coordinates.",
      };
    }

    return data;
  } catch (error) {
    return {
      success: false,
      error: "Unable to connect to address lookup service.",
    };
  }
}

const API = {
  // Base URL for backend API
  baseURL: `${API_BASE_URL}/api`,

  // Flag to use mock data or real API (Strictly FALSE for production telemetry)
  useMockData: false,

  // ==================== Authentication APIs ====================

  /**
   * Login user with email and password
   */
  login: async function (identifier, password) {
    const response = await apiFetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ identifier, password }),
    });
    return response.json();
  },

  /**
   * Logout user
   */
  logout: async function () {
    const response = await apiFetch("/api/auth/logout", { method: "POST" });
    return response.json();
  },

  // ==================== Farm APIs ====================

  /**
   * Get farm information from backend FarmContext
   */
  getFarmData: async function () {
    return loadFarmContext(true);
  },

  /**
   * Update farm information in backend FarmContext
   */
  updateFarmData: async function (farmData) {
    try {
      const res = await apiFetch("/api/farm-context", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ farm_context: farmData }),
      });
      if (res.ok) {
        const data = await res.json();
        return { success: true, data: data.farm_context || data };
      }
    } catch (e) {
      console.warn("FarmContext update error:", e);
    }
    return { success: false, error: "Unable to update farm context." };
  },

  // ==================== Weather APIs ====================

  /**
   * Get live weather data from OpenWeather via backend
   */
  getWeatherData: async function (lat, lon) {
    try {
      let targetLat = lat;
      let targetLon = lon;
      if (targetLat == null || targetLon == null || isNaN(parseFloat(targetLat)) || isNaN(parseFloat(targetLon))) {
        const coordinates = getFarmCoordinates();
        if (!coordinates)
          return { success: false, error: "Farm location is unavailable." };
        targetLat = coordinates.latitude;
        targetLon = coordinates.longitude;
      }
      const res = await apiFetch(
        `/api/weather?lat=${encodeURIComponent(targetLat)}&lon=${encodeURIComponent(targetLon)}`,
      );
      if (res.ok) {
        const data = await res.json();
        return { success: true, data: data };
      }
    } catch (e) {
      console.warn("Weather API fetch error:", e);
    }
    return { success: false, error: "Weather data currently unavailable." };
  },

  getWeatherHistory: async function (days = 7) {
    return {
      success: false,
      error: "Weather history is not available from the backend.",
    };
  },

  getWeatherForecast: async function (days = 7) {
    return {
      success: false,
      error: "Weather forecast is not available from the backend.",
    };
  },

  // ==================== Soil APIs ====================

  /**
   * Get real soil data from ISRIC SoilGrids 2.0 via backend
   */
  getSoilData: async function (lat, lon) {
    try {
      let targetLat = lat;
      let targetLon = lon;
      if (targetLat == null || targetLon == null || isNaN(parseFloat(targetLat)) || isNaN(parseFloat(targetLon))) {
        const coordinates = getFarmCoordinates();
        if (!coordinates)
          return { success: false, error: "Farm location is unavailable." };
        targetLat = coordinates.latitude;
        targetLon = coordinates.longitude;
      }
      const res = await apiFetch(
        `/api/soil?lat=${encodeURIComponent(targetLat)}&lon=${encodeURIComponent(targetLon)}`,
      );
      if (res.ok) {
        const data = await res.json();
        return { success: true, data: data };
      }
    } catch (e) {
      console.warn("Soil API fetch error:", e);
    }
    return { success: false, error: "Soil data currently unavailable." };
  },

  getSoilHistory: async function () {
    return {
      success: false,
      error: "Soil history is not available from the backend.",
    };
  },

  // ==================== Satellite / NDVI APIs ====================

  getNDVIData: async function (maxCloud = 30) {
    return getLatestNDVIData(maxCloud);
  },

  getSatelliteImage: async function (maxCloud = 30, lat = null, lon = null) {
    const ndvi = await getLatestNDVIData(maxCloud, lat, lon);
    if (ndvi && ndvi.success && (ndvi.image_url || ndvi.preview_url || ndvi.thumbnail_url)) {
      return {
        success: true,
        image_url: ndvi.image_url || ndvi.preview_url || ndvi.thumbnail_url,
        preview_url: ndvi.preview_url,
        thumbnail_url: ndvi.thumbnail_url,
        acquisition_date: ndvi.acquisition_date,
        cloud_percentage: ndvi.cloud_percentage,
        vegetation_condition: ndvi.vegetation_condition,
        ndvi: ndvi.ndvi,
        item_id: ndvi.item_id,
      };
    }
    return {
      success: false,
      error: ndvi?.error || "Satellite imagery currently unavailable for this farm location.",
    };
  },

  // ==================== AI Prediction APIs ====================

  /**
   * Get 4-tier AI farm risk prediction from backend
   */
  getPrediction: async function (farmContext = null) {
    try {
      const activeCtx =
        farmContext ||
        (typeof FarmState !== "undefined" ? FarmState.get() : null);
      const res = await apiFetch("/api/prediction/evaluate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ farm_context: activeCtx }),
      });
      if (res.ok) {
        return await res.json();
      }
    } catch (e) {
      console.warn("Prediction API error:", e);
    }
    return {
      success: false,
      error: "Prediction engine currently unavailable.",
      risks: {
        irrigation_risk: "UNAVAILABLE",
        crop_stress_risk: "UNAVAILABLE",
        disease_risk: "UNAVAILABLE",
        overall_farm_risk: "UNAVAILABLE",
      },
      factors: [],
    };
  },

  getPredictionHistory: async function () {
    return {
      success: false,
      error: "Prediction history is not available from the backend.",
    };
  },

  // ==================== Explainable AI APIs ====================

  /**
   * Get XAI contributing factors & model attribution
   */
  getExplainableAI: async function (farmContext = null) {
    try {
      const pred = await this.getPrediction(farmContext);
      if (pred && pred.success) {
        return {
          success: true,
          data: {
            features: pred.factors || [],
            risks: pred.risks || {},
            data_used: pred.data_used || [],
            model_attribution: pred.model_attribution || {},
            timestamp: pred.timestamp || new Date().toISOString(),
          },
        };
      }
    } catch (e) {
      console.warn("ExplainableAI error:", e);
    }
    return {
      success: false,
      error: "Explainable AI data currently unavailable.",
    };
  },

  // ==================== Recommendations APIs ====================

  /**
   * Get dynamic agricultural recommendations synthesized from active FarmContext + ICAR retrieval
   * @param {object} [farmContext]
   * @param {string} [language]
   * @returns {Promise}
   */
  getRecommendations: async function (farmContext = null, language = "en") {
    try {
      const activeCtx =
        farmContext ||
        (typeof FarmState !== "undefined" ? FarmState.get() : null);
      const res = await apiFetch("/api/recommendations/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ farm_context: activeCtx, language: language }),
      });
      if (res.ok) {
        const data = await res.json();
        return data;
      }
    } catch (e) {
      console.warn("Error fetching recommendations API:", e);
    }

    return {
      success: false,
      error:
        "Unable to generate dynamic recommendations. Please check the backend connection.",
    };
  },

  /**
   * Evaluate a What-If farm simulation scenario against ICAR agricultural evidence
   * @param {string} scenario
   * @param {number} [moistureDelta]
   * @param {number} [tempDelta]
   * @param {object} [farmContext]
   * @returns {Promise}
   */
  runSimulation: async function (
    scenario,
    moistureDelta = 0,
    tempDelta = 0,
    farmContext = null,
  ) {
    try {
      const activeCtx =
        farmContext ||
        (typeof FarmState !== "undefined" ? FarmState.get() : null);
      const res = await apiFetch("/api/simulation/evaluate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          scenario: scenario,
          moisture_delta: moistureDelta,
          temperature_delta: tempDelta,
          farm_context: activeCtx,
        }),
      });
      if (res.ok) {
        return await res.json();
      }
    } catch (e) {
      console.error("Simulation API error:", e);
    }
    return {
      success: false,
      error: "Simulation engine temporarily unavailable.",
    };
  },

  /**
   * Record farmer decision and feedback ([Accept], [Modify], [Ignore])
   * @param {string} decision
   * @param {string} feedbackText
   * @param {string} recTitle
   * @param {object} [farmContext]
   * @returns {Promise}
   */
  submitFeedback: async function (
    decision,
    feedbackText = "",
    recTitle = "General Advisory",
    farmContext = null,
  ) {
    try {
      const activeCtx =
        farmContext ||
        (typeof FarmState !== "undefined" ? FarmState.get() : null);
      const res = await apiFetch("/api/feedback/submit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          decision: decision,
          feedback: feedbackText,
          recommendation_title: recTitle,
          farm_context: activeCtx,
        }),
      });
      if (res.ok) {
        return await res.json();
      }
    } catch (e) {
      console.error("Feedback submit error:", e);
    }
    return { success: false, error: "Unable to submit feedback." };
  },

  /**
   * Get feedback audit logs
   */
  getFeedbackList: async function () {
    try {
      const res = await apiFetch("/api/feedback/list");
      if (res.ok) return await res.json();
    } catch (e) {}
    return {
      success: false,
      error: "Unable to load feedback from the backend.",
    };
  },

  /**
   * Execute 3-way research evaluation benchmark
   */
  runEvaluation: async function () {
    try {
      const res = await apiFetch("/api/evaluation/run", { method: "POST" });
      if (res.ok) return await res.json();
    } catch (e) {
      console.error("Evaluation run error:", e);
    }
    return { success: false, error: "Evaluation engine unreachable." };
  },

  // ==================== Chatbot / RAG APIs ====================

  /**
   * Send question to RAG Assistant API
   * Calls POST /api/rag/chat on the Flask backend
   * @param {string} question - Farmer's agricultural question
   * @param {object} [farmContext] - Optional centralized FarmContext object
   * @param {string} [language] - Language code ('en', 'te', 'ta', 'hi' or BCP-47 tag)
   * @returns {Promise<{success: boolean, query?: string, answer?: string, language?: string, sources?: Array, farm_context_used?: boolean, farm_context?: object, provenance?: object, context_used?: object, error?: string}>}
   */
  sendChatMessage: async function (
    question,
    farmContext = null,
    language = "en",
  ) {
    if (!question || !question.trim()) {
      return {
        success: false,
        error: "Please enter your question.",
      };
    }

    const farmResult = await loadFarmContext();
    if (!farmResult.success) return farmResult;

    try {
      const authoritativeContext =
        farmContext && typeof farmContext === "object"
          ? {
              ...farmResult.data,
              ...farmContext,
              location: farmResult.data.location,
            }
          : farmResult.data;
      const payload = {
        query: question.trim(),
        message: question.trim(),
        language: language || "en",
        selected_language: language || "en",
      };
      payload.farm_context = authoritativeContext;

      const response = await apiFetch("/api/rag/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });

      let data = {};
      try {
        data = await response.json();
      } catch (parseErr) {
        data = {};
      }

      if (!response.ok) {
        console.error("RAG API error response:", response.status, data);

        let errorMsg = data.error;
        if (!errorMsg) {
          if (response.status === 400) {
            errorMsg = "Please enter a valid agricultural question.";
          } else if (response.status === 401) {
            errorMsg =
              "AI service authentication failed. Please try again later.";
          } else if (response.status === 404) {
            errorMsg = "No relevant agricultural information was found.";
          } else if (response.status === 503) {
            errorMsg =
              "AI service is currently unavailable. Please check configuration.";
          } else {
            errorMsg = "AgriTwin encountered a server error. Please try again.";
          }
        }

        return {
          success: false,
          error: errorMsg,
          statusCode: response.status,
        };
      }

      // Successful 200 response
      return {
        success: data.success !== false,
        query: data.query || question,
        answer: data.answer || "No response received.",
        sources: Array.isArray(data.sources) ? data.sources : [],
        farm_context_used: Boolean(data.farm_context_used),
        farm_context: data.farm_context || null,
        provenance: data.provenance || null,
      };
    } catch (networkError) {
      console.error("RAG API network error:", networkError);
      return {
        success: false,
        error:
          "Unable to connect to AgriTwin. Please check that the server is running.",
      };
    }
  },

  /**
   * Get chat history
   * @returns {Promise}
   */
  getChatHistory: async function () {
    return {
      success: false,
      error: "Chat history is not available from the backend.",
    };
  },

  // ==================== Digital Twin APIs ====================

  /**
   * Get digital twin data from FarmState
   */
  getDigitalTwin: async function () {
    if (typeof FarmState !== "undefined") {
      const state = FarmState.get();
      return {
        success: true,
        data: {
          cropHealth:
            state.satellite.ndvi !== null
              ? Math.round(state.satellite.ndvi * 100)
              : null,
          stressScore: state.prediction.water_stress_score,
          riskLevel: state.prediction.water_stress,
          weather: state.weather,
          soil: state.soil,
          satellite: state.satellite,
        },
      };
    }
    return { success: false, error: "Digital Twin state unavailable." };
  },

  // ==================== Reports APIs ====================

  /**
   * Generate report based on live FarmState
   */
  generateReport: async function (reportType) {
    return {
      success: false,
      error: "Report generation is not available from the backend.",
    };
  },

  /**
   * Download report
   */
  downloadReport: async function (reportType) {
    return {
      success: false,
      error: "Report downloads are not available from the backend.",
    };
  },

  // ==================== Settings APIs ====================

  /**
   * Get user settings
   */
  getUserSettings: async function () {
    return {
      success: false,
      error: "User settings are not available from the backend.",
    };
  },

  /**
   * Update user settings
   */
  updateUserSettings: async function (settings) {
    return {
      success: false,
      error: "User settings are not available from the backend.",
    };
  },

  /**
   * Update user profile
   */
  updateUserProfile: async function (profileData) {
    if (typeof FarmState !== "undefined") {
      FarmState.updateProfile(profileData);
    }
    return {
      success: false,
      error: "Profile persistence is not available from the backend.",
    };
  },
};

API.getLiveWeather = getLiveWeather;
API.getLiveSoilData = getLiveSoilData;
API.getLatestNDVIData = getLatestNDVIData;
API.searchLocation = searchLocation;
API.reverseGeocode = reverseGeocode;

/**
 * Assemble centralized FarmContext structure from live telemetry and local storage.
 * Missing fields remain null or "Not available". Never invents values.
 */
API.getFarmContext = async function (customCrop = null) {
  const farmResult = await loadFarmContext();
  if (!farmResult.success) return farmResult;
  const farmState = typeof FarmState !== "undefined" ? FarmState.get() : null;
  const location = farmResult.data.location || farmState?.location || {};
  const latitude = location.latitude;
  const longitude = location.longitude;

  const cropState = farmState?.crop || {};

  const crop = {
    name: customCrop?.name || cropState.name || "Rice",
    variety: customCrop?.variety || cropState.variety || null,
    growth_stage:
      customCrop?.growth_stage ||
      customCrop?.stage ||
      cropState.growth_stage ||
      cropState.growthStage ||
      null,
  };

  const context = {
    location: {
      latitude: latitude ?? null,
      longitude: longitude ?? null,
      place_name: location.place_name || null,
    },
    crop: crop,
    weather: {
      temperature: null,
      humidity: null,
      rainfall: null,
      wind_speed: null,
      pressure: null,
      weather_condition: null,
    },
    soil: {
      soil_type: null,
      ph: null,
      moisture: null,
      nitrogen: null,
      phosphorus: null,
      potassium: null,
    },
    satellite: {
      ndvi: null,
      vegetation_status: "Not available",
    },
  };

  if (latitude != null && longitude != null) {
    try {
      const weatherRes = await getLiveWeather();
      if (weatherRes && weatherRes.success && weatherRes.weather) {
        const w = weatherRes.weather;
        context.weather.temperature =
          w.temperature !== undefined ? w.temperature : null;
        context.weather.humidity = w.humidity !== undefined ? w.humidity : null;
        context.weather.rainfall =
          w.rainfall !== undefined
            ? w.rainfall
            : w.rainfall_1h !== undefined
              ? w.rainfall_1h
              : null;
        context.weather.wind_speed =
          w.wind_speed !== undefined ? w.wind_speed : null;
        context.weather.pressure = w.pressure !== undefined ? w.pressure : null;
        context.weather.weather_condition =
          w.condition || w.description || null;
      }
    } catch (e) {
      console.warn("Weather context error:", e);
    }

    try {
      const soilRes = await getLiveSoilData();
      if (soilRes && soilRes.success && soilRes.soil) {
        const s = soilRes.soil;
        context.soil.soil_type = soilRes.texture_class || null;
        context.soil.ph = s.ph !== undefined ? s.ph : null;
        context.soil.moisture =
          s.water_content !== undefined ? s.water_content : null;
        context.soil.nitrogen =
          s.total_nitrogen !== undefined ? s.total_nitrogen : null;
      }
    } catch (e) {
      console.warn("Soil context error:", e);
    }

    try {
      const ndviRes = await getLatestNDVIData();
      if (ndviRes && ndviRes.success) {
        context.satellite.ndvi =
          ndviRes.ndvi !== undefined ? ndviRes.ndvi : null;
        context.satellite.vegetation_status =
          ndviRes.vegetation_condition || "Not available";
      }
    } catch (e) {
      console.warn("NDVI context error:", e);
    }
  }

  return context;
};

API.predictDisease = async function (formData) {
  try {
    const response = await apiFetch("/api/disease/predict", {
      method: "POST",
      body: formData,
    });
    const data = await response.json();
    return data;
  } catch (error) {
    return {
      success: false,
      error: "Network error communicating with disease prediction service.",
    };
  }
};

API.getDiseaseAdvisory = async function (payload) {
  try {
    const response = await apiFetch("/api/disease/advisory", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    return data;
  } catch (error) {
    return {
      success: false,
      error: "Network error retrieving ICAR disease advisory.",
    };
  }
};

API.getDiseaseStatus = async function () {
  try {
    const response = await apiFetch("/api/disease/status");
    const data = await response.json();
    return data;
  } catch (error) {
    return {
      success: false,
      error: "Unable to retrieve disease model status.",
    };
  }
};

API.getPrediction = async function (farmContext = null) {
  try {
    const payload = farmContext || (window.FarmState ? window.FarmState.get() : null);
    const response = await apiFetch("/api/prediction", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ farm_context: payload }),
    });
    return await response.json();
  } catch (error) {
    console.error("API.getPrediction error:", error);
    return {
      success: false,
      error: "Network error fetching farm risk assessment.",
      risks: {
        irrigation_risk: "UNAVAILABLE",
        crop_stress_risk: "UNAVAILABLE",
        disease_risk: "UNAVAILABLE",
        overall_farm_risk: "UNAVAILABLE",
      },
    };
  }
};

API.getFarmRisk = API.getPrediction;

API.getRecommendations = async function (farmContext = null) {
  try {
    const payload = farmContext || (window.FarmState ? window.FarmState.get() : null);
    const response = await apiFetch("/api/recommendations/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ farm_context: payload }),
    });
    return await response.json();
  } catch (error) {
    console.error("API.getRecommendations error:", error);
    return {
      success: false,
      cards: [],
      error: "Network error retrieving recommendations.",
    };
  }
};

API.submitFeedback = async function (decision, feedback, recommendationTitle = "Agronomic Advisory") {
  try {
    const response = await apiFetch("/api/feedback/submit", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        decision: decision,
        feedback: feedback,
        recommendation_title: recommendationTitle,
        farm_context: window.FarmState ? window.FarmState.get() : null,
      }),
    });
    return await response.json();
  } catch (error) {
    console.error("API.submitFeedback error:", error);
    return { success: false, error: error.message };
  }
};

API.getFarmerFeedbackList = async function () {
  try {
    const response = await apiFetch("/api/feedback/list");
    return await response.json();
  } catch (error) {
    return { success: false, feedback: [] };
  }
};

API.runEvaluationBenchmark = async function (sampleCount = 3) {
  try {
    const response = await apiFetch("/api/evaluation/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ sample_count: sampleCount }),
    });
    return await response.json();
  } catch (error) {
    console.error("API.runEvaluationBenchmark error:", error);
    return { success: false, error: error.message };
  }
};

API.refreshFarmTelemetry = async function () {
  try {
    const response = await apiFetch("/api/farm/refresh", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
    });
    return await response.json();
  } catch (error) {
    return { success: false, error: "Network error refreshing telemetry." };
  }
};

API.generateReport = async function (farmContext = null) {
  try {
    const payload = farmContext || (window.FarmState ? window.FarmState.get() : null);
    const response = await apiFetch("/api/reports/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ farm_context: payload }),
    });
    return await response.json();
  } catch (error) {
    console.error("API.generateReport error:", error);
    return { success: false, error: "Network error generating farm report." };
  }
};

API.getReportsHistory = async function () {
  try {
    const response = await apiFetch("/api/reports/history");
    return await response.json();
  } catch (error) {
    return { success: false, reports: [] };
  }
};

// Export for use in other modules
if (typeof module !== "undefined" && module.exports) {
  module.exports = API;
}
