// frontend/js/location.js
// Handles Browser Geolocation (Mode A), Location Search (Mode B), Leaflet/OpenStreetMap Integration, and Centralized FarmContext Synchronization

document.addEventListener("DOMContentLoaded", () => {
  // UI Elements
  const currentLocationBtn = document.getElementById("currentLocationBtn");
  const searchInput = document.getElementById("locationSearchInput");
  const searchBtn = document.getElementById("searchLocationBtn");
  const searchResultsContainer = document.getElementById("searchResultsContainer");
  const searchResultsList = document.getElementById("searchResultsList");
  const searchStatus = document.getElementById("searchStatus");
  const gpsStatus = document.getElementById("gpsStatus");

  // Verification Summary Card Elements
  const verifiedName = document.getElementById("verifiedName");
  const verifiedDisplay = document.getElementById("verifiedDisplay");
  const verifiedLat = document.getElementById("verifiedLat");
  const verifiedLon = document.getElementById("verifiedLon");
  const verifiedSource = document.getElementById("verifiedSource");
  const verifiedAccuracy = document.getElementById("verifiedAccuracy");
  const accuracyRow = document.getElementById("accuracyRow");
  const confirmLocationBtn = document.getElementById("confirmLocationBtn");
  const confirmationAlert = document.getElementById("confirmationAlert");
  const topbarLocationPill = document.getElementById("topbarLocationText");

  // Map Elements
  const mapContainer = document.getElementById("farmMap");
  const mapConfigAlert = document.getElementById("mapConfigAlert");
  const mapConfigMsg = document.getElementById("mapConfigMsg");
  const mapStatusBadge = document.getElementById("mapStatusBadge");
  const mapLatReadout = document.getElementById("mapLatReadout");
  const mapLonReadout = document.getElementById("mapLonReadout");
  const mapActionHint = document.getElementById("mapActionHint");

  // Layer & Boundary Toolbar Elements
  const layerOsmBtn = document.getElementById("layerOsmBtn");
  const layerSatelliteBtn = document.getElementById("layerSatelliteBtn");
  const layerTerrainBtn = document.getElementById("layerTerrainBtn");
  const boundaryInfoPill = document.getElementById("boundaryInfoPill");
  const boundaryAcreageText = document.getElementById("boundaryAcreageText");
  const drawBoundaryBtn = document.getElementById("drawBoundaryBtn");
  const saveBoundaryBtn = document.getElementById("saveBoundaryBtn");
  const clearBoundaryBtn = document.getElementById("clearBoundaryBtn");

  // Leaflet Map & Layer State
  let leafletMap = null;
  let farmMarker = null;
  let accuracyCircle = null;
  let pendingLocation = null;
  let searchRequestCounter = 0;

  let osmLayer = null;
  let satelliteLayer = null;
  let terrainLayer = null;
  let activeBaseLayer = "osm";

  let isDrawingBoundary = false;
  let boundaryPoints = [];
  let boundaryPolygon = null;
  let boundaryPointMarkers = [];

  // --------------------------------------------------------------------------
  // 1. Initial State Loading from Centralized FarmState
  // --------------------------------------------------------------------------
  async function loadInitialLocation() {
    let activeLocation = null;

    // First try backend context
    try {
      if (typeof loadFarmContext === "function") {
        const farmResult = await loadFarmContext();
        if (farmResult && farmResult.success && farmResult.data && farmResult.data.location) {
          const loc = farmResult.data.location;
          if (loc.latitude !== null && loc.longitude !== null && !isNaN(loc.latitude) && !isNaN(loc.longitude)) {
            activeLocation = {
              latitude: parseFloat(loc.latitude),
              longitude: parseFloat(loc.longitude),
              name: loc.locality || loc.place_name || "Farm Location",
              display_name: loc.place_name || `${loc.latitude}, ${loc.longitude}`,
              district: loc.district || null,
              state: loc.state || null,
              country: loc.country || "India",
              source: loc.source || "backend",
              accuracy: loc.accuracy || null,
              confirmed: true,
            };
          }
        }
      }
    } catch (e) {
      console.warn("Unable to load initial context from backend:", e);
    }

    // Second: Check localStorage if backend returned nothing
    if (!activeLocation) {
      try {
        const raw = localStorage.getItem("farmLocation");
        if (raw) {
          const parsed = JSON.parse(raw);
          if (parsed && typeof parsed.latitude === "number" && typeof parsed.longitude === "number") {
            activeLocation = parsed;
          }
        }
      } catch (e) {
        console.warn("Error parsing saved farmLocation from storage:", e);
      }
    }

    // Third: Fallback to FarmState default location
    if (!activeLocation && window.FarmState) {
      const stateLoc = FarmState.get().location;
      if (stateLoc && stateLoc.latitude !== null && stateLoc.longitude !== null) {
        activeLocation = {
          latitude: parseFloat(stateLoc.latitude),
          longitude: parseFloat(stateLoc.longitude),
          name: stateLoc.locality || stateLoc.place_name || "Project Farm",
          display_name: stateLoc.place_name || `${stateLoc.latitude}, ${stateLoc.longitude}`,
          district: stateLoc.district || null,
          state: stateLoc.state || null,
          country: stateLoc.country || "India",
          source: stateLoc.source || "default",
          accuracy: stateLoc.accuracy || null,
          confirmed: true,
        };
      }
    }

    // If still no location, default coordinates
    if (!activeLocation) {
      activeLocation = {
        latitude: 9.571529,
        longitude: 77.675734,
        name: "Srivilliputhur",
        display_name: "Srivilliputhur, Virudhunagar District, Tamil Nadu, India",
        district: "Virudhunagar",
        state: "Tamil Nadu",
        country: "India",
        source: "default",
        accuracy: null,
        confirmed: true,
      };
    }

    pendingLocation = activeLocation;
    displayVerifiedLocation(activeLocation, true);
    updateTopbar(activeLocation.name);
    updateMapReadout(activeLocation.latitude, activeLocation.longitude, true);
    initOrUpdateLeafletMap(
      activeLocation.latitude,
      activeLocation.longitude,
      activeLocation.name,
      activeLocation.source,
      activeLocation.accuracy
    );
  }

  function updateTopbar(name) {
    if (topbarLocationPill && name) {
      topbarLocationPill.textContent = name;
    }
    const headerPill = document.querySelector("#farmLocation span");
    if (headerPill && name) {
      headerPill.textContent = name;
    }
  }

  function updateMapReadout(lat, lon, isConfirmed = false) {
    if (mapLatReadout) {
      mapLatReadout.textContent = lat !== null ? `${Number(lat).toFixed(6)}°` : "—";
    }
    if (mapLonReadout) {
      mapLonReadout.textContent = lon !== null ? `${Number(lon).toFixed(6)}°` : "—";
    }
    if (mapStatusBadge) {
      if (lat !== null && lon !== null) {
        if (isConfirmed) {
          mapStatusBadge.className = "badge bg-success-subtle text-success border border-success-subtle";
          mapStatusBadge.innerHTML = '<i class="fas fa-check-circle me-1"></i> Farm Location Active';
        } else {
          mapStatusBadge.className = "badge bg-warning-subtle text-dark border border-warning-subtle";
          mapStatusBadge.innerHTML = '<i class="fas fa-clock me-1"></i> Pending Confirmation';
        }
      } else {
        mapStatusBadge.className = "badge bg-light text-dark border";
        mapStatusBadge.innerHTML = '<i class="fas fa-circle text-secondary me-1"></i> No Location Set';
      }
    }
    if (mapActionHint) {
      if (lat !== null && lon !== null) {
        mapActionHint.textContent = isConfirmed
          ? "Location active. Drag marker or click map to fine-tune."
          : "Drag marker or click map to adjust, then click Confirm & Save.";
      } else {
        mapActionHint.textContent = "Detect GPS or search location above.";
      }
    }
  }

  // --------------------------------------------------------------------------
  // 2. Display Location in Verification Card
  // --------------------------------------------------------------------------
  function displayVerifiedLocation(loc, isConfirmed = false) {
    if (!loc) return;

    if (verifiedName) {
      verifiedName.textContent = loc.name || "Selected Farm Location";
    }
    if (verifiedDisplay) {
      verifiedDisplay.textContent =
        loc.display_name ||
        `Coordinates: ${Number(loc.latitude).toFixed(6)}, ${Number(loc.longitude).toFixed(6)}`;
    }
    if (verifiedLat) {
      verifiedLat.textContent = Number(loc.latitude).toFixed(6);
    }
    if (verifiedLon) {
      verifiedLon.textContent = Number(loc.longitude).toFixed(6);
    }

    // Source badge
    if (verifiedSource) {
      const src = String(loc.source || "").toLowerCase();
      if (src.includes("gps") || src.includes("browser") || src.includes("device")) {
        verifiedSource.className = "badge bg-success";
        verifiedSource.innerHTML = '<i class="fas fa-location-arrow me-1"></i> Device GPS';
      } else if (src.includes("search") || src.includes("geocoded") || src.includes("manual")) {
        verifiedSource.className = "badge bg-primary";
        verifiedSource.innerHTML = '<i class="fas fa-search me-1"></i> Search Geocoded';
      } else if (src.includes("map") || src.includes("pinpoint")) {
        verifiedSource.className = "badge bg-info text-dark";
        verifiedSource.innerHTML = '<i class="fas fa-map-pin me-1"></i> Map Pinpoint';
      } else {
        verifiedSource.className = "badge bg-secondary";
        verifiedSource.innerHTML = '<i class="fas fa-database me-1"></i> Stored Farm';
      }
    }

    // Accuracy row
    if (verifiedAccuracy && accuracyRow) {
      if (loc.accuracy !== undefined && loc.accuracy !== null && !isNaN(loc.accuracy)) {
        verifiedAccuracy.textContent = `±${Math.round(loc.accuracy)} meters`;
        accuracyRow.classList.remove("d-none");
      } else {
        accuracyRow.classList.add("d-none");
      }
    }

    // Confirm button state
    if (confirmLocationBtn) {
      if (isConfirmed) {
        confirmLocationBtn.classList.remove("btn-warning");
        confirmLocationBtn.classList.add("btn-success");
        confirmLocationBtn.innerHTML = '<i class="fas fa-check-circle me-1"></i> Location Active & Verified';
        confirmLocationBtn.disabled = true;
      } else {
        confirmLocationBtn.classList.remove("btn-success");
        confirmLocationBtn.classList.add("btn-warning");
        confirmLocationBtn.innerHTML = '<i class="fas fa-check me-1"></i> Confirm & Save This Location';
        confirmLocationBtn.disabled = false;
        if (confirmationAlert) confirmationAlert.classList.add("d-none");
      }
    }

    updateMapReadout(loc.latitude, loc.longitude, isConfirmed);
  }

  // --------------------------------------------------------------------------
  // 3. Leaflet + OpenStreetMap Interactive Mapping
  // --------------------------------------------------------------------------
  function initOrUpdateLeafletMap(lat, lon, name = "Farm Location", source = "gps", accuracy = null) {
    if (!mapContainer) return;

    if (typeof L === "undefined") {
      console.error("Leaflet library is not loaded.");
      if (mapConfigAlert) {
        mapConfigAlert.classList.remove("d-none");
        if (mapConfigMsg) {
          mapConfigMsg.textContent = "Interactive map engine (Leaflet) could not be loaded. Please check your connection.";
        }
      }
      return;
    }

    const nLat = Number(lat);
    const nLon = Number(lon);
    if (isNaN(nLat) || isNaN(nLon)) return;

    if (leafletMap) {
      leafletMap.setView([nLat, nLon], Math.max(leafletMap.getZoom(), 15));
      updateMarker(nLat, nLon, name, source, accuracy);
      return;
    }

    try {
      leafletMap = L.map(mapContainer, {
        center: [nLat, nLon],
        zoom: 15,
        zoomControl: true,
      });

      // 1. Standard OpenStreetMap
      osmLayer = L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19,
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank">OpenStreetMap</a> contributors',
      });

      // 2. High-Resolution Esri World Imagery (Satellite)
      satelliteLayer = L.tileLayer(
        "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        {
          maxZoom: 19,
          attribution: 'Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP',
        }
      );

      // 3. 3D Terrain & Shaded Elevation (OpenTopoMap)
      terrainLayer = L.tileLayer("https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png", {
        maxZoom: 17,
        attribution: 'Map data: &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors, <a href="http://viewfinderpanoramas.org">SRTM</a> | Map style: &copy; <a href="https://opentopomap.org">OpenTopoMap</a>',
      });

      [osmLayer, satelliteLayer, terrainLayer].forEach((layer) => {
        layer.on("tileerror", function (error) {
          console.warn("Tile layer loading notice:", error);
        });
      });

      // Default to Standard OSM
      osmLayer.addTo(leafletMap);

      // Add native Leaflet layer control in top-right
      L.control.layers({
        "Standard Map": osmLayer,
        "Satellite Aerial": satelliteLayer,
        "3D Terrain": terrainLayer,
      }).addTo(leafletMap);

      // Map click handler: switches between Location Pinpoint and Boundary Drawing
      leafletMap.on("click", async (e) => {
        const clickLat = parseFloat(e.latlng.lat.toFixed(6));
        const clickLon = parseFloat(e.latlng.lng.toFixed(6));

        if (isDrawingBoundary) {
          // Add point to boundary
          boundaryPoints.push([clickLat, clickLon]);
          const vertexMarker = L.circleMarker([clickLat, clickLon], {
            radius: 5,
            color: "#059669",
            fillColor: "#10b981",
            fillOpacity: 0.9,
          }).addTo(leafletMap);
          boundaryPointMarkers.push(vertexMarker);

          renderBoundaryPolygon(boundaryPoints, false);

          if (boundaryPoints.length >= 3 && saveBoundaryBtn) {
            saveBoundaryBtn.classList.remove("d-none");
          }
          if (clearBoundaryBtn) {
            clearBoundaryBtn.classList.remove("d-none");
          }
        } else {
          await handleCoordinatesSelected(clickLat, clickLon, "map");
        }
      });

      updateMarker(nLat, nLon, name, source, accuracy);
      initSavedBoundary();

      setTimeout(() => {
        if (leafletMap) leafletMap.invalidateSize();
      }, 250);
    } catch (err) {
      console.error("Leaflet initialization error:", err);
      if (mapConfigAlert) {
        mapConfigAlert.classList.remove("d-none");
        if (mapConfigMsg) {
          mapConfigMsg.textContent = "Failed to initialize interactive map: " + err.message;
        }
      }
    }
  }

  function updateMarker(lat, lon, name = "Farm Location", source = "gps", accuracy = null) {
    if (!leafletMap || typeof L === "undefined") return;

    const pos = [Number(lat), Number(lon)];

    if (!farmMarker) {
      farmMarker = L.marker(pos, {
        draggable: true,
        title: "Farm Location Marker",
      }).addTo(leafletMap);

      farmMarker.on("drag", (e) => {
        const curPos = e.target.getLatLng();
        updateMapReadout(curPos.lat, curPos.lng, false);
        if (verifiedLat) verifiedLat.textContent = curPos.lat.toFixed(6);
        if (verifiedLon) verifiedLon.textContent = curPos.lng.toFixed(6);
      });

      farmMarker.on("dragend", async (e) => {
        const dragPos = e.target.getLatLng();
        const dragLat = parseFloat(dragPos.lat.toFixed(6));
        const dragLon = parseFloat(dragPos.lng.toFixed(6));
        await handleCoordinatesSelected(dragLat, dragLon, "map");
      });
    } else {
      farmMarker.setLatLng(pos);
    }

    let accuracyText = "Manual search/selection";
    if (source === "gps" && accuracy) {
      accuracyText = `±${Math.round(accuracy)} meters (GPS)`;
    } else if (source === "map") {
      accuracyText = "User map pinpoint";
    }

    const popupHtml = `
      <div style="min-width: 200px; font-family: sans-serif; padding: 2px;">
        <h6 style="margin: 0 0 6px 0; font-weight: bold; color: #1b4d2e; font-size: 14px;">
          <i class="fas fa-leaf" style="color: #2d6a4f; margin-right: 4px;"></i> ${name || "Farm Location"}
        </h6>
        <div style="font-size: 12px; color: #334155; margin-bottom: 2px;">
          <strong>Lat:</strong> ${Number(lat).toFixed(6)}°
        </div>
        <div style="font-size: 12px; color: #334155; margin-bottom: 2px;">
          <strong>Lon:</strong> ${Number(lon).toFixed(6)}°
        </div>
        <div style="font-size: 11px; color: #64748b; margin-bottom: 6px;">
          <strong>Accuracy:</strong> ${accuracyText}
        </div>
        <div style="font-size: 11px; background: #fef3c7; color: #92400e; padding: 3px 6px; border-radius: 4px; border: 1px solid #fde68a;">
          <i class="fas fa-arrows-alt" style="margin-right: 2px;"></i> Drag marker or click map to reposition
        </div>
      </div>
    `;

    farmMarker.bindPopup(popupHtml).openPopup();
  }

  // --------------------------------------------------------------------------
  // Map Layer Switcher (Standard, Satellite Aerial, 3D Terrain)
  // --------------------------------------------------------------------------
  function setBaseLayer(type) {
    if (!leafletMap) return;
    activeBaseLayer = type;
    [layerOsmBtn, layerSatelliteBtn, layerTerrainBtn].forEach((btn) => {
      if (btn) {
        btn.classList.remove("active", "btn-secondary");
        btn.classList.add("btn-outline-secondary");
      }
    });

    if (osmLayer && leafletMap.hasLayer(osmLayer)) leafletMap.removeLayer(osmLayer);
    if (satelliteLayer && leafletMap.hasLayer(satelliteLayer)) leafletMap.removeLayer(satelliteLayer);
    if (terrainLayer && leafletMap.hasLayer(terrainLayer)) leafletMap.removeLayer(terrainLayer);

    if (type === "satellite") {
      if (satelliteLayer) satelliteLayer.addTo(leafletMap);
      if (layerSatelliteBtn) {
        layerSatelliteBtn.classList.add("active", "btn-secondary");
        layerSatelliteBtn.classList.remove("btn-outline-secondary");
      }
    } else if (type === "terrain") {
      if (terrainLayer) terrainLayer.addTo(leafletMap);
      if (layerTerrainBtn) {
        layerTerrainBtn.classList.add("active", "btn-secondary");
        layerTerrainBtn.classList.remove("btn-outline-secondary");
      }
    } else {
      if (osmLayer) osmLayer.addTo(leafletMap);
      if (layerOsmBtn) {
        layerOsmBtn.classList.add("active", "btn-secondary");
        layerOsmBtn.classList.remove("btn-outline-secondary");
      }
    }
  }

  if (layerOsmBtn) layerOsmBtn.addEventListener("click", () => setBaseLayer("osm"));
  if (layerSatelliteBtn) layerSatelliteBtn.addEventListener("click", () => setBaseLayer("satellite"));
  if (layerTerrainBtn) layerTerrainBtn.addEventListener("click", () => setBaseLayer("terrain"));

  // --------------------------------------------------------------------------
  // Farm Boundary Polygon Drawing & Acreage Calculation
  // --------------------------------------------------------------------------
  function calculatePolygonAreaAcres(points) {
    if (!points || points.length < 3) return 0;
    const R = 6378137; // Earth radius in meters
    let area = 0;
    const len = points.length;
    for (let i = 0; i < len; i++) {
      const p1 = points[i];
      const p2 = points[(i + 1) % len];
      const lat1 = (p1[0] * Math.PI) / 180;
      const lat2 = (p2[0] * Math.PI) / 180;
      const lon1 = (p1[1] * Math.PI) / 180;
      const lon2 = (p2[1] * Math.PI) / 180;
      area += (lon2 - lon1) * (2 + Math.sin(lat1) + Math.sin(lat2));
    }
    area = Math.abs((area * R * R) / 2.0);
    const acres = area / 4046.86;
    return Math.round(acres * 100) / 100;
  }

  function renderBoundaryPolygon(points, isFinished = false) {
    if (!leafletMap || typeof L === "undefined") return;

    if (boundaryPolygon) {
      leafletMap.removeLayer(boundaryPolygon);
      boundaryPolygon = null;
    }

    if (!points || points.length < 2) return;

    const acres = calculatePolygonAreaAcres(points);
    const ha = (acres * 0.404686).toFixed(2);

    if (boundaryAcreageText) {
      boundaryAcreageText.textContent = `${acres.toFixed(2)} Acres (${ha} ha) • ${points.length} pts`;
    }

    const polyOptions = {
      color: isFinished ? "#059669" : "#f59e0b",
      weight: 2.5,
      opacity: 0.9,
      fillColor: isFinished ? "#10b981" : "#fbbf24",
      fillOpacity: isFinished ? 0.35 : 0.2,
      dashArray: isFinished ? null : "4, 6",
    };

    boundaryPolygon = L.polygon(points, polyOptions).addTo(leafletMap);

    if (isFinished) {
      boundaryPolygon.bindPopup(`<strong>Farm Boundary</strong><br>Area: ${acres.toFixed(2)} Acres (${ha} ha)<br>Vertices: ${points.length}`);
    }
  }

  function clearBoundaryDisplay() {
    if (boundaryPolygon && leafletMap) {
      leafletMap.removeLayer(boundaryPolygon);
      boundaryPolygon = null;
    }
    boundaryPointMarkers.forEach((m) => {
      if (leafletMap && m) leafletMap.removeLayer(m);
    });
    boundaryPointMarkers = [];
    boundaryPoints = [];
    isDrawingBoundary = false;
    if (drawBoundaryBtn) {
      drawBoundaryBtn.innerHTML = '<i class="fas fa-pen-nib me-1"></i> Draw Boundary';
      drawBoundaryBtn.classList.remove("btn-warning");
      drawBoundaryBtn.classList.add("btn-outline-success");
    }
    if (boundaryAcreageText) boundaryAcreageText.textContent = "Not Drawn";
    if (saveBoundaryBtn) saveBoundaryBtn.classList.add("d-none");
    if (clearBoundaryBtn) clearBoundaryBtn.classList.add("d-none");
    if (mapActionHint) mapActionHint.textContent = "Drag marker or click map to adjust farm position";
  }

  function initSavedBoundary() {
    try {
      const state = window.FarmState ? FarmState.get() : null;
      const b = state?.location?.boundary;
      if (b && Array.isArray(b) && b.length >= 3) {
        boundaryPoints = b;
        renderBoundaryPolygon(b, true);
        if (clearBoundaryBtn) clearBoundaryBtn.classList.remove("d-none");
      }
    } catch (e) {
      console.warn("Boundary init error:", e);
    }
  }

  if (drawBoundaryBtn) {
    drawBoundaryBtn.addEventListener("click", () => {
      isDrawingBoundary = !isDrawingBoundary;
      if (isDrawingBoundary) {
        drawBoundaryBtn.innerHTML = '<i class="fas fa-times me-1"></i> Cancel Drawing';
        drawBoundaryBtn.classList.remove("btn-outline-success");
        drawBoundaryBtn.classList.add("btn-warning");
        if (mapActionHint) mapActionHint.textContent = "Click around field perimeter on the map to place boundary corner vertices.";
        if (clearBoundaryBtn) clearBoundaryBtn.classList.remove("d-none");
      } else {
        drawBoundaryBtn.innerHTML = '<i class="fas fa-pen-nib me-1"></i> Draw Boundary';
        drawBoundaryBtn.classList.remove("btn-warning");
        drawBoundaryBtn.classList.add("btn-outline-success");
        if (mapActionHint) mapActionHint.textContent = "Drag marker or click map to adjust farm position";
      }
    });
  }

  if (saveBoundaryBtn) {
    saveBoundaryBtn.addEventListener("click", async () => {
      if (!boundaryPoints || boundaryPoints.length < 3) {
        alert("Please click at least 3 points on the map to define your farm boundary polygon.");
        return;
      }

      const acres = calculatePolygonAreaAcres(boundaryPoints);
      if (window.FarmState && typeof FarmState.setBoundary === "function") {
        FarmState.setBoundary(boundaryPoints, acres);
      }

      renderBoundaryPolygon(boundaryPoints, true);
      isDrawingBoundary = false;

      boundaryPointMarkers.forEach((m) => {
        if (leafletMap && m) leafletMap.removeLayer(m);
      });
      boundaryPointMarkers = [];

      if (drawBoundaryBtn) {
        drawBoundaryBtn.innerHTML = '<i class="fas fa-pen-nib me-1"></i> Redraw Boundary';
        drawBoundaryBtn.classList.remove("btn-warning");
        drawBoundaryBtn.classList.add("btn-outline-success");
      }
      saveBoundaryBtn.classList.add("d-none");
      if (clearBoundaryBtn) clearBoundaryBtn.classList.remove("d-none");
      if (mapActionHint) mapActionHint.textContent = `Boundary saved! Total area: ${acres} acres.`;

      alert(`Farm boundary saved successfully! Acreage: ${acres.toFixed(2)} Acres.`);
    });
  }

  if (clearBoundaryBtn) {
    clearBoundaryBtn.addEventListener("click", () => {
      clearBoundaryDisplay();
      if (window.FarmState && typeof FarmState.setBoundary === "function") {
        FarmState.setBoundary(null, null);
      }
    });
  }

  // --------------------------------------------------------------------------
  // 4. Mode A: Browser GPS Detection & Reverse Geocoding
  // --------------------------------------------------------------------------
  function setGpsStatus(message, type = "info") {
    if (!gpsStatus) return;
    gpsStatus.classList.remove("d-none", "alert-danger", "alert-warning", "alert-success", "alert-info", "alert-light");
    if (type === "error") {
      gpsStatus.classList.add("alert-danger");
    } else if (type === "warning") {
      gpsStatus.classList.add("alert-warning");
    } else if (type === "success") {
      gpsStatus.classList.add("alert-success");
    } else {
      gpsStatus.classList.add("alert-info");
    }
    gpsStatus.innerHTML = message;
  }

  async function handleGpsSuccess(position) {
    const { latitude, longitude, accuracy } = position.coords;

    // Validate coordinates
    if (
      latitude < -90 ||
      latitude > 90 ||
      longitude < -180 ||
      longitude > 180 ||
      isNaN(latitude) ||
      isNaN(longitude)
    ) {
      setGpsStatus(
        '<i class="fas fa-exclamation-triangle me-1"></i> Invalid coordinates received from device GPS.',
        "error"
      );
      if (currentLocationBtn) {
        currentLocationBtn.disabled = false;
        currentLocationBtn.innerHTML = '<i class="fas fa-location-crosshairs me-1"></i> Use My Current Location';
      }
      return;
    }

    const accuracyNum = typeof accuracy === "number" && !isNaN(accuracy) ? Math.round(accuracy) : null;
    const accuracyText = accuracyNum ? `±${accuracyNum}m` : "High Accuracy";

    setGpsStatus(
      `<i class="fas fa-spinner fa-spin me-1"></i> GPS locked (${accuracyText}). Resolving address and activating farm location...`,
      "info"
    );

    const cleanLat = parseFloat(Number(latitude).toFixed(6));
    const cleanLon = parseFloat(Number(longitude).toFixed(6));

    let resolvedName = `Farm (${cleanLat.toFixed(4)}, ${cleanLon.toFixed(4)})`;
    let resolvedDisplay = `Coordinates: ${cleanLat.toFixed(6)}, ${cleanLon.toFixed(6)}`;
    let revData = null;

    try {
      if (typeof reverseGeocode === "function") {
        revData = await reverseGeocode(cleanLat, cleanLon);
        if (revData && revData.success) {
          resolvedName = revData.name || resolvedName;
          resolvedDisplay = revData.display_name || resolvedDisplay;
        }
      }
    } catch (err) {
      console.warn("Reverse geocode lookup warning:", err);
    }

    // Immediately activate and persist farm location via FarmState as authoritative source
    try {
      if (window.FarmState && typeof FarmState.setLocation === "function") {
        await FarmState.setLocation(
          cleanLat,
          cleanLon,
          resolvedName,
          "Device GPS",
          accuracyNum
        );
      } else {
        await apiFetch("/api/farm/context/location", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            location: {
              latitude: cleanLat,
              longitude: cleanLon,
              place_name: resolvedDisplay,
              locality: resolvedName,
              source: "Device GPS",
              accuracy: accuracyNum,
              accuracy_m: accuracyNum,
            },
          }),
        });
      }
    } catch (err) {
      console.warn("Error activating location via FarmState:", err);
    }

    const confirmedLocation = {
      latitude: cleanLat,
      longitude: cleanLon,
      name: resolvedName,
      display_name: resolvedDisplay,
      village: revData?.village || null,
      locality: revData?.locality || resolvedName,
      district: revData?.district || null,
      state: revData?.state || null,
      country: revData?.country || "India",
      postcode: revData?.postcode || null,
      source: "Device GPS",
      accuracy: accuracyNum,
      accuracy_m: accuracyNum,
      confirmed: true,
      confirmed_at: new Date().toISOString(),
    };

    pendingLocation = confirmedLocation;

    // Synchronize localStorage
    try {
      localStorage.setItem("farmLocation", JSON.stringify(confirmedLocation));
      localStorage.setItem("farmLatitude", String(cleanLat));
      localStorage.setItem("farmLongitude", String(cleanLon));
      localStorage.setItem("farmLocationName", confirmedLocation.name);
    } catch (e) {
      console.warn("Storage write error:", e);
    }

    // Update UI components
    displayVerifiedLocation(confirmedLocation, true);
    initOrUpdateLeafletMap(cleanLat, cleanLon, resolvedName, "gps", accuracyNum);
    updateTopbar(confirmedLocation.name);
    updateMapReadout(cleanLat, cleanLon, true);
    updateMarker(cleanLat, cleanLon, confirmedLocation.name, "gps", accuracyNum);

    setGpsStatus(
      `<i class="fas fa-check-circle text-success me-1"></i> Active farm location set to <strong>${resolvedName}</strong> (${accuracyText}). Weather, Soil, and NDVI telemetry updated.`,
      "success"
    );

    if (confirmationAlert) {
      confirmationAlert.classList.remove("d-none");
      confirmationAlert.innerHTML = `
        <div class="d-flex align-items-center justify-content-between flex-wrap gap-2">
          <div>
            <i class="fas fa-check-circle fs-5 me-2"></i>
            <strong>Current Location Active!</strong>
            <div class="small mt-1">Farm coordinates set to <strong>${resolvedName}</strong> (${cleanLat.toFixed(6)}°, ${cleanLon.toFixed(6)}°). Real-time telemetry synchronized across all modules.</div>
          </div>
          <div class="d-flex gap-2">
            <a href="weather.html" class="btn btn-sm btn-light text-success fw-bold flex-shrink-0">
              <i class="fas fa-cloud-sun me-1"></i> View Weather
            </a>
            <a href="satellite.html" class="btn btn-sm btn-light text-success fw-bold flex-shrink-0">
              <i class="fas fa-satellite me-1"></i> Satellite NDVI
            </a>
          </div>
        </div>
      `;
      confirmationAlert.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }

    if (confirmLocationBtn) {
      confirmLocationBtn.disabled = false;
      confirmLocationBtn.innerHTML = '<i class="fas fa-check me-1"></i> Saved & Active';
      confirmLocationBtn.classList.remove("btn-warning");
      confirmLocationBtn.classList.add("btn-success");
    }

    if (currentLocationBtn) {
      currentLocationBtn.disabled = false;
      currentLocationBtn.innerHTML = '<i class="fas fa-location-crosshairs me-1"></i> Use My Current Location';
    }
  }

  function handleGpsError(err) {
    if (currentLocationBtn) {
      currentLocationBtn.disabled = false;
      currentLocationBtn.innerHTML = '<i class="fas fa-location-crosshairs me-1"></i> Use My Current Location';
    }

    switch (err.code) {
      case err.PERMISSION_DENIED:
        setGpsStatus(
          '<i class="fas fa-lock text-danger me-1"></i> Location permission was denied by your browser. Please allow location access in your browser address bar/settings, or search for your farm below. Your active farm location has been preserved.',
          "error"
        );
        break;
      case err.POSITION_UNAVAILABLE:
        setGpsStatus(
          '<i class="fas fa-exclamation-circle text-danger me-1"></i> Location information is unavailable from your device sensors. Please search for your farm or village manually below. Your active farm location has been preserved.',
          "error"
        );
        break;
      case err.TIMEOUT:
        setGpsStatus(
          '<i class="fas fa-clock text-warning me-1"></i> GPS location request timed out. Please try again or search for your farm/village manually below. Your active farm location has been preserved.',
          "error"
        );
        break;
      default:
        setGpsStatus(
          '<i class="fas fa-exclamation-triangle text-danger me-1"></i> Unable to acquire device location. Please search for your farm location manually below. Your active farm location has been preserved.',
          "error"
        );
        break;
    }
  }

  function startGpsDetection() {
    if (!("geolocation" in navigator)) {
      setGpsStatus(
        '<i class="fas fa-exclamation-triangle me-1"></i> Geolocation is not supported by your browser. Please search for your farm location manually.',
        "error"
      );
      return;
    }

    setGpsStatus(
      '<i class="fas fa-spinner fa-spin me-1"></i> Requesting GPS permission and reading coordinates from device...',
      "info"
    );

    if (currentLocationBtn) {
      currentLocationBtn.disabled = true;
      currentLocationBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i> Acquiring GPS...';
    }

    navigator.geolocation.getCurrentPosition(
      handleGpsSuccess,
      handleGpsError,
      {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 0,
      }
    );
  }

  if (currentLocationBtn) {
    currentLocationBtn.disabled = false;
    currentLocationBtn.addEventListener("click", startGpsDetection);
  }

  // --------------------------------------------------------------------------
  // 5. Mode B: Search Farm Location by Name / Village
  // --------------------------------------------------------------------------
  function setSearchStatus(message, type = "info") {
    if (!searchStatus) return;
    searchStatus.classList.remove("d-none", "alert-danger", "alert-warning", "alert-success", "alert-info", "alert-light");
    if (type === "error") {
      searchStatus.classList.add("alert-danger");
    } else if (type === "warning") {
      searchStatus.classList.add("alert-warning");
    } else if (type === "success") {
      searchStatus.classList.add("alert-success");
    } else {
      searchStatus.classList.add("alert-info");
    }
    searchStatus.innerHTML = message;
  }

  async function performLocationSearch() {
    const query = (searchInput ? searchInput.value : "").trim();
    if (!query) {
      setSearchStatus("Please enter a village, town, or district name to search.", "warning");
      if (searchInput) searchInput.focus();
      return;
    }

    const currentReq = ++searchRequestCounter;

    setSearchStatus('<i class="fas fa-spinner fa-spin me-1"></i> Searching for matching locations...', "info");
    if (searchBtn) {
      searchBtn.disabled = true;
      searchBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
    }
    if (searchResultsList) searchResultsList.innerHTML = "";
    if (searchResultsContainer) searchResultsContainer.classList.remove("d-none");

    try {
      const data = await searchLocation(query);

      // Race condition check: ignore if user initiated a newer search
      if (currentReq !== searchRequestCounter) return;

      if (!data || data.success === false) {
        setSearchStatus(data?.error || "Location search failed. Please try again.", "error");
        if (searchResultsList) {
          searchResultsList.innerHTML = `<div class="p-3 text-center text-muted small"><i class="fas fa-exclamation-circle text-danger me-1"></i> ${data?.error || "Unable to search locations."}</div>`;
        }
        return;
      }

      const results = data.results || [];
      if (results.length === 0) {
        setSearchStatus(`No locations found matching "${query}". Please check the spelling or search with district/state.`, "warning");
        if (searchResultsList) {
          searchResultsList.innerHTML = `<div class="p-3 text-center text-muted small"><i class="fas fa-search me-1"></i> No matching locations found for "${query}". Try searching with village and state name.</div>`;
        }
        return;
      }

      setSearchStatus(`Found ${results.length} matching location(s). Select your farm to preview on the map:`, "success");

      if (searchResultsList) {
        results.forEach((item) => {
          const itemEl = document.createElement("div");
          itemEl.className = "search-result-item p-3 border-bottom d-flex justify-content-between align-items-center";
          itemEl.style.cursor = "pointer";

          itemEl.innerHTML = `
            <div class="me-3">
              <div class="fw-bold text-dark"><i class="fas fa-map-pin text-primary me-1"></i> ${item.name}</div>
              <div class="small text-muted text-break">${item.display_name}</div>
              <div class="badge bg-light text-dark border font-monospace mt-1">Lat: ${Number(item.latitude).toFixed(4)}, Lon: ${Number(item.longitude).toFixed(4)}</div>
            </div>
            <button type="button" class="btn btn-sm btn-outline-primary select-location-btn flex-shrink-0">
              <i class="fas fa-check me-1"></i> Select
            </button>
          `;

          itemEl.addEventListener("mouseenter", () => {
            itemEl.style.backgroundColor = "#f0fdf4";
          });
          itemEl.addEventListener("mouseleave", () => {
            if (!itemEl.classList.contains("bg-success-subtle")) {
              itemEl.style.backgroundColor = "";
            }
          });

          itemEl.addEventListener("click", () => {
            document.querySelectorAll(".search-result-item").forEach((el) => {
              el.classList.remove("bg-success-subtle");
              el.style.backgroundColor = "";
            });
            itemEl.classList.add("bg-success-subtle");
            itemEl.style.backgroundColor = "#dcfce7";

            handleCoordinatesSelected(
              item.latitude,
              item.longitude,
              "search",
              null,
              item.name,
              item.display_name,
              item
            );

            setSearchStatus(
              `Selected: <strong>${item.name}</strong>. Please review on the map and click <strong>Confirm & Save This Location</strong> below.`,
              "success"
            );
          });

          searchResultsList.appendChild(itemEl);
        });
      }
    } catch (err) {
      if (currentReq === searchRequestCounter) {
        console.error("Search error:", err);
        setSearchStatus("Network error occurred during location search. Please check your connection.", "error");
      }
    } finally {
      if (currentReq === searchRequestCounter && searchBtn) {
        searchBtn.disabled = false;
        searchBtn.innerHTML = '<i class="fas fa-search me-1"></i> Search';
      }
    }
  }

  if (searchBtn) {
    searchBtn.disabled = false;
    searchBtn.addEventListener("click", performLocationSearch);
  }

  if (searchInput) {
    searchInput.disabled = false;
    searchInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        performLocationSearch();
      }
    });
  }

  // --------------------------------------------------------------------------
  // 6. Unified Coordinates Selection Handler
  // --------------------------------------------------------------------------
  async function handleCoordinatesSelected(
    lat,
    lon,
    source = "search",
    accuracy = null,
    preName = null,
    preDisplay = null,
    extraData = null
  ) {
    const cleanLat = parseFloat(Number(lat).toFixed(6));
    const cleanLon = parseFloat(Number(lon).toFixed(6));

    if (isNaN(cleanLat) || isNaN(cleanLon)) return;
    if (cleanLat < -90 || cleanLat > 90 || cleanLon < -180 || cleanLon > 180) return;

    let resolvedName = preName || `Farm (${cleanLat.toFixed(4)}, ${cleanLon.toFixed(4)})`;
    let resolvedDisplay = preDisplay || `Coordinates: ${cleanLat.toFixed(6)}, ${cleanLon.toFixed(6)}`;
    let revData = extraData || null;

    if (!preName) {
      try {
        if (typeof reverseGeocode === "function") {
          revData = await reverseGeocode(cleanLat, cleanLon);
          if (revData && revData.success) {
            resolvedName = revData.name || resolvedName;
            resolvedDisplay = revData.display_name || resolvedDisplay;
          }
        }
      } catch (err) {
        console.warn("Reverse geocode lookup error:", err);
      }
    }

    pendingLocation = {
      latitude: cleanLat,
      longitude: cleanLon,
      name: resolvedName,
      display_name: resolvedDisplay,
      village: revData?.village || null,
      locality: revData?.locality || resolvedName,
      district: revData?.district || null,
      state: revData?.state || null,
      country: revData?.country || "India",
      postcode: revData?.postcode || null,
      source: source,
      accuracy: accuracy !== null && !isNaN(accuracy) ? Math.round(accuracy) : null,
      confirmed: false,
    };

    displayVerifiedLocation(pendingLocation, false);
    initOrUpdateLeafletMap(cleanLat, cleanLon, resolvedName, source, accuracy);
  }

  // --------------------------------------------------------------------------
  // 7. Confirm & Save Location to Centralized FarmContext & Backend
  // --------------------------------------------------------------------------
  if (confirmLocationBtn) {
    confirmLocationBtn.disabled = false;
    confirmLocationBtn.addEventListener("click", async () => {
      if (!pendingLocation) {
        alert("Please detect your GPS location or search and select a farm location first.");
        return;
      }

      const lat = parseFloat(pendingLocation.latitude);
      const lon = parseFloat(pendingLocation.longitude);

      if (
        isNaN(lat) ||
        isNaN(lon) ||
        lat < -90 ||
        lat > 90 ||
        lon < -180 ||
        lon > 180
      ) {
        alert("Invalid coordinates. Please select a valid farm location.");
        return;
      }

      confirmLocationBtn.disabled = true;
      confirmLocationBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i> Saving Location...';

      try {
        const confirmedLocation = {
          ...pendingLocation,
          latitude: lat,
          longitude: lon,
          confirmed: true,
          confirmed_at: new Date().toISOString(),
        };

        // Persist to FarmState & Backend
        if (window.FarmState && typeof FarmState.setLocation === "function") {
          await FarmState.setLocation(
            lat,
            lon,
            confirmedLocation.name,
            confirmedLocation.source || "GPS",
            confirmedLocation.accuracy
          );
        } else {
          // Direct backend update fallback
          await apiFetch("/api/farm/context/location", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              latitude: lat,
              longitude: lon,
              locality: confirmedLocation.name,
              place_name: confirmedLocation.display_name,
              source: confirmedLocation.source,
              accuracy: confirmedLocation.accuracy,
            }),
          });
        }

        // Save to localStorage for quick restore
        localStorage.setItem("farmLocation", JSON.stringify(confirmedLocation));
        localStorage.setItem("farmLatitude", String(lat));
        localStorage.setItem("farmLongitude", String(lon));
        localStorage.setItem("farmLocationName", confirmedLocation.name);

        pendingLocation = confirmedLocation;
        displayVerifiedLocation(confirmedLocation, true);
        updateTopbar(confirmedLocation.name);
        updateMapReadout(lat, lon, true);
        updateMarker(lat, lon, confirmedLocation.name, confirmedLocation.source, confirmedLocation.accuracy);

        if (confirmationAlert) {
          confirmationAlert.classList.remove("d-none");
          confirmationAlert.innerHTML = `
            <div class="d-flex align-items-center justify-content-between flex-wrap gap-2">
              <div>
                <i class="fas fa-check-circle fs-5 me-2"></i>
                <strong>Farm location confirmed & saved!</strong>
                <div class="small mt-1">Weather, SoilGrids, and Sentinel-2 NDVI modules are now synchronized to <strong>${confirmedLocation.name}</strong> (${lat.toFixed(6)}°, ${lon.toFixed(6)}°).</div>
              </div>
              <div class="d-flex gap-2">
                <a href="weather.html" class="btn btn-sm btn-light text-success fw-bold flex-shrink-0">
                  <i class="fas fa-cloud-sun me-1"></i> View Weather
                </a>
                <a href="satellite.html" class="btn btn-sm btn-light text-success fw-bold flex-shrink-0">
                  <i class="fas fa-satellite me-1"></i> Satellite NDVI
                </a>
              </div>
            </div>
          `;
          confirmationAlert.scrollIntoView({ behavior: "smooth", block: "nearest" });
        }
      } catch (err) {
        console.error("Error saving location:", err);
        alert("Failed to save location to the server. Please try again.");
        confirmLocationBtn.disabled = false;
        confirmLocationBtn.innerHTML = '<i class="fas fa-check me-1"></i> Confirm & Save This Location';
      }
    });
  }

  // Mobile drawer toggle
  const mobileMenuBtn = document.getElementById("mobileMenuBtn");
  const appSidebar = document.getElementById("appSidebar");
  if (mobileMenuBtn && appSidebar) {
    mobileMenuBtn.addEventListener("click", () => {
      appSidebar.classList.toggle("sidebar-open");
    });
  }

  // Initialize
  loadInitialLocation();
});
