"""
AgriTwin-RAG — Intelligent Query Understanding & Intent Router
Classifies user agricultural queries into one or more data source categories:
- WEATHER: Live temperature, rainfall, humidity, wind, forecast, heat, cold, ambient conditions
- SOIL: Soil moisture, pH, nitrogen, phosphorus, potassium, texture, fertility, soil suitability
- SATELLITE: Sentinel-2 NDVI, canopy greenness, spectral vigor, spatial crop stress/health
- LOCATION: Farm location, coordinates, GPS position, place name
- CROP: Crop name, variety, sowing date, phenological stage
- RAG: ICAR agricultural practices, fertilizer rates, disease/pest management, agronomic guidance

Supports:
1. Single direct telemetry (e.g. WEATHER, SOIL, SATELLITE, LOCATION -> direct deterministic response)
2. Multi-source combinations (e.g. WEATHER + CROP + RAG, SOIL + WEATHER + RAG, SATELLITE + WEATHER + SOIL + RAG)
3. Multilingual queries in English, Telugu (తెలుగు), and Tamil (தமிழ்)
"""
import re
from typing import Any, Dict, List, Optional


# Regex Patterns for Direct Single-Telemetry Inquiries (Zero LLM Hallucination Path)
DIRECT_TELEMETRY_PATTERNS = {
    "temperature": [
        r"^what is (the |my )?(current |today'?s )?(weather )?(temperature|temp)(\s+(at|on|in)\s+(my|the)?\s*farm)?\??$",
        r"^what'?s (the |my )?(current |today'?s )?(weather )?(temperature|temp)(\s+(at|on|in)\s+(my|the)?\s*farm)?\??$",
        r"^give me (my |the )?(current )?(weather )?(temperature|temp)(\s+(at|on|in)\s+(my|the)?\s*farm)?\??$",
        r"^tell me (my |the )?(current )?(weather )?(temperature|temp)(\s+(at|on|in)\s+(my|the)?\s*farm)?\??$",
        r"^current (weather )?temperature(\s+(at|on|in)\s+(my|the)?\s*farm)?\??$",
        r"^today'?s temperature(\s+(at|on|in)\s+(my|the)?\s*farm)?\??$",
        r"^(what is|give me|tell me)\s+(the |my )?temperature(\s+(at|on|in)\s+(my|the)?\s*farm)?\??$",
        # Telugu
        r"ప్రస్తుత ఉష్ణోగ్రత", r"ఉష్ణోగ్రత ఎంత",
        # Tamil
        r"தற்போதைய வெப்பநிலை", r"வெப்பநிலை என்ன",
        # Hindi
        r"वर्तमान तापमान", r"तापमान कितना है", r"मौसम का तापमान", r"आज का तापमान"
    ],
    "humidity": [
        r"^what is (the |my )?(current |today'?s )?humidity(\s+(at|on|in)\s+(my|the)?\s*farm)?\??$",
        r"^what'?s (the |my )?(current |today'?s )?humidity(\s+(at|on|in)\s+(my|the)?\s*farm)?\??$",
        r"^tell me (my |the )?(current )?humidity(\s+(at|on|in)\s+(my|the)?\s*farm)?\??$",
        r"^give me (my |the )?(current )?humidity(\s+(at|on|in)\s+(my|the)?\s*farm)?\??$",
        r"^current humidity(\s+(at|on|in)\s+(my|the)?\s*farm)?\??$",
        r"^today'?s humidity(\s+(at|on|in)\s+(my|the)?\s*farm)?\??$",
        # Telugu
        r"ప్రస్తుత తేమ", r"గాలిలో తేమ ఎంత",
        # Tamil
        r"தற்போதைய ஈரப்பதம்", r"ஈரப்பதம் என்ன",
        # Hindi
        r"वर्तमान नमी", r"हवा में नमी", r"आर्द्रता कितनी है", r"नमी कितनी है"
    ],
    "rainfall": [
        r"^what is (the |my )?(current |today'?s )?(rainfall|rain)(\s+(at|on|in)\s+(my|the)?\s*farm)?\??$",
        r"^what'?s (the |my )?(current |today'?s )?(rainfall|rain)(\s+(at|on|in)\s+(my|the)?\s*farm)?\??$",
        r"^how much did it rain( today)?(\s+(at|on|in)\s+(my|the)?\s*farm)?\??$",
        r"^is it raining(\s+(at|on|in)\s+(my|the)?\s*farm)?\??$",
        r"^will it rain( today)?(\s+(at|on|in)\s+(my|the)?\s*farm)?\??$",
        r"^current rainfall(\s+(at|on|in)\s+(my|the)?\s*farm)?\??$",
        # Telugu
        r"వర్షపాతం ఎంత", r"వర్షం పడిందా",
        # Tamil
        r"மழை அளவு என்ன", r"மழை பெய்கிறதா",
        # Hindi
        r"बारिश कितनी हुई", r"क्या बारिश होगी", r"वर्तमान वर्षा", r"वर्षा कितनी है"
    ],
    "weather_summary": [
        r"^what is (the |my )?(current |today'?s )?weather(\s+(at|on|in)\s+(my|the)?\s*farm)?\??$",
        r"^what'?s (the |my )?(current |today'?s )?weather(\s+(at|on|in)\s+(my|the)?\s*farm)?\??$",
        r"^how is (the )?weather( today| now)?(\s+(at|on|in)\s+(my|the)?\s*farm)?\??$",
        r"^tell me (the |my )?weather(\s+(at|on|in)\s+(my|the)?\s*farm)?\??$",
        r"^give me (the |my )?weather(\s+(at|on|in)\s+(my|the)?\s*farm)?\??$",
        r"^current weather(\s+(at|on|in)\s+(my|the)?\s*farm)?\??$",
        # Telugu
        r"వాతావరణం ఎలా ఉంది", r"వాతావరణం ఏమిటి", r"వాతావరణ వివరాలు", r"ప్రస్తుత వాతావరణం",
        # Tamil
        r"வானிலை எப்படி உள்ளது", r"வானிலை எப்படி இருக்கிறது", r"வானிலை என்ன", r"வானிலை நிலவரம்", r"தற்போதைய வானிலை",
        # Hindi
        r"मौसम कैसा है", r"वर्तमान मौसम", r"आज का मौसम", r"मौसम की जानकारी"
    ],
    "location": [
        r"^where is my farm\??$",
        r"^where is my field\??$",
        r"^what is my (farm )?location\??$",
        r"^where am i\??$",
        r"^show (my )?(farm )?(location|coordinates|gps)\??$",
        r"^what are my (farm )?coordinates\??$",
        # Telugu
        r"నా పొలం ఎక్కడ ఉంది", r"పొలం లొకేషన్",
        # Tamil
        r"என் பண்ணை எங்கே உள்ளது", r"பண்ணை இருப்பிடம்",
        # Hindi
        r"मेरा खेत कहाँ है", r"खेत का स्थान", r"खेत की लोकेशन"
    ],
    "soil_moisture": [
        r"^what is (the |my )?(current |latest |today'?s )?soil moisture\??$",
        r"^what'?s (the |my )?(current |latest |today'?s )?soil moisture\??$",
        r"^tell me (my |the )?(current |latest )?soil moisture\??$",
        r"^current soil moisture\??$",
        r"^latest soil moisture\??$",
        # Telugu
        r"నేల తేమ ఎంత", r"మట్టిలో తేమ ఎంత",
        # Tamil
        r"மண் ஈரப்பதம் என்ன",
        # Hindi
        r"मिट्टी की नमी", r"मृदा नमी कितनी है", r"खेत की मिट्टी में नमी"
    ],
    "soil_ph": [
        r"^what is (the |my )?(current |latest )?soil ph\??$",
        r"^what'?s (the |my )?(current |latest )?soil ph\??$",
        r"^tell me (my |the )?(current |latest )?soil ph\??$",
        r"^current soil ph\??$",
        r"^latest soil ph\??$",
        # Telugu
        r"నేల పిహెచ్ ఎంత", r"మట్టి పిహెచ్",
        # Tamil
        r"மண் கார அமிலத்தன்மை என்ன", r"மண் ph என்ன",
        # Hindi
        r"मिट्टी का पीएच", r"मृदा पीएच कितना है", r"मिट्टी का ph"
    ],
    "ndvi": [
        r"^what is (the |my )?(current |latest )?ndvi\??$",
        r"^what'?s (the |my )?(current |latest )?ndvi\??$",
        r"^tell me (my |the )?(latest )?ndvi\??$",
        r"^latest ndvi\??$",
        r"^current ndvi\??$",
        # Telugu
        r"ఎన్‌డివిఐ ఎంత",
        # Tamil
        r"என்டிவிஐ என்ன",
        # Hindi
        r"एनडीवीआई कितना है", r"वर्तमान एनडीवीआई", r"खेत का एनडीवीआई"
    ],
    "satellite_date": [
        r"^what is the observation date of (my |the )?(latest )?satellite (data|image|observation)\??$",
        r"^when was (the |my )?(latest )?satellite (data|image|observation|ndvi) (taken|observed|acquired)\??$",
        r"^what is the latest satellite image of my field\??$",
        r"^satellite observation date\??$",
        # Telugu
        r"శాటిలైట్ డేటా తేదీ ఏమిటి",
        # Tamil
        r"செயற்கைக்கோள் பதிவு தேதி என்ன",
        # Hindi
        r"सैटेलाइट डेटा की तारीख", r"उपग्रह डेटा तारीख"
    ]
}

# Domain Topic Matchers
WEATHER_PATTERNS = [
    r"\btemp\b", r"\btemperature\b", r"\bheat\b", r"\bcold\b", r"\bweather\b",
    r"\brain\b", r"\brainfall\b", r"\bhumid\b", r"\bhumidity\b", r"\bwind\b",
    r"\bforecast\b", r"\bclimate\b", r"\bhot\b", r"\bsunny\b", r"\bcloudy\b",
    r"\bstorm\b", r"\bprecipitation\b", r"\bdegree\b", r"\b°c\b", r"\bcelsius\b",
    r"ఉష్ణోగ్రత", r"వాతావరణం", r"వర్షం", r"తేమ", r"గాలి", r"ఎండ",
    r"வெப்பநிலை", r"வானிலை", r"மழை", r"ஈரப்பதம்", r"காற்று",
    r"तापमान", r"मौसम", r"बारिश", r"वर्षा", r"आर्द्रता", r"नमी", r"हवा", r"गर्मी", r"ठंड"
]

SOIL_PATTERNS = [
    r"\bsoil\b", r"\bmoisture\b", r"\bph\b", r"\bnitrogen\b", r"\bphosphorus\b",
    r"\bpotassium\b", r"\bnpk\b", r"\bfertility\b", r"\brhizosphere\b",
    r"\bclay\b", r"\bsand\b", r"\bloam\b", r"\bcarbon\b", r"\borganic carbon\b",
    r"\bsoil condition\b", r"\bsoil health\b", r"\bsoil moisture\b", r"\bsoil test\b",
    r"\bsoil suitable\b", r"\bsoil suitability\b", r"\bwater content\b", r"\birrigate\b", r"\birrigation\b",
    r"నేల", r"మట్టి", r"నేల తేమ", r"పిహెచ్", r"సారవంతం",
    r"மண்", r"மண் வளம்", r"மண் ஈரப்பதம்", r"கார அமிலத்தன்மை",
    r"मिट्टी", r"मृदा", r"मिट्टी की नमी", r"पीएच", r"उर्वरता", r"नाइट्रोजन", r"सिंचाई", r"पानी"
]

SATELLITE_PATTERNS = [
    r"\bndvi\b", r"\bsatellite\b", r"\bremote sensing\b", r"\bvegetation\b",
    r"\bvegetation health\b", r"\bcanopy\b", r"\bcanopy vigor\b", r"\bgreenness\b",
    r"\bfield health\b", r"\bspectral\b", r"\bsentinel\b", r"\bb04\b", r"\bb08\b",
    r"\bvegetation stress\b", r"\bspatial\b", r"\bimagery\b", r"\bcrop health\b",
    r"శాటిలైట్", r"ఉపగ్రహం", r"పంట పచ్చదనం", r"ఎన్‌డివిఐ",
    r"செயற்கைக்கோள்", r"பயிர் பசுமை", r"என்டிவிஐ",
    r"सैटेलाइट", r"उपग्रह", r"एनडीवीआई", r"फसल का स्वास्थ्य", r"हरियाली"
]

LOCATION_PATTERNS = [
    r"\bwhere is my farm\b", r"\bwhere is my field\b", r"\bfarm location\b",
    r"\bfield location\b", r"\bcoordinates\b", r"\bgps\b", r"\bwhere am i\b",
    r"నా పొలం ఎక్కడ", r"என் பண்ணை எங்கே",
    r"मेरा खेत कहां", r"मेरा खेत कहाँ", r"खेत का स्थान", r"खेत की लोकेशन"
]

CROP_PATTERNS = [
    r"\bcrop\b", r"\brice\b", r"\bpaddy\b", r"\bvariety\b", r"\bgrowth stage\b",
    r"\bstage\b", r"\bflowering\b", r"\btillering\b", r"\bpanicle\b", r"\byield\b",
    r"పంట", r"వరి", r"பயிர்", r"நெல்",
    r"फसल", r"धान", r"चावल", r"किस्म", r"फूल आने की अवस्था", r"वृद्धि चरण"
]

RAG_KNOWLEDGE_PATTERNS = [
    r"\bmanage\b", r"\bmanagement\b", r"\bpractice\b", r"\bpractices\b",
    r"\bfertilizer\b", r"\bfertiliser\b", r"\bdose\b", r"\bdosage\b", r"\bnutrient\b",
    r"\bpest\b", r"\bdisease\b", r"\binsect\b", r"\bfungus\b", r"\bblight\b", r"\bblast\b",
    r"\bicar\b", r"\bvariety\b", r"\bcultivar\b", r"\byield\b", r"\bsowing\b",
    r"\btransplant\b", r"\bweed\b", r"\bherbicide\b", r"\bpesticide\b",
    r"\bwhat should i do\b", r"\bwhat to do\b", r"\brecommend\b", r"\brecommendation\b",
    r"\bhow to\b", r"\bguidance\b", r"\bguide\b", r"\bwhy is\b", r"\bwhat causes\b",
    r"\bwhat could be the reason\b", r"\bcause\b", r"\baffect\b", r"\bimpact\b",
    r"\birrigate\b", r"\birrigation\b", r"\bsuitable for\b", r"\bsuitability\b",
    r"\bhealthy\b", r"\bstress\b", r"\bdecreased\b", r"\bdecrease\b", r"\bdeclined\b",
    r"\bwater stress\b", r"\bweather stress\b", r"\bheat stress\b",
    r"యాజమాన్యం", r"ఎరువులు", r"పురుగులు", r"తెగుళ్లు", r"సిఫార్సులు", r"ఏమి చేయాలి",
    r"మేలాண்மை", r"உரங்கள்", r"பூச்சிகள்", r"நோய்கள்", r"பரிந்துரைகள்", r"என்ன செய்ய வேண்டும்",
    r"प्रबंधन", r"खाद", r"उर्वरक", r"कीट", r"रोग", r"दवा", r"सिफारिश", r"क्या करना चाहिए", r"उपचार"
]


def match_patterns(text: str, patterns: List[str]) -> bool:
    """Check if any regex pattern matches the lowercase text."""
    lower_text = text.lower().strip()
    for pat in patterns:
        if re.search(pat, lower_text, re.IGNORECASE):
            return True
    return False


def detect_direct_telemetry(query: str) -> Optional[str]:
    """
    Detect if the user query is asking for a direct, simple factual telemetry value.
    If the query asks for agronomic reasoning, impacts, causes, actions, or diagnostic advice,
    returns None to ensure multi-source RAG processing.
    """
    q = query.strip().lower()

    # Guard against advisory/reasoning queries
    advisory_keywords = [
        "affect", "impact", "effect", "stress", "should", "what to do", "why", "how to",
        "cause", "causing", "suitable", "suitability", "manage", "healthy", "health", "guidance",
        "recommend", "decrease", "decreasing", "damage", "remedy", "advisory", "fertilizer",
        "water stress", "weather stress", "irrigate", "irrigation", "condition of my crop"
    ]
    if any(k in q for k in advisory_keywords):
        return None

    for direct_key, patterns in DIRECT_TELEMETRY_PATTERNS.items():
        if match_patterns(q, patterns):
            return direct_key
    return None


def route_query(query: str) -> Dict[str, Any]:
    """
    Analyze user query and return multi-label routing decisions:
    - intents: list of active intents from ['WEATHER', 'SOIL', 'SATELLITE', 'LOCATION', 'CROP', 'RAG']
    - sources: same as intents (standard alias)
    - data_sources: list of source names required
    - rag_required: boolean flag (True if ChromaDB search needed, False to bypass)
    - direct_key: optional direct telemetry key for zero-hallucination deterministic answer
    - retrieval_query: optimized search query for ChromaDB (if rag_required is True)
    - query_type: 'SINGLE_TELEMETRY', 'COMBINED', or 'AGRICULTURAL_KNOWLEDGE'
    """
    if not query or not str(query).strip():
        return {
            "intents": ["RAG"],
            "sources": ["RAG"],
            "data_sources": ["ICAR Knowledge Base (ChromaDB)"],
            "rag_required": True,
            "direct_key": None,
            "retrieval_query": "crop management practices",
            "query_type": "AGRICULTURAL_KNOWLEDGE",
            "reason": "Default empty query routed to general agricultural knowledge."
        }

    q = query.strip()
    q_lower = q.lower()

    # 1. Direct Factual Telemetry Queries (Zero LLM Hallucination Path)
    direct_key = detect_direct_telemetry(q)
    if direct_key:
        if direct_key in ("temperature", "humidity", "rainfall", "weather_summary"):
            return {
                "intents": ["WEATHER"],
                "sources": ["WEATHER"],
                "data_sources": ["OpenWeather API"],
                "rag_required": False,
                "direct_key": direct_key,
                "retrieval_query": None,
                "query_type": "SINGLE_TELEMETRY",
                "reason": f"Direct {direct_key} inquiry: answered directly from verified live weather telemetry."
            }
        elif direct_key in ("soil_moisture", "soil_ph"):
            return {
                "intents": ["SOIL"],
                "sources": ["SOIL"],
                "data_sources": ["ISRIC SoilGrids 2.0"],
                "rag_required": False,
                "direct_key": direct_key,
                "retrieval_query": None,
                "query_type": "SINGLE_TELEMETRY",
                "reason": f"Direct {direct_key} inquiry: answered directly from verified soil telemetry."
            }
        elif direct_key in ("ndvi", "satellite_date"):
            return {
                "intents": ["SATELLITE"],
                "sources": ["SATELLITE"],
                "data_sources": ["Sentinel-2 Level-2A"],
                "rag_required": False,
                "direct_key": direct_key,
                "retrieval_query": None,
                "query_type": "SINGLE_TELEMETRY",
                "reason": "Direct satellite inquiry: answered directly from latest Sentinel-2 observation."
            }
        elif direct_key == "location":
            return {
                "intents": ["LOCATION"],
                "sources": ["LOCATION"],
                "data_sources": ["Selected Farm GPS / Geocoded Coordinates"],
                "rag_required": False,
                "direct_key": direct_key,
                "retrieval_query": None,
                "query_type": "SINGLE_TELEMETRY",
                "reason": "Direct location inquiry: answered directly from active farm coordinates."
            }

    # 2. Multi-Source Domain Matchers
    has_weather = match_patterns(q, WEATHER_PATTERNS)
    has_soil = match_patterns(q, SOIL_PATTERNS)
    has_satellite = match_patterns(q, SATELLITE_PATTERNS)
    has_location = match_patterns(q, LOCATION_PATTERNS)
    has_crop = match_patterns(q, CROP_PATTERNS)
    has_rag = match_patterns(q, RAG_KNOWLEDGE_PATTERNS)

    # 3. Comprehensive & Multi-Source Inquiry Patterns
    # Daily Plan / Action / Monitoring
    if any(k in q_lower for k in [
        "what should i do today", "what to do today", "today's action", "today plan",
        "what should i monitor today", "monitor today", "what to monitor",
        "based on my weather, soil and satellite", "based on my weather, soil, satellite",
        "based on my weather", "ఈ రోజు ఏమి చేయాలి", "ఈ రోజు ఏమి పర్యవేక్షించాలి",
        "இன்று என்ன செய்ய வேண்டும்", "இன்று எதை கண்காணிக்க வேண்டும்",
        "आज क्या करना चाहिए", "आज क्या निगरानी करें", "आज के काम", "खेत में आज क्या करें"
    ]):
        has_weather = True
        has_soil = True
        has_satellite = True
        has_crop = True
        has_rag = True

    # Complete Farm Assessment
    if any(k in q_lower for k in [
        "complete assessment", "complete assessment of my farm", "full assessment",
        "farm assessment", "assessment of my farm", "overall assessment",
        "పొలం పూర్తి వివరాలు", "పొలం పూర్తి సమాచారం",
        "பண்ணையின் முழு மதிப்பீடு",
        "खेत का पूरा आकलन", "खेत का पूरा विश्लेषण", "खेत की पूरी जानकारी"
    ]):
        has_location = True
        has_weather = True
        has_soil = True
        has_satellite = True
        has_crop = True
        has_rag = True

    # Crop Health Assessment
    if any(k in q_lower for k in [
        "current crop health", "crop health", "is my crop healthy", "is my crop currently healthy",
        "crop currently healthy", "how is my crop doing", "crop condition",
        "పంట ఆరోగ్యం", "పంట స్థితి", "பயிர் ஆரோக்கியம்", "பயிர் நிலை",
        "फसल का स्वास्थ्य", "फसल कैसी है", "फसल की स्थिति", "फसल स्वास्थ्य"
    ]):
        has_satellite = True
        has_weather = True
        has_soil = True
        has_crop = True
        has_rag = True

    # Weather Impact on Crop
    if any(k in q_lower for k in [
        "weather affect my crop", "weather affect", "temperature affect my crop",
        "temperature affect", "will the current weather affect", "heat stress",
        "వాతావరణం పంటను ప్రభావితం చేస్తుందా", "ఉష్ణోగ్రత పంటను",
        "வானிலை பயிரை பாதிக்குமா", "வெப்பநிலை பயிரை பாதிக்குமா",
        "मौसम फसल को प्रभावित करेगा", "मौसम का प्रभाव", "तापमान का प्रभाव", "गर्मी का असर"
    ]):
        has_weather = True
        has_crop = True
        has_rag = True

    # Low Soil Moisture & Irrigation Decision
    if any(k in q_lower for k in [
        "soil moisture is low", "moisture is low", "soil is dry", "should i irrigate",
        "should i water", "irrigate based on", "water my field", "irrigate my rice field",
        "నీరు పెట్టాలా", "తడి ఇవ్వాలా", "பாசனம் செய்ய வேண்டுமா", "தண்ணீர் விட வேண்டுமா",
        "सिंचाई करनी चाहिए", "पानी देना चाहिए", "क्या पानी लगाएं"
    ]):
        has_soil = True
        has_weather = True
        has_crop = True
        has_rag = True

    # NDVI Decline & Crop Stress Diagnostics
    if any(k in q_lower for k in [
        "ndvi is decreasing", "ndvi has decreased", "ndvi decreased", "why is my ndvi",
        "why has my ndvi", "crop health is decreasing", "water stress", "weather stress",
        "what does my ndvi mean", "what does my current ndvi indicate",
        "ఎన్‌డివిఐ ఏమి సూచిస్తుంది", "என்டிவிஐ என்ன குறிக்கிறது",
        "एनडीवीआई क्या दर्शाता है", "एनडीवीआई का क्या मतलब है"
    ]):
        has_satellite = True
        has_weather = True
        has_soil = True
        has_crop = True
        has_rag = True

    # Fertilizer & Agronomy (Pure Knowledge)
    if any(k in q_lower for k in ["fertilizer", "fertiliser", "dose", "nutrient", "urea", "dap", "potash", "ఎరువులు", "உரங்கள்", "खाद", "उर्वरक"]):
        has_crop = True
        has_rag = True

    # Build active intents and data sources
    intents = []
    data_sources = []

    if has_weather:
        intents.append("WEATHER")
        data_sources.append("OpenWeather API")

    if has_soil:
        intents.append("SOIL")
        data_sources.append("ISRIC SoilGrids 2.0")

    if has_satellite:
        intents.append("SATELLITE")
        data_sources.append("Sentinel-2 Level-2A")

    if has_location:
        intents.append("LOCATION")
        data_sources.append("Selected Farm GPS Coordinates")

    if has_crop:
        intents.append("CROP")
        data_sources.append("Farmer Crop Profile")

    # If agronomic reasoning, management guidance, or multiple telemetry domains are active, include RAG
    if has_rag or not intents or len(intents) >= 2 or "fertilizer" in q_lower:
        if "RAG" not in intents:
            intents.append("RAG")
            data_sources.append("ICAR Knowledge Base (ChromaDB)")

    # Fallback to RAG if no specific category resolved
    if not intents:
        intents = ["RAG"]
        data_sources = ["ICAR Knowledge Base (ChromaDB)"]

    rag_required = "RAG" in intents

    # Optimize retrieval query for semantic vector search in ChromaDB
    retrieval_query = q
    if rag_required:
        if "fertilizer" in q_lower or "nutrient" in q_lower or "खाद" in q_lower or "ఎరువు" in q_lower:
            retrieval_query = f"{q} rice fertilizer NPK dose recommendation basal top dressing"
        elif "temperature" in q_lower or "heat" in q_lower or "weather" in q_lower or "मौसम" in q_lower or "వాతావరణం" in q_lower:
            retrieval_query = f"{q} rice temperature tolerance heat cold stress critical growth stage"
        elif "moisture" in q_lower or "soil" in q_lower or "irrigate" in q_lower or "water" in q_lower or "सिंचाई" in q_lower or "నీరు" in q_lower:
            retrieval_query = f"{q} rice irrigation water management soil moisture deficit alternate wetting drying AWD"
        elif "ndvi" in q_lower or "health" in q_lower or "vigor" in q_lower or "stress" in q_lower or "एनडीवीआई" in q_lower:
            retrieval_query = f"{q} rice crop health vegetative vigor nitrogen deficiency moisture stress symptoms"
        elif "what should i do" in q_lower or "today" in q_lower or "monitor" in q_lower or "assessment" in q_lower or "निगरानी" in q_lower:
            retrieval_query = f"{q} rice daily crop management irrigation nutrient pest surveillance"

    # Query classification
    if len(intents) == 1 and intents[0] != "RAG":
        query_type = "SINGLE_TELEMETRY"
    elif len(intents) == 1 and intents[0] == "RAG":
        query_type = "AGRICULTURAL_KNOWLEDGE"
    else:
        query_type = "COMBINED_MULTI_SOURCE"

    return {
        "intents": intents,
        "sources": intents,
        "data_sources": data_sources,
        "rag_required": rag_required,
        "direct_key": None,
        "retrieval_query": retrieval_query if rag_required else None,
        "query_type": query_type,
        "reason": f"Routed to {', '.join(intents)} based on query requirements."
    }


def detect_query_language(text: Optional[str]) -> str:
    """
    Lightweight script and character detector for queries.
    Returns 'hi', 'te', 'ta', or 'en'.
    """
    if not text or not isinstance(text, str):
        return "en"
    
    # Check Devanagari (Hindi)
    if re.search(r"[\u0900-\u097F]", text):
        return "hi"
    # Check Telugu
    if re.search(r"[\u0C00-\u0C7F]", text):
        return "te"
    # Check Tamil
    if re.search(r"[\u0B80-\u0BFF]", text):
        return "ta"
    
    return "en"

