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

### Dashboard

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/dashboard/kpis` | Segment KPI metrics (priceSensitivity, walletShare, churnRisk) |
| `GET` | `/dashboard/segments` | Segment distribution for TreeMap visualization |
| `GET` | `/dashboard/trends` | Time-series revenue data by segment for Area Chart |

### Stock Items

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/stock-items` | Search products with elasticity data |
| `GET` | `/stock-items/{code}` | Product details with full elasticity info |

### Simulation

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/simulate` | Quick simulation of price change impact |
| `GET` | `/simulations` | List saved simulations |
| `POST` | `/simulations` | Create new simulation |
| `GET` | `/simulations/{id}` | Get simulation by ID |
| `PUT` | `/simulations/{id}` | Update simulation |
| `DELETE` | `/simulations/{id}` | Delete simulation |
| `GET` | `/simulations/{id}/metrics` | Get segment-based simulation metrics |

### Transactions

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/transactions/{transaction_id}` | Get a single transaction by ID |
| `PUT` | `/transactions/{transaction_id}` | Update a transaction (partial updates supported) |
| `DELETE` | `/transactions/{transaction_id}` | Delete a single transaction |
| `DELETE` | `/transactions?confirm=true` | Delete all transactions (requires confirmation) |
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
- [ecommerce-data source](https://www.kaggle.com/datasets/carrie1/ecommerce-data)
---

## 🔗 Related

- **Frontend**: [elastix](https://github.com/Mert-55/elastix) — React dashboard for visualization

---

## 📄 License

MIT License — see [LICENSE](LICENSE)
