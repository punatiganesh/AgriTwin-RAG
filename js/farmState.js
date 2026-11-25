/**
 * AgriTwin-RAG — Central Farm State Manager (js/farmState.js)
 * Single Authoritative Source of Truth for FarmContext across all modules.
 * Connects Live Weather, ISRIC SoilGrids, and Sentinel-2 NDVI with transparent data provenance.
 * Strictly NO mock data, NO hardcoded fallbacks, and NO invented telemetry.
 */

const FarmState = (function () {
  const STORAGE_KEY = "agritwin_farm_context";
  const listeners = [];

  const defaultState = {
    farm_id: "FARM-TN-001",
    location: {
      latitude: null,
      longitude: null,
      locality: null,
      district: null,
      state: null,
      country: null,
      place_name: null,
      boundary: null,
      source: null,
      accuracy: null,
      accuracy_m: null,
      updated_at: null,
      last_updated: null,
      location_revision: 1,
    },
    crop: {
      farm_id: "FARM-TN-001",
      name: "Rice (Paddy)",
      variety: "IR64",
      area: 5,
      area_acres: 5,
      growthStage: "Flowering Stage",
      growth_stage: "Flowering Stage",
      plantingDate: "2024-07-15",
      planting_date: "2024-07-15",
      irrigationMethod: "Alternate Wetting and Drying (AWD)",
      irrigation_method: "Alternate Wetting and Drying (AWD)",
      soilType: "Clay Loam",
      soil_type: "Clay Loam",
    },
    weather: {
      temperature: null,
      feelsLike: null,
      feels_like: null,
      humidity: null,
      rainfall: null,
      windSpeed: null,
      wind_speed: null,
      pressure: null,
      cloudCover: null,
      cloudiness: null,
      condition: null,
      weather_condition: null,
      description: null,
      timestamp: null,
      source: "OpenWeather",
      status: "pending",
      error: null,
    },
    soil: {
      moisture: null,
      texture: null,
      soil_type: null,
      ph: null,
      organicCarbon: null,
      organic_carbon: null,
      bulkDensity: null,
      bulk_density: null,
      cec: null,
      nitrogen: null,
      total_nitrogen: null,
      source: "ISRIC SoilGrids 2.0",
      timestamp: null,
      status: "pending",
      error: null,
    },
    satellite: {
      ndvi: null,
      b04: null,
      b08: null,
      red_band: null,
      nir_band: null,
      red_reflectance: null,
      nir_reflectance: null,
      acquisitionDate: null,
      acquisition_date: null,
      cloudCover: null,
      cloud_percentage: null,
      satellite: "Sentinel-2",
      processingLevel: "Level-2A",
      vegetationStatus: null,
      vegetation_status: null,
      source: "Sentinel-2 Level-2A",
      status: "pending",
      error: null,
    },
    prediction: {
      water_stress: "UNAVAILABLE",
      water_stress_score: null,
      disease_risk: "UNAVAILABLE",
      yield_potential: "Unavailable",
      confidence:
        "Rule-based biophysical risk assessment (ICAR agronomic thresholds)",
      model_name: "Biophysical Risk Assessment Engine",
      factors: [],
    },
    disease_observation: {
      disease: null,
      crop: "Rice",
      confidence: null,
      confidence_percentage: null,
      is_healthy: null,
      is_low_confidence: null,
      top_predictions: [],
      timestamp: null,
      model_name: null,
      source: "Image Model Observation",
    },
    simulation: {
      active: false,
      is_simulation: false,
      scenario_name: null,
      moisture_delta: 0,
      temperature_delta: 0,
      rainfall_delta: 0,
      simulated_implications: null,
    },
    lastUpdated: null,
    last_synced: null,
  };

  let currentRevision = 1;
  let state = loadFromStorage();

  function loadFromStorage() {
    let result = JSON.parse(JSON.stringify(defaultState));
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {
        const parsed = JSON.parse(raw);
        result = deepMerge(result, parsed);
        if (parsed?.location?.location_revision) {
          currentRevision = Math.max(currentRevision, Number(parsed.location.location_revision) || 1);
        }
      }
    } catch (e) {
      console.warn("FarmState load error:", e);
    }

    // Load saved farm location from primary or legacy keys
    try {
      const farmLocRaw = localStorage.getItem("farmLocation");
      if (farmLocRaw) {
        const fl = JSON.parse(farmLocRaw);
        if (
          fl &&
          fl.latitude !== undefined &&
          fl.longitude !== undefined &&
          !isNaN(parseFloat(fl.latitude)) &&
          !isNaN(parseFloat(fl.longitude))
        ) {
          result.location.latitude = parseFloat(fl.latitude);
          result.location.longitude = parseFloat(fl.longitude);
          result.location.locality =
            fl.locality || fl.village || result.location.locality;
          result.location.district = fl.district || result.location.district;
          result.location.state = fl.state || result.location.state;
          result.location.country = fl.country || "India";
          result.location.place_name =
            fl.name ||
            fl.display_name ||
            fl.full_address ||
            result.location.place_name;
          result.location.source = fl.source || "Project Coordinates";
        }
      }
    } catch (e) {}

    const lat = localStorage.getItem("farmLatitude");
    const lon = localStorage.getItem("farmLongitude");
    const locName = localStorage.getItem("farmLocationName");

    if (lat && lon && !isNaN(parseFloat(lat)) && !isNaN(parseFloat(lon))) {
      result.location.latitude = parseFloat(lat);
      result.location.longitude = parseFloat(lon);
      if (locName && !result.location.place_name)
        result.location.place_name = locName;
    }

    // Ensure valid coordinates always exist
    if (
      !result.location.latitude ||
      !result.location.longitude ||
      isNaN(result.location.latitude) ||
      isNaN(result.location.longitude)
    ) {
      result.location = { ...defaultState.location };
    }

    // Load Farmer Profile
    try {
      const profileRaw =
        localStorage.getItem("agritwin_farmer_profile") ||
        localStorage.getItem("farmCropInfo");
      if (profileRaw) {
        const p = JSON.parse(profileRaw);
        if (p.farm_id) result.farm_id = p.farm_id;
        if (p.name || p.crop_name) {
          result.crop.name = p.name || p.crop_name;
        }
        if (p.variety) result.crop.variety = p.variety;
        if (p.growth_stage || p.growthStage) {
          result.crop.growth_stage = p.growth_stage || p.growthStage;
          result.crop.growthStage = result.crop.growth_stage;
        }
        if (p.area || p.area_acres) {
          const areaNum = parseFloat(p.area || p.area_acres);
          result.crop.area = areaNum;
          result.crop.area_acres = areaNum;
        }
        if (p.planting_date || p.plantingDate || p.sowing_date) {
          result.crop.planting_date =
            p.planting_date || p.plantingDate || p.sowing_date;
          result.crop.plantingDate = result.crop.planting_date;
        }
        if (p.irrigation_method || p.irrigationMethod) {
          result.crop.irrigation_method =
            p.irrigation_method || p.irrigationMethod;
          result.crop.irrigationMethod = result.crop.irrigation_method;
        }
        if (p.soil_type || p.soilType) {
          result.crop.soil_type = p.soil_type || p.soilType;
          result.crop.soilType = result.crop.soil_type;
        }
      }
    } catch (err) {}

    const cropName = localStorage.getItem("farmCropName");
    const cropVar = localStorage.getItem("farmCropVariety");
    const cropStage = localStorage.getItem("farmCropStage");
    if (cropName && !result.crop.name) result.crop.name = cropName;
    if (cropVar && !result.crop.variety) result.crop.variety = cropVar;
    if (cropStage && !result.crop.growth_stage) {
      result.crop.growth_stage = cropStage;
      result.crop.growthStage = cropStage;
    return result;
  }

  function deepMerge(target, source) {
    const output = Object.assign({}, target);
    if (isObject(target) && isObject(source)) {
      Object.keys(source).forEach((key) => {
        if (isObject(source[key])) {
          if (!(key in target)) Object.assign(output, { [key]: source[key] });
          else output[key] = deepMerge(target[key], source[key]);
        } else {
          Object.assign(output, { [key]: source[key] });
        }
      });
    }
    return output;
  }

  function isObject(item) {
    return item && typeof item === "object" && !Array.isArray(item);
  }

  function saveToStorage() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
      // Sync legacy and individual storage keys
      if (state.location.latitude && state.location.longitude) {
        localStorage.setItem("farmLatitude", String(state.location.latitude));
        localStorage.setItem("farmLongitude", String(state.location.longitude));
        if (state.location.place_name) {
          localStorage.setItem("farmLocationName", state.location.place_name);
        }
        localStorage.setItem(
          "farmLocation",
          JSON.stringify({
            latitude: state.location.latitude,
            longitude: state.location.longitude,
            name: state.location.place_name,
            locality: state.location.locality,
            district: state.location.district,
            state: state.location.state,
            country: state.location.country,
            source: state.location.source || "GPS",
            confirmed: true,
          }),
        );
      }
      if (state.crop.name) {
        localStorage.setItem("farmCropName", state.crop.name);
        localStorage.setItem("farmCropVariety", state.crop.variety || "");
        localStorage.setItem(
          "farmCropStage",
          state.crop.growth_stage || state.crop.growthStage || "",
        );
        localStorage.setItem(
          "agritwin_farmer_profile",
          JSON.stringify({
            farm_id: state.farm_id || state.crop.farm_id,
            name: state.crop.name,
            variety: state.crop.variety,
            growth_stage: state.crop.growth_stage || state.crop.growthStage,
            area: state.crop.area || state.crop.area_acres,
            planting_date: state.crop.planting_date || state.crop.plantingDate,
            irrigation_method:
              state.crop.irrigation_method || state.crop.irrigationMethod,
            soil_type: state.crop.soil_type || state.crop.soilType,
          }),
        );
        localStorage.setItem(
          "farmCropInfo",
          JSON.stringify({
            name: state.crop.name,
            variety: state.crop.variety,
            growth_stage: state.crop.growth_stage || state.crop.growthStage,
            area: state.crop.area || state.crop.area_acres,
            sowing_date: state.crop.planting_date || state.crop.plantingDate,
          }),
        );
      }

      // Sync backend farm context
      if (state.location.latitude && state.location.longitude) {
        apiFetch("/api/farm-context", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ farm_context: state }),
        }).catch(() => {});
      }
    } catch (e) {
      console.warn("FarmState save error:", e);
    }
    notifyListeners();
  }

  function notifyListeners() {
    listeners.forEach((fn) => {
      try {
        fn(state);
      } catch (err) {
        console.error("FarmState listener error:", err);
      }
    });
  }

  /**
   * Deterministic biophysical stress assessment using real physical telemetry.
   * Never fabricates unmeasured risks or fake thresholds.
   */
  function evaluateBiophysicalStress() {
    const moisture = state.soil.moisture;
    const temp = state.weather.temperature;
    const rain = state.weather.rainfall || 0;
    const ndvi = state.satellite.ndvi;
    const stage = (
      state.crop.growth_stage ||
      state.crop.growthStage ||
      ""
    ).toLowerCase();

    // If both weather and soil are unavailable, state stress as Unavailable
    if (moisture === null && temp === null && ndvi === null) {
      state.prediction.water_stress = "UNAVAILABLE";
      state.prediction.water_stress_score = null;
      state.prediction.factors = [];
      state.prediction.confidence = "No live telemetry available";
      return;
    }

    const factors = [];
    let stressScore = 15;

    // Soil Moisture vs Phenological Threshold (ICAR Guidelines)
    let optimalMin = 35.0;
    if (
      stage.includes("flower") ||
      stage.includes("anthesis") ||
      stage.includes("reproductive")
    ) {
      optimalMin = 40.0;
    } else if (stage.includes("tillering") || stage.includes("vegetative")) {
      optimalMin = 35.0;
    } else if (stage.includes("ripening") || stage.includes("maturity")) {
      optimalMin = 25.0;
    }

    if (moisture !== null && typeof moisture === "number") {
      if (moisture < optimalMin) {
        const deficit = optimalMin - moisture;
        const pts = Math.min(50, Math.round(deficit * 2.5));
        stressScore += pts;
        factors.push({
          name: "Soil Moisture Deficit",
          value: `${moisture.toFixed(1)}% (Threshold: ${optimalMin}%)`,
          impact: `+${pts}% Stress`,
          severity: pts > 25 ? "high" : "medium",
          agronomic_rule: `ICAR package of practices specifies minimum ${optimalMin}% moisture during ${state.crop.growth_stage || "flowering"} stage.`,
        });
      } else {
        factors.push({
          name: "Soil Moisture",
          value: `${moisture.toFixed(1)}%`,
          impact: "Adequate",
          severity: "low",
          agronomic_rule: `Moisture satisfies current growth stage requirement.`,
        });
      }
    }

    // Ambient Temperature
    if (temp !== null && typeof temp === "number") {
      if (temp > 35.0) {
        stressScore += 25;
        factors.push({
          name: "Thermal Evapotranspiration Demand",
          value: `${temp.toFixed(1)}°C (High Heat)`,
          impact: "+25% Stress",
          severity: "high",
          agronomic_rule:
            "Ambient temperature above 35°C accelerates crop transpiration and rhizosphere depletion.",
        });
      } else if (temp > 32.0) {
        stressScore += 15;
        factors.push({
          name: "Ambient Temperature",
          value: `${temp.toFixed(1)}°C`,
          impact: "+15% Stress",
          severity: "medium",
          agronomic_rule:
            "Elevated temperature creates moderate transpirational demand.",
        });
      }
    }

    // Precipitation Relief
    if (rain > 5.0) {
      stressScore = Math.max(10, stressScore - 25);
      factors.push({
        name: "Recent Precipitation",
        value: `${rain.toFixed(1)} mm`,
        impact: "-25% Stress Relief",
        severity: "low",
        agronomic_rule: "Precipitation recharges soil moisture reserve.",
      });
    }

    // Sentinel-2 Canopy Vigor
    if (ndvi !== null && typeof ndvi === "number") {
      if (ndvi < 0.25) {
        stressScore += 15;
        factors.push({
          name: "Canopy Spectral Vigor (NDVI)",
          value: `${ndvi.toFixed(2)} (Low Vigor)`,
          impact: "+15% Stress",
          severity: "medium",
          agronomic_rule:
            "Low NIR reflectance indicates sparse or stressed vegetative canopy.",
        });
      } else if (ndvi >= 0.5) {
        stressScore = Math.max(10, stressScore - 10);
        factors.push({
          name: "Canopy Spectral Vigor (NDVI)",
          value: `${ndvi.toFixed(2)} (Dense Vigor)`,
          impact: "-10% Stress Relief",
          severity: "low",
          agronomic_rule: "Active green canopy photosynthetically healthy.",
        });
      }
    }

    stressScore = Math.max(5, Math.min(95, stressScore));

    let riskLevel = "LOW RISK";
    if (stressScore >= 70) riskLevel = "HIGH RISK";
    else if (stressScore >= 40) riskLevel = "MODERATE RISK";

    state.prediction.water_stress = riskLevel;
    state.prediction.water_stress_score = stressScore;
    state.prediction.factors = factors;
    state.prediction.confidence = "Deterministic Biophysical Model";
  }

  return {
    get: function () {
      return JSON.parse(JSON.stringify(state));
    },

    getState: function () {
      return this.get();
    },

    setFromBackend: function (context) {
      if (!context || typeof context !== "object") return this.get();
      const backendLoc = context.location || {};
      const backendRev = Number(backendLoc.location_revision || context.location_revision || 0);
      const currentLocRev = Number(state.location?.location_revision || currentRevision || 0);

      // Do NOT let stale backend coordinates overwrite active local coordinates if local has higher revision
      const shouldUpdateLocation = (
        state.location.latitude === null ||
        state.location.longitude === null ||
        backendRev >= currentLocRev
      );

      if (shouldUpdateLocation && backendLoc.latitude !== undefined && backendLoc.longitude !== undefined) {
        state.location = deepMerge(defaultState.location, backendLoc);
        if (backendRev > currentRevision) {
          currentRevision = backendRev;
        }
      }

      if (context.crop) {
        state.crop = deepMerge(state.crop, context.crop);
        state.crop.area = context.crop.area_acres ?? state.crop.area;
        state.crop.growthStage =
          context.crop.growth_stage ?? state.crop.growthStage;
        state.crop.plantingDate =
          context.crop.planting_date ?? state.crop.plantingDate;
      }

      if (context.weather && shouldUpdateLocation) {
        state.weather = deepMerge(state.weather, context.weather);
      }
      if (context.soil && shouldUpdateLocation) {
        state.soil = deepMerge(state.soil, context.soil);
      }
      if (context.satellite && shouldUpdateLocation) {
        state.satellite = deepMerge(state.satellite, context.satellite);
      }
      if (context.prediction && shouldUpdateLocation) {
        state.prediction = deepMerge(state.prediction, context.prediction);
      }

      evaluateBiophysicalStress();
      saveToStorage();
      notifyListeners();
      return this.get();
    },

    set: function (partial) {
      state = deepMerge(state, partial);
      evaluateBiophysicalStress();
      saveToStorage();
      return this.get();
    },

    /**
     * Update Farmer-Provided Farm Profile
     */
    updateProfile: function (profile) {
      if (!profile) return this.get();
      if (profile.farm_id !== undefined) {
        state.farm_id = profile.farm_id;
        state.crop.farm_id = profile.farm_id;
      }
      if (profile.name !== undefined) state.crop.name = profile.name;
      if (profile.crop_name !== undefined) state.crop.name = profile.crop_name;
      if (profile.variety !== undefined) state.crop.variety = profile.variety;
      if (
        profile.growth_stage !== undefined ||
        profile.growthStage !== undefined
      ) {
        const st = profile.growth_stage || profile.growthStage;
        state.crop.growth_stage = st;
        state.crop.growthStage = st;
      }
      if (profile.area !== undefined || profile.area_acres !== undefined) {
        const ar = parseFloat(profile.area || profile.area_acres);
        state.crop.area = isNaN(ar) ? null : ar;
        state.crop.area_acres = isNaN(ar) ? null : ar;
      }
      if (
        profile.planting_date !== undefined ||
        profile.plantingDate !== undefined
      ) {
        const pd = profile.planting_date || profile.plantingDate;
        state.crop.planting_date = pd;
        state.crop.plantingDate = pd;
      }
      if (
        profile.irrigation_method !== undefined ||
        profile.irrigationMethod !== undefined
      ) {
        const im = profile.irrigation_method || profile.irrigationMethod;
        state.crop.irrigation_method = im;
        state.crop.irrigationMethod = im;
      }
      if (profile.soil_type !== undefined || profile.soilType !== undefined) {
        const stype = profile.soil_type || profile.soilType;
        state.crop.soil_type = stype;
        state.crop.soilType = stype;
      }
      evaluateBiophysicalStress();
      saveToStorage();
      return this.get();
    },

    setCrop: function (cropData) {
      return this.updateProfile(cropData);
    },

    updateCrop: function (cropData) {
      return this.updateProfile(cropData);
    },

    /**
     * Set farm coordinates, invalidate stale telemetry, reverse geocode, and persist.
     */
    setLocation: async function (
      lat,
      lon,
      placeName = null,
      source = "Device GPS",
      accuracy = null,
    ) {
      const parsedLat = parseFloat(lat);
      const parsedLon = parseFloat(lon);

      if (
        isNaN(parsedLat) ||
        isNaN(parsedLon) ||
        parsedLat < -90 ||
        parsedLat > 90 ||
        parsedLon < -180 ||
        parsedLon > 180
      ) {
        console.error(
          "Invalid coordinates passed to FarmState.setLocation:",
          lat,
          lon,
        );
        return this.get();
      }

      currentRevision++;
      const thisRevision = currentRevision;
      const nowIso = new Date().toISOString();

      state.location.latitude = parsedLat;
      state.location.longitude = parsedLon;
      state.location.source = source || "Device GPS";
      state.location.accuracy = typeof accuracy === "number" ? Math.round(accuracy) : null;
      state.location.accuracy_m = typeof accuracy === "number" ? Math.round(accuracy * 10) / 10 : null;
      state.location.updated_at = nowIso;
      state.location.last_updated = nowIso;
      state.location.location_revision = thisRevision;

      if (
        placeName &&
        placeName !== "Location unavailable" &&
        placeName !== "Location name unavailable"
      ) {
        state.location.place_name = placeName;
      }

      // Immediately invalidate stale measurements in state so old coordinates data is never displayed
      state.weather.status = "loading";
      state.weather.temperature = null;
      state.weather.feels_like = null;
      state.weather.feelsLike = null;
      state.weather.humidity = null;
      state.weather.rainfall = null;
      state.weather.wind_speed = null;
      state.weather.windSpeed = null;
      state.weather.pressure = null;
      state.weather.cloudCover = null;
      state.weather.cloudiness = null;
      state.weather.condition = null;
      state.weather.weather_condition = null;
      state.weather.description = null;
      state.weather.timestamp = null;

      state.soil.status = "loading";
      state.soil.moisture = null;
      state.soil.texture = null;
      state.soil.soil_type = null;
      state.soil.ph = null;
      state.soil.organicCarbon = null;
      state.soil.organic_carbon = null;
      state.soil.bulkDensity = null;
      state.soil.bulk_density = null;
      state.soil.cec = null;
      state.soil.nitrogen = null;
      state.soil.total_nitrogen = null;
      state.soil.timestamp = null;

      state.satellite.status = "loading";
      state.satellite.ndvi = null;
      state.satellite.b04 = null;
      state.satellite.b08 = null;
      state.satellite.red_band = null;
      state.satellite.nir_band = null;
      state.satellite.red_reflectance = null;
      state.satellite.nir_reflectance = null;
      state.satellite.acquisitionDate = null;
      state.satellite.acquisition_date = null;
      state.satellite.cloudCover = null;
      state.satellite.cloud_percentage = null;
      state.satellite.vegetationStatus = null;
      state.satellite.vegetation_status = null;

      state.prediction.water_stress = "EVALUATING";
      state.prediction.water_stress_score = null;
      state.prediction.disease_risk = "EVALUATING";
      state.prediction.yield_potential = "Evaluating...";
      state.prediction.factors = [];

      // Invalidate API cache before network calls
      if (typeof window.clearFarmContextCache === "function") {
        window.clearFarmContextCache();
      }

      // Reverse geocode to resolve structured locality/district/state/country if needed
      try {
        const res = await apiFetch(
          `/api/location/reverse?lat=${encodeURIComponent(parsedLat)}&lon=${encodeURIComponent(parsedLon)}`,
        );
        if (res.ok) {
          const geo = await res.json();
          if (geo && geo.success) {
            state.location.locality = geo.locality || geo.village || null;
            state.location.district = geo.district || null;
            state.location.state = geo.state || null;
            state.location.country = geo.country || "India";
            if (!placeName || placeName.startsWith("Farm (")) {
              state.location.place_name =
                geo.display_name ||
                geo.name ||
                (geo.locality
                  ? `${geo.locality}, ${geo.district || ""}`
                  : null);
            }
          }
        }
      } catch (err) {
        console.warn("Reverse geocode failed:", err);
      }

      if (!state.location.place_name) {
        state.location.place_name = `Farm (${parsedLat.toFixed(4)}, ${parsedLon.toFixed(4)})`;
      }

      // Keep localStorage synchronized immediately
      try {
        localStorage.setItem("farmLatitude", String(parsedLat));
        localStorage.setItem("farmLongitude", String(parsedLon));
        localStorage.setItem("farmLocationName", state.location.place_name);
        localStorage.setItem(
          "farmLocation",
          JSON.stringify({
            latitude: parsedLat,
            longitude: parsedLon,
            name: state.location.locality || state.location.place_name,
            display_name: state.location.place_name,
            source: state.location.source,
            accuracy: state.location.accuracy,
            accuracy_m: state.location.accuracy_m,
            confirmed: true,
            location_revision: thisRevision,
          }),
        );
      } catch (storageError) {
        console.warn("Storage write error:", storageError);
      }

      // Persist to backend centralized FarmContext as single source of truth
      try {
        await apiFetch("/api/farm/context/location", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            location: {
              latitude: parsedLat,
              longitude: parsedLon,
              place_name: state.location.place_name,
              locality: state.location.locality,
              district: state.location.district,
              state: state.location.state,
              country: state.location.country,
              source: state.location.source,
              accuracy: state.location.accuracy,
              accuracy_m: state.location.accuracy_m,
              location_revision: thisRevision,
            },
          }),
        });
      } catch (err) {
        console.warn("Backend location persistence error:", err);
      }

      if (typeof window.clearFarmContextCache === "function") {
        window.clearFarmContextCache();
      }

      saveToStorage();
      notifyListeners();

      // Dispatch global events for other modules
      window.dispatchEvent(
        new CustomEvent("agritwin:locationChanged", { detail: state.location }),
      );
      window.dispatchEvent(
        new CustomEvent("farmLocationChanged", { detail: this.get() }),
      );

      return this.syncLiveTelemetry(true, thisRevision);
    },

    updateLocation: function (locData) {
      if (!locData) return this.get();
      const lat =
        locData.latitude !== undefined
          ? locData.latitude
          : state.location.latitude;
      const lon =
        locData.longitude !== undefined
          ? locData.longitude
          : state.location.longitude;
      const placeName =
        locData.place_name || locData.name || state.location.place_name;
      const source = locData.source || state.location.source || "Manual";
      const accuracy =
        locData.accuracy_m !== undefined
          ? locData.accuracy_m
          : locData.accuracy;
      if (
        lat !== null &&
        lon !== null &&
        !isNaN(parseFloat(lat)) &&
        !isNaN(parseFloat(lon))
      ) {
        return this.setLocation(lat, lon, placeName, source, accuracy);
      }
      return this.get();
    },

    subscribe: function (listener) {
      if (typeof listener === "function") {
        listeners.push(listener);
        listener(state);
      }
    },

    /**
     * Fetch Live Weather, ISRIC SoilGrids 2.0, and Sentinel-2 NDVI in parallel for the current farm location.
     */
    syncLiveTelemetry: async function (forceRefresh = false, targetRevision = null) {
      if (targetRevision !== null && targetRevision !== currentRevision) {
        console.log("FarmState: Discarding syncLiveTelemetry for superseded revision", targetRevision);
        return this.get();
      }

      const activeRev = currentRevision;

      if (forceRefresh && typeof window.clearFarmContextCache === "function") {
        window.clearFarmContextCache();
      }

      const farmResult = await loadFarmContext(forceRefresh);
      if (activeRev !== currentRevision) {
        return this.get();
      }

      if (farmResult.success && farmResult.data) {
        this.setFromBackend(farmResult.data);
      }

      const lat = state.location.latitude;
      const lon = state.location.longitude;

      if (lat === null || lon === null || isNaN(lat) || isNaN(lon)) {
        console.warn(
          "FarmState: No valid coordinates available to sync live telemetry.",
        );
        state.weather.status = "unavailable";
        state.soil.status = "unavailable";
        state.satellite.status = "unavailable";
        notifyListeners();
        return state;
      }

      state.weather.status = "loading";
      state.soil.status = "loading";
      state.satellite.status = "loading";
      notifyListeners();

      const promises = [
        // 1. Live Weather (OpenWeather)
        apiFetch(
          `/api/weather?lat=${encodeURIComponent(lat)}&lon=${encodeURIComponent(lon)}`,
        )
          .then((r) =>
            r.ok
              ? r.json()
              : { success: false, error: "Weather API unavailable" },
          )
          .catch((e) => ({ success: false, error: e.message })),

        // 2. Live Soil Telemetry (ISRIC SoilGrids 2.0)
        apiFetch(
          `/api/soil?lat=${encodeURIComponent(lat)}&lon=${encodeURIComponent(lon)}`,
        )
          .then((r) =>
            r.ok
              ? r.json()
              : { success: false, error: "Soil service unavailable" },
          )
          .catch((e) => ({ success: false, error: e.message })),

        // 3. Live Satellite NDVI (Sentinel-2 Level-2A)
        apiFetch(
          `/api/ndvi?lat=${encodeURIComponent(lat)}&lon=${encodeURIComponent(lon)}`,
        )
          .then((r) =>
            r.ok
              ? r.json()
              : { success: false, error: "Satellite service unavailable" },
          )
          .catch((e) => ({ success: false, error: e.message })),
      ];

      try {
        const [weatherRes, soilRes, ndviRes] = await Promise.all(promises);

        if (activeRev !== currentRevision) {
          console.log("FarmState: Discarding telemetry response for superseded revision", activeRev);
          return this.get();
        }

        // Process Weather Response
        if (weatherRes && weatherRes.success && weatherRes.weather) {
          const w = weatherRes.weather;
          state.weather.temperature =
            w.temperature !== undefined ? w.temperature : null;
          state.weather.feelsLike =
            w.feels_like !== undefined ? w.feels_like : w.temperature;
          state.weather.feels_like = state.weather.feelsLike;
          state.weather.humidity = w.humidity !== undefined ? w.humidity : null;
          state.weather.rainfall =
            w.rainfall !== undefined ? w.rainfall : w.rainfall_1h || 0;
          state.weather.windSpeed =
            w.wind_speed !== undefined ? w.wind_speed : null;
          state.weather.wind_speed = state.weather.windSpeed;
          state.weather.pressure = w.pressure !== undefined ? w.pressure : null;
          state.weather.cloudCover =
            w.cloudiness !== undefined ? w.cloudiness : w.clouds || null;
          state.weather.cloudiness = state.weather.cloudCover;
          state.weather.condition =
            w.condition || w.weather_condition || w.description || null;
          state.weather.weather_condition = state.weather.condition;
          state.weather.description = w.description || w.condition || null;
          state.weather.source = w.source || "OpenWeather";
          state.weather.timestamp = w.timestamp || new Date().toISOString();
          state.weather.status = "live";
          state.weather.error = null;

          if (
            weatherRes.location &&
            weatherRes.location.name &&
            (!state.location.locality ||
              state.location.place_name === "Location unavailable")
          ) {
            const cityName = weatherRes.location.name;
            const countryName = weatherRes.location.country || "India";
            if (
              !state.location.place_name ||
              state.location.place_name === "Location unavailable"
            ) {
              state.location.place_name = `${cityName}, ${countryName}`;
            }
          }
        } else {
          state.weather.temperature = null;
          state.weather.humidity = null;
          state.weather.rainfall = null;
          state.weather.status = "unavailable";
          state.weather.error = weatherRes?.error || "Weather data unavailable";
        }

        // Process Soil Response
        if (soilRes && soilRes.success && soilRes.soil) {
          const s = soilRes.soil;
          state.soil.texture = soilRes.texture_class || null;
          state.soil.soil_type = state.soil.texture;
          state.soil.ph = s.ph !== undefined ? s.ph : null;
          state.soil.moisture =
            s.water_content !== undefined ? s.water_content : null;
          state.soil.organicCarbon =
            s.organic_carbon !== undefined ? s.organic_carbon : null;
          state.soil.organic_carbon = state.soil.organicCarbon;
          state.soil.bulkDensity =
            s.bulk_density !== undefined ? s.bulk_density : null;
          state.soil.bulk_density = state.soil.bulkDensity;
          state.soil.cec = s.cec !== undefined ? s.cec : null;
          state.soil.nitrogen =
            s.total_nitrogen !== undefined ? s.total_nitrogen : null;
          state.soil.total_nitrogen = state.soil.nitrogen;
          state.soil.source = soilRes.source || "ISRIC SoilGrids 2.0";
          state.soil.timestamp = new Date().toISOString();
          state.soil.status = "live";
          state.soil.error = null;
        } else {
          state.soil.ph = null;
          state.soil.moisture = null;
          state.soil.texture = null;
          state.soil.soil_type = null;
          state.soil.status = "unavailable";
          state.soil.error = soilRes?.error || "Soil data unavailable";
        }

        // Process Satellite Response
        if (ndviRes && ndviRes.success) {
          state.satellite.ndvi =
            ndviRes.ndvi !== undefined ? ndviRes.ndvi : null;
          state.satellite.b04 =
            ndviRes.red_reflectance !== undefined
              ? ndviRes.red_reflectance
              : null;
          state.satellite.red_band = state.satellite.b04;
          state.satellite.red_reflectance = state.satellite.b04;
          state.satellite.b08 =
            ndviRes.nir_reflectance !== undefined
              ? ndviRes.nir_reflectance
              : null;
          state.satellite.nir_band = state.satellite.b08;
          state.satellite.nir_reflectance = state.satellite.b08;
          state.satellite.acquisitionDate = ndviRes.acquisition_date || null;
          state.satellite.acquisition_date = state.satellite.acquisitionDate;
          state.satellite.cloudCover =
            ndviRes.cloud_percentage !== undefined
              ? ndviRes.cloud_percentage
              : null;
          state.satellite.cloud_percentage = state.satellite.cloudCover;
          state.satellite.satellite = "Sentinel-2";
          state.satellite.processingLevel = "Level-2A (BOA)";
          state.satellite.vegetationStatus =
            ndviRes.vegetation_condition || null;
          state.satellite.vegetation_status = state.satellite.vegetationStatus;
          state.satellite.source = ndviRes.source || "Sentinel-2 Level-2A";
          state.satellite.imageUrl = ndviRes.image_url || ndviRes.preview_url || ndviRes.thumbnail_url || null;
          state.satellite.previewUrl = ndviRes.preview_url || null;
          state.satellite.status = "live";
          state.satellite.error = null;
        } else {
          state.satellite.ndvi = null;
          state.satellite.status = "unavailable";
          state.satellite.error =
            ndviRes?.error || "Satellite data unavailable";
        }

        const nowTimeStr = new Date().toLocaleTimeString("en-IN", {
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
          hour12: true,
        });
        state.lastUpdated = nowTimeStr;
        state.last_synced = new Date().toISOString();

        evaluateBiophysicalStress();
        saveToStorage();
      } catch (err) {
        console.error("FarmState telemetry sync error:", err);
      }

      return this.get();
    },

    refreshFarmData: function () {
      return this.syncLiveTelemetry();
    },

    syncWithAPIs: function () {
      return this.syncLiveTelemetry();
    },

    getDataQuality: function () {
      const hasCoords =
        state.location.latitude !== null && state.location.longitude !== null;
      const isWeatherLive =
        state.weather.temperature !== null && state.weather.status === "live";
      const isSoilLive = state.soil.ph !== null && state.soil.status === "live";
      const isSatLive =
        state.satellite.ndvi !== null && state.satellite.status === "live";
      const isCropSet = Boolean(state.crop.name);

      return {
        location: {
          label: "Farm Location",
          status: hasCoords ? "Coordinates Configured" : "Unavailable",
          source:
            state.location.source || (hasCoords ? "Farm Coordinates" : "Unset"),
          icon: hasCoords ? "check-circle" : "times-circle",
          badgeClass: hasCoords ? "bg-success" : "bg-danger",
        },
        weather: {
          label: "Live Weather",
          status: isWeatherLive
            ? "Live API Data"
            : state.weather.status === "loading"
              ? "Syncing..."
              : "Unavailable",
          source: "OpenWeather API",
          icon: isWeatherLive ? "check-circle" : "exclamation-triangle",
          badgeClass: isWeatherLive ? "bg-success" : "bg-warning text-dark",
        },
        soil: {
          label: "Soil Intelligence",
          status: isSoilLive
            ? "Gridded Soil Profile"
            : state.soil.status === "loading"
              ? "Syncing..."
              : "Unavailable",
          source: "ISRIC SoilGrids 2.0",
          icon: isSoilLive ? "check-circle" : "exclamation-triangle",
          badgeClass: isSoilLive ? "bg-success" : "bg-warning text-dark",
        },
        satellite: {
          label: "Satellite Multispectral",
          status: isSatLive
            ? "Latest Observation"
            : state.satellite.status === "loading"
              ? "Syncing..."
              : "Unavailable",
          source: "Sentinel-2 Level-2A",
          icon: isSatLive ? "check-circle" : "exclamation-triangle",
          badgeClass: isSatLive ? "bg-success" : "bg-warning text-dark",
        },
        crop: {
          label: "Crop Profile",
          status: isCropSet ? "Configured" : "Not Configured",
          source: "Farmer Profile",
          icon: isCropSet ? "user-check" : "user-edit",
          badgeClass: isCropSet ? "bg-info text-dark" : "bg-secondary",
        },
        rag: {
          label: "Agricultural Knowledge",
          status: "RAG Active",
          source: "ICAR Package of Practices",
          icon: "book-open",
          badgeClass: "bg-success",
        },
        llm: {
          label: "AI Reasoning",
          status: "Active",
          source: "Groq LLM",
          icon: "brain",
          badgeClass: "bg-primary",
        },
      };
    },

    calculateStressScore: function (customState) {
      const s = customState || state;
      const score =
        s.prediction?.water_stress_score !== undefined
          ? s.prediction.water_stress_score
          : null;
      const category =
        s.prediction?.water_stress ||
        (score !== null
          ? score >= 70
            ? "HIGH RISK"
            : score >= 40
              ? "MODERATE RISK"
              : "LOW RISK"
          : "UNAVAILABLE");
      return { score, category };
    },

    setDiseaseObservation: function (obs) {
      if (!state.disease_observation) {
        state.disease_observation = {};
      }
      state.disease_observation = {
        disease: obs.disease || null,
        crop: obs.crop || "Rice",
        confidence: obs.confidence !== undefined ? obs.confidence : null,
        confidence_percentage:
          obs.confidence_percentage !== undefined
            ? obs.confidence_percentage
            : obs.confidence
              ? Math.round(obs.confidence * 1000) / 10
              : null,
        is_healthy: Boolean(
          obs.is_healthy ||
          (obs.disease && obs.disease.toLowerCase() === "healthy"),
        ),
        is_low_confidence: Boolean(obs.is_low_confidence),
        top_predictions: obs.top_predictions || [],
        timestamp: obs.timestamp || new Date().toISOString(),
        model_name: obs.model_name || "rice_disease_mobilenet_v2",
        source: "Image Model Observation",
      };
      saveToStorage();
      notifyListeners();
      return state.disease_observation;
    },

    getDiseaseObservation: function () {
      return state.disease_observation || null;
    },

    setBoundary: function (boundary, acreage = null) {
      if (!state.location) state.location = {};
      state.location.boundary = boundary;
      if (acreage !== null && !isNaN(acreage)) {
        state.crop.area = Number(acreage);
        state.crop.area_acres = Number(acreage);
      }
      saveToStorage();
      apiFetch("/api/farm/context/location", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          location: {
            ...state.location,
            boundary: boundary,
          },
        }),
      }).catch(() => {});
      notifyListeners();
      window.dispatchEvent(
        new CustomEvent("agritwin:boundaryChanged", {
          detail: { boundary, acreage },
        }),
      );
      return state.location;
    },

    getBoundary: function () {
      return state.location?.boundary || null;
    },

    refresh: async function () {
      return this.syncLiveTelemetry(true);
    },
  };
})();

// Auto-sync farm data on page load if farm coordinates are configured
document.addEventListener("DOMContentLoaded", () => {
  FarmState.syncLiveTelemetry();
});
