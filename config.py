"""Konfiguration für DocScanner."""
import os
from pathlib import Path
from dotenv import load_dotenv

# .env Datei laden
load_dotenv()

# OpenAI API Key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY muss in .env gesetzt sein")

# Verzeichnisse
INPUT_DIR = Path(os.getenv("INPUT_DIR", "./input"))
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "./output"))
TEMP_DIR = Path(os.getenv("TEMP_DIR", "./temp"))

# SMB-Einstellungen
SMB_SERVER = os.getenv("SMB_SERVER", "smb://192.168.1.140/scans")
SMB_MOUNT_POINT = Path.home() / "smb_scans"  # Lokaler Mount-Punkt

# OpenAI Einstellungen
OPENAI_MODEL = "gpt-5"  # Neuestes Modell mit Vision-Unterstützung
MAX_TOKENS = 2000  # GPT-5 braucht mehr Tokens (verwendet viele für Reasoning)

# PDF zu Bild Konvertierung
PDF_DPI = 300  # Qualität für die Bildkonvertierung

# Patientenbogen-Einstellungen
PAGES_PER_PATIENT = 3  # Jeder Patientenbogen hat 3 Seiten
