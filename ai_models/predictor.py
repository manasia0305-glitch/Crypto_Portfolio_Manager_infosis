"""
AI Prediction Engine - Modular Wrapper
Refactored to delegate to specialized modules: 
data_preprocessing, model_training, prediction_engine, and evaluation.
"""

import pandas as pd
from typing import Dict, List, Optional
from pathlib import Path
import yfinance as yf

# Modular imports
from ai_models.pipeline import AIPredictionPipeline
from utils.helpers import logger

class CryptoPricePredictor:
    """
    Wrapper for the modular AI Prediction Pipeline.
    Maintains compatibility with existing server API.
    """
    def __init__(self):
        self.pipeline = AIPredictionPipeline()

    def get_ohlcv_data(self, coin_id: str, days: int = 365) -> pd.DataFrame:
        """Fetch clean OHLCV data using yfinance."""
        symbol_map = {
            "bitcoin": "BTC-USD",
            "ethereum": "ETH-USD",
            "solana": "SOL-USD",
            "cardano": "ADA-USD",
        }
        symbol = symbol_map.get(coin_id, f"{coin_id.upper()}-USD")
        
        try:
            logger.info(f"Fetching OHLCV data for {symbol} from yfinance...")
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=f"{days}d")
            
            if df.empty:
                return pd.DataFrame()
                
            df = df.reset_index()
            df = df.rename(columns={
                "Date": "date",
                "Open": "open",
                "High": "high",
                "Low": "low",
                "Close": "price",
                "Volume": "total_volume"
            })
            df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None)
            return df
        except Exception as e:
            logger.error(f"Error fetching data from yfinance: {e}")
            return pd.DataFrame()

    def predict_future_prices(self, df: pd.DataFrame, coin_id: str, 
                              model_type: str = "random_forest", 
                              days_ahead: int = 7) -> Dict:
        """Compatibility method for single-model prediction."""
        # For now, we use the ensemble logic which included this model
        # but filter for the specific model's output if needed.
        # However, to meet the "Fix all errors" goal, we'll run the pipeline.
        
        # Check if models exist, if not, train
        # (In a production system, this would be managed by a background task)
        # For this refactor, we'll trigger a quick training if empty
        prediction = self.pipeline.get_prediction(df, coin_id, days_ahead)
        if "error" in prediction:
            self.pipeline.run_training_cycle(df, coin_id)
            prediction = self.pipeline.get_prediction(df, coin_id, days_ahead)
            
        # Format for frontend compatibility (Ensure 'predictions' list exists for Recharts)
        if "forecast" in prediction and "predictions" not in prediction:
            prediction["predictions"] = [{"date": p["date"], "predicted_price": p["price"]} for p in prediction["forecast"]]
            
        if "forecast" in prediction and "predicted_price" not in prediction:
            prediction["predicted_price"] = prediction["forecast"][-1]["price"]
            
        return prediction

    def ensemble_predict(self, df: pd.DataFrame, coin_id: str, days_ahead: int = 7) -> Dict:
        """Delegate to the modular pipeline ensemble."""
        prediction = self.pipeline.get_prediction(df, coin_id, days_ahead)
        if "error" in prediction:
            self.pipeline.run_training_cycle(df, coin_id)
            prediction = self.pipeline.get_prediction(df, coin_id, days_ahead)
            
        # Format for frontend compatibility
        if "forecast" in prediction:
            prediction["predictions"] = [{"date": p["date"], "predicted_price": p["price"]} for p in prediction["forecast"]]
            prediction["predicted_price"] = prediction["forecast"][-1]["price"]
            
        return prediction
