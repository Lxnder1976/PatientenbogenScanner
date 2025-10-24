#!/bin/bash
# Setup-Script für DocScanner

echo "🚀 DocScanner Setup"
echo "===================="
echo ""

# Prüfe ob Python installiert ist
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 ist nicht installiert!"
    exit 1
fi

echo "✓ Python gefunden: $(python3 --version)"
echo ""

# Erstelle Virtual Environment
echo "📦 Erstelle Virtual Environment..."
python3 -m venv venv

# Aktiviere Virtual Environment
echo "🔧 Aktiviere Virtual Environment..."
source venv/bin/activate

# Installiere Dependencies
echo "📥 Installiere Dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Prüfe ob poppler installiert ist (für pdf2image)
if ! command -v pdftoppm &> /dev/null; then
    echo ""
    echo "⚠️  WICHTIG: poppler ist nicht installiert!"
    echo "   pdf2image benötigt poppler für die PDF-Konvertierung."
    echo ""
    echo "   Installation mit Homebrew:"
    echo "   brew install poppler"
    echo ""
fi

echo ""
echo "✅ Setup abgeschlossen!"
echo ""
echo "Nächste Schritte:"
echo "1. OpenAI API Key in .env eintragen"
echo "2. Virtual Environment aktivieren: source venv/bin/activate"
echo "3. PDFs ins 'input/' Verzeichnis legen"
echo "4. Programm starten: python main.py"
