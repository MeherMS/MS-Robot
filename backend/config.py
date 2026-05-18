# backend/config.py

import os
from dotenv import load_dotenv

load_dotenv()

# ============================================================================
# GEMINI API CONFIGURATION - MULTIPLE KEYS FOR QUOTA ROTATION
# ============================================================================

# Parse multiple API keys from comma-separated env variable
GEMINI_API_KEYS_RAW = os.getenv("GEMINI_API_KEYS", "").strip()
MONGODB_URI = os.getenv("MONGODB_URI")
if not GEMINI_API_KEYS_RAW:
    raise ValueError(
        "GEMINI_API_KEYS environment variable not set. \n"
        "Format: GEMINI_API_KEYS=key1,key2,key3\n"
        "Get keys at: https://ai.google.dev/"
    )

GEMINI_API_KEYS = [key.strip() for key in GEMINI_API_KEYS_RAW.split(",") if key.strip()]

if not GEMINI_API_KEYS:
    raise ValueError("No valid API keys found in GEMINI_API_KEYS")

print(f"[CONFIG] ✅ Loaded {len(GEMINI_API_KEYS)} Gemini API key(s)")

GEMINI_MODEL = "gemini-2.5-flash"  # Free tier model
MAX_RESPONSE_TOKENS = 1024  # Max tokens in LLM response


# ============================================================================
# KB RETRIEVAL THRESHOLDS
# ============================================================================
KB_HIGH_THRESHOLD = 0.4         # > 40% match → Direct KB
KB_MEDIUM_THRESHOLD = 0.15      # 15-40% match → Blended KB+LLM
KB_LOW_THRESHOLD = 0.0          # < 15% match → LLM-only

# ============================================================================
# CONFIDENCE SCORES (based on routing)
# ============================================================================
CONF_KB_HIGH = 0.95             # Direct KB match
CONF_KB_MEDIUM = 0.7            # Blended KB + LLM
CONF_LLM_ONLY = 0.6             # LLM-only response

# ============================================================================
# SYSTEM PROMPTS
# ============================================================================
SYSTEM_PROMPT_BASE = """
You are MSRobot, an AI assistant representing Meher Selmi, a Senior Data Scientist.

PERSONALITY:
- Direct, casual 
- Transparent about KB vs. training knowledge
- Technical depth when appropriate
- Prefers clear, simple language over jargon
- Professional but approachable

INSTRUCTIONS:
1. If answering from the Knowledge Base, cite it clearly: "I created/worked on [project name]..."
2. If answering from general knowledge, prefix with: "Based on my training knowledge, I can..."
3. Keep responses concise (1-2 paragraphs max unless asked for details)
4. For personal questions, offer to connect directly with Meher
5. Never make up projects or achievements
6. Be transparent about your limitations

TONE:
You will be told to adopt a specific tone (formal/casual) - follow those instructions.

Use first person (I, me, my) when speaking about yourself.
Use male pronouns (he, him, his) if referring to yourself in third person.
"""

TONE_FORMAL = """
TONE ADAPTATION:
Adopt a formal, professional tone suitable for recruiters and business contexts.
- Use proper grammar and professional vocabulary
- Structure responses clearly with bullet points if needed
- Focus on measurable outcomes and technical details
- Be concise and direct
"""

TONE_CASUAL = """
TONE ADAPTATION:
Adopt a casual, conversational tone suitable for peers and colleagues.
- Use natural, everyday language
- Be relaxed and friendly
- Use contractions and informal phrasing
- Can use light humor if appropriate
"""

# ============================================================================
# CLASSIFIER KEYWORDS
# ============================================================================
PERSONAL_KEYWORDS = {
    "hobby", "music", "espérance", "family", "personal life", 
    "you personally", "your life", "favorite",
    "interests", "weekends", "hobbies"
}

DOMAIN_KEYWORDS = {
    # Technical
    "build", "develop", "can you", "how to", "framework", "implement",
    "create", "design", "architecture", "algorithm", "code", "deploy",
    # Domain-specific
    "esg", "credit", "fintech", "rag", "langgraph", "gcp", "mlops",
    "mistral", "gemini", "llm", "ai", "machine learning", "data science",
    "agent", "copilot", "scoring", "underwriting", "modeling",
    # Project names (add as needed)
    "loan", "portfolio", "compliance", "regulatory", "projects", "experience", "skills", "tell me about", "what have you", "what did you"
}

# ============================================================================
# TOKEN LIMITING
# ============================================================================
DAILY_MESSAGE_LIMIT = 100  # Messages per user per day (by IP)
WARNING_THRESHOLD = 80      # Warn when reaching 80% of limit