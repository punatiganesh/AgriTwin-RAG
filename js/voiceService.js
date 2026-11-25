/**
 * AgriTwin-RAG — Voice Service (STT & TTS Engine)
 * Browser-native Web Speech API wrapper for Multilingual Speech-to-Text and Text-to-Speech.
 * Supports English (en-IN), Telugu (te-IN), Tamil (ta-IN), and Hindi (hi-IN).
 */

const VoiceService = (function () {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition || null;
  const synth = window.speechSynthesis || null;

  let recognitionInstance = null;
  let currentlyListening = false;
  let currentSpeechUtterance = null;

  // Language mapping to standard BCP-47 locale tags
  const LANGUAGE_MAP = {
    en: "en-IN",
    "en-in": "en-IN",
    english: "en-IN",
    te: "te-IN",
    "te-in": "te-IN",
    telugu: "te-IN",
    ta: "ta-IN",
    "ta-in": "ta-IN",
    tamil: "ta-IN",
    hi: "hi-IN",
    "hi-in": "hi-IN",
    hindi: "hi-IN"
  };

  /**
   * Normalize input language key to BCP-47 tag
   * @param {string} langKey
   * @returns {string}
   */
  function normalizeLanguageTag(langKey) {
    if (!langKey) return "en-IN";
    const cleaned = String(langKey).toLowerCase().trim();
    return LANGUAGE_MAP[cleaned] || (cleaned.length === 2 ? `${cleaned}-IN` : cleaned);
  }

  /**
   * Check if Speech Recognition (STT) is supported
   * @returns {boolean}
   */
  function isSpeechRecognitionSupported() {
    return SpeechRecognition !== null;
  }

  /**
   * Check if Speech Synthesis (TTS) is supported
   * @returns {boolean}
   */
  function isSpeechSynthesisSupported() {
    return synth !== null && typeof window.SpeechSynthesisUtterance !== "undefined";
  }

  /**
   * Clean Markdown, emojis, and symbols for natural Speech Synthesis pronunciation
   * @param {string} rawText
   * @returns {string}
   */
  function cleanTextForSpeech(rawText) {
    if (!rawText) return "";

    let text = String(rawText);

    // Remove markdown headers, bold, italics, strikethrough, backticks
    text = text.replace(/^#+\s+/gm, "");
    text = text.replace(/\*\*(.*?)\*\*/g, "$1");
    text = text.replace(/\*(.*?)\*/g, "$1");
    text = text.replace(/__(.*?)__/g, "$1");
    text = text.replace(/_(.*?)_/g, "$1");
    text = text.replace(/`{1,3}(.*?)`{1,3}/gs, "$1");

    // Remove markdown links [text](url) -> text
    text = text.replace(/\[([^\]]+)\]\([^)]+\)/g, "$1");

    // Remove bullet point symbols and dashes
    text = text.replace(/^\s*[-*•+]\s+/gm, "");
    text = text.replace(/^\s*\d+\.\s+/gm, "");

    // Clean units and symbols for natural reading
    text = text.replace(/°C/g, " degrees Celsius ");
    text = text.replace(/%/g, " percent ");
    text = text.replace(/&/g, " and ");
    text = text.replace(/→/g, " to ");

    // Remove emojis
    text = text.replace(/[\u{1F300}-\u{1F9FF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}]/gu, "");

    // Normalize multiple spaces and newlines
    text = text.replace(/\n+/g, ". ");
    text = text.replace(/\s{2,}/g, " ").trim();

    return text;
  }

  /**
   * Start Speech-to-Text listening
   * @param {Object} options
   * @param {string} [options.language='en'] - 'en', 'te', 'ta', 'hi', or BCP-47 tag
   * @param {Function} [options.onStart] - Callback when listening starts
   * @param {Function} [options.onResult] - Callback with { transcript, isFinal }
   * @param {Function} [options.onError] - Callback with friendly error message
   * @param {Function} [options.onEnd] - Callback when listening stops
   */
  function startListening(options = {}) {
    if (!isSpeechRecognitionSupported()) {
      const errMsg = "Speech recognition is not supported in this browser. Please use Chrome, Edge, or Safari.";
      if (typeof options.onError === "function") {
        options.onError({ code: "not_supported", message: errMsg });
      }
      return false;
    }

    // Stop any ongoing recognition first
    stopListening();

    try {
      recognitionInstance = new SpeechRecognition();
      const langTag = normalizeLanguageTag(options.language || "en");
      recognitionInstance.lang = langTag;
      recognitionInstance.continuous = false;
      recognitionInstance.interimResults = true;
      recognitionInstance.maxAlternatives = 1;

      recognitionInstance.onstart = function () {
        currentlyListening = true;
        if (typeof options.onStart === "function") {
          options.onStart();
        }
      };

      recognitionInstance.onresult = function (event) {
        let finalTranscript = "";
        let interimTranscript = "";

        for (let i = event.resultIndex; i < event.results.length; ++i) {
          const result = event.results[i];
          if (result.isFinal) {
            finalTranscript += result[0].transcript;
          } else {
            interimTranscript += result[0].transcript;
          }
        }

        const currentText = (finalTranscript || interimTranscript).trim();
        if (typeof options.onResult === "function") {
          options.onResult({
            transcript: currentText,
            isFinal: finalTranscript.length > 0,
            finalTranscript: finalTranscript.trim(),
            interimTranscript: interimTranscript.trim()
          });
        }
      };

      recognitionInstance.onerror = function (event) {
        currentlyListening = false;
        let userMessage = "Speech recognition encountered an issue. Please try again.";

        if (event.error === "not-allowed" || event.error === "service-not-allowed") {
          userMessage = "Microphone permission is required for voice questions. Please allow microphone access in your browser.";
        } else if (event.error === "no-speech") {
          userMessage = "I couldn't hear your question. Please tap the microphone and speak again.";
        } else if (event.error === "audio-capture") {
          userMessage = "No microphone was found on this device.";
        } else if (event.error === "network") {
          userMessage = "Network error occurred during speech recognition. Please check your internet connection.";
        }

        if (typeof options.onError === "function") {
          options.onError({
            code: event.error,
            message: userMessage,
            rawEvent: event
          });
        }
      };

      recognitionInstance.onend = function () {
        currentlyListening = false;
        if (typeof options.onEnd === "function") {
          options.onEnd();
        }
      };

      recognitionInstance.start();
      return true;
    } catch (err) {
      currentlyListening = false;
      console.error("Error starting SpeechRecognition:", err);
      if (typeof options.onError === "function") {
        options.onError({
          code: "exception",
          message: "Unable to start microphone recording. Please try again.",
          error: err
        });
      }
      return false;
    }
  }

  /**
   * Stop Speech-to-Text listening
   */
  function stopListening() {
    if (recognitionInstance) {
      try {
        recognitionInstance.stop();
      } catch (e) {
        // Ignore stop errors if already inactive
      }
      recognitionInstance = null;
    }
    currentlyListening = false;
  }

  /**
   * Is STT currently active
   * @returns {boolean}
   */
  function isListening() {
    return currentlyListening;
  }

  /**
   * Find the best matching installed SpeechSynthesis voice for a given language
   * @param {string} langTag - BCP-47 tag e.g. 'te-IN', 'hi-IN', 'ta-IN', 'en-IN'
   * @returns {SpeechSynthesisVoice|null}
   */
  function findVoiceForLanguage(langTag) {
    if (!synth) return null;
    const voices = synth.getVoices() || [];
    if (!voices.length) return null;

    const normalizedTarget = langTag.toLowerCase().replace("_", "-");
    const langPrefix = normalizedTarget.split("-")[0];

    // 1. Exact match (e.g. 'te-in')
    let match = voices.find(v => v.lang && v.lang.toLowerCase().replace("_", "-") === normalizedTarget);
    if (match) return match;

    // 2. Prefix match with region (e.g. 'te-')
    match = voices.find(v => v.lang && v.lang.toLowerCase().replace("_", "-").startsWith(`${langPrefix}-`));
    if (match) return match;

    // 3. Simple language code prefix (e.g. 'te')
    match = voices.find(v => v.lang && v.lang.toLowerCase().startsWith(langPrefix));
    if (match) return match;

    // 4. Default Indian English fallback if English requested
    if (langPrefix === "en") {
      match = voices.find(v => v.lang && v.lang.toLowerCase().includes("en"));
      if (match) return match;
    }

    return null;
  }

  /**
   * Speak text using SpeechSynthesis (TTS)
   * @param {string} text - The answer text to read aloud
   * @param {string} [language='en'] - 'en', 'te', 'ta', 'hi'
   * @param {Object} [callbacks={}]
   * @param {Function} [callbacks.onStart]
   * @param {Function} [callbacks.onEnd]
   * @param {Function} [callbacks.onError]
   * @returns {boolean}
   */
  function speakText(text, language = "en", callbacks = {}) {
    if (!isSpeechSynthesisSupported()) {
      if (typeof callbacks.onError === "function") {
        callbacks.onError({
          code: "not_supported",
          message: "Voice playback is unavailable on this device."
        });
      }
      return false;
    }

    // Stop any ongoing speech playback
    stopSpeaking();

    const cleanContent = cleanTextForSpeech(text);
    if (!cleanContent) {
      if (typeof callbacks.onEnd === "function") callbacks.onEnd();
      return false;
    }

    try {
      const langTag = normalizeLanguageTag(language);
      const utterance = new SpeechSynthesisUtterance(cleanContent);
      utterance.lang = langTag;
      utterance.rate = 0.95; // Slightly slower for clear agronomic listening
      utterance.pitch = 1.0;

      // Select matching regional voice if available
      const voice = findVoiceForLanguage(langTag);
      if (voice) {
        utterance.voice = voice;
      }

      utterance.onstart = function () {
        currentSpeechUtterance = utterance;
        if (typeof callbacks.onStart === "function") {
          callbacks.onStart();
        }
      };

      utterance.onend = function () {
        currentSpeechUtterance = null;
        if (typeof callbacks.onEnd === "function") {
          callbacks.onEnd();
        }
      };

      utterance.onerror = function (event) {
        currentSpeechUtterance = null;
        // Canceled errors occur on stopSpeaking(), ignore those
        if (event.error === "canceled" || event.error === "interrupted") {
          if (typeof callbacks.onEnd === "function") callbacks.onEnd();
          return;
        }

        let userMsg = "Voice playback was interrupted.";
        if (event.error === "language-unavailable") {
          userMsg = "Voice playback is unavailable for this language on your device.";
        }

        if (typeof callbacks.onError === "function") {
          callbacks.onError({
            code: event.error,
            message: userMsg,
            rawEvent: event
          });
        }
      };

      synth.speak(utterance);
      return true;
    } catch (err) {
      console.error("SpeechSynthesis error:", err);
      if (typeof callbacks.onError === "function") {
        callbacks.onError({
          code: "exception",
          message: "Voice playback is unavailable on this device.",
          error: err
        });
      }
      return false;
    }
  }

  /**
   * Stop Speech-to-Text playback immediately
   */
  function stopSpeaking() {
    if (synth) {
      try {
        synth.cancel();
      } catch (e) {
        // Ignore cancel errors
      }
    }
    currentSpeechUtterance = null;
  }

  /**
   * Is TTS currently speaking
   * @returns {boolean}
   */
  function isSpeaking() {
    return synth !== null && synth.speaking;
  }

  // Preload browser voices
  if (synth && typeof synth.onvoiceschanged !== "undefined") {
    synth.onvoiceschanged = function () {
      synth.getVoices();
    };
  }

  return {
    isSpeechRecognitionSupported,
    isSpeechSynthesisSupported,
    startListening,
    stopListening,
    isListening,
    speakText,
    stopSpeaking,
    isSpeaking,
    cleanTextForSpeech,
    normalizeLanguageTag,
    findVoiceForLanguage
  };
})();

// Export globally
window.VoiceService = VoiceService;
