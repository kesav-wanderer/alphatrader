#!/bin/bash
set -e

echo "=== AlphaTrader Setup (Mac) ==="

# Check Python 3
if ! command -v python3 &>/dev/null; then
    echo "ERROR: python3 not found. Install from https://python.org or via Homebrew: brew install python"
    exit 1
fi

echo "[1/4] Creating virtual environment..."
python3 -m venv venv

echo "[2/4] Activating venv..."
source venv/bin/activate

echo "[3/4] Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "[4/4] Copying .env template..."
if [ ! -f .env ] && [ -f .env.example ]; then
    cp .env.example .env
    echo ".env created — add Kite API keys when ready for live trading"
fi

echo ""
echo "=== Setup Complete ==="
echo "To run: ./run.sh"
