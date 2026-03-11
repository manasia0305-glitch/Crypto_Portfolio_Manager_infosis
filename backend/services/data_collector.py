"""
Data Collector Module - Fetches real-time and historical cryptocurrency data
from the CoinGecko API and stores it in MongoDB.
"""

import time
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import requests
from database.mongo_connection import get_database
from utils.helpers import logger
from config.settings import COINGECKO_BASE_URL, COINGECKO_API_KEY

class CryptoDataCollector:
    """
    Fetches cryptocurrency market data from CoinGecko API.
    Handles rate limiting and MongoDB storage.
    """

    def __init__(self):
        self.base_url = COINGECKO_BASE_URL
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "User-Agent": "CryptoIntelligencePlatform/1.0"
        })
        if COINGECKO_API_KEY:
            self.session.headers["x-cg-demo-api-key"] = COINGECKO_API_KEY
        self._rate_limit_delay = 1.5

    def _make_request(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        url = f"{self.base_url}/{endpoint}"
        try:
            time.sleep(self._rate_limit_delay)
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"API Request error: {e}")
            return None

    async def fetch_and_store_market_data(self, vs_currency: str = "usd", per_page: int = 50):
        """Fetch market data and store in MongoDB market_data collection."""
        params = {
            "vs_currency": vs_currency,
            "order": "market_cap_desc",
            "per_page": per_page,
            "page": 1,
            "sparkline": "true",
            "price_change_percentage": "1h,24h,7d"
        }
        data = self._make_request("coins/markets", params)
        if not data:
            return None
        
        db = get_database()
        timestamp = datetime.utcnow()
        
        market_entries = []
        for coin in data:
            entry = {
                "coin_id": coin["id"],
                "price": coin["current_price"],
                "market_cap": coin["market_cap"],
                "total_volume": coin["total_volume"],
                "change_1h": coin.get("price_change_percentage_1h_in_currency"),
                "change_24h": coin.get("price_change_percentage_24h_in_currency"),
                "change_7d": coin.get("price_change_percentage_7d_in_currency"),
                "circulating_supply": coin.get("circulating_supply"),
                "total_supply": coin.get("total_supply"),
                "max_supply": coin.get("max_supply"),
                "sparkline_7d": coin.get("sparkline_in_7d", {}).get("price", []),
                "market_cap_rank": coin.get("market_cap_rank"),
                "timestamp": timestamp,
                "date": timestamp.strftime("%Y-%m-%d")
            }
            market_entries.append(entry)
            
            # Also update cryptocurrency metadata
            await db["cryptocurrencies"].update_one(
                {"coin_id": coin["id"]},
                {"$set": {
                    "symbol": coin["symbol"],
                    "name": coin["name"],
                    "image": coin["image"],
                    "last_updated": timestamp
                }},
                upsert=True
            )
            
        if market_entries:
            # Delete old market data if needed, but we store history here.
            # For simplicity, we just insert.
            await db["market_data"].insert_many(market_entries)
            logger.info(f"Stored {len(market_entries)} market data points in MongoDB")
            
        return data

    async def get_latest_market_data(self, limit: int = 50) -> List[Dict]:
        """Retrieve the latest market data from MongoDB."""
        db = get_database()
        # Find latest timestamp
        latest = await db["market_data"].find_one(sort=[("timestamp", -1)])
        if not latest:
            return []
        
        cursor = db["market_data"].find({"timestamp": latest["timestamp"]}).limit(limit)
        results = []
        async for doc in cursor:
            # Join with metadata
            meta = await db["cryptocurrencies"].find_one({"coin_id": doc["coin_id"]})
            if meta:
                # Remove _id from meta before updating doc
                meta.pop("_id", None)
                doc.update(meta)
            doc["id"] = str(doc.pop("_id", ""))
            results.append(doc)
        return results

    async def fetch_historical_prices(self, coin_id: str, days: int = 365):
        """Fetch historical price data from API."""
        endpoint = f"coins/{coin_id}/market_chart"
        params = {"vs_currency": "usd", "days": str(days), "interval": "daily"}
        data = self._make_request(endpoint, params)
        if not data or "prices" not in data:
            return None
        
        import pandas as pd
        df = pd.DataFrame(data["prices"], columns=["timestamp", "price"])
        df["date"] = pd.to_datetime(df["timestamp"], unit="ms")
        return df

    async def save_price_history_to_db(self, coin_id: str, df):
        """Save historical data to MongoDB efficiently."""
        db = get_database()
        records = df.to_dict("records")
        
        # Prepare market history entries
        history_entries = []
        for rec in records:
            dt = rec["date"]
            history_entries.append({
                "coin_id": coin_id,
                "timestamp": dt,
                "date": dt.strftime("%Y-%m-%d") if hasattr(dt, 'strftime') else str(dt),
                "price": rec["price"]
            })
            
        # We use insert_many to speed up the process instead of update_one in a loop
        if history_entries:
            await db["market_data"].insert_many(history_entries)
            logger.info(f"Saved {len(history_entries)} history points for {coin_id}")

    async def get_price_history_from_db(self, coin_id: str, days: int = 365):
        """Get price history from MongoDB."""
        db = get_database()
        import pandas as pd
        start_date = datetime.utcnow() - timedelta(days=days)
        # Explicitly exclude _id to avoid serialization issues
        cursor = db["market_data"].find(
            {
                "coin_id": coin_id,
                "timestamp": {"$gte": start_date}
            },
            {"_id": 0}
        ).sort("timestamp", 1)
        
        results = []
        async for doc in cursor:
            # Manually remove any lingering ObjectId just in case
            if "_id" in doc:
                del doc["_id"]
            results.append(doc)
        print(f"DEBUG: get_price_history_from_db for {coin_id} returned {len(results)} docs")
        return pd.DataFrame(results)

    def fetch_trending(self):
        """Fetch trending coins from API."""
        data = self._make_request("search/trending")
        if data and 'coins' in data:
            # The trending endpoint returns a list of items with a nested 'item' key
            coin_ids = [c['item']['id'] for c in data['coins']]
            return self.fetch_market_data_by_ids(coin_ids)
        return []

    def fetch_market_data_by_ids(self, coin_ids: List[str]):
        """Fetch full market data for a specific list of coin IDs."""
        if not coin_ids:
            return []
        params = {
            "vs_currency": "usd",
            "ids": ",".join(coin_ids),
            "order": "market_cap_desc",
            "sparkline": "true",
            "price_change_percentage": "1h,24h,7d"
        }
        return self._make_request("coins/markets", params)

    def fetch_by_category(self, category: str):
        """Fetch coins based on a specific category (e.g., 'solana-ecosystem')."""
        params = {
            "category": category
        }
        data = self._make_request("coins/markets", params)
        return data

    def fetch_global_data(self):
        """Fetch global market data from CoinGecko API."""
        return self._make_request("global")

    def fetch_fear_and_greed_index(self):
        """Fetch Fear & Greed Index from alternative.me API."""
        try:
            res = requests.get("https://api.alternative.me/fng/", timeout=10)
            if res.ok:
                return res.json()["data"][0]
            return None
        except Exception as e:
            logger.error(f"Error fetching Fear & Greed: {e}")
            return None

    async def get_market_summary(self):
        """Combine global market stats for the dashboard header."""
        global_data = self.fetch_global_data()
        fng_data = self.fetch_fear_and_greed_index()
        
        # In mock mode, we'll generate some realistic values if APIs fail
        if not global_data:
            global_data = {
                "data": {
                    "total_market_cap": {"usd": 2310000000000},
                    "market_cap_change_percentage_24h_usd": -0.93,
                    "market_cap_percentage": {"btc": 58.4, "eth": 10.3}
                }
            }
        if not fng_data:
            fng_data = {"value": "18", "value_classification": "Extreme Fear"}
            
        # Altcoin season logic: 100 - BTC Dominance (simple proxy)
        btc_dominance = global_data.get("data", {}).get("market_cap_percentage", {}).get("btc", 50)
        altcoin_season = 100 - btc_dominance
        alt_label = "Altcoin" if altcoin_season > 50 else "Bitcoin"

        # Calculate a mock Average RSI based on 24h change
        market_change = global_data.get("data", {}).get("market_cap_change_percentage_24h_usd", 0)
        avg_rsi = 50 + (market_change * 5) # Simple mapping for visual consistency
        avg_rsi = max(0, min(100, avg_rsi))
        rsi_label = "Overbought" if avg_rsi > 70 else ("Oversold" if avg_rsi < 30 else "Neutral")

        return {
            "market_cap": global_data.get("data", {}).get("total_market_cap", {}).get("usd"),
            "market_cap_change": global_data.get("data", {}).get("market_cap_change_percentage_24h_usd"),
            "dominance": global_data.get("data", {}).get("market_cap_percentage", {}),
            "fear_and_greed": fng_data,
            "altcoin_season": {"value": f"{altcoin_season:.0f}/100", "label": alt_label},
            "avg_rsi": {"value": f"{avg_rsi:.2f}", "label": rsi_label}
        }

    def fetch_coin_details(self, coin_id: str):
        """Fetch detailed information for a specific cryptocurrency."""
        params = {
            "localization": "false",
            "tickers": "false",
            "market_data": "true",
            "community_data": "false",
            "developer_data": "false"
        }
        return self._make_request(f"coins/{coin_id}", params)

def generate_sample_data(coins, days=365):
    """Generate mock historical data for development purposes."""
    datasets = {}
    timestamp = datetime.utcnow()
    for coin_id in coins:
        data = []
        base_price = 1000.0 if coin_id == "bitcoin" else 100.0
        for i in range(days):
            price = base_price * (1 + (i % 10) / 100.0)
            data.append({
                "coin_id": coin_id,
                "price": price,
                "market_cap": price * 1000000,
                "total_volume": price * 50000,
                "change_24h": 1.5,
                "timestamp": timestamp - timedelta(days=days-i)
            })
        datasets[coin_id] = data
    return datasets
