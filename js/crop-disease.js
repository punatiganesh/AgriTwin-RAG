/**
 * AgriTwin-RAG — Crop Disease Diagnostic Module (js/crop-disease.js)
 * Manages image upload, client-side validation, neural model inference,
 * Grad-CAM visual attention mapping, ICAR RAG synthesis, and FarmState synchronization.
 */

document.addEventListener("DOMContentLoaded", () => {
  // DOM Elements
  const leafFileInput = document.getElementById("leafFileInput");
  const dropzoneArea = document.getElementById("dropzoneArea");
  const chooseImageBtn = document.getElementById("chooseImageBtn");
  const previewContainer = document.getElementById("previewContainer");
  const leafImagePreview = document.getElementById("leafImagePreview");
  const previewFileName = document.getElementById("previewFileName");
  const previewDimensions = document.getElementById("previewDimensions");
  const previewFileSize = document.getElementById("previewFileSize");
  const removeImageBtn = document.getElementById("removeImageBtn");
  const analyzeDiseaseBtn = document.getElementById("analyzeDiseaseBtn");
  const uploadErrorBanner = document.getElementById("uploadErrorBanner");
  const uploadErrorText = document.getElementById("uploadErrorText");

  // Results Section Elements
  const resultsPlaceholder = document.getElementById("resultsPlaceholder");
  const resultsLoading = document.getElementById("resultsLoading");
  const resultsContent = document.getElementById("resultsContent");
  const predictionStatusBadge = document.getElementById("predictionStatusBadge");
  const detectedDiseaseTitle = document.getElementById("detectedDiseaseTitle");
  const confidenceValue = document.getElementById("confidenceValue");
  const predictionTimeSub = document.getElementById("predictionTimeSub");
  const lowConfidenceAlert = document.getElementById("lowConfidenceAlert");
  const lowConfidenceThresholdText = document.getElementById("lowConfidenceThresholdText");
  const healthyCropAlert = document.getElementById("healthyCropAlert");
  const topPredictionsContainer = document.getElementById("topPredictionsContainer");

  // XAI Elements
  const xaiSection = document.getElementById("xaiSection");
  const gradcamOriginalImg = document.getElementById("gradcamOriginalImg");
  const gradcamOverlayImg = document.getElementById("gradcamOverlayImg");

  // Farm Context Elements
  const farmContextSection = document.getElementById("farmContextSection");
  const farmContextPillsGrid = document.getElementById("farmContextPillsGrid");

  // Advisory Elements
  const advisorySection = document.getElementById("advisorySection");
  const evidenceDiseaseName = document.getElementById("evidenceDiseaseName");
  const ragSourcesContainer = document.getElementById("ragSourcesContainer");
  const recommendationsLoading = document.getElementById("recommendationsLoading");
  const recommendationsContent = document.getElementById("recommendationsContent");
  const askAgriTwinBtn = document.getElementById("askAgriTwinBtn");

  // Diagnostic diagnostics button
  const checkModelStatusBtn = document.getElementById("checkModelStatusBtn");
  const modelStatusPill = document.getElementById("modelStatusPill");

  let selectedFile = null;
  let isAnalyzing = false;

  // 1. Initial Diagnostics Check
  checkModelHealth();

  async function checkModelHealth() {
    if (modelStatusPill) {
      modelStatusPill.textContent = "⏳ Initializing Disease Model...";
      modelStatusPill.className = "text-white-50 small";
    }
    try {
      const statusRes = await API.getDiseaseStatus();
      if (statusRes && (statusRes.model_loaded || (statusRes.success && statusRes.model_configured))) {
        const count = statusRes.classes_count || (statusRes.classes ? statusRes.classes.length : 5);
        if (modelStatusPill) {
          modelStatusPill.textContent = `🟢 Model Ready (${count} Classes)`;
          modelStatusPill.className = "text-success small fw-semibold";
        }
      } else {
        if (modelStatusPill) {
          modelStatusPill.textContent = "🔴 Model Unavailable";
          modelStatusPill.className = "text-danger small fw-semibold";
        }
      }
    } catch (e) {
      console.warn("Disease model diagnostics check error:", e);
      if (modelStatusPill) {
        modelStatusPill.textContent = "🔴 Model Unavailable";
        modelStatusPill.className = "text-danger small fw-semibold";
      }
    }
  }

  if (checkModelStatusBtn) {
    checkModelStatusBtn.addEventListener("click", async () => {
      try {
        const status = await API.getDiseaseStatus();
        alert(
          `AgriTwin Rice Pathology Diagnostic:\n\n` +
          `• Model Configured: ${status.model_configured ? "YES" : "NO"}\n` +
          `• Architecture: ${status.model_architecture || "PyTorch MobileNetV2"}\n` +
          `• Target Crop: ${status.target_crop || "Rice"}\n` +
          `• Classes (${status.classes_count || 5}): ${(status.classes || []).join(", ")}\n` +
          `• Low Confidence Threshold: ${(status.low_confidence_threshold || 0.6) * 100}%\n` +
          `• Grad-CAM Visual Attention: ${status.gradcam_supported ? "Active" : "Unavailable"}`
        );
      } catch (err) {
        alert("Unable to query disease model status.");
      }
    });
  }

  // 2. File Selection & Drag-and-Drop Handlers
  if (chooseImageBtn) {
    chooseImageBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      leafFileInput.click();
    });
  }

  if (dropzoneArea) {
    dropzoneArea.addEventListener("click", () => {
      leafFileInput.click();
    });

    ["dragenter", "dragover"].forEach((evt) => {
      dropzoneArea.addEventListener(evt, (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropzoneArea.classList.add("dragover");
      });
    });

    ["dragleave", "drop"].forEach((evt) => {
      dropzoneArea.addEventListener(evt, (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropzoneArea.classList.remove("dragover");
      });
    });

    dropzoneArea.addEventListener("drop", (e) => {
      if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files.length > 0) {
        handleFileSelected(e.dataTransfer.files[0]);
      }
    });
  }

  if (leafFileInput) {
    leafFileInput.addEventListener("change", (e) => {
      if (e.target.files && e.target.files.length > 0) {
        handleFileSelected(e.target.files[0]);
      }
    });
  }

  if (removeImageBtn) {
    removeImageBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      clearSelectedImage();
    });
  }

  function showError(msg) {
    if (uploadErrorBanner && uploadErrorText) {
      uploadErrorText.textContent = msg;
      uploadErrorBanner.classList.remove("d-none");
    }
  }

  function hideError() {
    if (uploadErrorBanner) {
      uploadErrorBanner.classList.add("d-none");
    }
  }

  function clearSelectedImage() {
    selectedFile = null;
    leafFileInput.value = "";
    previewContainer.classList.add("d-none");
    dropzoneArea.classList.remove("d-none");
    analyzeDiseaseBtn.disabled = true;
    hideError();
  }

  function handleFileSelected(file) {
    hideError();
    if (!file) return;

    // Validate mime type and extension
    const validExtensions = [".jpg", ".jpeg", ".png", ".webp"];
    const fileName = file.name.toLowerCase();
    const isValidExt = validExtensions.some((ext) => fileName.endsWith(ext));

    if (!isValidExt && !file.type.startsWith("image/")) {
      showError("Invalid file type. Please select a JPG, JPEG, or PNG image.");
      clearSelectedImage();
      return;
    }

    // Validate file size (12MB max)
    const maxSize = 12 * 1024 * 1024;
    if (file.size > maxSize) {
      showError("File size exceeds 12MB. Please choose a smaller crop leaf image.");
      clearSelectedImage();
      return;
    }

    if (file.size === 0) {
      showError("Selected file is empty (0 bytes). Please choose a valid image.");
      clearSelectedImage();
      return;
    }

    selectedFile = file;

    // Load preview and compute natural dimensions
    const reader = new FileReader();
    reader.onload = function (evt) {
      const dataUrl = evt.target.result;
      leafImagePreview.src = dataUrl;

      // Extract image dimensions
      const img = new Image();
      img.onload = function () {
        previewDimensions.textContent = `${this.naturalWidth} × ${this.naturalHeight} px`;
      };
      img.src = dataUrl;

      previewFileName.textContent = file.name;
      const sizeKB = (file.size / 1024).toFixed(1);
      const sizeMB = (file.size / (1024 * 1024)).toFixed(2);
      previewFileSize.textContent = file.size > 1024 * 1024 ? `${sizeMB} MB` : `${sizeKB} KB`;

      dropzoneArea.classList.add("d-none");
      previewContainer.classList.remove("d-none");
      analyzeDiseaseBtn.disabled = false;
    };
    reader.onerror = function () {
      showError("Failed to read image file from disk.");
      clearSelectedImage();
    };
    reader.readAsDataURL(file);
  }

  // 3. Analyze Disease Action
  if (analyzeDiseaseBtn) {
    analyzeDiseaseBtn.addEventListener("click", async () => {
      if (!selectedFile || isAnalyzing) return;

      isAnalyzing = true;
      hideError();
      setLoadingState(true);

      const formData = new FormData();
      formData.append("file", selectedFile);

      try {
        const data = await API.predictDisease(formData);

        if (!data || data.success === false) {
          const errMsg = data?.error || "Disease analysis failed. Please verify that the model is configured.";
          showError(errMsg);
          setLoadingState(false);
          isAnalyzing = false;
          return;
        }

        // Render Prediction Results
        renderPredictionResult(data);

        // Render Explainable AI (Grad-CAM)
        renderXAISegment(data);

        // Update Farm Context & Digital Twin
        renderFarmContextSegment(data);

        // Save Disease observation in Central FarmState
        if (typeof FarmState !== "undefined" && FarmState.setDiseaseObservation) {
          FarmState.setDiseaseObservation({
            disease: data.disease,
            crop: data.crop || "Rice",
            confidence: data.confidence,
            confidence_percentage: data.confidence_percentage,
            is_healthy: data.is_healthy,
            is_low_confidence: data.is_low_confidence,
            top_predictions: data.top_predictions,
            model_name: data.model_name,
            timestamp: new Date().toISOString(),
          });
        }

        // Trigger Grounded ICAR RAG Advisory
        await triggerAdvisorySynthesis(data);
      } catch (err) {
        showError(`Network or execution error: ${err.message || err}`);
      } finally {
        setLoadingState(false);
        isAnalyzing = false;
      }
    });
  }

  function setLoadingState(isLoading) {
    if (isLoading) {
      analyzeDiseaseBtn.disabled = true;
      analyzeDiseaseBtn.innerHTML = `<span class="spinner-border spinner-border-sm me-2"></span>Analyzing crop image...`;
      resultsPlaceholder.classList.add("d-none");
      resultsContent.classList.add("d-none");
      resultsLoading.classList.remove("d-none");
      predictionStatusBadge.className = "badge bg-warning text-dark";
      predictionStatusBadge.textContent = "Analyzing Image...";
    } else {
      analyzeDiseaseBtn.disabled = false;
      analyzeDiseaseBtn.innerHTML = `<i class="fas fa-search-plus me-2"></i>Analyze Disease`;
      resultsLoading.classList.add("d-none");
    }
  }

  function renderPredictionResult(data) {
    resultsPlaceholder.classList.add("d-none");
    resultsLoading.classList.add("d-none");
    resultsContent.classList.remove("d-none");

    predictionStatusBadge.className = data.is_healthy
      ? "badge bg-success text-white"
      : (data.is_low_confidence ? "badge bg-warning text-dark" : "badge bg-danger text-white");
    predictionStatusBadge.innerHTML = `<i class="fas fa-check-circle me-1"></i>${data.is_healthy ? "Healthy Plant" : "Condition Detected"}`;

    detectedDiseaseTitle.textContent = data.is_healthy ? "Healthy Crop Leaf" : `Rice ${data.disease}`;
    confidenceValue.textContent = `${data.confidence_percentage}%`;
    predictionTimeSub.textContent = `Neural inference execution: ${data.prediction_time_ms || 0} ms • PyTorch MobileNetV2`;

    // Low confidence alert
    if (data.is_low_confidence) {
      lowConfidenceAlert.classList.remove("d-none");
      if (lowConfidenceThresholdText) {
        lowConfidenceThresholdText.textContent = `${Math.round((data.low_confidence_threshold || 0.6) * 100)}%`;
      }
    } else {
      lowConfidenceAlert.classList.add("d-none");
    }

    // Healthy crop alert
    if (data.is_healthy) {
      healthyCropAlert.classList.remove("d-none");
    } else {
      healthyCropAlert.classList.add("d-none");
    }

    // Top Predictions Breakdown
    topPredictionsContainer.innerHTML = "";
    if (data.top_predictions && data.top_predictions.length > 0) {
      data.top_predictions.forEach((item, index) => {
        const isTop = index === 0;
        const barColor = isTop
          ? (item.class_name.toLowerCase() === "healthy" ? "#2e7d32" : "#d32f2f")
          : "#64748b";

        const row = document.createElement("div");
        row.className = "small";
        row.innerHTML = `
          <div class="d-flex justify-content-between align-items-center mb-1">
            <span class="${isTop ? "fw-bold text-dark" : "text-muted"}">
              ${index + 1}. ${item.class_name}
            </span>
            <span class="${isTop ? "fw-bold text-dark" : "text-muted"}">
              ${item.percentage}%
            </span>
          </div>
          <div class="prob-bar-container">
            <div class="prob-bar-fill" style="width: ${Math.max(item.percentage, 2)}%; background-color: ${barColor};"></div>
          </div>
        `;
        topPredictionsContainer.appendChild(row);
      });
    }
  }

  function renderXAISegment(data) {
    if (!xaiSection) return;

    if (data.gradcam && data.gradcam.supported && data.gradcam.image_data) {
      xaiSection.classList.remove("d-none");
      gradcamOriginalImg.src = leafImagePreview.src;
      gradcamOverlayImg.src = data.gradcam.image_data;
    } else {
      xaiSection.classList.add("d-none");
    }
  }

  function renderFarmContextSegment(data) {
    if (!farmContextSection || !farmContextPillsGrid) return;
    farmContextSection.classList.remove("d-none");
    farmContextPillsGrid.innerHTML = "";

    const ctx = typeof FarmState !== "undefined" ? FarmState.get() : {};
    const loc = ctx.location || {};
    const crop = ctx.crop || {};
    const weather = ctx.weather || {};
    const soil = ctx.soil || {};
    const sat = ctx.satellite || {};

    const items = [
      {
        icon: "fas fa-map-marker-alt text-success",
        label: "Farm Location",
        val: loc.place_name || (loc.latitude ? `${loc.latitude.toFixed(3)}°N, ${loc.longitude.toFixed(3)}°E` : "Location not set"),
      },
      {
        icon: "fas fa-seedling text-success",
        label: "Crop & Variety",
        val: `${crop.name || "Rice"}${crop.variety ? " (" + crop.variety + ")" : ""}`,
      },
      {
        icon: "fas fa-clock text-warning",
        label: "Growth Stage",
        val: crop.growth_stage || crop.growthStage || "Vegetative Stage",
      },
      {
        icon: "fas fa-temperature-high text-danger",
        label: "Temperature",
        val: weather.temperature !== null ? `${weather.temperature}°C` : "Unavailable",
      },
      {
        icon: "fas fa-tint text-primary",
        label: "Air Humidity",
        val: weather.humidity !== null ? `${weather.humidity}%` : "Unavailable",
      },
      {
        icon: "fas fa-cloud-rain text-info",
        label: "Rainfall",
        val: weather.rainfall !== null ? `${weather.rainfall} mm` : "0 mm",
      },
      {
        icon: "fas fa-water text-teal",
        label: "Soil Moisture",
        val: soil.moisture !== null ? `${soil.moisture}%` : "Unavailable",
      },
      {
        icon: "fas fa-satellite text-emerald",
        label: "Sentinel-2 NDVI",
        val: sat.ndvi !== null ? `${sat.ndvi}` : "Unavailable",
      },
    ];

    items.forEach((it) => {
      const col = document.createElement("div");
      col.className = "col-sm-6 col-md-3";
      col.innerHTML = `
        <div class="p-2 bg-light rounded-3 border h-100">
          <div class="text-muted" style="font-size: 0.75rem;"><i class="${it.icon} me-1"></i> ${it.label}</div>
          <div class="fw-bold text-dark text-truncate" title="${it.val}">${it.val}</div>
        </div>
      `;
      farmContextPillsGrid.appendChild(col);
    });
  }

  async function triggerAdvisorySynthesis(predictionData) {
    if (!advisorySection) return;

    advisorySection.classList.remove("d-none");
    evidenceDiseaseName.textContent = predictionData.is_healthy ? "Healthy Rice Crop" : `Rice ${predictionData.disease}`;
    recommendationsLoading.classList.remove("d-none");
    recommendationsContent.innerHTML = "";
    ragSourcesContainer.innerHTML = "";

    // Set up Ask AgriTwin link
    const queryText = `Image model detected Rice ${predictionData.disease} with ${predictionData.confidence_percentage}% model confidence. Explain the relevant ICAR management practices.`;
    if (askAgriTwinBtn) {
      askAgriTwinBtn.href = `assistant.html?query=${encodeURIComponent(queryText)}`;
    }

    const currentContext = typeof FarmState !== "undefined" ? FarmState.get() : {};

    try {
      const advisoryData = await API.getDiseaseAdvisory({
        disease: predictionData.disease,
        confidence: predictionData.confidence,
        farm_context: currentContext,
        language: "en",
      });

      recommendationsLoading.classList.add("d-none");

      if (!advisoryData || advisoryData.success === false) {
        recommendationsContent.innerHTML = `<div class="text-danger small"><i class="fas fa-exclamation-circle me-1"></i> Unable to generate ICAR agronomic advisory.</div>`;
        return;
      }

      // Render RAG Sources
      if (advisoryData.rag_sources && advisoryData.rag_sources.length > 0) {
        advisoryData.rag_sources.forEach((src) => {
          const card = document.createElement("div");
          card.className = "p-2 rounded-3 border bg-light small";
          card.innerHTML = `
            <div class="d-flex justify-content-between align-items-center">
              <strong class="text-dark"><i class="fas fa-file-pdf text-danger me-1"></i>${src.document || src.source}</strong>
              <span class="badge bg-secondary-subtle text-dark">Page ${src.page}</span>
            </div>
            <div class="text-muted mt-1" style="font-size: 0.72rem;">Deduplicated ICAR Section: ${src.chunk_id}</div>
          `;
          ragSourcesContainer.appendChild(card);
        });
      } else {
        ragSourcesContainer.innerHTML = `<div class="text-muted small">No specific ICAR document citations retrieved for this condition.</div>`;
      }

      // Render Recommendations Markdown
      if (advisoryData.advisory_markdown) {
        if (typeof marked !== "undefined" && marked.parse) {
          recommendationsContent.innerHTML = marked.parse(advisoryData.advisory_markdown);
        } else {
          recommendationsContent.innerHTML = advisoryData.advisory_markdown.replace(/\n/g, "<br>");
        }
      } else {
        recommendationsContent.innerHTML = `<p class="text-muted">Specific management information was not found in the current agricultural knowledge base.</p>`;
      }
    } catch (err) {
      recommendationsLoading.classList.add("d-none");
      recommendationsContent.innerHTML = `<div class="text-danger small"><i class="fas fa-exclamation-triangle me-1"></i> Error loading ICAR RAG advisory: ${err.message || err}</div>`;
    }
  }
});
