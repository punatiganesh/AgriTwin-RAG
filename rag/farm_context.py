"""
AgriTwin-RAG - Centralized Farm Context Data Model & Utilities
Unified schema, validation, sanitation, provenance metadata, and prompt formatting.
"""
from typing import Any, Dict, List, Optional, Tuple


def get_empty_farm_context() -> Dict[str, Any]:
    """
    Returns the standard centralized FarmContext structure with null/empty values.
    """
    return {
        "farm_id": None,
        "location": {
            "latitude": None,
            "longitude": None,
            "village": None,
            "district": None,
            "state": None,
            "country": None,
            "place_name": None,
            "source": None,
        },
        "crop": {
            "name": None,
            "variety": None,
            "growth_stage": None,
            "sowing_date": None,
            "area_acres": None,
        },
        "weather": {
            "temperature": None,
            "humidity": None,
            "rainfall": None,
            "wind_speed": None,
            "pressure": None,
            "weather_condition": None,
            "timestamp": None,
            "source": None,
        },
        "soil": {
            "soil_type": None,
            "ph": None,
            "moisture": None,
            "nitrogen": None,
            "organic_carbon": None,
            "sand": None,
            "silt": None,
            "clay": None,
            "cec": None,
            "bulk_density": None,
            "source": None,
            "timestamp": None,
        },
        "satellite": {
            "ndvi": None,
            "B04": None,
            "B08": None,
            "red_band": None,
            "nir_band": None,
            "red_reflectance": None,
            "nir_reflectance": None,
            "acquisition_date": None,
            "cloud_cover": None,
            "vegetation_status": None,
            "source": None,
        },
        "prediction": {
            "water_stress": None,
            "disease_risk": None,
            "yield": None,
            "confidence": None,
            "model_name": None,
        },
    }


def sanitize_farm_context(raw_context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Sanitize and validate incoming farm context against the standard schema.
    Guarantees all keys exist, retains valid types, and leaves missing data as None.
    Never invents fake values.
    """
    standard = get_empty_farm_context()
    if not raw_context or not isinstance(raw_context, dict):
        return standard

    # 0. Farm ID
    if "farm_id" in raw_context and raw_context["farm_id"] is not None:
        standard["farm_id"] = str(raw_context["farm_id"]).strip() or None

    # 1. Location
    raw_loc = raw_context.get("location")
    if isinstance(raw_loc, dict):
        lat = raw_loc.get("latitude") or raw_loc.get("lat")
        lon = raw_loc.get("longitude") or raw_loc.get("lon") or raw_loc.get("lng")
        name = raw_loc.get("place_name") or raw_loc.get("name") or raw_loc.get("display_name")
        src = raw_loc.get("source")
        village = raw_loc.get("village")
        district = raw_loc.get("district")
        state_name = raw_loc.get("state")
        country = raw_loc.get("country")

        try:
            standard["location"]["latitude"] = float(lat) if lat is not None else None
        except (ValueError, TypeError):
            standard["location"]["latitude"] = None

        try:
            standard["location"]["longitude"] = float(lon) if lon is not None else None
        except (ValueError, TypeError):
            standard["location"]["longitude"] = None

        standard["location"]["place_name"] = str(name).strip() if name is not None and str(name).strip() else None
        standard["location"]["village"] = str(village).strip() if village is not None and str(village).strip() else None
        standard["location"]["district"] = str(district).strip() if district is not None and str(district).strip() else None
        standard["location"]["state"] = str(state_name).strip() if state_name is not None and str(state_name).strip() else None
        standard["location"]["country"] = str(country).strip() if country is not None and str(country).strip() else None
        standard["location"]["source"] = str(src).strip() if src is not None and str(src).strip() else None
    elif isinstance(raw_loc, str) and raw_loc.strip():
        standard["location"]["place_name"] = raw_loc.strip()

    # Top-level location fallback
    if standard["location"]["latitude"] is None and "latitude" in raw_context:
        try:
            standard["location"]["latitude"] = float(raw_context["latitude"]) if raw_context["latitude"] is not None else None
        except (ValueError, TypeError):
            pass
    if standard["location"]["longitude"] is None and "longitude" in raw_context:
        try:
            standard["location"]["longitude"] = float(raw_context["longitude"]) if raw_context["longitude"] is not None else None
        except (ValueError, TypeError):
            pass

    # 2. Crop & Growth Stage
    raw_crop = raw_context.get("crop")
    if isinstance(raw_crop, dict):
        c_name = raw_crop.get("name") or raw_crop.get("crop_name") or raw_crop.get("crop")
        variety = raw_crop.get("variety")
        growth_stage = raw_crop.get("growth_stage") or raw_crop.get("stage")
        sowing_date = raw_crop.get("sowing_date") or raw_crop.get("sowingDate")
        area = raw_crop.get("area_acres") or raw_crop.get("area")

        standard["crop"]["name"] = str(c_name).strip() if c_name is not None and str(c_name).strip() else None
        standard["crop"]["variety"] = str(variety).strip() if variety is not None and str(variety).strip() else None
        standard["crop"]["growth_stage"] = str(growth_stage).strip() if growth_stage is not None and str(growth_stage).strip() else None
        standard["crop"]["sowing_date"] = str(sowing_date).strip() if sowing_date is not None and str(sowing_date).strip() else None
        if area is not None:
            try:
                standard["crop"]["area_acres"] = float(area)
            except (ValueError, TypeError):
                standard["crop"]["area_acres"] = None
    elif isinstance(raw_crop, str) and raw_crop.strip():
        standard["crop"]["name"] = raw_crop.strip()

    # Top-level crop name fallback
    if not standard["crop"]["name"] and "crop_name" in raw_context:
        standard["crop"]["name"] = str(raw_context["crop_name"]).strip() or None

    # Top-level growth_stage fallback
    if not standard["crop"]["growth_stage"]:
        top_stage = raw_context.get("growth_stage") or raw_context.get("stage") or raw_context.get("crop_stage")
        if top_stage and str(top_stage).strip():
            standard["crop"]["growth_stage"] = str(top_stage).strip()

    # 3. Weather
    raw_weather = raw_context.get("weather")
    if isinstance(raw_weather, dict):
        for num_field in ("temperature", "humidity", "rainfall", "wind_speed", "pressure"):
            val = raw_weather.get(num_field)
            if val is not None:
                try:
                    standard["weather"][num_field] = float(val) if "." in str(val) else int(val)
                except (ValueError, TypeError):
                    standard["weather"][num_field] = None

        cond = raw_weather.get("weather_condition") or raw_weather.get("condition") or raw_weather.get("description")
        standard["weather"]["weather_condition"] = str(cond).strip() if cond is not None and str(cond).strip() else None
        ts = raw_weather.get("timestamp") or raw_weather.get("dt")
        standard["weather"]["timestamp"] = str(ts).strip() if ts is not None and str(ts).strip() else None
        w_src = raw_weather.get("source")
        standard["weather"]["source"] = str(w_src).strip() if w_src is not None and str(w_src).strip() else "OpenWeather"

    # Top-level weather field fallbacks
    for fld in ("temperature", "humidity", "rainfall", "wind_speed", "pressure"):
        if standard["weather"][fld] is None and fld in raw_context and raw_context[fld] is not None:
            try:
                standard["weather"][fld] = float(raw_context[fld]) if "." in str(raw_context[fld]) else int(raw_context[fld])
            except (ValueError, TypeError):
                pass

    # 4. Soil
    raw_soil = raw_context.get("soil")
    if isinstance(raw_soil, dict):
        st = raw_soil.get("soil_type") or raw_soil.get("texture_class")
        standard["soil"]["soil_type"] = str(st).strip() if st is not None and str(st).strip() else None

        for num_field in ("ph", "moisture", "nitrogen", "organic_carbon", "sand", "silt", "clay", "cec", "bulk_density"):
            val = raw_soil.get(num_field)
            if val is not None:
                try:
                    standard["soil"][num_field] = float(val) if "." in str(val) else int(val)
                except (ValueError, TypeError):
                    standard["soil"][num_field] = None

        s_src = raw_soil.get("source")
        standard["soil"]["source"] = str(s_src).strip() if s_src is not None and str(s_src).strip() else "ISRIC SoilGrids 2.0"
        s_ts = raw_soil.get("timestamp")
        standard["soil"]["timestamp"] = str(s_ts).strip() if s_ts is not None and str(s_ts).strip() else None

    # Top-level soil moisture fallback
    if standard["soil"]["moisture"] is None:
        sm = raw_context.get("soil_moisture") or raw_context.get("moisture")
        if sm is not None:
            try:
                standard["soil"]["moisture"] = float(sm) if "." in str(sm) else int(sm)
            except (ValueError, TypeError):
                pass

    # 5. Satellite / NDVI
    raw_sat = raw_context.get("satellite")
    if isinstance(raw_sat, dict):
        ndvi_val = raw_sat.get("ndvi")
        if ndvi_val is not None:
            try:
                standard["satellite"]["ndvi"] = round(float(ndvi_val), 4)
            except (ValueError, TypeError):
                standard["satellite"]["ndvi"] = None

        b04_val = raw_sat.get("B04") or raw_sat.get("red_band") or raw_sat.get("red_reflectance") or raw_sat.get("red")
        if b04_val is not None:
            try:
                b04_num = round(float(b04_val), 4)
                standard["satellite"]["B04"] = b04_num
                standard["satellite"]["red_band"] = b04_num
                standard["satellite"]["red_reflectance"] = b04_num
            except (ValueError, TypeError):
                pass

        b08_val = raw_sat.get("B08") or raw_sat.get("nir_band") or raw_sat.get("nir_reflectance") or raw_sat.get("nir")
        if b08_val is not None:
            try:
                b08_num = round(float(b08_val), 4)
                standard["satellite"]["B08"] = b08_num
                standard["satellite"]["nir_band"] = b08_num
                standard["satellite"]["nir_reflectance"] = b08_num
            except (ValueError, TypeError):
                pass

        acq = raw_sat.get("acquisition_date") or raw_sat.get("acq_date") or raw_sat.get("acquisition_datetime")
        standard["satellite"]["acquisition_date"] = str(acq).strip() if acq is not None and str(acq).strip() else None

        cloud = raw_sat.get("cloud_cover") or raw_sat.get("cloud_percentage")
        if cloud is not None:
            try:
                standard["satellite"]["cloud_cover"] = round(float(cloud), 2)
            except (ValueError, TypeError):
                standard["satellite"]["cloud_cover"] = None

        veg_stat = raw_sat.get("vegetation_status") or raw_sat.get("vegetation_condition")
        standard["satellite"]["vegetation_status"] = str(veg_stat).strip() if veg_stat is not None and str(veg_stat).strip() else None

        sat_src = raw_sat.get("source")
        standard["satellite"]["source"] = str(sat_src).strip() if sat_src is not None and str(sat_src).strip() else "Sentinel-2 Level-2A"

    # Top-level NDVI fallback
    if standard["satellite"]["ndvi"] is None and "ndvi" in raw_context and raw_context["ndvi"] is not None:
        try:
            standard["satellite"]["ndvi"] = round(float(raw_context["ndvi"]), 4)
        except (ValueError, TypeError):
            pass

    # 6. Prediction
    raw_pred = raw_context.get("prediction")
    if isinstance(raw_pred, dict):
        standard["prediction"]["water_stress"] = raw_pred.get("water_stress")
        standard["prediction"]["disease_risk"] = raw_pred.get("disease_risk")
        standard["prediction"]["yield"] = raw_pred.get("yield")
        standard["prediction"]["confidence"] = raw_pred.get("confidence")
        standard["prediction"]["model_name"] = raw_pred.get("model_name") or "Biophysical Heuristic Engine"

    return standard


def has_meaningful_farm_context(context: Optional[Dict[str, Any]]) -> bool:
    """
    Check if at least one meaningful farm context field is populated.
    """
    if not context or not isinstance(context, dict):
        return False

    for section_key, section_val in context.items():
        if isinstance(section_val, dict):
            for _, v in section_val.items():
                if v is not None and str(v).strip() not in ("", "Not available", "null", "None", "Unknown"):
                    return True
        elif section_val is not None and str(section_val).strip() not in ("", "Not available", "null", "None", "Unknown"):
            return True
    return False


def get_available_context_fields(context: Optional[Dict[str, Any]]) -> Dict[str, list]:
    """
    Return a map of sections and their populated field names for safe logging.
    """
    if not context or not isinstance(context, dict):
        return {}

    available = {}
    for section_key, section_val in context.items():
        if isinstance(section_val, dict):
            populated = [
                k for k, v in section_val.items()
                if v is not None and str(v).strip() not in ("", "Not available", "null", "None", "Unknown")
            ]
            if populated:
                available[section_key] = populated
    return available


def get_data_provenance(context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Generate transparent data provenance metadata for every major parameter.
    Types: REAL, USER_PROVIDED, CALCULATED, MODEL_PREDICTED, RAG_RETRIEVED, SIMULATED, UNAVAILABLE
    """
    ctx = sanitize_farm_context(context)
    provenance = {}

    # Location
    loc = ctx.get("location", {})
    if loc.get("latitude") is not None and loc.get("longitude") is not None:
        src = loc.get("source") or "Browser GPS"
        is_real = any(k in str(src).lower() for k in ("gps", "browser", "nominatim", "geocoded", "reverse"))
        loc_desc = []
        if loc.get("place_name"):
            loc_desc.append(loc["place_name"])
        elif loc.get("village") or loc.get("district") or loc.get("state"):
            parts = [loc.get("village"), loc.get("district"), loc.get("state"), loc.get("country")]
            loc_desc.append(", ".join([p for p in parts if p]))
        loc_desc.append(f"({loc['latitude']}, {loc['longitude']})")

        provenance["location"] = {
            "value": " ".join(loc_desc),
            "village": loc.get("village"),
            "district": loc.get("district"),
            "state": loc.get("state"),
            "country": loc.get("country"),
            "latitude": loc.get("latitude"),
            "longitude": loc.get("longitude"),
            "source": src,
            "type": "REAL" if is_real else "USER_PROVIDED",
        }
    else:
        provenance["location"] = {"value": None, "source": "Not configured", "type": "UNAVAILABLE"}

    # Crop
    crop = ctx.get("crop", {})
    if crop.get("name"):
        provenance["crop"] = {
            "value": f"{crop['name']} ({crop.get('variety') or 'Standard'}) - {crop.get('growth_stage') or 'Stage unspecified'}",
            "name": crop.get("name"),
            "variety": crop.get("variety"),
            "growth_stage": crop.get("growth_stage"),
            "area_acres": crop.get("area_acres"),
            "sowing_date": crop.get("sowing_date"),
            "source": "Farmer Configuration / Profile",
            "type": "USER_PROVIDED",
        }
    else:
        provenance["crop"] = {"value": None, "source": "Farmer Configuration", "type": "UNAVAILABLE"}

    # Weather
    weather = ctx.get("weather", {})
    if weather.get("temperature") is not None:
        provenance["weather"] = {
            "value": f"{weather['temperature']}°C, {weather.get('humidity')}% RH, {weather.get('rainfall')} mm rain, {weather.get('wind_speed')} m/s wind",
            "temperature": weather.get("temperature"),
            "humidity": weather.get("humidity"),
            "rainfall": weather.get("rainfall"),
            "wind_speed": weather.get("wind_speed"),
            "pressure": weather.get("pressure"),
            "condition": weather.get("weather_condition"),
            "source": weather.get("source") or "OpenWeather",
            "timestamp": weather.get("timestamp"),
            "type": "REAL",
        }
    else:
        provenance["weather"] = {"value": None, "source": "OpenWeather", "type": "UNAVAILABLE"}

    # Soil
    soil = ctx.get("soil", {})
    if soil.get("ph") is not None or soil.get("moisture") is not None:
        provenance["soil"] = {
            "value": f"pH: {soil.get('ph')}, Moisture: {soil.get('moisture')}%, Texture: {soil.get('soil_type')}, N: {soil.get('nitrogen')} g/kg, SOC: {soil.get('organic_carbon')} g/kg",
            "soil_type": soil.get("soil_type"),
            "ph": soil.get("ph"),
            "moisture": soil.get("moisture"),
            "nitrogen": soil.get("nitrogen"),
            "organic_carbon": soil.get("organic_carbon"),
            "sand": soil.get("sand"),
            "silt": soil.get("silt"),
            "clay": soil.get("clay"),
            "cec": soil.get("cec"),
            "bulk_density": soil.get("bulk_density"),
            "source": soil.get("source") or "ISRIC SoilGrids 2.0",
            "type": "REAL",
            "soil_type_type": "CALCULATED" if soil.get("soil_type") else "UNAVAILABLE",
        }
    else:
        provenance["soil"] = {"value": None, "source": "ISRIC SoilGrids 2.0", "type": "UNAVAILABLE"}

    # Satellite
    sat = ctx.get("satellite", {})
    if sat.get("ndvi") is not None or sat.get("B04") is not None:
        provenance["satellite"] = {
            "value": f"NDVI: {sat.get('ndvi')}, B04 (Red): {sat.get('B04')}, B08 (NIR): {sat.get('B08')}, Cloud: {sat.get('cloud_cover')}%, Acquired: {sat.get('acquisition_date')}",
            "ndvi": sat.get("ndvi"),
            "B04": sat.get("B04") or sat.get("red_band"),
            "B08": sat.get("B08") or sat.get("nir_band"),
            "acquisition_date": sat.get("acquisition_date"),
            "cloud_cover": sat.get("cloud_cover"),
            "vegetation_status": sat.get("vegetation_status"),
            "source": sat.get("source") or "Sentinel-2 Level-2A",
            "type": "REAL",
            "ndvi_type": "CALCULATED",
        }
    else:
        provenance["satellite"] = {"value": None, "source": "Sentinel-2 Level-2A", "type": "UNAVAILABLE"}

    # Prediction
    pred = ctx.get("prediction", {})
    if pred.get("water_stress") is not None:
        provenance["prediction"] = {
            "value": f"Water Stress: {pred.get('water_stress')}",
            "source": pred.get("model_name") or "Biophysical Risk Assessment Engine",
            "type": "CALCULATED",
        }
    else:
        provenance["prediction"] = {"value": None, "source": "Biophysical Risk Assessment Engine", "type": "UNAVAILABLE"}

    return provenance


def format_location_str(loc: Dict[str, Any]) -> str:
    parts = []
    if loc.get("place_name"):
        parts.append(f"Place: {loc['place_name']}")
    if loc.get("latitude") is not None and loc.get("longitude") is not None:
        parts.append(f"Coordinates: ({loc['latitude']}, {loc['longitude']})")
    if loc.get("source"):
        parts.append(f"Source: {loc['source']}")
    return ", ".join(parts) if parts else "Not available"


def format_crop_str(crop: Dict[str, Any]) -> str:
    parts = []
    if crop.get("name"):
        parts.append(f"Name: {crop['name']}")
    if crop.get("variety"):
        parts.append(f"Variety: {crop['variety']}")
    if crop.get("area_acres") is not None:
        parts.append(f"Area: {crop['area_acres']} acres")
    if crop.get("sowing_date"):
        parts.append(f"Sown: {crop['sowing_date']}")
    return ", ".join(parts) if parts else "Not available"


def format_growth_stage_str(crop: Dict[str, Any]) -> str:
    return crop.get("growth_stage") or "Not available"


def format_weather_str(weather: Dict[str, Any]) -> str:
    parts = []
    if weather.get("temperature") is not None:
        parts.append(f"Temperature: {weather['temperature']}°C")
    if weather.get("humidity") is not None:
        parts.append(f"Humidity: {weather['humidity']}%")
    if weather.get("rainfall") is not None:
        parts.append(f"Rainfall: {weather['rainfall']} mm")
    if weather.get("wind_speed") is not None:
        parts.append(f"Wind Speed: {weather['wind_speed']} m/s")
    if weather.get("pressure") is not None:
        parts.append(f"Pressure: {weather['pressure']} hPa")
    if weather.get("weather_condition"):
        parts.append(f"Condition: {weather['weather_condition']}")
    if weather.get("source"):
        parts.append(f"Source: {weather['source']}")
    return ", ".join(parts) if parts else "Not available"


def format_soil_str(soil: Dict[str, Any]) -> str:
    parts = []
    if soil.get("soil_type"):
        parts.append(f"Soil Type: {soil['soil_type']}")
    if soil.get("ph") is not None:
        parts.append(f"pH: {soil['ph']}")
    if soil.get("moisture") is not None:
        parts.append(f"Moisture: {soil['moisture']}% (33 kPa Field Capacity)")
    if soil.get("organic_carbon") is not None:
        parts.append(f"Organic Carbon: {soil['organic_carbon']} g/kg")
    if soil.get("nitrogen") is not None:
        parts.append(f"Total Nitrogen: {soil['nitrogen']} g/kg")
    if soil.get("source"):
        parts.append(f"Source: {soil['source']}")
    return ", ".join(parts) if parts else "Not available"


def format_satellite_str(satellite: Dict[str, Any]) -> str:
    parts = []
    if satellite.get("ndvi") is not None:
        parts.append(f"NDVI: {satellite['ndvi']}")
    if satellite.get("vegetation_status"):
        parts.append(f"Vegetation Status: {satellite['vegetation_status']}")
    if satellite.get("acquisition_date"):
        parts.append(f"Acquisition Date: {satellite['acquisition_date']}")
    if satellite.get("source"):
        parts.append(f"Source: {satellite['source']}")
    return ", ".join(parts) if parts else "Not available"


def format_farm_context_block(context: Optional[Dict[str, Any]]) -> Tuple[str, bool]:
    """
    Format FarmContext into the exact structured format for Groq LLM prompt.
    Returns (formatted_string, is_context_used).
    """
    sanitized = sanitize_farm_context(context)
    has_ctx = has_meaningful_farm_context(sanitized)

    loc = sanitized.get("location", {})
    crop = sanitized.get("crop", {})
    w = sanitized.get("weather", {})
    s = sanitized.get("soil", {})
    sat = sanitized.get("satellite", {})

    lines = []

    # Location
    loc_parts = []
    if loc.get("place_name"):
        loc_parts.append(loc["place_name"])
    elif loc.get("city"):
        loc_parts.append(f"{loc['city']}, {loc.get('country', 'IN')}")
    elif loc.get("village") or loc.get("district") or loc.get("state"):
        p = [loc.get("village"), loc.get("district"), loc.get("state"), loc.get("country")]
        loc_parts.append(", ".join([x for x in p if x]))
    if loc.get("latitude") is not None and loc.get("longitude") is not None:
        loc_parts.append(f"({loc['latitude']:.4f}, {loc['longitude']:.4f})")
    loc_str = " ".join(loc_parts) if loc_parts else "Unavailable (No farm coordinates configured)"
    lines.append(f"Location: {loc_str}")

    # Crop
    lines.append(f"Crop: {crop.get('name') or 'Rice'}")
    if crop.get("variety"):
        lines.append(f"Variety: {crop['variety']}")
    lines.append(f"Growth Stage: {crop.get('growth_stage') or 'Not specified in farm profile'}")

    # Weather
    if w.get("temperature") is not None:
        lines.append(f"Temperature: {w['temperature']}°C")
    else:
        lines.append("Temperature: Unavailable (No farm coordinates configured)")
    if w.get("humidity") is not None:
        lines.append(f"Humidity: {w['humidity']}%")
    if w.get("rainfall") is not None:
        lines.append(f"Rainfall: {w['rainfall']} mm")
    if w.get("wind_speed") is not None:
        lines.append(f"Wind Speed: {w['wind_speed']} m/s")
    if w.get("weather_condition"):
        lines.append(f"Weather Condition: {w['weather_condition']}")
    if w.get("timestamp"):
        lines.append(f"Weather Observation Time: {w['timestamp']}")

    # Soil
    if s.get("moisture") is not None:
        lines.append(f"Soil Moisture: {s['moisture']}%")
    if s.get("soil_type"):
        lines.append(f"Soil Type: {s['soil_type']}")
    if s.get("ph") is not None:
        lines.append(f"pH: {s['ph']}")
    if s.get("organic_carbon") is not None:
        lines.append(f"Organic Carbon: {s['organic_carbon']} g/kg")
    if s.get("nitrogen") is not None:
        lines.append(f"Total Nitrogen: {s['nitrogen']} g/kg")

    # Satellite
    if sat.get("ndvi") is not None:
        lines.append(f"NDVI: {sat['ndvi']}")
    if sat.get("B04") is not None:
        lines.append(f"B04 (Red Band): {sat['B04']}")
    if sat.get("B08") is not None:
        lines.append(f"B08 (NIR Band): {sat['B08']}")
    if sat.get("acquisition_date"):
        lines.append(f"Satellite Acquisition Date: {sat['acquisition_date']}")
    if sat.get("cloud_cover") is not None:
        lines.append(f"Cloud Cover: {sat['cloud_cover']}%")
    if sat.get("vegetation_status"):
        lines.append(f"Vegetation Status: {sat['vegetation_status']}")

    block = "\n".join(lines)
    return block, has_ctx


def format_selective_farm_context_block(
    context: Optional[Dict[str, Any]],
    active_intents: Optional[List[str]] = None
) -> Tuple[str, bool]:
    """
    Format all relevant farm telemetry clearly for the LLM prompt.
    """
    return format_farm_context_block(context)


