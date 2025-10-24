# DocScanner - Patientenbögen Automatische Umbenennung

Ein Tool zum automatischen Auslesen handschriftlicher Namen aus eingescannten Patientenbögen und Umbenennung der PDF-Dateien.

## Features

- Liest PDFs aus einem vorgegebenen Verzeichnis
- Nutzt OpenAI Vision API zum Erkennen handschriftlicher Namen
- Benennt Dateien automatisch um: "Patientenbogen - [NAME].pdf"

## Setup

1. Python Virtual Environment erstellen:
```bash
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
```

2. Dependencies installieren:
```bash
pip install -r requirements.txt
```

3. Umgebungsvariablen konfigurieren:
```bash
cp .env.example .env
# .env bearbeiten und OPENAI_API_KEY eintragen
```

4. Verzeichnisse erstellen:
```bash
mkdir -p input output
```

## Verwendung

```bash
python main.py
```

Das Tool:
1. Scannt alle PDFs im `input/` Verzeichnis
2. Extrahiert die handschriftlichen Namen mit OpenAI Vision API
3. Benennt die Dateien um und verschiebt sie nach `output/`

## Konfiguration

Alle Einstellungen können in der `.env` Datei vorgenommen werden:
- `OPENAI_API_KEY`: Dein OpenAI API Key
- `INPUT_DIR`: Verzeichnis mit den zu verarbeitenden PDFs
- `OUTPUT_DIR`: Verzeichnis für die umbenannten PDFs
