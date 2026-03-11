# 🚀 AI Crypto Investment Intelligence Platform

An advanced cryptocurrency analytics platform combining CoinMarketCap-style market data with AI-powered investment intelligence. Built with Python, FastAPI, Streamlit, and machine learning.

## ✨ Features

### 📊 Modern React Web Dashboard
- Top cryptocurrencies by market cap with real-time charts using Recharts
- Premium dark-themed UI with glassmorphism effects
- Portfolio tracking, risk analysis, and AI-powered insights
- JWT-based authentication flow

### 💼 Portfolio Manager
- Add/remove crypto holdings with real-time valuation
- Asset allocation visualization
- Performance tracking and P&L calculations

### 🔬 Risk Analysis Engine
- Volatility, VaR, Drawdown, and Sharpe ratio metrics
- Composite risk scoring (0-1)
- Market condition detection

### 🤖 AI Prediction Engine
- Linear Regression, Random Forest, and Gradient Boosting models
- Future price forecasting with confidence metrics
- Technical analysis-based feature engineering

### 📈 Portfolio Optimizer
- **Monte Carlo Simulation** - 10,000 random portfolios for efficient frontier
- **Mathematical Optimization** - Max Sharpe, Min Volatility, Max Return
- **Rule-Based Allocation** - Conservative/Moderate/Aggressive profiles
- **Rebalancing Engine** - Drift detection and trade recommendations

### 🔔 Alert System
- Price threshold alerts (up/down/change)
- Risk level alerts
- Portfolio rebalancing notifications
- Email notifications via SMTP

### 📋 Report Generator
- Portfolio performance reports (CSV export)
- Market overview reports
- Prediction summary reports

### ⚡ Parallel Processing
- Concurrent risk analysis across multiple assets
- Parallel ML model training
- ThreadPoolExecutor for performance optimization

## 🏗️ Architecture

```
Data Sources (CoinGecko API)
        ↓
Data Collector → SQLite Database
        ↓
┌─────────────────────────────────────┐
│  Analytics Engine                   │
│  ├── Risk Analyzer                  │
│  ├── ML Predictor (3 models)        │
│  ├── Portfolio Optimizer            │
│  └── Alert System                   │
└─────────────────────────────────────┘
        ↓
┌─────────────────────────────────────┐
│  Presentation Layer                 │
│  ├── Streamlit Dashboard (7 pages)  │
│  └── FastAPI REST API (25+ routes)  │
└─────────────────────────────────────┘
```

## 📁 Project Structure

```
ai-crypto-investment-platform/
├── config.py                    # Configuration & constants
├── main.py                      # CLI entry point for API & Analysis
├── requirements.txt             # Dependencies
├── backend/                     # FastAPI server and core services
│   ├── data_collector.py        # CoinGecko API integration
│   ├── portfolio_manager.py     # Portfolio CRUD & analytics
│   ├── risk_analyzer.py         # Risk metrics & scoring
│   ├── predictor.py             # ML prediction engine
│   ├── investment_optimizer.py  # Portfolio optimization
│   ├── alert_system.py          # Alerts & notifications
│   ├── report_generator.py      # CSV report generation
│   └── api_server.py            # FastAPI REST API
├── frontend/
│   └── dashboard.py             # Streamlit dashboard
├── database/
│   └── db_setup.py              # SQLAlchemy models & schema
├── utils/
│   └── helpers.py               # Utilities & formatters
├── data/                        # CSV price data cache
├── models/                      # Trained ML model files
├── reports/                     # Generated reports
└── database/                    # SQLite database file
```

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd crypto_portfolio-1
pip install -r requirements.txt
```

### 2. Setup (Initialize DB + Generate Sample Data)

```bash
python main.py setup
```

### 3. Launch Dashboard

```bash
python main.py dashboard
```

Open your browser at **http://localhost:8501**

### 4. Launch API Server (optional)

```bash
python main.py api
```

API docs available at **http://localhost:8000/docs**

### 5. Run Full Analysis

```bash
python main.py analyze
```

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/market` | Top 50 cryptos by market cap |
| GET | `/api/market/{coin_id}` | Coin details |
| GET | `/api/market/{coin_id}/history` | Price history |
| GET | `/api/trending` | Trending coins |
| POST | `/api/portfolio` | Create portfolio |
| GET | `/api/portfolio/{id}` | Get portfolio |
| POST | `/api/portfolio/{id}/holding` | Add holding |
| GET | `/api/risk/{coin_id}` | Risk analysis |
| GET | `/api/predict/{coin_id}` | Price prediction |
| GET | `/api/predict/{coin_id}/ensemble` | Ensemble prediction |
| GET | `/api/optimize` | Portfolio optimization |
| GET | `/api/optimize/monte-carlo` | Monte Carlo simulation |
| POST | `/api/alerts` | Create alert |
| GET | `/api/alerts` | List active alerts |
| GET | `/api/report/portfolio/{id}` | Portfolio report |
| GET | `/api/report/market` | Market report |
| POST | `/api/collect-data` | Fetch live data |
| POST | `/api/generate-sample-data` | Generate demo data |

## 🛠️ Technology Stack

| Category | Technology |
|----------|-----------|
| Backend | Python 3.10+, FastAPI |
| Dashboard | Streamlit, Plotly |
| ML | scikit-learn (LR, RF, GB) |
| Database | SQLite, SQLAlchemy |
| Data | Pandas, NumPy, SciPy |
| API | CoinGecko (free tier) |
| Parallel | concurrent.futures |

## 📊 Sample Output

### Risk Analysis
```
BITCOIN
  Risk Score: 0.342 🟡 Medium Risk
  Volatility: 54.3%
  Max Drawdown: -28.4%
  Sharpe Ratio: 0.876

SOLANA
  Risk Score: 0.621 🟠 High Risk
  Volatility: 98.7%
  Max Drawdown: -45.2%
  Sharpe Ratio: 0.234
```

### Price Prediction
```
ETHEREUM Prediction (14 days)
  Current: $2,800.00
  Predicted: $2,942.50
  Change: +5.09%
  Direction: 📈 Bullish
```

## 📝 Environment Variables (Optional)

```bash
# CoinGecko Pro API (optional, free tier works without key)
COINGECKO_API_KEY=your_api_key

# Email notifications
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SENDER_EMAIL=your@email.com
SENDER_PASSWORD=your_app_password
RECIPIENT_EMAIL=recipient@email.com
```

## 📄 License

MIT License - Free for personal and commercial use.
