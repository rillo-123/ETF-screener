#!/bin/bash
# setup_pi.sh
# Run this on your Raspberry Pi to prepare the environment

echo "[PI] Updating system..."
sudo apt-get update && sudo apt-get install -y python3.11 python3.11-venv sqlite3

echo "[PI] Creating virtual environment..."
python3 -m venv .venv
source .venv/bin/activate

echo "[PI] Installing dependencies..."
# We use pip install instead of requirements.txt for speed/consistency on Pi
pip install pandas yfinance requests tqdm sqlalchemy pyarrow

echo "[PI] Environment ready!"
echo "Next steps:"
echo "1. Copy the 'src', 'config', 'data', and 'reference' folders to the Pi."
echo "2. Run: export PYTHONPATH=src; python3 -m ETF_screener.main refresh --depth 730"
