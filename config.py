"""
Centralized configuration module for Amadeus.
Auto-detects paths and provides sensible defaults.
All settings can be overridden via environment variables.
"""

import os
import sys
import platform
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# =============================================================================
# Path Detection
# =============================================================================

# Project root directory (where this config.py lives)
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

def get_platform():
    """Detect the current platform."""
    system = platform.system().lower()
    if system == "darwin":
        return "mac"
    elif system == "windows":
        return "windows"
    else:
        return "linux"

PLATFORM = get_platform()

def find_android_sdk():
    """Auto-detect Android SDK location."""
    # Check environment variable first
    sdk_from_env = os.environ.get("ANDROID_HOME") or os.environ.get("ANDROID_SDK_ROOT")
    if sdk_from_env and os.path.isdir(sdk_from_env):
        return sdk_from_env

    # Common SDK locations by platform
    home = os.path.expanduser("~")
    common_paths = {
        "mac": [
            os.path.join(home, "Library", "Android", "sdk"),
            "/usr/local/share/android-sdk",
        ],
        "windows": [
            os.path.join(home, "AppData", "Local", "Android", "Sdk"),
            "C:\\Android\\sdk",
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "Android", "Sdk"),
        ],
        "linux": [
            os.path.join(home, "Android", "Sdk"),
            "/opt/android-sdk",
            "/usr/lib/android-sdk",
        ]
    }

    for path in common_paths.get(PLATFORM, []):
        if path and os.path.isdir(path):
            return path

    return None

# =============================================================================
# API Configuration
# =============================================================================

class APIConfig:
    """API configuration with provider selection."""

    # Supported providers: "nvidia", "xai", "openrouter", "openai"
    PROVIDER = os.environ.get("LLM_PROVIDER", "nvidia").lower()

    # NVIDIA NIM
    NIM_API_KEY = os.environ.get("NIM_API_KEY")
    NIM_BASE_URL = os.environ.get("NIM_BASE_URL", "https://integrate.api.nvidia.com/v1")

    # xAI (Grok)
    XAI_API_KEY = os.environ.get("xAI_API_KEY")
    XAI_BASE_URL = os.environ.get("XAI_BASE_URL", "https://api.x.ai/v1")

    # OpenRouter
    OPENROUTER_API_KEY = os.environ.get("open_router_API")
    OPENROUTER_BASE_URL = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

    # OpenAI
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
    OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")

    # Groq (for audio)
    GROQ_API_KEY = os.environ.get("groq_API")

    @classmethod
    def get_api_key(cls):
        """Get the API key for the selected provider."""
        providers = {
            "nvidia": cls.NIM_API_KEY,
            "xai": cls.XAI_API_KEY,
            "openrouter": cls.OPENROUTER_API_KEY,
            "openai": cls.OPENAI_API_KEY,
        }
        return providers.get(cls.PROVIDER)

    @classmethod
    def get_base_url(cls):
        """Get the base URL for the selected provider."""
        providers = {
            "nvidia": cls.NIM_BASE_URL,
            "xai": cls.XAI_BASE_URL,
            "openrouter": cls.OPENROUTER_BASE_URL,
            "openai": cls.OPENAI_BASE_URL,
        }
        return providers.get(cls.PROVIDER)


# =============================================================================
# Model Configuration
# =============================================================================

class ModelConfig:
    """Model names for different providers."""

    # Default models by provider
    PROVIDER_MODELS = {
        "nvidia": {
            "chat": os.environ.get("NIM_CHAT_MODEL", "meta/llama-3.1-70b-instruct"),
            "vision": os.environ.get("NIM_VISION_MODEL", "meta/llama-3.2-90b-vision-instruct"),
        },
        "xai": {
            "chat": os.environ.get("XAI_CHAT_MODEL", "grok-3-fast-beta"),
            "vision": os.environ.get("XAI_VISION_MODEL", "grok-2-vision-latest"),
        },
        "openrouter": {
            "chat": os.environ.get("OPENROUTER_CHAT_MODEL", "anthropic/claude-3-sonnet"),
            "vision": os.environ.get("OPENROUTER_VISION_MODEL", "anthropic/claude-3-sonnet"),
        },
        "openai": {
            "chat": os.environ.get("OPENAI_CHAT_MODEL", "gpt-4-turbo"),
            "vision": os.environ.get("OPENAI_VISION_MODEL", "gpt-4-vision-preview"),
        },
    }

    # Audio models (Groq)
    WHISPER_MODEL = os.environ.get("WHISPER_MODEL", "whisper-large-v3-turbo")
    TTS_MODEL = os.environ.get("TTS_MODEL", "playai-tts")
    TTS_VOICE = os.environ.get("TTS_VOICE", "Arista-PlayAI")

    @classmethod
    def get_chat_model(cls):
        """Get the chat model for the current provider."""
        provider = APIConfig.PROVIDER
        return cls.PROVIDER_MODELS.get(provider, {}).get("chat")

    @classmethod
    def get_vision_model(cls):
        """Get the vision model for the current provider."""
        provider = APIConfig.PROVIDER
        return cls.PROVIDER_MODELS.get(provider, {}).get("vision")


# =============================================================================
# Appium Configuration
# =============================================================================

class AppiumConfig:
    """Appium server and device configuration."""

    SERVER_URL = os.environ.get("APPIUM_URL", "http://localhost:4723")

    # Timeouts (in milliseconds unless noted)
    UI_AUTOMATOR_INSTALL_TIMEOUT = int(os.environ.get("APPIUM_INSTALL_TIMEOUT", 120000))
    UI_AUTOMATOR_LAUNCH_TIMEOUT = int(os.environ.get("APPIUM_LAUNCH_TIMEOUT", 120000))
    ANDROID_INSTALL_TIMEOUT = int(os.environ.get("APPIUM_APK_TIMEOUT", 600000))
    NEW_COMMAND_TIMEOUT = int(os.environ.get("APPIUM_CMD_TIMEOUT", 600))  # seconds
    ADB_EXEC_TIMEOUT = int(os.environ.get("APPIUM_ADB_TIMEOUT", 60000))
    WAIT_FOR_IDLE_TIMEOUT = int(os.environ.get("APPIUM_IDLE_TIMEOUT", 1000))

    # Device settings
    DEVICE_NAME = os.environ.get("DEVICE_NAME", "Android")
    NO_RESET = os.environ.get("APPIUM_NO_RESET", "true").lower() == "true"
    AUTO_GRANT_PERMISSIONS = os.environ.get("APPIUM_AUTO_GRANT", "true").lower() == "true"
    DISABLE_ANIMATIONS = os.environ.get("APPIUM_DISABLE_ANIM", "true").lower() == "true"

    @classmethod
    def get_capabilities(cls):
        """Get the full Appium capabilities dict."""
        return {
            "platformName": "Android",
            "automationName": "UiAutomator2",
            "deviceName": cls.DEVICE_NAME,
            "noReset": cls.NO_RESET,
            "autoGrantPermissions": cls.AUTO_GRANT_PERMISSIONS,
            "skipServerInstallation": False,
            "skipDeviceInitialization": False,
            "disableWindowAnimation": cls.DISABLE_ANIMATIONS,
            "uiautomator2ServerInstallTimeout": cls.UI_AUTOMATOR_INSTALL_TIMEOUT,
            "uiautomator2ServerLaunchTimeout": cls.UI_AUTOMATOR_LAUNCH_TIMEOUT,
            "androidInstallTimeout": cls.ANDROID_INSTALL_TIMEOUT,
            "newCommandTimeout": cls.NEW_COMMAND_TIMEOUT,
            "adbExecTimeout": cls.ADB_EXEC_TIMEOUT,
            "settings[waitForIdleTimeout]": cls.WAIT_FOR_IDLE_TIMEOUT,
        }


# =============================================================================
# Audio Configuration (Porcupine Wake Word)
# =============================================================================

class AudioConfig:
    """Audio and wake word configuration."""

    # Porcupine API keys (platform-specific)
    PORCUPINE_API_KEY = os.environ.get(
        f"pvporcupine_{PLATFORM}_API",
        os.environ.get("PORCUPINE_API_KEY")
    )

    WAKE_WORD = os.environ.get("WAKE_WORD", "Hello Amadeus")
    RECORD_DURATION = float(os.environ.get("RECORD_DURATION", 5.0))

    @classmethod
    def get_keyword_path(cls):
        """Get the wake word model file path for current platform."""
        keyword_file = f"Hello-Amadeus_{PLATFORM}.ppn"
        # Check if custom path is set
        custom_path = os.environ.get("PORCUPINE_KEYWORD_PATH")
        if custom_path and os.path.exists(custom_path):
            return custom_path
        # Default path in project root
        default_path = os.path.join(PROJECT_ROOT, keyword_file)
        if os.path.exists(default_path):
            return default_path
        return None


# =============================================================================
# Data/ML Configuration
# =============================================================================

class DataConfig:
    """Data storage and ML configuration."""

    @classmethod
    def get_data_dir(cls):
        """Get the data directory, creating it if needed."""
        data_dir = os.environ.get("DATA_DIR", os.path.join(PROJECT_ROOT, "data"))
        os.makedirs(data_dir, exist_ok=True)
        return data_dir

    @classmethod
    def get_ml_csv_path(cls):
        """Get the ML click logs CSV path."""
        custom_path = os.environ.get("ML_CSV_PATH")
        if custom_path:
            return custom_path
        return os.path.join(cls.get_data_dir(), "ml_click_logs.csv")

    @classmethod
    def get_tools_definition_path(cls):
        """Get the path to tools definition JSON."""
        custom_path = os.environ.get("TOOLS_DEFINITION_PATH")
        if custom_path and os.path.exists(custom_path):
            return custom_path
        return os.path.join(PROJECT_ROOT, "tools", "main_agent_tools.json")


# =============================================================================
# Agent Configuration
# =============================================================================

class AgentConfig:
    """Agent behavior configuration."""

    TEMPERATURE = float(os.environ.get("LLM_TEMPERATURE", 0.6))
    MAX_TOKENS = int(os.environ.get("LLM_MAX_TOKENS", 2000))


# =============================================================================
# Environment Setup Helper
# =============================================================================

def setup_android_environment():
    """Set up Android SDK environment variables if not already set."""
    if not os.environ.get("ANDROID_HOME"):
        sdk_path = find_android_sdk()
        if sdk_path:
            os.environ["ANDROID_HOME"] = sdk_path
            os.environ["ANDROID_SDK_ROOT"] = sdk_path
            # Add to PATH
            paths_to_add = [
                os.path.join(sdk_path, "emulator"),
                os.path.join(sdk_path, "tools"),
                os.path.join(sdk_path, "tools", "bin"),
                os.path.join(sdk_path, "platform-tools"),
            ]
            current_path = os.environ.get("PATH", "")
            for p in paths_to_add:
                if p not in current_path:
                    os.environ["PATH"] = p + os.pathsep + current_path
            return True
    return bool(os.environ.get("ANDROID_HOME"))


# =============================================================================
# Convenience exports
# =============================================================================

# Auto-setup Android environment on import
ANDROID_SDK = find_android_sdk()
setup_android_environment()

# Quick access to commonly used values
API_KEY = APIConfig.get_api_key()
BASE_URL = APIConfig.get_base_url()
CHAT_MODEL = ModelConfig.get_chat_model()
VISION_MODEL = ModelConfig.get_vision_model()
