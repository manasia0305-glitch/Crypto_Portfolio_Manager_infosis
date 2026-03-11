"""
Investment Optimizer Module - Portfolio optimization using mathematical models.
Implements Modern Portfolio Theory, Monte Carlo simulation, and rule-based allocation.
"""

from typing import Dict, List, Optional, Tuple
from pathlib import Path

import pandas as pd
import numpy as np
from scipy.optimize import minimize

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import OPTIMIZATION_CONFIG, RISK_CONFIG
from utils.helpers import (
    logger, timer, calculate_returns, calculate_sharpe_ratio,
    calculate_max_drawdown, format_currency, format_percentage
)


class InvestmentOptimizer:
    """
    Portfolio optimization engine using Modern Portfolio Theory.
    Provides optimal asset allocation through Monte Carlo simulation
    and mathematical optimization.
    """

    def __init__(self):
        self.config = OPTIMIZATION_CONFIG
        self.risk_config = RISK_CONFIG

    # ============================================================
    # MONTE CARLO PORTFOLIO OPTIMIZATION
    # ============================================================
    @timer
    def monte_carlo_optimization(
        self,
        price_data: Dict[str, pd.Series],
        num_portfolios: int = None,
        risk_free_rate: float = None,
    ) -> Dict:
        """
        Run Monte Carlo simulation to find optimal portfolios.

        Args:
            price_data: Dict mapping coin_id to price series
            num_portfolios: Number of random portfolios to generate
            risk_free_rate: Annual risk-free rate

        Returns:
            Dictionary with optimal portfolios and efficient frontier data
        """
        if num_portfolios is None:
            num_portfolios = self.config["num_portfolios"]
        if risk_free_rate is None:
            risk_free_rate = self.risk_config["risk_free_rate"]

        # Calculate returns
        returns_dict = {}
        for coin_id, prices in price_data.items():
            if prices is not None and len(prices) > 30:
                returns_dict[coin_id] = calculate_returns(prices)

        if len(returns_dict) < 2:
            return {"error": "Need at least 2 assets with sufficient data"}

        returns_df = pd.DataFrame(returns_dict).dropna()
        assets = list(returns_df.columns)
        n_assets = len(assets)

        # Annualized returns and covariance
        mean_returns = returns_df.mean() * 365
        cov_matrix = returns_df.cov() * 365

        # Generate random portfolios
        results = np.zeros((num_portfolios, 3))  # return, volatility, sharpe
        weights_record = np.zeros((num_portfolios, n_assets))

        np.random.seed(42)
        for i in range(num_portfolios):
            # Random weights
            w = np.random.random(n_assets)
            w = w / w.sum()

            # Portfolio metrics
            port_return = np.dot(w, mean_returns)
            port_vol = np.sqrt(np.dot(w.T, np.dot(cov_matrix.values, w)))
            sharpe = (port_return - risk_free_rate) / port_vol if port_vol > 0 else 0

            results[i] = [port_return, port_vol, sharpe]
            weights_record[i] = w

        # Find optimal portfolios
        max_sharpe_idx = results[:, 2].argmax()
        min_vol_idx = results[:, 1].argmin()

        # Max Sharpe Ratio Portfolio
        max_sharpe_portfolio = {
            "name": "Maximum Sharpe Ratio Portfolio",
            "weights": dict(zip(assets, weights_record[max_sharpe_idx].tolist())),
            "expected_return": float(results[max_sharpe_idx, 0]),
            "volatility": float(results[max_sharpe_idx, 1]),
            "sharpe_ratio": float(results[max_sharpe_idx, 2]),
        }

        # Minimum Volatility Portfolio
        min_vol_portfolio = {
            "name": "Minimum Volatility Portfolio",
            "weights": dict(zip(assets, weights_record[min_vol_idx].tolist())),
            "expected_return": float(results[min_vol_idx, 0]),
            "volatility": float(results[min_vol_idx, 1]),
            "sharpe_ratio": float(results[min_vol_idx, 2]),
        }

        # Efficient frontier data points
        frontier_returns = np.linspace(results[:, 0].min(), results[:, 0].max(), 50)
        frontier_volatilities = []
        for target_ret in frontier_returns:
            # Find minimum volatility for each target return (approximate)
            mask = np.abs(results[:, 0] - target_ret) < 0.05
            if mask.any():
                frontier_volatilities.append(float(results[mask, 1].min()))
            else:
                frontier_volatilities.append(None)

        return {
            "max_sharpe_portfolio": max_sharpe_portfolio,
            "min_volatility_portfolio": min_vol_portfolio,
            "efficient_frontier": {
                "returns": frontier_returns.tolist(),
                "volatilities": frontier_volatilities,
            },
            "all_portfolios": {
                "returns": results[:, 0].tolist(),
                "volatilities": results[:, 1].tolist(),
                "sharpe_ratios": results[:, 2].tolist(),
            },
            "assets": assets,
            "individual_stats": {
                asset: {
                    "expected_return": float(mean_returns[asset]),
                    "volatility": float(np.sqrt(cov_matrix.loc[asset, asset])),
                }
                for asset in assets
            },
        }

    # ============================================================
    # SCIPY OPTIMIZATION
    # ============================================================
    @timer
    def optimize_portfolio(
        self,
        price_data: Dict[str, pd.Series],
        objective: str = "max_sharpe",
        risk_free_rate: float = None,
    ) -> Dict:
        """
        Optimize portfolio using scipy minimization.

        Args:
            price_data: Dict mapping coin_id to price series
            objective: 'max_sharpe', 'min_volatility', or 'max_return'
            risk_free_rate: Annual risk-free rate

        Returns:
            Optimized portfolio weights and metrics
        """
        if risk_free_rate is None:
            risk_free_rate = self.risk_config["risk_free_rate"]

        returns_dict = {}
        for coin_id, prices in price_data.items():
            if prices is not None and len(prices) > 30:
                returns_dict[coin_id] = calculate_returns(prices)

        if len(returns_dict) < 2:
            return {"error": "Need at least 2 assets"}

        returns_df = pd.DataFrame(returns_dict).dropna()
        assets = list(returns_df.columns)
        n_assets = len(assets)
        mean_returns = returns_df.mean() * 365
        cov_matrix = returns_df.cov() * 365

        # Constraints: weights sum to 1
        constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1}]

        # Bounds: each weight between min and max allocation
        bounds = tuple(
            (self.config["min_allocation"], self.config["max_allocation"])
            for _ in range(n_assets)
        )

        # Initial guess: equal weights
        init_weights = np.array([1.0 / n_assets] * n_assets)

        # Objective function
        def neg_sharpe(weights):
            port_return = np.dot(weights, mean_returns)
            port_vol = np.sqrt(np.dot(weights.T, np.dot(cov_matrix.values, weights)))
            return -(port_return - risk_free_rate) / port_vol if port_vol > 0 else 0

        def portfolio_volatility(weights):
            return np.sqrt(np.dot(weights.T, np.dot(cov_matrix.values, weights)))

        def neg_return(weights):
            return -np.dot(weights, mean_returns)

        objectives = {
            "max_sharpe": neg_sharpe,
            "min_volatility": portfolio_volatility,
            "max_return": neg_return,
        }

        obj_func = objectives.get(objective, neg_sharpe)

        result = minimize(
            obj_func, init_weights,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
            options={"maxiter": 1000}
        )

        if not result.success:
            logger.warning(f"Optimization did not converge: {result.message}")

        optimal_weights = result.x
        port_return = float(np.dot(optimal_weights, mean_returns))
        port_vol = float(np.sqrt(np.dot(optimal_weights.T, np.dot(cov_matrix.values, optimal_weights))))
        sharpe = (port_return - risk_free_rate) / port_vol if port_vol > 0 else 0

        return {
            "objective": objective,
            "optimal_weights": dict(zip(assets, optimal_weights.tolist())),
            "expected_annual_return": port_return,
            "annual_volatility": port_vol,
            "sharpe_ratio": float(sharpe),
            "success": result.success,
            "allocations": [
                {"asset": asset, "weight": float(w), "weight_pct": float(w * 100)}
                for asset, w in zip(assets, optimal_weights)
                if w > 0.01
            ],
        }

    # ============================================================
    # RULE-BASED ALLOCATION
    # ============================================================
    def rule_based_allocation(
        self,
        risk_scores: Dict[str, float],
        market_caps: Dict[str, float],
        investor_profile: str = "moderate"
    ) -> Dict:
        """
        Rule-based portfolio allocation based on risk appetite and market caps.

        Args:
            risk_scores: Dict mapping coin_id to risk score (0-1)
            market_caps: Dict mapping coin_id to market cap
            investor_profile: 'conservative', 'moderate', or 'aggressive'

        Returns:
            Recommended allocation
        """
        profiles = {
            "conservative": {"large_cap": 0.60, "mid_cap": 0.30, "small_cap": 0.10, "max_risk": 0.4},
            "moderate": {"large_cap": 0.40, "mid_cap": 0.35, "small_cap": 0.25, "max_risk": 0.6},
            "aggressive": {"large_cap": 0.20, "mid_cap": 0.30, "small_cap": 0.50, "max_risk": 0.9},
        }

        profile = profiles.get(investor_profile, profiles["moderate"])

        # Classify assets by market cap
        sorted_by_cap = sorted(market_caps.items(), key=lambda x: x[1], reverse=True)
        total = len(sorted_by_cap)
        large_cap = [c[0] for c in sorted_by_cap[:max(1, total // 3)]]
        mid_cap = [c[0] for c in sorted_by_cap[max(1, total // 3):max(2, 2 * total // 3)]]
        small_cap = [c[0] for c in sorted_by_cap[max(2, 2 * total // 3):]]

        # Filter out high-risk assets for conservative profiles
        def filter_by_risk(assets, max_risk):
            return [a for a in assets if risk_scores.get(a, 0.5) <= max_risk]

        large_cap = filter_by_risk(large_cap, profile["max_risk"])
        mid_cap = filter_by_risk(mid_cap, profile["max_risk"])
        small_cap = filter_by_risk(small_cap, profile["max_risk"])

        # Allocate weights
        allocation = {}

        def distribute_weight(assets, total_weight):
            if not assets:
                return
            weight_per_asset = total_weight / len(assets)
            for asset in assets:
                allocation[asset] = weight_per_asset

        distribute_weight(large_cap, profile["large_cap"])
        distribute_weight(mid_cap, profile["mid_cap"])
        distribute_weight(small_cap, profile["small_cap"])

        # Normalize
        total_weight = sum(allocation.values())
        if total_weight > 0:
            allocation = {k: v / total_weight for k, v in allocation.items()}

        return {
            "investor_profile": investor_profile,
            "allocation": allocation,
            "categories": {
                "large_cap": large_cap,
                "mid_cap": mid_cap,
                "small_cap": small_cap,
            },
            "profile_settings": profile,
        }

    # ============================================================
    # REBALANCING ENGINE
    # ============================================================
    @timer
    def calculate_rebalancing(
        self,
        current_holdings: Dict[str, float],  # coin_id -> current value
        target_weights: Dict[str, float],     # coin_id -> target weight (0-1)
        current_prices: Dict[str, float],     # coin_id -> price
        total_portfolio_value: float = None,
    ) -> Dict:
        """
        Calculate trades needed to rebalance portfolio to target weights.

        Returns:
            Dictionary with trade recommendations
        """
        if total_portfolio_value is None:
            total_portfolio_value = sum(current_holdings.values())

        if total_portfolio_value <= 0:
            return {"error": "Portfolio value is zero or negative"}

        # Current weights
        current_weights = {
            k: v / total_portfolio_value for k, v in current_holdings.items()
        }

        trades = []
        total_buy = 0
        total_sell = 0

        all_assets = set(list(current_holdings.keys()) + list(target_weights.keys()))

        for asset in all_assets:
            current_weight = current_weights.get(asset, 0)
            target_weight = target_weights.get(asset, 0)
            weight_diff = target_weight - current_weight

            current_value = current_holdings.get(asset, 0)
            target_value = target_weight * total_portfolio_value
            value_diff = target_value - current_value

            price = current_prices.get(asset, 1)
            quantity_change = value_diff / price if price > 0 else 0

            if abs(weight_diff) > 0.005:  # Only trade if drift > 0.5%
                trade = {
                    "asset": asset,
                    "action": "BUY" if value_diff > 0 else "SELL",
                    "current_weight": float(current_weight * 100),
                    "target_weight": float(target_weight * 100),
                    "weight_change": float(weight_diff * 100),
                    "value_change": float(value_diff),
                    "quantity_change": float(quantity_change),
                    "current_value": float(current_value),
                    "target_value": float(target_value),
                }
                trades.append(trade)

                if value_diff > 0:
                    total_buy += value_diff
                else:
                    total_sell += abs(value_diff)

        trades.sort(key=lambda x: abs(x["value_change"]), reverse=True)

        return {
            "trades": trades,
            "total_buy_value": float(total_buy),
            "total_sell_value": float(total_sell),
            "num_trades": len(trades),
            "portfolio_value": float(total_portfolio_value),
            "current_weights": current_weights,
            "target_weights": target_weights,
            "is_rebalance_needed": len(trades) > 0,
        }


if __name__ == "__main__":
    from backend.data_collector import generate_sample_data

    print("📊 Running Portfolio Optimization...\n")
    datasets = generate_sample_data(
        ["bitcoin", "ethereum", "solana", "cardano", "polkadot"], days=365
    )

    optimizer = InvestmentOptimizer()
    price_data = {coin_id: df["price"] for coin_id, df in datasets.items()}

    # Monte Carlo
    mc_result = optimizer.monte_carlo_optimization(price_data)
    if "error" not in mc_result:
        print("🎯 Maximum Sharpe Ratio Portfolio:")
        for asset, weight in mc_result["max_sharpe_portfolio"]["weights"].items():
            print(f"  {asset:15s}: {weight*100:.1f}%")
        print(f"  Expected Return: {mc_result['max_sharpe_portfolio']['expected_return']*100:.1f}%")
        print(f"  Volatility: {mc_result['max_sharpe_portfolio']['volatility']*100:.1f}%")
        print(f"  Sharpe Ratio: {mc_result['max_sharpe_portfolio']['sharpe_ratio']:.3f}")

    # Scipy optimization
    opt_result = optimizer.optimize_portfolio(price_data, objective="max_sharpe")
    if "error" not in opt_result:
        print(f"\n🔧 Optimized Portfolio (Max Sharpe):")
        for alloc in opt_result["allocations"]:
            print(f"  {alloc['asset']:15s}: {alloc['weight_pct']:.1f}%")
