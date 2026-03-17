# Munshi (OpenClaw)

Voice-first AI assistant for Indian kirana stores and small marts.

Say **"Munshi"** → speak in Hindi/Hinglish → get instant voice response.

## Features
- **Daily ledger** — record sales and expenses by voice
- **Udhar tracking** — track credit customers (with fuzzy name matching)
- **Inventory queries** — "Maggi kahan hai?" → shelf location
- **Offline-first** — works without internet; syncs to cloud when available
- **Hardware** — runs on Raspberry Pi 4 (~₹7,000 BOM) or Android phone

## Quick Start

### Prerequisites
- Python 3.11+
- [Poetry](https://python-poetry.org/)

### Setup

```bash
# 1. Install dependencies
poetry install

# 2. Configure
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

# 3. Download ML models
python scripts/download_models.py

# 4. Run database migrations
poetry run alembic upgrade head

# 5. Start Munshi
poetry run munshi
```

### Usage

| Voice Command (Hindi) | Action |
|----------------------|--------|
| "Teen sau rupaye ki chai biki" | Records ₹300 sale |
| "Ramesh ka do sau udhar likh do" | Adds ₹200 credit for Ramesh |
| "Sharma ji ne panch sau diye" | Records ₹500 payment |
| "Aaj ka total kitna hua?" | Daily sales summary |
| "Maggi kahan hai?" | Product shelf location |
| "Chawal kitna bacha hai?" | Stock level check |

## Project Structure

```
munshi/
├── munshi/
│   ├── audio/          # Wake word, STT, TTS, audio pipeline
│   ├── ai/             # Claude API client + offline NLP fallback
│   ├── core/           # Orchestrator (state machine) + response builder
│   ├── modules/        # Business logic: ledger, udhar, inventory, reports
│   ├── db/             # SQLAlchemy models + repositories
│   ├── api/            # FastAPI REST server (for companion app)
│   └── hardware/       # Pi GPIO, LED controller
├── scripts/            # Setup, model download, CSV seed
├── tests/              # Unit tests (no hardware/AI dependencies)
└── alembic/            # Database migrations
```

## REST API

The device also exposes a REST API at `http://munshi.local:8000`:

```
GET  /status
POST /api/v1/ledger/sale
POST /api/v1/ledger/expense
GET  /api/v1/ledger/summary
GET  /api/v1/udhar/outstanding
POST /api/v1/udhar/credit
POST /api/v1/udhar/payment
GET  /api/v1/inventory/location/{product}
```

See `http://munshi.local:8000/docs` for full API documentation.

## Hardware (Raspberry Pi 4)

| Component | Cost (INR) |
|-----------|-----------|
| Raspberry Pi 4B 4GB | ~4,500 |
| ReSpeaker 2-Mic HAT | ~1,200 |
| 3W speaker | ~200 |
| 32GB SD card | ~400 |
| PSU + case + LEDs | ~800 |
| **Total** | **~7,100** |

For Pi setup: `sudo bash scripts/setup_device.sh`

## Running Tests

```bash
poetry run pytest tests/ -v
```
