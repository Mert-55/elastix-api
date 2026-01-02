# 🚀 elastix-api

> FastAPI backend for price elasticity simulation and RFM segment analysis in e-commerce

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16+-blue.svg)](https://postgresql.org)
[![License:  MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📖 Overview

**elastix-api** powers the [elastix](https://github.com/Mert-55/elastix) frontend with real-time price elasticity calculations based on log-log regression (Paczkowski, 2018). It enables e-commerce managers to simulate pricing scenarios and analyze customer behavior across RFM segments. 

### Key Features
- 📊 **Price Elasticity Calculation** — Log-log regression with R² metrics
- 🎯 **RFM Segmentation** — Customer segment analytics (Champions, At-Risk, etc.)
- 🔮 **What-If Simulation** — Project revenue impact of price changes
- 📈 **Dashboard Metrics** — Aggregated KPIs and time-series data

---

## 🏗️ Architecture

```
elastix-api/
├── api/
│   ├── app. py              # FastAPI application
│   ├── settings.py         # Configuration
│   ├── database/           # SQLAlchemy async setup
│   ├── models/             # ORM models
│   ├── schemas/            # Pydantic schemas
│   ├── services/           # Business logic
│   └── endpoints/          # Route handlers
├── alembic/                # Database migrations
├── tests/                  # Test suite
├── docker-compose.yml
└── requirements.txt
```

---

## ⚡ Quickstart

### Option 1: Docker (Recommended)

```bash
# Clone repository
git clone https://github.com/Mert-55/elastix-api.git
cd elastix-api

# Start services
docker-compose up -d

# API available at http://localhost:8000
# Docs at http://localhost:8000/docs
```

### Option 2: Local Development

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start PostgreSQL
docker run --name elastix-db -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=elastix -p 5432:5432 -d postgres:16

# Run migrations
alembic upgrade head

# Start server
uvicorn api.app:app --reload
```

---

## 📡 API Endpoints

### Elasticity

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/elasticity` | Calculate price elasticity for products |
| `GET` | `/elasticity/segments` | Elasticity by RFM segment |

### Simulation

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/simulate` | Simulate price change impact |
| `GET` | `/simulations` | List saved simulations |
| `POST` | `/simulations` | Create new simulation |
| `PUT` | `/simulations/{id}` | Update simulation |
| `DELETE` | `/simulations/{id}` | Delete simulation |

### Dashboard Data

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/dashboard/kpis` | Aggregated KPI metrics |
| `GET` | `/dashboard/segments` | Segment distribution (Treemap) |
| `GET` | `/dashboard/trends` | Time-series data (Area Chart) |

### Stock Items

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/stock-items` | Search products |
| `GET` | `/stock-items/{code}` | Product details with elasticity |

---

## 🔧 Configuration

Create `.env` file:

```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost: 5432/elastix
DEBUG=false
LOG_LEVEL=INFO
CORS_ORIGINS=http://localhost:5173
```

---

## 📚 References

- Paczkowski, W. R. (2018). *Pricing Analytics*. Routledge.
- Percival, H., & Gregory, B. (2020). *Architecture Patterns with Python*. O'Reilly. 

---

## 🔗 Related

- **Frontend**: [elastix](https://github.com/Mert-55/elastix) — React dashboard for visualization

---

## 📄 License

MIT License — see [LICENSE](LICENSE)
