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
