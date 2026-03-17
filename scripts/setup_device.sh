#!/usr/bin/env bash
# Munshi — Raspberry Pi device setup script
# Run as: sudo bash scripts/setup_device.sh

set -euo pipefail

echo "============================================"
echo "   Munshi Device Setup — Raspberry Pi 4"
echo "============================================"

# ── System dependencies ──────────────────────────────────────────────────────
echo "[1/6] Installing system packages..."
apt-get update -q
apt-get install -y -q \
    python3.11 python3.11-dev python3-pip \
    portaudio19-dev libsndfile1-dev \
    ffmpeg libespeak-ng1 \
    sqlite3 \
    git curl

# ── Python dependencies ───────────────────────────────────────────────────────
echo "[2/6] Installing Python dependencies..."
pip3 install poetry
cd /home/pi/munshi || cd "$(dirname "$0")/.."
poetry install --no-dev

# ── Audio configuration ───────────────────────────────────────────────────────
echo "[3/6] Configuring audio (ReSpeaker 2-Mic HAT)..."
# Install ReSpeaker drivers
if [ ! -d /home/pi/seeed-voicecard ]; then
    git clone https://github.com/HinTak/seeed-voicecard /home/pi/seeed-voicecard
    cd /home/pi/seeed-voicecard
    bash install.sh
    cd -
fi
# Set default audio device
cat > /etc/asound.conf << 'EOF'
pcm.!default {
    type asym
    capture.pcm "mic"
    playback.pcm "speaker"
}
pcm.mic {
    type plug
    slave { pcm "hw:seeed2micvoicec,0" }
}
pcm.speaker {
    type plug
    slave { pcm "hw:seeed2micvoicec,0" }
}
EOF

# ── Data directories ──────────────────────────────────────────────────────────
echo "[4/6] Creating data directories..."
mkdir -p data/db data/models/whisper data/models/tts data/models/wake_word logs
chown -R pi:pi data/ logs/

# ── Environment file ──────────────────────────────────────────────────────────
echo "[5/6] Setting up environment..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "⚠️  Created .env from example. Edit it and add your ANTHROPIC_API_KEY!"
fi

# ── Systemd service ───────────────────────────────────────────────────────────
echo "[6/6] Installing systemd service..."
cat > /etc/systemd/system/munshi.service << EOF
[Unit]
Description=Munshi Voice Assistant
After=network.target sound.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/munshi
ExecStart=/home/pi/.venv/bin/python -m munshi.main
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable munshi.service

echo ""
echo "============================================"
echo "Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Edit .env: nano .env"
echo "  2. Download models: python3 scripts/download_models.py"
echo "  3. Run migrations: poetry run alembic upgrade head"
echo "  4. Start: sudo systemctl start munshi"
echo "  5. Logs: sudo journalctl -u munshi -f"
echo "============================================"
