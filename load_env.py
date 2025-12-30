"""
Environment variable loader - now delegates to config.py for centralized configuration.
This file is kept for backwards compatibility with existing imports.
"""

from config import (
    APIConfig,
    ModelConfig,
    AudioConfig,
    PLATFORM,
)

# Backwards compatibility exports
xAI = APIConfig.XAI_API_KEY
open_router_API = APIConfig.OPENROUTER_API_KEY
groq_API = APIConfig.GROQ_API_KEY
pvporcupine_win_API = AudioConfig.PORCUPINE_API_KEY if PLATFORM == "windows" else None
pvporcupine_mac_API = AudioConfig.PORCUPINE_API_KEY if PLATFORM == "mac" else None

# New unified exports
NIM_API_KEY = APIConfig.NIM_API_KEY
NIM_BASE_URL = APIConfig.NIM_BASE_URL

# Current provider settings
API_KEY = APIConfig.get_api_key()
BASE_URL = APIConfig.get_base_url()
CHAT_MODEL = ModelConfig.get_chat_model()
VISION_MODEL = ModelConfig.get_vision_model()
