"""
Central configuration for Sahayak.
Uses absolute paths throughout (lesson learned from Job Hunter Crew:
relative paths break depending on where the script is invoked from).
"""
import os
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)

DATA_DIR = os.path.join(PROJECT_ROOT, "data")
SCHEMES_PATH = os.path.join(DATA_DIR, "schemes.json")
NGOS_PATH = os.path.join(DATA_DIR, "ngos.json")
CASES_PATH = os.path.join(DATA_DIR, "cases.json")  # runtime-generated case log

load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = "openrouter/meta-llama/llama-3.3-70b-instruct"

# Keep request rate modest to avoid free-tier throttling, as seen before.
MAX_RPM = 8

# Voice I/O: Groq is used directly (not via OpenRouter) for the audio
# endpoints below, since OpenRouter does not proxy speech APIs.
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_WHISPER_MODEL = "whisper-large-v3-turbo"

# Groq's TTS only ships English/Arabic voices, so it's used for English
# output only; Hindi output uses Sarvam AI (purpose-built for Indian
# languages), falling back to gTTS if no Sarvam key is configured or the
# Sarvam call fails (see voice_tools.py).
GROQ_TTS_MODEL = "canopylabs/orpheus-v1-english"
GROQ_TTS_VOICE = "troy"

SARVAM_API_KEY = os.getenv("SARVAM_API_KEY", "")
SARVAM_TTS_MODEL = "bulbul:v2"
SARVAM_TTS_SPEAKER = "anushka"
