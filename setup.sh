#!/bin/bash
# Setup script pentru Orange Internet Toggle
# Rulează o singură dată: bash setup.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== Orange Internet Toggle - Setup ==="

# 1. Verifică Python
if ! command -v python3 &>/dev/null; then
    echo "EROARE: python3 nu este instalat."
    exit 1
fi
echo "✓ Python3: $(python3 --version)"

# 2. Creează virtualenv
if [ ! -d "venv" ]; then
    echo "Creez virtualenv..."
    python3 -m venv venv
fi
source venv/bin/activate

# 3. Instalează dependențe
echo "Instalez dependențe Python..."
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

# 4. Instalează browserul Chromium pentru Playwright
echo "Instalez Chromium (Playwright)..."
playwright install chromium
playwright install-deps chromium

echo ""
echo "=== Setup complet! ==="
echo ""
echo "PASUL URMĂTOR: Editează fișierul .env și pune parola corectă:"
echo "  nano $SCRIPT_DIR/.env"
echo ""
echo "Testează manual:"
echo "  source venv/bin/activate"
echo "  python orange_internet.py disable   # dezactivează"
echo "  python orange_internet.py enable    # activează"
echo ""
echo "Instalează cron jobs automate:"
echo "  bash install_cron.sh"
