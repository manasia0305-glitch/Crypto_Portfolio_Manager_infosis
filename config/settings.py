"""
Configuration file for AI Crypto Investment Intelligence Platform.
Contains API settings, database configuration, and application constants.
"""

import os
from pathlib import Path

# ============================================================
# PROJECT PATHS
# ============================================================
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
MODELS_DIR = BASE_DIR / "models"
DATABASE_DIR = BASE_DIR / "database"
REPORTS_DIR = BASE_DIR / "reports"

# Create directories if they don't exist
for d in [DATA_DIR, MODELS_DIR, DATABASE_DIR, REPORTS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ============================================================
# DATABASE CONFIGURATION
# ============================================================
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DATABASE_NAME = "crypto_intelligence_platform"
# DATABASE_PATH = DATABASE_DIR / "crypto_platform.db"
# DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

# ============================================================
# API CONFIGURATION (CoinGecko - Free, no API key needed)
# ============================================================
COINGECKO_BASE_URL = "https://api.coingecko.com/api/v3"
COINGECKO_API_KEY = os.getenv("COINGECKO_API_KEY", "")  # Optional for pro tier

# CoinMarketCap (optional, requires API key)
CMC_API_KEY = os.getenv("CMC_API_KEY", "")
CMC_BASE_URL = "https://pro-api.coinmarketcap.com/v1"

# ============================================================
# DEFAULT CRYPTOCURRENCIES TO TRACK
# ============================================================
DEFAULT_CRYPTOS = [
    "bitcoin", "ethereum", "binancecoin", "solana", "cardano",
    "ripple", "polkadot", "dogecoin", "avalanche-2", "chainlink",
    "polygon", "litecoin", "uniswap", "stellar", "cosmos",
    "near", "algorand", "fantom", "aave", "the-sandbox"
]

DEFAULT_CRYPTO_SYMBOLS = {
    "bitcoin": "BTC", "ethereum": "ETH", "binancecoin": "BNB",
    "solana": "SOL", "cardano": "ADA", "ripple": "XRP",
    "polkadot": "DOT", "dogecoin": "DOGE", "avalanche-2": "AVAX",
    "chainlink": "LINK", "polygon": "MATIC", "litecoin": "LTC",
    "uniswap": "UNI", "stellar": "XLM", "cosmos": "ATOM",
    "near": "NEAR", "algorand": "ALGO", "fantom": "FTM",
    "aave": "AAVE", "the-sandbox": "SAND"
}

# ============================================================
# MACHINE LEARNING SETTINGS
# ============================================================
ML_CONFIG = {
    "prediction_days": 30,       # Days to predict ahead
    "training_window": 365,      # Days of historical data for training
    "test_split": 0.2,           # Train/test split ratio
    "random_state": 42,
    "n_estimators_rf": 100,      # Random Forest estimators
    "sequence_length": 60,       # LSTM sequence length
    "lstm_epochs": 50,
    "lstm_batch_size": 32,
}

# ============================================================
# RISK ANALYSIS SETTINGS
# ============================================================
RISK_CONFIG = {
    "high_volatility_threshold": 0.05,   # 5% daily volatility
    "max_drawdown_threshold": 0.30,      # 30% drawdown alert
    "risk_free_rate": 0.045,             # 4.5% annual risk-free rate (T-bills)
    "var_confidence": 0.95,              # 95% VaR confidence level
    "lookback_days": 90,                 # Risk calculation lookback window
}

# ============================================================
# ALERT CONFIGURATION
# ============================================================
ALERT_CONFIG = {
    "price_change_threshold": 5.0,       # Alert if price changes > 5%
    "volume_spike_threshold": 3.0,       # Alert if volume > 3x average
    "portfolio_risk_threshold": 0.7,     # Alert if risk score > 0.7
    "rebalance_threshold": 0.10,         # Alert if allocation drifts > 10%
}

# ============================================================
# EMAIL NOTIFICATION SETTINGS
# ============================================================
EMAIL_CONFIG = {
    "smtp_server": os.getenv("SMTP_SERVER", "smtp.gmail.com"),
    "smtp_port": int(os.getenv("SMTP_PORT", 587)),
    "sender_email": os.getenv("SENDER_EMAIL", ""),
    "sender_password": os.getenv("SENDER_PASSWORD", ""),
    "recipient_email": os.getenv("RECIPIENT_EMAIL", ""),
}

# ============================================================
# AUTH SETTINGS
# ============================================================
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440")) # 24 hours

# ============================================================
# FASTAPI SETTINGS
# ============================================================
API_HOST = "127.0.0.1"
API_PORT = 8001

# ============================================================
# STREAMLIT SETTINGS
# ============================================================
STREAMLIT_PORT = 8501

# ============================================================
# PARALLEL PROCESSING
# ============================================================
MAX_WORKERS = min(8, os.cpu_count() or 4)

# ============================================================
# PORTFOLIO OPTIMIZATION SETTINGS
# ============================================================
OPTIMIZATION_CONFIG = {
    "min_allocation": 0.02,    # Minimum 2% allocation per asset
    "max_allocation": 0.40,    # Maximum 40% allocation per asset
    "num_portfolios": 10000,   # Monte Carlo simulation count
    "target_return": 0.15,     # 15% target annual return
}
