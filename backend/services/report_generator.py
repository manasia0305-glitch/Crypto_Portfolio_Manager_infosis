"""
Report Generator - Generates detailed portfolio and market analysis reports.
Exports reports as CSV and formatted text summaries.
"""

import csv
from datetime import datetime
from typing import Dict, List
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.settings import REPORTS_DIR
from utils.helpers import logger, timer, format_currency, format_percentage


class ReportGenerator:
    def __init__(self):
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    @timer
    def generate_portfolio_report(self, portfolio_data, risk_data=None, predictions=None):
        """Generate a comprehensive portfolio report."""
        if not portfolio_data:
            return {"error": "No portfolio data"}
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report = {"generated_at": str(datetime.now()), "portfolio_summary": {
            "name": portfolio_data.get("name", "Portfolio"),
            "total_value": portfolio_data.get("total_value", 0),
            "total_cost": portfolio_data.get("total_cost", 0),
            "total_pnl": portfolio_data.get("total_value", 0) - portfolio_data.get("total_cost", 0),
            "total_pnl_pct": portfolio_data.get("total_pl_pct", 0),
            "num_assets": portfolio_data.get("num_assets", 0)}}
        # Holdings detail
        holdings = []
        for item in portfolio_data.get("assets", []):
            holding = {"symbol": item.get("symbol", ""), "name": item.get("name", ""),
                "quantity": item.get("quantity", 0), "purchase_price": item.get("purchase_price", 0),
                "current_price": item.get("current_price", 0), "current_value": item.get("current_value", 0),
                "profit_loss": item.get("profit_loss", 0), "profit_loss_pct": item.get("profit_loss_pct", 0),
                "allocation_pct": item.get("allocation_pct", 0)}
            if risk_data and item.get("coin_id") in risk_data:
                rd = risk_data[item["coin_id"]]
                holding["risk_score"] = rd.get("risk_score", 0)
                holding["risk_label"] = rd.get("risk_label", "")
                holding["volatility"] = rd.get("volatility", {}).get("annualized", 0)
            if predictions and item.get("coin_id") in predictions:
                pd_item = predictions[item["coin_id"]]
                holding["predicted_price"] = pd_item.get("predicted_price_final", 0)
                holding["predicted_change_pct"] = pd_item.get("predicted_change_pct", 0)
            holdings.append(holding)
        report["holdings"] = holdings
        # Export CSV
        csv_path = REPORTS_DIR / f"portfolio_report_{timestamp}.csv"
        self._export_holdings_csv(holdings, csv_path)
        report["csv_path"] = str(csv_path)
        # Text summary
        report["text_summary"] = self._generate_text_summary(report)
        logger.info(f"Portfolio report generated: {csv_path}")
        return report

    @timer
    def generate_market_report(self, market_data, risk_analyses=None):
        """Generate a market overview report."""
        if not market_data:
            return {"error": "No market data"}
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_data = []
        for coin in market_data[:50]:
            row = {"rank": coin.get("market_cap_rank", ""), "name": coin.get("name", ""),
                "symbol": coin.get("symbol", "").upper(), "price": coin.get("current_price", 0),
                "market_cap": coin.get("market_cap", 0), "volume_24h": coin.get("total_volume", 0),
                "change_24h_pct": coin.get("price_change_percentage_24h", 0)}
            if risk_analyses and coin.get("id") in risk_analyses:
                ra = risk_analyses[coin["id"]]
                row["risk_score"] = ra.get("risk_score", 0)
                row["risk_label"] = ra.get("risk_label", "")
            report_data.append(row)
        csv_path = REPORTS_DIR / f"market_report_{timestamp}.csv"
        if report_data:
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=report_data[0].keys())
                writer.writeheader(); writer.writerows(report_data)
        logger.info(f"Market report generated: {csv_path}")
        return {"generated_at": str(datetime.now()), "num_coins": len(report_data),
            "csv_path": str(csv_path), "data": report_data}

    @timer
    def generate_prediction_report(self, predictions):
        """Generate prediction summary report."""
        if not predictions:
            return {"error": "No predictions"}
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        rows = []
        for coin_id, pred in predictions.items():
            if "error" in pred: continue
            rows.append({"coin_id": coin_id, "current_price": pred.get("current_price", 0),
                "predicted_price": pred.get("predicted_price_final", 0),
                "change_pct": pred.get("predicted_change_pct", 0),
                "direction": pred.get("prediction_direction", ""),
                "model": pred.get("model_type", "")})
        csv_path = REPORTS_DIR / f"prediction_report_{timestamp}.csv"
        if rows:
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                writer.writeheader(); writer.writerows(rows)
        return {"generated_at": str(datetime.now()), "predictions": rows, "csv_path": str(csv_path)}

    def _export_holdings_csv(self, holdings, csv_path):
        if not holdings: return
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=holdings[0].keys())
            writer.writeheader(); writer.writerows(holdings)

    def _generate_text_summary(self, report):
        ps = report.get("portfolio_summary", {})
        lines = [
            "=" * 60,
            "📊 PORTFOLIO REPORT",
            f"Generated: {report.get('generated_at', '')}",
            "=" * 60,
            f"Portfolio: {ps.get('name', '')}",
            f"Total Value: {format_currency(ps.get('total_value', 0))}",
            f"Total Cost: {format_currency(ps.get('total_cost', 0))}",
            f"Total P&L: {format_currency(ps.get('total_pnl', 0))} ({format_percentage(ps.get('total_pnl_pct', 0))})",
            f"Assets: {ps.get('num_assets', 0)}",
            "", "HOLDINGS:", "-" * 60]
        for h in report.get("holdings", []):
            lines.append(f"  {h.get('symbol',''):6s} | Value: {format_currency(h.get('current_value',0)):>10s} | "
                f"P&L: {format_percentage(h.get('profit_loss_pct',0)):>8s} | Alloc: {h.get('allocation_pct',0):.1f}%")
        lines.append("=" * 60)
        return "\n".join(lines)
