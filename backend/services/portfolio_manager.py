"""
Portfolio Manager Module - Manages cryptocurrency portfolios using MongoDB.
Handles CRUD operations, P&L calculations, and allocation tracking.
"""

from datetime import datetime
from typing import Dict, List, Optional, Tuple
from bson import ObjectId
from database.mongo_connection import get_database
from utils.helpers import logger

class PortfolioManager:
    """
    Manages user cryptocurrency portfolios.
    Provides CRUD operations, value tracking, P&L analysis,
    and allocation calculations.
    """

    def __init__(self):
        pass

    async def create_portfolio(self, user_id: str, name: str = "My Portfolio", description: str = "") -> str:
        """Create a new portfolio. Returns portfolio ID."""
        db = get_database()
        try:
            portfolio = {
                "user_id": ObjectId(user_id),
                "name": name,
                "description": description,
                "assets": [],
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            result = await db["portfolios"].insert_one(portfolio)
            logger.info(f"Created portfolio '{name}' for user {user_id}")
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"Error creating portfolio: {e}")
            return None

    async def get_portfolio(self, portfolio_id: str) -> Optional[Dict]:
        """Get portfolio details including all items."""
        db = get_database()
        try:
            portfolio = await db["portfolios"].find_one({"_id": ObjectId(portfolio_id)})
            if not portfolio:
                return None

            items = []
            total_value = 0
            total_cost = 0

            for asset in portfolio.get("assets", []):
                # Fetch current price from market_data collection (latest)
                market_data = await db["market_data"].find_one(
                    {"coin_id": asset["coin_id"]},
                    sort=[("timestamp", -1)]
                )
                
                # Fetch metadata
                crypto = await db["cryptocurrencies"].find_one({"coin_id": asset["coin_id"]})
                
                current_price = market_data["price"] if market_data else 0
                current_value = asset["quantity"] * current_price
                cost_basis = asset["quantity"] * asset["purchase_price"]
                profit_loss = current_value - cost_basis
                profit_loss_pct = (profit_loss / cost_basis * 100) if cost_basis > 0 else 0

                total_value += current_value
                total_cost += cost_basis

                items.append({
                    "coin_id": asset["coin_id"],
                    "name": crypto["name"] if crypto else asset["coin_id"].capitalize(),
                    "symbol": crypto["symbol"] if crypto else "",
                    "quantity": asset["quantity"],
                    "purchase_price": asset["purchase_price"],
                    "current_price": current_price,
                    "current_value": current_value,
                    "cost_basis": cost_basis,
                    "profit_loss": profit_loss,
                    "profit_loss_pct": profit_loss_pct,
                    "purchase_date": asset.get("purchase_date"),
                })

            # Calculate allocation percentages
            for item in items:
                item["allocation_pct"] = (
                    (item["current_value"] / total_value * 100) if total_value > 0 else 0
                )

            total_pl = total_value - total_cost
            total_pl_pct = (total_pl / total_cost * 100) if total_cost > 0 else 0

            return {
                "id": str(portfolio["_id"]),
                "name": portfolio["name"],
                "description": portfolio.get("description"),
                "total_value": total_value,
                "total_cost": total_cost,
                "total_pl": total_pl,
                "total_pl_pct": total_pl_pct,
                "assets": items,
                "num_assets": len(items)
            }
        except Exception as e:
            logger.error(f"Error fetching portfolio {portfolio_id}: {e}")
            return None

    async def add_asset(self, portfolio_id: str, coin_id: str, quantity: float, purchase_price: float) -> bool:
        """Add an asset to a portfolio."""
        db = get_database()
        try:
            asset = {
                "coin_id": coin_id,
                "quantity": quantity,
                "purchase_price": purchase_price,
                "purchase_date": datetime.utcnow()
            }
            await db["portfolios"].update_one(
                {"_id": ObjectId(portfolio_id)},
                {"$push": {"assets": asset}, "$set": {"updated_at": datetime.utcnow()}}
            )
            return True
        except Exception as e:
            logger.error(f"Error adding asset to portfolio {portfolio_id}: {e}")
            return False

    async def remove_asset(self, portfolio_id: str, coin_id: str) -> bool:
        """Remove all holdings of a specific coin from a portfolio."""
        db = get_database()
        try:
            await db["portfolios"].update_one(
                {"_id": ObjectId(portfolio_id)},
                {"$pull": {"assets": {"coin_id": coin_id}}, "$set": {"updated_at": datetime.utcnow()}}
            )
            return True
        except Exception as e:
            logger.error(f"Error removing asset {coin_id} from portfolio {portfolio_id}: {e}")
            return False

    async def list_portfolios(self, user_id: str) -> List[Dict]:
        """List all portfolios for a user."""
        db = get_database()
        try:
            cursor = db["portfolios"].find({"user_id": ObjectId(user_id)})
            portfolios = []
            async for p in cursor:
                portfolios.append(await self.get_portfolio(str(p["_id"])))
            return portfolios
        except Exception as e:
            logger.error(f"Error listing portfolios for user {user_id}: {e}")
            return []
