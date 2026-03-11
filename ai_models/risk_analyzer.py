"""
Risk Analyzer Module - Analyzes cryptocurrency and portfolio risk.
Calculates volatility, drawdowns, VaR, and provides risk scoring.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path

import pandas as pd
import numpy as np
from scipy import stats

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import RISK_CONFIG, DATA_DIR
from utils.helpers import (
    logger, timer, calculate_returns, calculate_max_drawdown,
    calculate_volatility, calculate_sharpe_ratio, calculate_sortino_ratio,
    get_risk_label, get_risk_color
)


class RiskAnalyzer:
    """
    Comprehensive risk analysis engine for cryptocurrency assets.
    Provides volatility metrics, drawdown analysis, Value-at-Risk (VaR),
    and composite risk scoring.
    """

    def __init__(self):
        self.config = RISK_CONFIG

    # ============================================================
    # INDIVIDUAL ASSET RISK ANALYSIS
    # ============================================================
    @timer
    def analyze_asset_risk(self, prices: pd.Series, coin_id: str = "unknown") -> Dict:
        """
        Perform comprehensive risk analysis on a single cryptocurrency.

        Args:
            prices: Price series (indexed by date)
            coin_id: Identifier for the cryptocurrency

        Returns:
            Dictionary containing risk metrics
        """
        if prices is None or len(prices) < 10:
            return {"coin_id": coin_id, "error": "Insufficient data for risk analysis"}

        returns = calculate_returns(prices)

        # ---- Volatility Metrics ----
        daily_volatility = returns.std()
        annualized_volatility = calculate_volatility(returns)

        # ---- Drawdown Analysis ----
        max_drawdown = calculate_max_drawdown(prices)
        cumulative_max = prices.cummax()
        drawdowns = (prices - cumulative_max) / cumulative_max
        current_drawdown = drawdowns.iloc[-1] if len(drawdowns) > 0 else 0

        # ---- Value at Risk (VaR) ----
        confidence = self.config["var_confidence"]
        var_historical = np.percentile(returns, (1 - confidence) * 100)
        var_parametric = returns.mean() - stats.norm.ppf(confidence) * returns.std()

        # Conditional VaR (Expected Shortfall)
        cvar = returns[returns <= var_historical].mean() if len(returns[returns <= var_historical]) > 0 else var_historical

        # ---- Performance Metrics ----
        sharpe_ratio = calculate_sharpe_ratio(returns, self.config["risk_free_rate"])
        sortino_ratio = calculate_sortino_ratio(returns, self.config["risk_free_rate"])

        # ---- Distribution Analysis ----
        skewness = returns.skew()
        kurtosis = returns.kurtosis()

        # ---- Trend Analysis ----
        # Simple moving averages
        sma_20 = prices.rolling(window=20).mean().iloc[-1] if len(prices) >= 20 else prices.mean()
        sma_50 = prices.rolling(window=50).mean().iloc[-1] if len(prices) >= 50 else prices.mean()
        current_price = prices.iloc[-1]

        trend = "bullish" if current_price > sma_20 > sma_50 else (
            "bearish" if current_price < sma_20 < sma_50 else "neutral"
        )

        # ---- Composite Risk Score (0-1, higher = riskier) ----
        risk_score = self._calculate_risk_score(
            annualized_volatility, max_drawdown, var_historical, sharpe_ratio, kurtosis
        )

        return {
            "coin_id": coin_id,
            "current_price": float(current_price),
            "volatility": {
                "daily": float(daily_volatility),
                "annualized": float(annualized_volatility),
                "is_high": bool(daily_volatility > self.config["high_volatility_threshold"]),
            },
            "drawdown": {
                "max_drawdown": float(max_drawdown),
                "current_drawdown": float(current_drawdown),
                "is_critical": bool(abs(max_drawdown) > self.config["max_drawdown_threshold"]),
            },
            "var": {
                "historical_var_95": float(var_historical),
                "parametric_var_95": float(var_parametric),
                "cvar_95": float(cvar),
                "interpretation": f"With 95% confidence, daily loss won't exceed {abs(var_historical)*100:.2f}%"
            },
            "performance": {
                "sharpe_ratio": float(sharpe_ratio),
                "sortino_ratio": float(sortino_ratio),
                "total_return": float((prices.iloc[-1] / prices.iloc[0] - 1) * 100),
            },
            "distribution": {
                "skewness": float(skewness),
                "kurtosis": float(kurtosis),
                "is_fat_tailed": bool(kurtosis > 3),
            },
            "trend": {
                "direction": trend,
                "sma_20": float(sma_20),
                "sma_50": float(sma_50),
                "price_vs_sma20": float((current_price / sma_20 - 1) * 100),
            },
            "risk_score": float(risk_score),
            "risk_label": get_risk_label(risk_score),
            "risk_color": get_risk_color(risk_score),
        }

    def _calculate_risk_score(
        self,
        volatility: float,
        max_drawdown: float,
        var: float,
        sharpe: float,
        kurtosis: float
    ) -> float:
        """
        Calculate composite risk score between 0 (lowest risk) and 1 (highest risk).
        Uses weighted combination of multiple risk factors.
        """
        # Normalize each factor to 0-1 range
        vol_score = min(volatility / 2.0, 1.0)  # 200% annualized vol = max
        dd_score = min(abs(max_drawdown) / 0.8, 1.0)  # 80% drawdown = max
        var_score = min(abs(var) / 0.15, 1.0)  # 15% daily VaR = max
        sharpe_score = max(1 - (sharpe + 1) / 4, 0)  # Higher Sharpe = lower risk
        tail_score = min(max(kurtosis, 0) / 10, 1.0)  # Higher kurtosis = higher risk

        # Weighted combination
        weights = {
            "volatility": 0.30,
            "drawdown": 0.25,
            "var": 0.20,
            "sharpe": 0.15,
            "tail_risk": 0.10,
        }

        risk_score = (
            weights["volatility"] * vol_score +
            weights["drawdown"] * dd_score +
            weights["var"] * var_score +
            weights["sharpe"] * sharpe_score +
            weights["tail_risk"] * tail_score
        )

        return min(max(risk_score, 0), 1)

    # ============================================================
    # PORTFOLIO RISK ANALYSIS
    # ============================================================
    @timer
    def analyze_portfolio_risk(
        self,
        coin_prices: Dict[str, pd.Series],
        weights: Dict[str, float]
    ) -> Dict:
        """
        Analyze risk for an entire portfolio.

        Args:
            coin_prices: Dictionary mapping coin_id to price series
            weights: Dictionary mapping coin_id to portfolio weight (0-1)

        Returns:
            Portfolio risk metrics
        """
        if not coin_prices or not weights:
            return {"error": "No data provided"}

        # Build returns matrix
        returns_dict = {}
        for coin_id, prices in coin_prices.items():
            if prices is not None and len(prices) > 10:
                returns_dict[coin_id] = calculate_returns(prices)

        if not returns_dict:
            return {"error": "Insufficient data for portfolio risk analysis"}

        returns_df = pd.DataFrame(returns_dict).dropna()
        if returns_df.empty:
            return {"error": "No overlapping data for portfolio analysis"}

        # Calculate correlation matrix
        correlation_matrix = returns_df.corr()

        # Calculate covariance matrix
        cov_matrix = returns_df.cov() * 365  # Annualized

        # Portfolio return and risk
        available_coins = [c for c in weights.keys() if c in returns_df.columns]
        w = np.array([weights.get(c, 0) for c in available_coins])

        if w.sum() > 0:
            w = w / w.sum()  # Normalize weights

        portfolio_return = float(np.dot(w, returns_df[available_coins].mean()) * 365)
        portfolio_vol = float(np.sqrt(
            np.dot(w.T, np.dot(cov_matrix.loc[available_coins, available_coins].values, w))
        ))

        # Portfolio VaR
        portfolio_returns = returns_df[available_coins].dot(w)
        var_95 = float(np.percentile(portfolio_returns, 5))

        # Diversification ratio
        individual_vols = np.array([
            returns_df[c].std() * np.sqrt(365) for c in available_coins
        ])
        weighted_vol_sum = np.dot(w, individual_vols)
        diversification_ratio = weighted_vol_sum / portfolio_vol if portfolio_vol > 0 else 1

        # Individual asset risks
        asset_risks = {}
        for coin_id in available_coins:
            if coin_id in coin_prices:
                asset_risks[coin_id] = self.analyze_asset_risk(coin_prices[coin_id], coin_id)

        return {
            "portfolio_metrics": {
                "expected_annual_return": portfolio_return,
                "annual_volatility": portfolio_vol,
                "sharpe_ratio": float(
                    (portfolio_return - self.config["risk_free_rate"]) / portfolio_vol
                ) if portfolio_vol > 0 else 0,
                "var_95_daily": var_95,
                "diversification_ratio": float(diversification_ratio),
            },
            "correlation_matrix": correlation_matrix.to_dict(),
            "asset_risks": asset_risks,
            "risk_decomposition": {
                coin: float(w[i] * individual_vols[i] / portfolio_vol * 100)
                if portfolio_vol > 0 else 0
                for i, coin in enumerate(available_coins)
            },
        }

    # ============================================================
    # MARKET CONDITION DETECTION
    # ============================================================
    def detect_market_conditions(self, prices: pd.Series) -> Dict:
        """
        Detect current market conditions based on price analysis.
        Identifies if market is in fear, greed, or neutral state.
        """
        if prices is None or len(prices) < 30:
            return {"condition": "unknown", "signals": []}

        returns = calculate_returns(prices)
        signals = []

        # Recent performance
        recent_return = (prices.iloc[-1] / prices.iloc[-7] - 1) * 100  # 7-day return
        monthly_return = (prices.iloc[-1] / prices.iloc[-30] - 1) * 100 if len(prices) >= 30 else 0

        # Volatility check
        recent_vol = returns.tail(14).std()
        historical_vol = returns.std()
        vol_ratio = recent_vol / historical_vol if historical_vol > 0 else 1

        if vol_ratio > 1.5:
            signals.append("⚠️ Elevated volatility ({}x normal)".format(f"{vol_ratio:.1f}"))
        elif vol_ratio < 0.5:
            signals.append("😴 Unusually low volatility")

        # Price vs SMAs
        sma_20 = prices.rolling(20).mean().iloc[-1] if len(prices) >= 20 else prices.mean()
        sma_50 = prices.rolling(50).mean().iloc[-1] if len(prices) >= 50 else prices.mean()
        current = prices.iloc[-1]

        if current > sma_20 and sma_20 > sma_50:
            signals.append("📈 Strong uptrend (price above SMA20 & SMA50)")
        elif current < sma_20 and sma_20 < sma_50:
            signals.append("📉 Strong downtrend (price below SMA20 & SMA50)")

        # Drawdown check
        max_dd = calculate_max_drawdown(prices.tail(90))
        if abs(max_dd) > 0.2:
            signals.append(f"🔻 Significant drawdown in past 90 days: {max_dd*100:.1f}%")

        # Determine overall condition
        if recent_return < -10 and vol_ratio > 1.3:
            condition = "🔴 Extreme Fear"
        elif recent_return < -5:
            condition = "🟠 Fear"
        elif recent_return > 10 and vol_ratio < 1.2:
            condition = "🟢 Extreme Greed"
        elif recent_return > 5:
            condition = "🟡 Greed"
        else:
            condition = "⚪ Neutral"

        return {
            "condition": condition,
            "recent_return_7d": float(recent_return),
            "monthly_return": float(monthly_return),
            "volatility_ratio": float(vol_ratio),
            "signals": signals,
        }

    # ============================================================
    # BATCH ANALYSIS
    # ============================================================
    def analyze_multiple_assets(self, price_data: Dict[str, pd.DataFrame]) -> Dict[str, Dict]:
        """
        Analyze risk for multiple cryptocurrencies at once.

        Args:
            price_data: Dict mapping coin_id to DataFrame with 'price' column

        Returns:
            Dictionary of risk analyses keyed by coin_id
        """
        results = {}
        for coin_id, df in price_data.items():
            if df is not None and not df.empty and "price" in df.columns:
                prices = df["price"].reset_index(drop=True)
                results[coin_id] = self.analyze_asset_risk(prices, coin_id)
            else:
                results[coin_id] = {"coin_id": coin_id, "error": "No data available"}

        # Rank by risk score
        valid_results = {k: v for k, v in results.items() if "risk_score" in v}
        ranked = sorted(valid_results.items(), key=lambda x: x[1]["risk_score"])

        for rank, (coin_id, _) in enumerate(ranked, 1):
            results[coin_id]["risk_rank"] = rank

        return results


if __name__ == "__main__":
    # Demo with sample data
    from backend.data_collector import generate_sample_data

    print("Generating sample data and analyzing risk...\n")
    datasets = generate_sample_data(["bitcoin", "ethereum", "solana", "dogecoin"], days=365)

    analyzer = RiskAnalyzer()

    for coin_id, df in datasets.items():
        result = analyzer.analyze_asset_risk(df["price"], coin_id)
        if "error" not in result:
            print(f"\n{'='*50}")
            print(f"📊 {coin_id.upper()} Risk Analysis")
            print(f"{'='*50}")
            print(f"  Risk Score: {result['risk_score']:.3f} {result['risk_label']}")
            print(f"  Volatility (Annual): {result['volatility']['annualized']*100:.1f}%")
            print(f"  Max Drawdown: {result['drawdown']['max_drawdown']*100:.1f}%")
            print(f"  Sharpe Ratio: {result['performance']['sharpe_ratio']:.3f}")
            print(f"  VaR (95%): {result['var']['interpretation']}")
            print(f"  Trend: {result['trend']['direction']}")
