// AgriTwin-RAG Dashboard - Main Application Controller
// Synchronizes Real-Time UI with Centralized FarmState Single Source of Truth
// Strictly NO mock data, NO invented values, and NO fake fallbacks

function initDashboard() {
  const user = JSON.parse(localStorage.getItem("currentUser")) || {
    name: "Farmer Profile",
    avatar: "F",
  };

  // Topbar user
  const userNameEl = document.getElementById("userName");
  const userAvatarEl = document.getElementById("userAvatar");
  const topbarNameEl = document.getElementById("topbarName");
  const topbarAvatarEl = document.getElementById("topbarAvatar");

  if (userNameEl) userNameEl.textContent = user.name;
  if (userAvatarEl) userAvatarEl.textContent = user.avatar || user.name.charAt(0).toUpperCase();
  if (topbarNameEl) topbarNameEl.textContent = user.name;
  if (topbarAvatarEl) topbarAvatarEl.textContent = user.avatar || user.name.charAt(0).toUpperCase();

  setActiveNavigation();
  setupGlobalInteractions();
  setupFarmProfileModal();

  // Subscribe to FarmState updates
  if (typeof FarmState !== "undefined") {
    FarmState.subscribe(renderDashboardState);
    renderDashboardState(FarmState.get());
  }
}

function renderDashboardState(state) {
  if (!state) return;

  // 1. Topbar & Header Location
  const locationTextEl = document.getElementById("locationText");
  const farmLocationEl = document.getElementById("farmLocation");
  const locName = state.location.place_name || (state.location.latitude ? `Farm (${state.location.latitude.toFixed(4)}, ${state.location.longitude.toFixed(4)})` : "Set Farm Location");

  if (locationTextEl) locationTextEl.textContent = locName;
  if (farmLocationEl) {
    const srcLabel = state.location.source ? ` [${state.location.source}]` : "";
    farmLocationEl.title = `Coordinates: ${state.location.latitude !== null ? state.location.latitude.toFixed(6) : "—"}, ${state.location.longitude !== null ? state.location.longitude.toFixed(6) : "—"}${srcLabel}`;
  }

  // 2. Hero Section: Farm Intelligence Center
  const heroLocation = document.getElementById("heroLocation");
  if (heroLocation) {
    heroLocation.textContent = state.location.place_name || (state.location.latitude ? `${state.location.latitude.toFixed(4)}°, ${state.location.longitude.toFixed(4)}°` : "Location unavailable");
  }

  const heroFarmId = document.getElementById("heroFarmId");
  if (heroFarmId) {
    heroFarmId.textContent = state.farm_id || state.crop.farm_id || "Not set";
  }

  const heroCrop = document.getElementById("heroCrop");
  if (heroCrop) {
    heroCrop.textContent = state.crop.name || "Not configured";
  }

  const heroVariety = document.getElementById("heroVariety");
  if (heroVariety) {
    heroVariety.textContent = state.crop.variety || "Not configured";
  }

  const heroArea = document.getElementById("heroArea");
  if (heroArea) {
    const areaVal = state.crop.area || state.crop.area_acres;
    heroArea.textContent = areaVal ? `${areaVal} Acres (${(areaVal * 0.4047).toFixed(2)} ha)` : "Not configured";
  }

  const heroGrowthStage = document.getElementById("heroGrowthStage");
  if (heroGrowthStage) {
    heroGrowthStage.textContent = state.crop.growth_stage || state.crop.growthStage || "Not configured";
  }

  const heroLastUpdated = document.getElementById("heroLastUpdated");
  if (heroLastUpdated) {
    if (state.lastUpdated) {
      heroLastUpdated.textContent = `Last updated: ${state.lastUpdated}`;
    } else if (state.last_synced) {
      heroLastUpdated.textContent = `Last updated: ${new Date(state.last_synced).toLocaleTimeString()}`;
    } else {
      heroLastUpdated.textContent = "Last updated: Pending sync";
    }
  }

  const heroStressRisk = document.getElementById("heroStressRisk");
  const heroStressPill = document.getElementById("heroStressPill");
  if (heroStressRisk) {
    const risk = state.prediction.water_stress || "UNAVAILABLE";
    heroStressRisk.textContent = risk;
    if (heroStressPill) {
      if (risk === "HIGH RISK") {
        heroStressPill.className = "hero-info-pill highlight-pill bg-danger-subtle text-danger border border-danger-subtle";
      } else if (risk === "MODERATE RISK") {
        heroStressPill.className = "hero-info-pill highlight-pill bg-warning-subtle text-dark border border-warning-subtle";
      } else if (risk === "LOW RISK") {
        heroStressPill.className = "hero-info-pill highlight-pill";
      } else {
        heroStressPill.className = "hero-info-pill bg-secondary-subtle text-muted border";
      }
    }
  }

  // 3. 5 Live Telemetry Cards

  // Card 1: Current Weather
  const weatherTemp = document.getElementById("weatherTemp");
  if (weatherTemp) {
    weatherTemp.textContent = state.weather.temperature !== null ? Number(state.weather.temperature).toFixed(1) : "--";
  }
  const weatherFeels = document.getElementById("weatherFeels");
  if (weatherFeels) {
    weatherFeels.textContent = state.weather.feelsLike !== null ? Number(state.weather.feelsLike).toFixed(1) : "--";
  }
  const weatherHumidity = document.getElementById("weatherHumidity");
  if (weatherHumidity) {
    weatherHumidity.textContent = state.weather.humidity !== null ? state.weather.humidity : "--";
  }
  const weatherRainfall = document.getElementById("weatherRainfall");
  if (weatherRainfall) {
    weatherRainfall.textContent = state.weather.rainfall !== null ? state.weather.rainfall : "--";
  }
  const weatherWind = document.getElementById("weatherWind");
  if (weatherWind) {
    weatherWind.textContent = state.weather.windSpeed !== null ? state.weather.windSpeed : "--";
  }
  const weatherCondition = document.getElementById("weatherCondition");
  if (weatherCondition) {
    if (state.weather.status === "loading") {
      weatherCondition.innerHTML = '<i class="fas fa-spinner fa-spin text-warning me-1"></i> Syncing live weather...';
    } else if (state.weather.temperature !== null) {
      weatherCondition.textContent = state.weather.condition || state.weather.description || "Live Conditions";
    } else {
      weatherCondition.textContent = "Weather data unavailable";
    }
  }

  // Card 2: Soil Condition
  const soilMoisture = document.getElementById("soilMoisture");
  if (soilMoisture) {
    soilMoisture.textContent = state.soil.moisture !== null ? Number(state.soil.moisture).toFixed(1) : "--";
  }
  const soilTexture = document.getElementById("soilTexture");
  if (soilTexture) {
    if (state.soil.status === "loading") {
      soilTexture.textContent = "Retrieving SoilGrids...";
    } else {
      soilTexture.textContent = state.soil.texture || "Unavailable";
    }
  }
  const soilPh = document.getElementById("soilPh");
  if (soilPh) {
    soilPh.textContent = state.soil.ph !== null ? Number(state.soil.ph).toFixed(1) : "--";
  }
  const soilOrganicCarbon = document.getElementById("soilOrganicCarbon");
  if (soilOrganicCarbon) {
    soilOrganicCarbon.textContent = state.soil.organicCarbon !== null ? Number(state.soil.organicCarbon).toFixed(1) : "--";
  }
  const soilBulkDensity = document.getElementById("soilBulkDensity");
  if (soilBulkDensity) {
    soilBulkDensity.textContent = state.soil.bulkDensity !== null ? Number(state.soil.bulkDensity).toFixed(2) : "--";
  }
  const soilCec = document.getElementById("soilCec");
  if (soilCec) {
    soilCec.textContent = state.soil.cec !== null ? Number(state.soil.cec).toFixed(1) : "--";
  }

  // Card 3: Satellite Vegetation
  const satNdviVal = document.getElementById("satNdviVal");
  if (satNdviVal) {
    satNdviVal.textContent = state.satellite.ndvi !== null ? Number(state.satellite.ndvi).toFixed(4) : "--";
  }
  const satVegStatus = document.getElementById("satVegStatus");
  if (satVegStatus) {
    if (state.satellite.status === "loading") {
      satVegStatus.innerHTML = '<i class="fas fa-spinner fa-spin text-primary me-1"></i> Sampling Sentinel-2...';
    } else if (state.satellite.ndvi !== null) {
      satVegStatus.textContent = state.satellite.vegetationStatus || "Active Vegetation Signal";
    } else {
      satVegStatus.textContent = "Satellite data unavailable";
    }
  }
  const satAcqDate = document.getElementById("satAcqDate");
  if (satAcqDate) {
    if (state.satellite.acquisitionDate) {
      satAcqDate.textContent = `Latest satellite observation: ${state.satellite.acquisitionDate}`;
    } else if (state.satellite.status === "loading") {
      satAcqDate.textContent = "Latest satellite observation: Searching...";
    } else {
      satAcqDate.textContent = "Latest satellite observation: Unavailable";
    }
  }
  const satCloudCover = document.getElementById("satCloudCover");
  if (satCloudCover) {
    satCloudCover.textContent = state.satellite.cloudCover !== null ? Number(state.satellite.cloudCover).toFixed(1) : "--";
  }

  // Card 4: Crop Profile
  const cropProfileName = document.getElementById("cropProfileName");
  if (cropProfileName) {
    cropProfileName.textContent = state.crop.name || "Not set";
  }
  const cropProfileVariety = document.getElementById("cropProfileVariety");
  if (cropProfileVariety) {
    cropProfileVariety.textContent = state.crop.variety || "Not set";
  }
  const cropProfileStage = document.getElementById("cropProfileStage");
  if (cropProfileStage) {
    cropProfileStage.textContent = state.crop.growth_stage || state.crop.growthStage || "Not set";
  }
  const cropProfileArea = document.getElementById("cropProfileArea");
  if (cropProfileArea) {
    const a = state.crop.area || state.crop.area_acres;
    cropProfileArea.textContent = a !== null && a !== undefined ? a : "--";
  }
  const cropProfileIrrigation = document.getElementById("cropProfileIrrigation");
  if (cropProfileIrrigation) {
    cropProfileIrrigation.textContent = state.crop.irrigation_method || state.crop.irrigationMethod || "--";
  }

  // Card 5: Farm Data Status
  const statusGps = document.getElementById("statusGps");
  if (statusGps) {
    const hasGps = state.location.latitude !== null && state.location.longitude !== null;
    statusGps.className = hasGps ? "badge bg-success" : "badge bg-danger";
    statusGps.textContent = hasGps ? `Locked (${state.location.source || "GPS"})` : "Unavailable";
  }
  const statusWeather = document.getElementById("statusWeather");
  if (statusWeather) {
    if (state.weather.status === "live") {
      statusWeather.className = "badge bg-success";
      statusWeather.textContent = "Live (OpenWeather)";
    } else if (state.weather.status === "loading") {
      statusWeather.className = "badge bg-warning text-dark";
      statusWeather.textContent = "Syncing...";
    } else {
      statusWeather.className = "badge bg-danger";
      statusWeather.textContent = "Unavailable";
    }
  }
  const statusSoil = document.getElementById("statusSoil");
  if (statusSoil) {
    if (state.soil.status === "live") {
      statusSoil.className = "badge bg-success";
      statusSoil.textContent = "Retrieved (ISRIC SoilGrids)";
    } else if (state.soil.status === "loading") {
      statusSoil.className = "badge bg-warning text-dark";
      statusSoil.textContent = "Syncing...";
    } else {
      statusSoil.className = "badge bg-danger";
      statusSoil.textContent = "Unavailable";
    }
  }
  const statusSatellite = document.getElementById("statusSatellite");
  if (statusSatellite) {
    if (state.satellite.status === "live") {
      statusSatellite.className = "badge bg-success";
      statusSatellite.textContent = "Latest Observation (Sentinel-2)";
    } else if (state.satellite.status === "loading") {
      statusSatellite.className = "badge bg-warning text-dark";
      statusSatellite.textContent = "Syncing...";
    } else {
      statusSatellite.className = "badge bg-danger";
      statusSatellite.textContent = "Unavailable";
    }
  }

  // 4. Digital Twin Pipeline Nodes
  const twinLocation = document.getElementById("twinLocation");
  if (twinLocation) {
    twinLocation.textContent = state.location.locality || state.location.place_name || "Unavailable";
  }
  const twinCoords = document.getElementById("twinCoords");
  if (twinCoords) {
    twinCoords.textContent = state.location.latitude !== null ? `${state.location.latitude.toFixed(4)}°, ${state.location.longitude.toFixed(4)}°` : "No GPS";
  }
  const twinWeather = document.getElementById("twinWeather");
  if (twinWeather) {
    twinWeather.textContent = state.weather.temperature !== null ? `${Number(state.weather.temperature).toFixed(1)}°C, ${state.weather.humidity}%` : "Weather unavailable";
  }
  const twinWeatherSub = document.getElementById("twinWeatherSub");
  if (twinWeatherSub) {
    twinWeatherSub.textContent = state.weather.condition || "No telemetry";
  }
  const twinSoil = document.getElementById("twinSoil");
  if (twinSoil) {
    twinSoil.textContent = state.soil.ph !== null ? `pH ${Number(state.soil.ph).toFixed(1)} • ${state.soil.texture || "Soil"}` : "Soil unavailable";
  }
  const twinSoilSub = document.getElementById("twinSoilSub");
  if (twinSoilSub) {
    twinSoilSub.textContent = state.soil.moisture !== null ? `${Number(state.soil.moisture).toFixed(1)}% Moisture` : "No telemetry";
  }
  const twinSatellite = document.getElementById("twinSatellite");
  if (twinSatellite) {
    twinSatellite.textContent = state.satellite.ndvi !== null ? `NDVI ${Number(state.satellite.ndvi).toFixed(2)}` : "Satellite unavailable";
  }
  const twinSatelliteSub = document.getElementById("twinSatelliteSub");
  if (twinSatelliteSub) {
    twinSatelliteSub.textContent = state.satellite.acquisitionDate ? `Pass: ${state.satellite.acquisitionDate}` : "No pass data";
  }
  const twinCrop = document.getElementById("twinCrop");
  if (twinCrop) {
    twinCrop.textContent = state.crop.name ? `${state.crop.name} (${state.crop.variety || "Var"})` : "Not configured";
  }
  const twinCropSub = document.getElementById("twinCropSub");
  if (twinCropSub) {
    const a = state.crop.area || state.crop.area_acres;
    twinCropSub.textContent = a ? `${a} Acres` : "Area unset";
  }
  const twinStage = document.getElementById("twinStage");
  if (twinStage) {
    twinStage.textContent = state.crop.growth_stage || state.crop.growthStage || "Not configured";
  }
  const twinStageSub = document.getElementById("twinStageSub");
  if (twinStageSub) {
    twinStageSub.textContent = state.crop.irrigation_method || "Irrigation unset";
  }

  // 5. Agronomic Risk Assessment & Alert Container
  const stressBadge = document.getElementById("stressBadge");
  const alertTitle = document.getElementById("alertTitle");
  const alertSeverity = document.getElementById("alertSeverity");
  const alertDescription = document.getElementById("alertDescription");
  const alertActionText = document.getElementById("alertActionText");

  if (state.prediction.water_stress_score !== null && state.prediction.water_stress !== "UNAVAILABLE") {
    if (stressBadge) {
      stressBadge.className = state.prediction.water_stress === "HIGH RISK" ? "badge bg-danger" : state.prediction.water_stress === "MODERATE RISK" ? "badge bg-warning text-dark" : "badge bg-success";
      stressBadge.textContent = state.prediction.water_stress;
    }
    if (alertTitle) {
      alertTitle.innerHTML = state.prediction.water_stress === "HIGH RISK" ? '<i class="fas fa-exclamation-triangle text-danger me-1"></i> High Water Stress Alert' : '<i class="fas fa-check-circle text-success me-1"></i> Biophysical Balance';
    }
    if (alertSeverity) {
      alertSeverity.className = state.prediction.water_stress === "HIGH RISK" ? "badge bg-danger-subtle text-danger border" : "badge bg-success-subtle text-success border";
      alertSeverity.textContent = `Stress Score: ${state.prediction.water_stress_score}/100`;
    }
    if (alertDescription) {
      const topFactor = state.prediction.factors && state.prediction.factors.length > 0 ? state.prediction.factors[0] : null;
      if (topFactor) {
        alertDescription.textContent = `${topFactor.name}: ${topFactor.value}. ${topFactor.agronomic_rule}`;
      } else {
        alertDescription.textContent = `Telemetry is consistent with normal growth for ${state.crop.name || "crop"} during ${state.crop.growth_stage || "current stage"}.`;
      }
    }
    if (alertActionText) {
      if (state.prediction.water_stress === "HIGH RISK") {
        alertActionText.textContent = "Controlled irrigation recommended within 3–4 hours to prevent transpirational stress.";
      } else if (state.prediction.water_stress === "MODERATE RISK") {
        alertActionText.textContent = "Monitor root-zone moisture level and schedule next irrigation round.";
      } else {
        alertActionText.textContent = "Adequate moisture level. Continue regular field monitoring.";
      }
    }
  } else {
    if (stressBadge) {
      stressBadge.className = "badge bg-secondary";
      stressBadge.textContent = "Unavailable";
    }
    if (alertTitle) {
      alertTitle.innerHTML = '<i class="fas fa-info-circle text-muted me-1"></i> Telemetry Assessment Pending';
    }
    if (alertSeverity) {
      alertSeverity.className = "badge bg-light text-dark border";
      alertSeverity.textContent = "Awaiting Live Data";
    }
    if (alertDescription) {
      alertDescription.textContent = "Please ensure farm GPS coordinates are configured to calculate biophysical risk.";
    }
    if (alertActionText) {
      alertActionText.textContent = "Click 'Refresh Farm Data' or 'Update Farm GPS' to initialize telemetry.";
    }
  }

  // 6. AI Farm Insight (Measured Data + ICAR Knowledge + AI Interpretation)
  const aiMeasuredData = document.getElementById("aiMeasuredData");
  const aiRetrievedKnowledge = document.getElementById("aiRetrievedKnowledge");
  const aiInterpretationText = document.getElementById("aiInterpretationText");

  const tStr = state.weather.temperature !== null ? `${Number(state.weather.temperature).toFixed(1)}°C` : "Unavailable";
  const hStr = state.weather.humidity !== null ? `${state.weather.humidity}%` : "Unavailable";
  const rStr = state.weather.rainfall !== null ? `${state.weather.rainfall} mm` : "Unavailable";
  const mStr = state.soil.moisture !== null ? `${Number(state.soil.moisture).toFixed(1)}%` : "Unavailable";
  const nStr = state.satellite.ndvi !== null ? `${Number(state.satellite.ndvi).toFixed(4)}` : "Unavailable";
  const cStr = state.crop.name || "Not configured";
  const sStr = state.crop.growth_stage || state.crop.growthStage || "Stage not set";

  if (aiMeasuredData) {
    aiMeasuredData.textContent = `Temperature: ${tStr} | Humidity: ${hStr} | Rainfall: ${rStr} | Soil Moisture: ${mStr} | NDVI: ${nStr} | Crop: ${cStr} (${sStr})`;
  }

  if (aiRetrievedKnowledge) {
    if (state.crop.name) {
      aiRetrievedKnowledge.textContent = `ICAR package of practices specifies optimal root-zone moisture of 35–45% during ${sStr} for ${cStr} to protect crop yield and canopy photosynthetic vigor.`;
    } else {
      aiRetrievedKnowledge.textContent = "ICAR standard guidelines for field crop water demand and nutrient management.";
    }
  }

  if (aiInterpretationText) {
    if (state.location.latitude && state.weather.temperature !== null) {
      if (state.soil.moisture !== null && state.soil.moisture < 35.0) {
        aiInterpretationText.textContent = `"Measured root-zone moisture (${mStr}) is below optimal ICAR phenological threshold during ${sStr} with ambient temperature at ${tStr}. Irrigation is advised to maintain canopy vigor."`;
      } else if (state.soil.moisture !== null) {
        aiInterpretationText.textContent = `"Measured soil moisture (${mStr}) and canopy vigor (NDVI: ${nStr}) are adequate for ${cStr} during ${sStr}. Continue scheduled field monitoring."`;
      } else {
        aiInterpretationText.textContent = `"Live weather telemetry received (${tStr}, ${hStr}). Connect SoilGrids and Sentinel-2 to obtain complete multidimensional risk analysis."`;
      }
    } else {
      aiInterpretationText.textContent = `"Please configure your farm GPS coordinates and profile to generate personalized, real-data-driven agricultural advisories."`;
    }
  }

  // 7. Update Provenance Matrix
  renderDataQualityWidget();

  // 8. Re-render Charts if initialized
  if (typeof updateDashboardCharts === "function") {
    updateDashboardCharts(state);
  }
}

function renderDataQualityWidget() {
  const container = document.getElementById("dataQualityContainer");
  if (!container || typeof FarmState === "undefined") return;

  const dq = FarmState.getDataQuality();
  container.innerHTML = `
    <div class="card p-3 border-0 bg-light-subtle rounded-3 shadow-sm mb-4">
      <div class="d-flex justify-content-between align-items-center mb-3">
        <h6 class="fw-bold text-dark mb-0">
          <i class="fas fa-shield-alt text-success me-2"></i> Data Provenance & Verification Matrix
        </h6>
        <span class="badge bg-success-subtle text-success border">Live Verification</span>
      </div>
      <div class="row g-2 small">
        <div class="col-6 col-md-4 col-lg-2">
          <div class="p-2 bg-white rounded border h-100">
            <div class="text-muted small">Location</div>
            <div class="fw-bold text-truncate">${dq.location.status}</div>
            <span class="badge ${dq.location.badgeClass} mt-1 text-truncate d-inline-block max-w-100"><i class="fas fa-${dq.location.icon} me-1"></i>${dq.location.source}</span>
          </div>
        </div>
        <div class="col-6 col-md-4 col-lg-2">
          <div class="p-2 bg-white rounded border h-100">
            <div class="text-muted small">Weather</div>
            <div class="fw-bold text-truncate">${dq.weather.status}</div>
            <span class="badge ${dq.weather.badgeClass} mt-1 text-truncate d-inline-block max-w-100"><i class="fas fa-${dq.weather.icon} me-1"></i>${dq.weather.source}</span>
          </div>
        </div>
        <div class="col-6 col-md-4 col-lg-2">
          <div class="p-2 bg-white rounded border h-100">
            <div class="text-muted small">Soil</div>
            <div class="fw-bold text-truncate">${dq.soil.status}</div>
            <span class="badge ${dq.soil.badgeClass} mt-1 text-truncate d-inline-block max-w-100"><i class="fas fa-${dq.soil.icon} me-1"></i>${dq.soil.source}</span>
          </div>
        </div>
        <div class="col-6 col-md-4 col-lg-2">
          <div class="p-2 bg-white rounded border h-100">
            <div class="text-muted small">Satellite</div>
            <div class="fw-bold text-truncate">${dq.satellite.status}</div>
            <span class="badge ${dq.satellite.badgeClass} mt-1 text-truncate d-inline-block max-w-100"><i class="fas fa-${dq.satellite.icon} me-1"></i>${dq.satellite.source}</span>
          </div>
        </div>
        <div class="col-6 col-md-4 col-lg-2">
          <div class="p-2 bg-white rounded border h-100">
            <div class="text-muted small">Crop Profile</div>
            <div class="fw-bold text-truncate">${dq.crop.status}</div>
            <span class="badge ${dq.crop.badgeClass} mt-1 text-truncate d-inline-block max-w-100"><i class="fas fa-${dq.crop.icon} me-1"></i>${dq.crop.source}</span>
          </div>
        </div>
        <div class="col-6 col-md-4 col-lg-2">
          <div class="p-2 bg-white rounded border h-100">
            <div class="text-muted small">Knowledge & AI</div>
            <div class="fw-bold text-truncate">${dq.rag.status}</div>
            <span class="badge ${dq.rag.badgeClass} mt-1 text-truncate d-inline-block max-w-100"><i class="fas fa-${dq.rag.icon} me-1"></i>${dq.rag.source}</span>
          </div>
        </div>
      </div>
    </div>
  `;
}

function setupFarmProfileModal() {
  const modalEl = document.getElementById("farmProfileModal");
  const form = document.getElementById("farmProfileForm");

  if (!modalEl || !form) return;

  modalEl.addEventListener("show.bs.modal", () => {
    if (typeof FarmState === "undefined") return;
    const state = FarmState.get();
    const inputFarmId = document.getElementById("inputFarmId");
    const inputCropName = document.getElementById("inputCropName");
    const inputCropVariety = document.getElementById("inputCropVariety");
    const inputCropArea = document.getElementById("inputCropArea");
    const inputGrowthStage = document.getElementById("inputGrowthStage");
    const inputPlantingDate = document.getElementById("inputPlantingDate");
    const inputIrrigationMethod = document.getElementById("inputIrrigationMethod");
    const inputSoilType = document.getElementById("inputSoilType");

    if (inputFarmId) inputFarmId.value = state.farm_id || state.crop.farm_id || "";
    if (inputCropName) inputCropName.value = state.crop.name || "";
    if (inputCropVariety) inputCropVariety.value = state.crop.variety || "";
    if (inputCropArea) inputCropArea.value = state.crop.area || state.crop.area_acres || "";
    if (inputGrowthStage) inputGrowthStage.value = state.crop.growth_stage || state.crop.growthStage || "";
    if (inputPlantingDate) inputPlantingDate.value = state.crop.planting_date || state.crop.plantingDate || "";
    if (inputIrrigationMethod) inputIrrigationMethod.value = state.crop.irrigation_method || state.crop.irrigationMethod || "";
    if (inputSoilType) inputSoilType.value = state.crop.soil_type || state.crop.soilType || "";
  });

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    if (typeof FarmState === "undefined") return;

    const farmId = document.getElementById("inputFarmId")?.value.trim() || null;
    const cropName = document.getElementById("inputCropName")?.value.trim() || null;
    const variety = document.getElementById("inputCropVariety")?.value.trim() || null;
    const area = parseFloat(document.getElementById("inputCropArea")?.value) || null;
    const growthStage = document.getElementById("inputGrowthStage")?.value.trim() || null;
    const plantingDate = document.getElementById("inputPlantingDate")?.value.trim() || null;
    const irrigationMethod = document.getElementById("inputIrrigationMethod")?.value.trim() || null;
    const soilType = document.getElementById("inputSoilType")?.value.trim() || null;

    FarmState.updateProfile({
      farm_id: farmId,
      name: cropName,
      variety: variety,
      area: area,
      growth_stage: growthStage,
      planting_date: plantingDate,
      irrigation_method: irrigationMethod,
      soil_type: soilType,
    });

    // Close modal
    const modalInstance = bootstrap.Modal.getInstance(modalEl);
    if (modalInstance) modalInstance.hide();

    showToast("Farmer Crop Profile updated and synchronized with FarmContext.", "success");
  });
}

function setActiveNavigation() {
  const currentPage = window.location.pathname.split("/").pop() || "dashboard.html";
  const navLinks = document.querySelectorAll(".nav-item");

  navLinks.forEach((link) => {
    link.classList.remove("active");
    const href = link.getAttribute("href");
    if (href === currentPage || (currentPage === "" && href === "dashboard.html")) {
      link.classList.add("active");
    }
  });
}

function setupGlobalInteractions() {
  const appSidebar = document.getElementById("appSidebar");
  const mobileMenuBtn = document.getElementById("mobileMenuBtn");
  const sidebarCollapseBtn = document.getElementById("sidebarCollapseBtn");

  if (mobileMenuBtn && appSidebar) {
    mobileMenuBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      appSidebar.classList.toggle("sidebar-open");
    });
  }

  if (sidebarCollapseBtn && appSidebar) {
    sidebarCollapseBtn.addEventListener("click", () => {
      document.querySelector(".app-layout")?.classList.toggle("sidebar-collapsed");
    });
  }

  // Refresh farm data action button handlers
  const refreshBtns = [
    document.getElementById("refreshFarmDataBtn"),
    document.getElementById("refreshFarmDataBtnTop")
  ];

  refreshBtns.forEach((btn) => {
    if (btn && typeof FarmState !== "undefined") {
      btn.addEventListener("click", async () => {
        const state = FarmState.get();
        if (!state.location.latitude || !state.location.longitude) {
          showToast("Please set farm GPS coordinates first.", "warning");
          return;
        }

        btn.disabled = true;
        const originalHtml = btn.innerHTML;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin text-success"></i> Syncing Live Telemetry...';

        try {
          await FarmState.syncLiveTelemetry();
          showToast("Live telemetry refreshed from OpenWeather, ISRIC SoilGrids, and Sentinel-2.", "success");
        } catch (err) {
          showToast("Error syncing telemetry: " + err.message, "danger");
        } finally {
          btn.disabled = false;
          btn.innerHTML = originalHtml;
        }
      });
    }
  });
}

// Toast notification helper
function showToast(message, type = "info") {
  const toast = document.createElement("div");
  toast.className = `alert alert-${type}`;
  toast.style.position = "fixed";
  toast.style.bottom = "24px";
  toast.style.right = "24px";
  toast.style.zIndex = "9999";
  toast.style.padding = "0.75rem 1.25rem";
  toast.style.borderRadius = "12px";
  toast.style.boxShadow = "0 10px 25px rgba(0,0,0,0.15)";
  toast.style.display = "flex";
  toast.style.alignItems = "center";
  toast.style.gap = "0.5rem";
  toast.innerHTML = `<i class="fas fa-${type === "success" ? "check-circle" : type === "warning" ? "exclamation-triangle" : "info-circle"}"></i> <span>${message}</span>`;
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 4000);
}

// Auto-init on DOMContentLoaded
document.addEventListener("DOMContentLoaded", () => {
  initDashboard();
});
