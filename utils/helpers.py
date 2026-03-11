"""
Utility helper functions for the AI Crypto Investment Intelligence Platform.
Provides formatting, validation, logging, and common operations.
"""

import logging
import time
import functools
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import pandas as pd
import numpy as np


# ============================================================
# LOGGING SETUP
# ============================================================
def setup_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """Create a configured logger with console and file handlers."""
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if not logger.handlers:
        # Console handler
        ch = logging.StreamHandler()
        ch.setLevel(level)
        formatter = logging.Formatter(
            "%(asctime)s | %(name)-20s | %(levelname)-8s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        ch.setFormatter(formatter)
        logger.addHandler(ch)

    return logger


logger = setup_logger("CryptoIntelligence")


# ============================================================
# DECORATORS
# ============================================================
def timer(func):
    """Decorator to measure function execution time."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start
        logger.info(f"{func.__name__} executed in {elapsed:.2f}s")
        return result
    return wrapper


def retry(max_retries: int = 3, delay: float = 1.0):
    """Decorator to retry a function on failure with exponential backoff."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt < max_retries - 1:
                        wait_time = delay * (2 ** attempt)
                        logger.warning(
                            f"{func.__name__} failed (attempt {attempt + 1}/{max_retries}): {e}. "
                            f"Retrying in {wait_time:.1f}s..."
                        )
                        time.sleep(wait_time)
                    else:
                        logger.error(f"{func.__name__} failed after {max_retries} attempts: {e}")
                        raise
        return wrapper
    return decorator


# ============================================================
# FORMATTING UTILITIES
# ============================================================
def format_currency(value: float, currency: str = "USD", decimals: int = 2) -> str:
    """Format a number as currency string."""
    if value is None:
        return "N/A"
    if abs(value) >= 1_000_000_000:
        return f"${value / 1_000_000_000:.2f}B"
    elif abs(value) >= 1_000_000:
        return f"${value / 1_000_000:.2f}M"
    elif abs(value) >= 1_000:
        return f"${value / 1_000:.2f}K"
    else:
        return f"${value:.{decimals}f}"


def format_percentage(value: float, decimals: int = 2) -> str:
    """Format a number as percentage string."""
    if value is None:
        return "N/A"
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.{decimals}f}%"


def format_large_number(value: float) -> str:
    """Format large numbers with suffixes."""
    if value is None:
        return "N/A"
    if abs(value) >= 1_000_000_000_000:
        return f"{value / 1_000_000_000_000:.2f}T"
    elif abs(value) >= 1_000_000_000:
        return f"{value / 1_000_000_000:.2f}B"
    elif abs(value) >= 1_000_000:
        return f"{value / 1_000_000:.2f}M"
    elif abs(value) >= 1_000:
        return f"{value / 1_000:.2f}K"
    else:
        return f"{value:.2f}"


# ============================================================
# DATA UTILITIES
# ============================================================
def calculate_returns(prices: pd.Series) -> pd.Series:
    """Calculate daily percentage returns from price series."""
    return prices.pct_change().dropna()


def calculate_cumulative_returns(prices: pd.Series) -> pd.Series:
    """Calculate cumulative returns from price series."""
    returns = calculate_returns(prices)
    return (1 + returns).cumprod() - 1


def calculate_sharpe_ratio(
    returns: pd.Series,
    risk_free_rate: float = 0.045,
    periods_per_year: int = 365
) -> float:
    """Calculate annualized Sharpe ratio."""
    if returns.std() == 0:
        return 0.0
    excess_returns = returns.mean() - (risk_free_rate / periods_per_year)
    return (excess_returns / returns.std()) * np.sqrt(periods_per_year)


def calculate_sortino_ratio(
    returns: pd.Series,
    risk_free_rate: float = 0.045,
    periods_per_year: int = 365
) -> float:
    """Calculate annualized Sortino ratio (downside deviation only)."""
    downside_returns = returns[returns < 0]
    if len(downside_returns) == 0 or downside_returns.std() == 0:
        return 0.0
    excess_returns = returns.mean() - (risk_free_rate / periods_per_year)
    return (excess_returns / downside_returns.std()) * np.sqrt(periods_per_year)


def calculate_max_drawdown(prices: pd.Series) -> float:
    """Calculate maximum drawdown from price series."""
    cumulative_max = prices.cummax()
    drawdown = (prices - cumulative_max) / cumulative_max
    return drawdown.min()


def calculate_volatility(returns: pd.Series, periods_per_year: int = 365) -> float:
    """Calculate annualized volatility."""
    return returns.std() * np.sqrt(periods_per_year)


# ============================================================
# VALIDATION
# ============================================================
def validate_crypto_id(crypto_id: str) -> bool:
    """Validate that a crypto ID is a non-empty string."""
    return isinstance(crypto_id, str) and len(crypto_id.strip()) > 0


def validate_positive_number(value: Any) -> bool:
    """Validate that a value is a positive number."""
    try:
        return float(value) > 0
    except (TypeError, ValueError):
        return False


def validate_date_range(start_date: str, end_date: str) -> bool:
    """Validate that date range is valid (start before end)."""
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        return start < end
    except ValueError:
        return False


# ============================================================
# DATE UTILITIES
# ============================================================
def days_ago(n: int) -> datetime:
    """Return datetime n days ago."""
    return datetime.now() - timedelta(days=n)


def timestamp_to_date(timestamp: int) -> str:
    """Convert Unix timestamp (milliseconds) to date string."""
    return datetime.fromtimestamp(timestamp / 1000).strftime("%Y-%m-%d")


def date_to_timestamp(date_str: str) -> int:
    """Convert date string to Unix timestamp (seconds)."""
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return int(dt.timestamp())


# ============================================================
# COLOR UTILITIES FOR DASHBOARD
# ============================================================
def get_color_for_change(value: float) -> str:
    """Return color based on positive/negative change."""
    if value > 0:
        return "#00C853"  # Green
    elif value < 0:
        return "#FF1744"  # Red
    return "#FFD600"  # Yellow for no change


def get_risk_color(risk_score: float) -> str:
    """Return color based on risk score (0-1)."""
    if risk_score < 0.3:
        return "#00C853"  # Green - Low risk
    elif risk_score < 0.6:
        return "#FFD600"  # Yellow - Medium risk
    elif risk_score < 0.8:
        return "#FF9100"  # Orange - High risk
    return "#FF1744"  # Red - Very high risk


def get_risk_label(risk_score: float) -> str:
    """Return human-readable risk label."""
    if risk_score < 0.3:
        return "🟢 Low Risk"
    elif risk_score < 0.6:
        return "🟡 Medium Risk"
    elif risk_score < 0.8:
        return "🟠 High Risk"
    return "🔴 Very High Risk"
