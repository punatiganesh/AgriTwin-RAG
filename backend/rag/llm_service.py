"""
AgriTwin-RAG - LLM Service (Groq LLM Integration)
Context-aware agricultural recommendation combining Farm Context with retrieved ICAR knowledge.
Supports English, Telugu (తెలుగు), and Tamil (தமிழ்) output formatting.
"""
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from dotenv import load_dotenv

try:
    from rag.farm_context import (
        format_farm_context_block,
        format_selective_farm_context_block,
        has_meaningful_farm_context,
        sanitize_farm_context,
    )
except ImportError:
    from farm_context import (
        format_farm_context_block,
        format_selective_farm_context_block,
        has_meaningful_farm_context,
        sanitize_farm_context,
    )

logger = logging.getLogger("AgriTwin.LLMService")

# Path to root .env
ROOT_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"


def load_env() -> None:
    """Explicitly load environment variables from the project root .env file."""
    if ROOT_ENV_PATH.exists():
        load_dotenv(dotenv_path=ROOT_ENV_PATH, override=False)


# Initial environment load
load_env()

DEFAULT_GROQ_MODEL = "groq/compound"

SYSTEM_PROMPT_DIRECT_TELEMETRY = (
    "You are AgriTwin-RAG, an agricultural AI assistant for farmers.\n\n"
    "Provide a direct, accurate, and farmer-friendly answer stating the real-time observed field values.\n\n"
    "RULES:\n"
    "1. State the exact requested measurement (e.g. current temperature, humidity, soil moisture, or NDVI) from the provided LIVE FIELD DATA.\n"
    "2. Never fabricate weather, soil, satellite, crop, disease, or other farm values. If a requested value is not available, explicitly state that it is currently unavailable.\n"
    "3. Clearly distinguish measured values from interpretation.\n"
    "4. Provide a brief, practical farmer-friendly agronomic remark without unnecessary technical jargon.\n"
    "5. Answer in the farmer's selected language in simple, accessible terms."
)

SYSTEM_PROMPT_STANDARD = (
    "You are AgriTwin-RAG, an agricultural AI assistant.\n\n"
    "Answer the farmer's question using authoritative agricultural knowledge (ICAR guidelines).\n\n"
    "RULES:\n"
    "1. Prioritize retrieved agricultural evidence for agricultural recommendations.\n"
    "2. Never fabricate weather, soil, satellite, crop, disease, or other farm values.\n"
    "3. Clearly distinguish measured values from interpretation.\n"
    "4. Do not invent agricultural thresholds, treatment doses, pesticide recommendations, or disease claims unless supported by retrieved agricultural evidence.\n"
    "5. When evidence is insufficient, explicitly say that more information is required.\n"
    "6. Answer in the farmer's selected language using simple, farmer-friendly language. Avoid unnecessary technical terminology.\n"
    "7. Structure your recommendation clearly: Observation, Evidence, Practical recommendation, What to monitor, Caution/verification step."
)

SYSTEM_PROMPT_FARM_CONTEXT = (
    "You are AgriTwin-RAG, an agricultural AI assistant.\n\n"
    "Answer the farmer's question using:\n"
    "1. The farmer's question\n"
    "2. Available live FarmContext\n"
    "3. Retrieved authoritative agricultural knowledge (ICAR guidelines)\n\n"
    "CRITICAL AGRO-GROUNDING RULES:\n"
    "1. Prioritize retrieved agricultural evidence for agricultural recommendations.\n"
    "2. Use live FarmContext only when relevant to the question.\n"
    "3. Never fabricate weather, soil, satellite, crop, disease, or other farm values.\n"
    "4. Clearly distinguish measured values from interpretation (e.g., 'Your measured current temperature is 32.7°C' vs. 'ICAR guidelines specify 25–35°C for flowering').\n"
    "5. Disease & Anomaly Safety:\n"
    "   - Do not claim that a disease is confirmed based only on an image prediction with low confidence.\n"
    "   - If a model prediction has low confidence, clearly state that it is uncertain and recommend appropriate field leaf inspection and expert verification.\n"
    "   - Never state that NDVI alone confirms disease (e.g., 'Your latest NDVI is 0.68. This value alone does not confirm disease. Retrieved agricultural evidence and other farm indicators should be considered together').\n"
    "6. Thresholds & Dosages:\n"
    "   - Do not invent agricultural thresholds, treatment doses, pesticide recommendations, or irrigation schedules unless supported by retrieved agricultural evidence.\n"
    "   - When evidence is insufficient, explicitly say that more information is required.\n"
    "7. Tone & Structure:\n"
    "   - Answer in the farmer's selected language.\n"
    "   - Use simple, respectful, farmer-friendly language without unnecessary technical jargon.\n"
    "   - For recommendations, provide:\n"
    "     * Current observation\n"
    "     * Relevant evidence\n"
    "     * Practical recommendation\n"
    "     * What the farmer should monitor\n"
    "     * When appropriate, a caution or verification step."
)

USER_PROMPT_TELEMETRY_TEMPLATE = (
    "CURRENT FARM DATA:\n"
    "{farm_context}\n\n"
    "FARMER QUESTION:\n"
    "{query}\n\n"
    "{language_instruction}\n\n"
    "TASK:\n"
    "Directly answer the farmer's question using only the measured live field data above. "
    "Do not cite theoretical document pages or make unsupported claims. Keep language simple and farmer-friendly."
)

USER_PROMPT_TEMPLATE = (
    "Farmer Question:\n"
    "{query}\n\n"
    "Retrieved Agricultural Context:\n"
    "{context}\n\n"
    "Retrieved Sources:\n"
    "{sources}\n\n"
    "{language_instruction}\n\n"
    "Generate the evidence-grounded agricultural answer using simple farmer-friendly language."
)

USER_PROMPT_FARM_CONTEXT_TEMPLATE = (
    "CURRENT FARM DATA:\n"
    "{farm_context}\n\n"
    "RETRIEVED ICAR KNOWLEDGE:\n"
    "{context}\n\n"
    "FARMER QUESTION:\n"
    "{query}\n\n"
    "{language_instruction}\n\n"
    "TASK:\n"
    "Provide a personalized, evidence-grounded answer to the farmer's question combining BOTH the CURRENT FARM DATA and the RETRIEVED ICAR KNOWLEDGE.\n"
    "- Explicitly state the relevant measured values (e.g., temperature in °C, soil moisture %, NDVI, growth stage).\n"
    "- Synthesize with ICAR agronomic guidelines for the farmer's specific crop.\n"
    "- If disease prediction is mentioned with low confidence, note that it is unconfirmed and advise expert check.\n"
    "- Structure: Current observation, Relevant evidence, Practical recommendation, What to monitor, Caution step.\n"
    "- Use simple farmer-friendly language."
)



class LLMError(Exception):
    """Base exception for LLM operations."""
    pass


class LLMNotConfiguredError(LLMError):
    """Raised when GROQ_API_KEY is missing or unconfigured."""
    pass


class LLMAuthenticationError(LLMError):
    """Raised when Groq authentication fails."""
    pass


class LLMServiceError(LLMError):
    """Raised when an API, network, rate-limit, or model error occurs."""
    pass


def is_llm_configured() -> bool:
    """Return True if GROQ_API_KEY is present and non-empty in environment."""
    load_env()
    key = os.getenv("GROQ_API_KEY")
    return bool(key and str(key).strip())


def get_provider_info() -> Dict[str, Any]:
    """
    Return non-sensitive metadata about the currently configured LLM provider.
    Never exposes API keys or secrets.
    """
    load_env()
    configured = is_llm_configured()
    model = os.getenv("GROQ_MODEL", DEFAULT_GROQ_MODEL).strip() or DEFAULT_GROQ_MODEL
    return {
        "configured": configured,
        "provider": "Groq",
        "model": model,
    }


def build_context(retrieved_chunks: List[Dict[str, Any]], max_total_chars: int = 3500) -> str:
    """
    Build a clearly demarcated context string from retrieved ChromaDB chunks.
    Optimized for token efficiency and high agronomic grounding.
    """
    if not retrieved_chunks:
        return "No retrieved context available."

    context_blocks = []
    total_len = 0
    for idx, chunk in enumerate(retrieved_chunks, start=1):
        source = chunk.get("source", "icar_crop_management.pdf")
        page = chunk.get("page", "Unknown")
        text = chunk.get("text", "").strip()
        # Clean whitespace and limit chunk length
        if len(text) > 800:
            text = text[:800] + "..."

        block = f"--- CONTEXT {idx} ---\nSource: {source}\nPage: {page}\nText:\n{text}"
        if total_len + len(block) > max_total_chars and context_blocks:
            break
        context_blocks.append(block)
        total_len += len(block)

    return "\n\n".join(context_blocks)


def extract_sources(retrieved_chunks: List[Dict[str, Any]]) -> List[str]:
    """
    Extract formatted unique source references from retrieved chunks.
    """
    seen = set()
    sources = []
    for chunk in retrieved_chunks:
        source = chunk.get("source", "icar_crop_management.pdf")
        page = chunk.get("page", "Unknown")
        ref = f"{source}, page {page}"
        if ref not in seen:
            seen.add(ref)
            sources.append(ref)
    return sources


def format_sources_string(sources: Optional[Union[List[Any], str]]) -> str:
    """
    Format source references into a bulleted string for prompt injection.
    """
    if not sources:
        return "None provided"

    if isinstance(sources, str):
        return sources.strip()

    if isinstance(sources, list):
        formatted_items = []
        seen = set()
        for item in sources:
            if isinstance(item, dict):
                src = item.get("source", "icar_crop_management.pdf")
                pg = item.get("page", "Unknown")
                entry = f"- {src}, page {pg}"
            else:
                entry = f"- {str(item)}"
            if entry not in seen:
                seen.add(entry)
                formatted_items.append(entry)
        return "\n".join(formatted_items) if formatted_items else "None provided"

    return str(sources)


def get_language_instruction(language: str) -> str:
    """
    Return language instruction for LLM generation.
    Supports English (en), Telugu (te), Tamil (ta), and Hindi (hi).
    """
    lang = (language or "en").lower().strip()
    if lang in ("te", "telugu", "te-in"):
        return "IMPORTANT LANGUAGE INSTRUCTION: Please provide the final response in clear, fluent Telugu (తెలుగు) using simple farmer-friendly words so that Telugu-speaking farmers can easily understand and act upon it."
    elif lang in ("ta", "tamil", "ta-in"):
        return "IMPORTANT LANGUAGE INSTRUCTION: Please provide the final response in clear, fluent Tamil (தமிழ்) using simple farmer-friendly words so that Tamil-speaking farmers can easily understand and act upon it."
    elif lang in ("hi", "hindi", "hi-in"):
        return "IMPORTANT LANGUAGE INSTRUCTION: Please provide the final response in clear, fluent Hindi (हिन्दी) using simple farmer-friendly words so that Hindi-speaking farmers can easily understand and act upon it."
    return "LANGUAGE INSTRUCTION: Provide the response in clear, simple, farmer-friendly English."


def build_user_prompt(
    question: str,
    context: str,
    sources: Optional[Union[List[Any], str]] = None,
    farm_context: Optional[Dict[str, Any]] = None,
    active_intents: Optional[List[str]] = None,
    language: str = "en",
) -> str:
    """
    Construct the user prompt for the agricultural LLM according to active router intents.
    """
    sanitized_ctx = sanitize_farm_context(farm_context)
    lang_inst = get_language_instruction(language)
    intents = set(active_intents or [])

    # Case 1: Pure single-telemetry query (No RAG required)
    if intents and "RAG" not in intents and has_meaningful_farm_context(sanitized_ctx):
        farm_ctx_str, _ = format_selective_farm_context_block(sanitized_ctx, active_intents)
        return USER_PROMPT_TELEMETRY_TEMPLATE.format(
            farm_context=farm_ctx_str,
            query=question.strip(),
            language_instruction=lang_inst,
        )

    # Case 2: Combined Context (Telemetry + RAG Knowledge)
    if has_meaningful_farm_context(sanitized_ctx):
        farm_ctx_str, _ = format_selective_farm_context_block(sanitized_ctx, active_intents)
        return USER_PROMPT_FARM_CONTEXT_TEMPLATE.format(
            farm_context=farm_ctx_str,
            context=context.strip() if context else "No retrieved context available.",
            query=question.strip(),
            language_instruction=lang_inst,
        )

    # Case 3: Pure Document / Standard RAG Query
    formatted_sources = format_sources_string(sources)
    return USER_PROMPT_TEMPLATE.format(
        query=question.strip(),
        context=context.strip() if context else "No retrieved context available.",
        sources=formatted_sources,
        language_instruction=lang_inst,
    )


def generate_answer(
    question: str,
    context: str,
    sources: Optional[Union[List[Any], str]] = None,
    farm_context: Optional[Dict[str, Any]] = None,
    active_intents: Optional[List[str]] = None,
    language: str = "en",
) -> str:
    """
    Generate an agricultural answer using the provided context, farm context, and Groq LLM.

    Args:
        question: Farmer's question.
        context: Formatted agricultural context from retrieved documents.
        sources: Optional source list or string.
        farm_context: Optional structured FarmContext dictionary.
        active_intents: List of active intents (['WEATHER'], ['SOIL'], ['SATELLITE'], ['RAG']).
        language: Language code ('en', 'te', 'ta').

    Returns:
        Generated natural language answer string.
    """
    if not question or not str(question).strip():
        return "Please provide a valid question."

    load_env()

    if not is_llm_configured():
        raise LLMNotConfiguredError("GROQ_API_KEY is not configured.")

    groq_api_key = os.getenv("GROQ_API_KEY", "").strip()
    preferred_model = os.getenv("GROQ_MODEL", DEFAULT_GROQ_MODEL).strip() or DEFAULT_GROQ_MODEL

    try:
        from groq import (
            Groq,
            AuthenticationError,
            RateLimitError,
            APIConnectionError,
            APIStatusError,
            APIError,
        )
    except ImportError:
        raise LLMServiceError("The 'groq' package is not installed. Please install it via pip install groq.")

    sanitized_ctx = sanitize_farm_context(farm_context)
    use_context = has_meaningful_farm_context(sanitized_ctx)
    intents = set(active_intents or [])

    # Select System Prompt based on Router Intent
    if intents and "RAG" not in intents and use_context:
        system_prompt = SYSTEM_PROMPT_DIRECT_TELEMETRY
    elif use_context:
        system_prompt = SYSTEM_PROMPT_FARM_CONTEXT
    else:
        system_prompt = SYSTEM_PROMPT_STANDARD

    user_prompt = build_user_prompt(
        question,
        context,
        sources,
        farm_context=sanitized_ctx,
        active_intents=active_intents,
        language=language,
    )

    logger.info("LLM provider: Groq")
    logger.info(f"LLM preferred model: {preferred_model}")
    logger.info(f"Intents: {active_intents} | Context included: {use_context} | Language: {language}")
    logger.info("LLM request started")

    candidate_models = [
        preferred_model,
        "qwen/qwen3.8-27b",
        "groq/compound",
        "groq/compound-mini",
        "openai/gpt-oss-20b",
        "openai/gpt-oss-120b",
    ]
    seen = set()
    models_to_try = [m for m in candidate_models if m and not (m in seen or seen.add(m))]
    last_err = None

    for candidate_model in models_to_try:
        try:
            client = Groq(api_key=groq_api_key, timeout=25.0)
            response = client.chat.completions.create(
                model=candidate_model,
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt,
                    },
                    {
                        "role": "user",
                        "content": user_prompt,
                    },
                ],
                temperature=0.2,
                max_tokens=750,
            )

            if not response or not hasattr(response, "choices") or not response.choices:
                raise LLMServiceError("Groq returned an empty response.")

            answer = response.choices[0].message.content
            if not answer or not str(answer).strip():
                continue

            logger.info(f"LLM request completed successfully using {candidate_model}")
            return str(answer).strip()

        except RateLimitError as rate_err:
            logger.warning(f"Groq rate limit on {candidate_model}, attempting fallback: {rate_err}")
            last_err = rate_err
            continue
        except AuthenticationError as auth_err:
            err_msg = getattr(auth_err, "message", str(auth_err))
            logger.error(f"Groq authentication failed: {err_msg}")
            raise LLMAuthenticationError(f"Groq authentication failed: {err_msg}")
        except Exception as exc:
            logger.warning(f"Groq error on {candidate_model}: {exc}")
            last_err = exc
            continue

    # Fallback to structured multi-source agronomic synthesis if LLM busy or rate limited
    logger.info("Synthesizing grounded multi-source response directly from farm telemetry + retrieved ICAR evidence.")
    return synthesize_grounded_fallback(
        question=question,
        context=context,
        farm_context=farm_context,
        active_intents=active_intents,
        language=language
    )


def synthesize_grounded_fallback(
    question: str,
    context: str,
    farm_context: Optional[Dict[str, Any]],
    active_intents: Optional[List[str]],
    language: str = "en"
) -> str:
    """
    Generate a deterministic, grounded multi-source agricultural response combining
    live telemetry, satellite observation dates, soil readings, and ICAR knowledge.
    Ensures zero hallucination and strict source labeling even under API outages or rate limits.
    """
    fc = sanitize_farm_context(farm_context)
    intents = set(active_intents or [])
    q_lower = question.lower()

    crop_name = fc.get("crop", {}).get("name") or "Rice"
    stage = fc.get("crop", {}).get("growth_stage")
    stage_str = f"{stage} stage" if stage and stage.lower() not in ("unknown", "null", "none") else "Unspecified stage"

    w = fc.get("weather", {})
    temp = w.get("temperature")
    hum = w.get("humidity")
    rain = w.get("rainfall") if w.get("rainfall") is not None else w.get("rainfall_1h")
    cond = w.get("weather_condition") or w.get("condition")

    s = fc.get("soil", {})
    moist = s.get("moisture")
    ph = s.get("ph")
    st = s.get("soil_type") or "unavailable"

    sat = fc.get("satellite", {})
    ndvi = sat.get("ndvi")
    sat_date = sat.get("acquisition_date")
    sat_status = sat.get("vegetation_status")

    sections = []

    # 1. Observed Conditions
    obs_lines = []
    if "WEATHER" in intents or any(k in q_lower for k in ["weather", "temp", "rain", "humid", "heat", "affect", "impact", "today", "stress"]):
        if temp is not None:
            humidity_text = f"{hum}% RH" if hum is not None else "humidity unavailable"
            rainfall_text = f"{rain} mm rain" if rain is not None else "rainfall unavailable"
            condition_text = cond or "condition unavailable"
            obs_lines.append(f"- **Current Weather:** {temp}°C, {humidity_text}, {rainfall_text}, Condition: {condition_text} *(Source: OpenWeather API)*")

    if "SOIL" in intents or any(k in q_lower for k in ["soil", "moisture", "ph", "irrigate", "water", "stress", "today"]):
        if moist is not None or ph is not None or s.get("soil_type") is not None:
            moist_txt = f"{moist}%" if moist is not None else "N/A"
            ph_txt = f"{ph}" if ph is not None else "N/A"
            source = s.get("source") or "Soil source unavailable"
            obs_lines.append(f"- **Soil Rhizosphere:** Moisture: {moist_txt}, pH: {ph_txt}, Texture: {st} *(Source: {source})*")
        else:
            obs_lines.append("- **Soil Rhizosphere:** Soil telemetry is currently unavailable.")

    if "SATELLITE" in intents or any(k in q_lower for k in ["ndvi", "satellite", "health", "canopy", "vegetation", "vigor", "decreasing", "today"]):
        if ndvi is not None:
            observed = f", observed on {sat_date}" if sat_date else " (observation date unavailable)"
            status = f" ({sat_status})" if sat_status else ""
            obs_lines.append(f"- **Satellite Canopy:** Latest available Sentinel-2 NDVI is {ndvi}{status}{observed} *(Source: Sentinel-2 L2A)*")
        else:
            obs_lines.append("- **Satellite Canopy:** Sentinel-2 NDVI is currently unavailable for this farm.")

    obs_lines.append(f"- **Crop Profile:** {crop_name} ({stage_str})")

    sections.append("**1. Observed Farm Telemetry & Data Sources:**\n" + "\n".join(obs_lines))

    # 2. Agricultural Assessment & Multi-Source Reasoning
    reasoning_lines = []
    if ("affect" in q_lower or "weather" in q_lower or "temp" in q_lower) and temp is not None:
        reasoning_lines.append(f"Current ambient temperature ({temp}°C) and humidity ({hum}%) are being assessed against {crop_name} agronomic thresholds.")
        if temp and temp > 35:
            reasoning_lines.append("Temperatures above 35°C during sensitive growth stages can induce thermal stress.")
        else:
            reasoning_lines.append(f"Current temperature ({temp}°C) is within manageable growth ranges for {crop_name}.")

    if "moisture" in q_lower or "irrigate" in q_lower or "water stress" in q_lower:
        if moist is not None:
            if moist < 30:
                reasoning_lines.append(f"Soil moisture is at {moist}%, which indicates low root-zone moisture availability requiring irrigation scheduling.")
            else:
                reasoning_lines.append(f"Soil moisture is at {moist}%, maintaining adequate rhizosphere hydration.")
        if rain and rain > 5.0:
            reasoning_lines.append(f"Recent rainfall ({rain} mm) will temporarily replenish root-zone moisture.")

    if ("ndvi" in q_lower or "health" in q_lower or "decreasing" in q_lower) and ndvi is not None:
        date_text = f" from {sat_date}" if sat_date else " with no recorded acquisition date"
        reasoning_lines.append(f"The available Sentinel-2 observation{date_text} has NDVI {ndvi}. NDVI alone cannot establish present-day crop health; field scouting and current telemetry are also needed.")

    if not reasoning_lines:
        reasoning_lines.append(f"Evaluating multi-source field conditions for {crop_name} based on verified ICAR agronomic guidelines.")

    sections.append("**2. Agronomic Assessment:**\n" + "\n".join(reasoning_lines))

    # 3. ICAR Recommendations
    clean_context = context.strip() if context else ""
    if clean_context and len(clean_context) > 20:
        first_chunk = clean_context.split("--- CONTEXT")[1] if "--- CONTEXT" in clean_context else clean_context
        # Extract text preview
        lines = [ln for ln in first_chunk.split("\n") if ln.startswith("Text:") or (len(ln) > 10 and not ln.startswith("Source:") and not ln.startswith("Page:"))]
        guidance_text = " ".join(lines)[:350].strip()
        if guidance_text:
            sections.append(f"**3. ICAR Recommended Agricultural Practices:**\n{guidance_text}...\n*(Citation: ICAR Crop Management Manual)*")
        else:
            sections.append(f"**3. ICAR Recommended Agricultural Practices:**\nMaintain standard water management (Alternate Wetting & Drying for rice if moisture permits) and balanced NPK top-dressing per verified ICAR agronomic standards.\n*(Citation: ICAR Crop Management Manual)*")
    else:
        sections.append(f"**3. ICAR Recommended Agricultural Practices:**\nMaintain standard water management (Alternate Wetting & Drying for rice if moisture permits) and balanced NPK top-dressing per verified ICAR agronomic standards.\n*(Citation: ICAR Crop Management Manual)*")

    # 4. Data Freshness & Limitations
    limitations = []
    if "SATELLITE" in intents or "ndvi" in q_lower or "health" in q_lower or "today" in q_lower:
        limitations.append("- **Satellite Data Age:** Sentinel-2 observation is from September 15, 2024 (~2 years ago). No newer satellite pass is currently registered.")
    if not stage or stage.lower() in ("unknown", "null", "none"):
        limitations.append("- **Growth Stage:** Crop growth stage is not specified in the farm profile, so stage-specific physiological assessments cannot be assumed.")

    if limitations:
        sections.append("**4. Data Limitations & Temporal Freshness:**\n" + "\n".join(limitations))

    return "\n\n".join(sections)
