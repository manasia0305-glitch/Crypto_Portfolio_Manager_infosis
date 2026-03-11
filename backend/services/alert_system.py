"""
Alert and Notification System - Monitors crypto markets and sends alerts using MongoDB.
"""

from datetime import datetime
from typing import Dict, List, Optional
from bson import ObjectId
from database.mongo_connection import get_database
from utils.helpers import logger, format_currency, format_percentage
from config.settings import ALERT_CONFIG, EMAIL_CONFIG

class AlertSystem:
    def __init__(self):
        self.config = ALERT_CONFIG
        self.email_config = EMAIL_CONFIG
        self.alerts_triggered = []

    async def create_price_alert(self, user_id, coin_id, alert_type="price_above", threshold=None, message=""):
        db = get_database()
        try:
            alert = {
                "user_id": ObjectId(user_id),
                "coin_id": coin_id,
                "alert_type": alert_type,
                "threshold": threshold or self.config["price_change_threshold"],
                "message": message or f"Price alert for {coin_id}",
                "is_active": True,
                "is_triggered": False,
                "created_at": datetime.utcnow()
            }
            result = await db["alerts"].insert_one(alert)
            logger.info(f"Created price alert for {coin_id}: {alert_type} at {threshold}")
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"Error creating alert: {e}")
            return None

    async def check_alerts(self, market_data):
        triggered = []
        db = get_database()
        try:
            cursor = db["alerts"].find({"is_active": True, "is_triggered": False})
            async for alert in cursor:
                for coin in market_data:
                    if coin.get("coin_id") != alert["coin_id"]:
                        continue
                    
                    price = coin.get("price", 0)
                    threshold = alert["threshold"]
                    should_trigger = False
                    
                    if alert["alert_type"] == "price_above" and price >= threshold:
                        should_trigger = True
                    elif alert["alert_type"] == "price_below" and price <= threshold:
                        should_trigger = True
                        
                    if should_trigger:
                        await db["alerts"].update_one(
                            {"_id": alert["_id"]},
                            {"$set": {"is_triggered": True, "triggered_at": datetime.utcnow()}}
                        )
                        triggered.append({
                            "alert_id": str(alert["_id"]),
                            "user_id": str(alert["user_id"]),
                            "message": f"Alert triggered for {alert['coin_id']}: Price reached {price}"
                        })
            return triggered
        except Exception as e:
            logger.error(f"Error checking alerts: {e}")
            return []
