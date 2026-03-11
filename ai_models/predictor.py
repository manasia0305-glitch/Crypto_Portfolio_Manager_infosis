"""
AI Prediction Engine - Machine Learning models for cryptocurrency price prediction.
Includes Linear Regression, Random Forest, and LSTM models.
"""

import os
import pickle
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from pathlib import Path

import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.tree import DecisionTreeRegressor
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import ML_CONFIG, MODELS_DIR, DATA_DIR
from utils.helpers import logger, timer


class CryptoPricePredictor:
    """
    Machine Learning prediction engine for cryptocurrency prices.
    Supports multiple models: Linear Regression, Random Forest, Gradient Boosting.
    """

    def __init__(self):
        self.config = ML_CONFIG
        self.models = {}
        self.scalers = {}

    # ============================================================
    # FEATURE ENGINEERING
    # ============================================================
    def create_features(self, df: pd.DataFrame, drop_nans: bool = True) -> pd.DataFrame:
        """
        Create technical indicator features from price data.

        Features include:
        - Moving averages (SMA, EMA)
        - Price momentum
        - Volatility indicators
        - Volume indicators
        - Lagged prices
        """
        data = df.copy()

        # Ensure proper types
        data["price"] = data["price"].astype(float)
        if "total_volume" in data.columns:
            data["total_volume"] = pd.to_numeric(data["total_volume"], errors="coerce").fillna(0)

        # ---- Moving Averages ----
        data["sma_7"] = data["price"].rolling(window=7).mean()
        data["sma_14"] = data["price"].rolling(window=14).mean()
        data["sma_30"] = data["price"].rolling(window=30).mean()
        data["sma_50"] = data["price"].rolling(window=50).mean()
        data["ema_12"] = data["price"].ewm(span=12, adjust=False).mean()
        data["ema_26"] = data["price"].ewm(span=26, adjust=False).mean()

        # MACD
        data["macd"] = data["ema_12" ] - data["ema_26"]
        data["macd_signal" ] = data["macd"].ewm(span=9, adjust=False).mean()

        # ---- Price Momentum ----
        data["return_1d"] = data["price"].pct_change(1)
        data["return_3d"] = data["price"].pct_change(3)
        data["return_7d"] = data["price"].pct_change(7)
        data["return_14d"] = data["price"].pct_change(14)
        data["return_30d"] = data["price"].pct_change(30)

        # ---- Volatility ----
        data["volatility_7"] = data["return_1d"].rolling(window=7).std()
        data["volatility_14"] = data["return_1d"].rolling(window=14).std()
        data["volatility_30"] = data["return_1d"].rolling(window=30).std()

        # ---- Bollinger Bands ----
        data["bb_middle"] = data["sma_14"]
        data["bb_std"] = data["price"].rolling(window=14).std()
        data["bb_upper"] = data["bb_middle"] + 2 * data["bb_std"]
        data["bb_lower"] = data["bb_middle"] - 2 * data["bb_std"]
        data["bb_position"] = (data["price"] - data["bb_lower"]) / (
            data["bb_upper"] - data["bb_lower"]
        ).replace(0, 1e-9)

        # ---- RSI (Relative Strength Index) ----
        delta = data["price"].diff()
        gain = delta.where(delta > 0, 0).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss.replace(0, np.nan)
        data["rsi"] = 100 - (100 / (1 + rs))

        # ---- Volume features ----
        if "total_volume" in data.columns:
            data["volume_sma_7"] = data["total_volume"].rolling(window=7).mean()
            data["volume_ratio"] = data["total_volume"] / data["volume_sma_7"].replace(0, np.nan)

        # ---- Lagged prices ----
        for lag in [1, 3, 7, 14]:
            data[f"price_lag_{lag}"] = data["price"].shift(lag)

        # ---- Price relative to SMAs ----
        data["price_to_sma7"] = data["price"] / data["sma_7"].replace(0, np.nan)
        data["price_to_sma30"] = data["price"] / data["sma_30"].replace(0, np.nan)

        # ---- Day of week / day of month ----
        if "date" in data.columns:
            dates = pd.to_datetime(data["date"])
            data["day_of_week"] = dates.dt.dayofweek
            data["day_of_month"] = dates.dt.day

        if not drop_nans:
            return data

        # Drop NaN rows from feature calculation
        original_len = len(data)
        all_possible_features = self.get_feature_columns()
        
        # Only drop rows where essential features are NaN
        existing_features = [f for f in all_possible_features if f in data.columns]
        
        data = data.dropna(subset=existing_features + ["price"])
        
        # If we dropped everything, try again with fewer features
        if len(data) == 0 and original_len > 0:
            essential = ["sma_7", "sma_14", "return_1d", "price"]
            existing_essential = [f for f in essential if f in data.columns or f == "price"]
            data = df.copy()
            # Recalculate only essential
            data["sma_7"] = data["price"].rolling(window=7).mean()
            data["sma_14"] = data["price"].rolling(window=14).mean()
            data["return_1d"] = data["price"].pct_change(1)
            data = data.dropna(subset=existing_essential)

        return data

    def get_feature_columns(self) -> List[str]:
        """Get the list of feature column names used for prediction."""
        return [
            "sma_7", "sma_14", "sma_30", "sma_50",
            "ema_12", "ema_26", "macd", "macd_signal",
            "return_1d", "return_3d", "return_7d", "return_14d", "return_30d",
            "volatility_7", "volatility_14", "volatility_30",
            "bb_position", "rsi",
            "price_lag_1", "price_lag_3", "price_lag_7", "price_lag_14",
            "price_to_sma7", "price_to_sma30",
            "day_of_week", "day_of_month",
        ]

    # ============================================================
    # MODEL TRAINING
    # ============================================================
    @timer
    def train_linear_regression(self, df: pd.DataFrame, coin_id: str) -> Dict:
        """Train a Linear Regression model for price prediction."""
        data = self.create_features(df)
        features = [f for f in self.get_feature_columns() if f in data.columns]

        X = data[features].values
        y = data["price"].values

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=self.config["test_split"],
            random_state=self.config["random_state"], shuffle=False
        )

        # Scale features
        scaler = MinMaxScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)

        # Train model
        model = LinearRegression()
        model.fit(X_train_scaled, y_train)

        # Evaluate
        y_pred = model.predict(X_test_scaled)
        metrics = self._calculate_metrics(y_test, y_pred)

        # Save model
        model_key = f"{coin_id}_linear_regression"
        self.models[model_key] = model
        self.scalers[model_key] = scaler
        self._save_model(model, scaler, model_key)

        logger.info(f"Linear Regression trained for {coin_id} | MAE: {metrics['mae']:.2f}")

        return {
            "model_type": "linear_regression",
            "coin_id": coin_id,
            "metrics": metrics,
            "feature_importance": dict(zip(features, model.coef_.tolist())),
            "predictions_test": y_pred.tolist(),
            "actual_test": y_test.tolist(),
        }

    @timer
    def train_decision_tree(self, df: pd.DataFrame, coin_id: str) -> Dict:
        """Train a Decision Tree model for price prediction."""
        data = self.create_features(df)
        features = [f for f in self.get_feature_columns() if f in data.columns]

        X = data[features].values
        y = data["price"].values

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=self.config["test_split"],
            random_state=self.config["random_state"], shuffle=False
        )

        scaler = MinMaxScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)

        # Train model
        model = DecisionTreeRegressor(
            max_depth=10,
            min_samples_split=10,
            random_state=self.config["random_state"],
        )
        model.fit(X_train_scaled, y_train)

        # Evaluate
        y_pred = model.predict(X_test_scaled)
        metrics = self._calculate_metrics(y_test, y_pred)

        # Feature importance
        importance = dict(zip(features, model.feature_importances_.tolist()))
        importance = dict(sorted(importance.items(), key=lambda x: x[1], reverse=True))

        # Save model
        model_key = f"{coin_id}_decision_tree"
        self.models[model_key] = model
        self.scalers[model_key] = scaler
        self._save_model(model, scaler, model_key)

        logger.info(f"Decision Tree trained for {coin_id} | MAE: {metrics['mae']:.2f}")

        return {
            "model_type": "decision_tree",
            "coin_id": coin_id,
            "metrics": metrics,
            "feature_importance": importance,
            "predictions_test": y_pred.tolist(),
            "actual_test": y_test.tolist(),
        }

    @timer
    def train_random_forest(self, df: pd.DataFrame, coin_id: str) -> Dict:
        """Train a Random Forest model for price prediction."""
        data = self.create_features(df)
        features = [f for f in self.get_feature_columns() if f in data.columns]

        X = data[features].values
        y = data["price"].values

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=self.config["test_split"],
            random_state=self.config["random_state"], shuffle=False
        )

        scaler = MinMaxScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)

        # Train model
        model = RandomForestRegressor(
            n_estimators=self.config["n_estimators_rf"],
            random_state=self.config["random_state"],
            max_depth=15,
            min_samples_split=5,
            n_jobs=-1,
        )
        model.fit(X_train_scaled, y_train)

        # Evaluate
        y_pred = model.predict(X_test_scaled)
        metrics = self._calculate_metrics(y_test, y_pred)

        # Feature importance
        importance = dict(zip(features, model.feature_importances_.tolist()))
        importance = dict(sorted(importance.items(), key=lambda x: x[1], reverse=True))

        # Save model
        model_key = f"{coin_id}_random_forest"
        self.models[model_key] = model
        self.scalers[model_key] = scaler
        self._save_model(model, scaler, model_key)

        logger.info(f"Random Forest trained for {coin_id} | MAE: {metrics['mae']:.2f}")

        return {
            "model_type": "random_forest",
            "coin_id": coin_id,
            "metrics": metrics,
            "feature_importance": importance,
            "predictions_test": y_pred.tolist(),
            "actual_test": y_test.tolist(),
        }

    @timer
    def train_gradient_boosting(self, df: pd.DataFrame, coin_id: str) -> Dict:
        """Train a Gradient Boosting model for price prediction."""
        data = self.create_features(df)
        features = [f for f in self.get_feature_columns() if f in data.columns]

        X = data[features].values
        y = data["price"].values

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=self.config["test_split"],
            random_state=self.config["random_state"], shuffle=False
        )

        scaler = MinMaxScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)

        model = GradientBoostingRegressor(
            n_estimators=200,
            max_depth=8,
            learning_rate=0.05,
            random_state=self.config["random_state"],
        )
        model.fit(X_train_scaled, y_train)

        y_pred = model.predict(X_test_scaled)
        metrics = self._calculate_metrics(y_test, y_pred)

        importance = dict(zip(features, model.feature_importances_.tolist()))
        importance = dict(sorted(importance.items(), key=lambda x: x[1], reverse=True))

        model_key = f"{coin_id}_gradient_boosting"
        self.models[model_key] = model
        self.scalers[model_key] = scaler
        self._save_model(model, scaler, model_key)

        logger.info(f"Gradient Boosting trained for {coin_id} | MAE: {metrics['mae']:.2f}")

        return {
            "model_type": "gradient_boosting",
            "coin_id": coin_id,
            "metrics": metrics,
            "feature_importance": importance,
            "predictions_test": y_pred.tolist(),
            "actual_test": y_test.tolist(),
        }

    # ============================================================
    # PREDICTION
    # ============================================================
    @timer
    def predict_future_prices(
        self,
        df: pd.DataFrame,
        coin_id: str,
        model_type: str = "random_forest",
        days_ahead: int = 30
    ) -> Dict:
        """
        Predict future cryptocurrency prices.

        Args:
            df: Historical price DataFrame
            coin_id: Cryptocurrency identifier
            model_type: Model to use (linear_regression, random_forest, gradient_boosting)
            days_ahead: Number of days to predict

        Returns:
            Dictionary with predicted prices and dates
        """
        model_key = f"{coin_id}_{model_type}"

        # Load or train model
        if model_key not in self.models:
            loaded = self._load_model(model_key)
            if not loaded:
                # Train the model first
                if model_type == "linear_regression":
                    self.train_linear_regression(df, coin_id)
                elif model_type == "decision_tree":
                    self.train_decision_tree(df, coin_id)
                elif model_type == "random_forest":
                    self.train_random_forest(df, coin_id)
                elif model_type == "gradient_boosting":
                    self.train_gradient_boosting(df, coin_id)

        model = self.models.get(model_key)
        scaler = self.scalers.get(model_key)

        if model is None or scaler is None:
            return {"error": f"Model {model_type} not available for {coin_id}"}

        # Generate future predictions iteratively
        data = df.copy()
        predictions = []
        
        # Ensure date column exists and is sorted
        if "date" not in data.columns:
            if "timestamp" in data.columns:
                data["date"] = pd.to_datetime(data["timestamp"]).dt.strftime("%Y-%m-%d")
            else:
                # Generate mock dates if missing
                end_date = datetime.now()
                dates = [end_date - timedelta(days=i) for i in range(len(data))][::-1]
                data["date"] = [d.strftime("%Y-%m-%d") for d in dates]

        # Filter out rows with NaN in date for prediction start point
        valid_data = data.dropna(subset=["date"])
        if valid_data.empty:
            last_date = datetime.now()
        else:
            last_date = pd.to_datetime(valid_data["date"].iloc[-1])

        features_df = self.create_features(data, drop_nans=False)
        features = [f for f in self.get_feature_columns() if f in features_df.columns]

        for day in range(1, days_ahead + 1):
            # Recalculate features for the current set of data
            # including our newly predicted prices
            feature_data = self.create_features(data, drop_nans=False)
            
            # Fill NaNs for the very last row using previous row's data if needed
            # (indicators like SMA won't have changed much in 1 day)
            current_row_features = feature_data[features].fillna(method='ffill').iloc[-1:].fillna(0)
            last_features = current_row_features.values
            last_features_scaled = scaler.transform(last_features)
            predicted_price = float(model.predict(last_features_scaled)[0])

            # Ensure price is positive
            predicted_price = max(predicted_price, 0.01)

            pred_date = last_date + timedelta(days=day)
            predictions.append({
                "date": pred_date.strftime("%Y-%m-%d"),
                "predicted_price": predicted_price,
                "day": day,
            })

            # Add prediction to data for next iteration
            new_row = pd.DataFrame({
                "date": [pred_date.strftime("%Y-%m-%d")],
                "price": [predicted_price],
                "total_volume": [data["total_volume"].iloc[-1] if "total_volume" in data.columns else 0],
                "market_cap": [data["market_cap"].iloc[-1] if "market_cap" in data.columns else 0],
            })
            data = pd.concat([data, new_row], ignore_index=True)

        current_price = float(df["price"].iloc[-1])
        if predictions:
            predicted_final = predictions[-1]["predicted_price"]
            price_change = ((predicted_final / current_price) - 1) * 100
        else:
            predicted_final = current_price
            price_change = 0

        return {
            "coin_id": coin_id,
            "model_type": model_type,
            "current_price": current_price,
            "predictions": predictions,
            "predicted_price_final": predicted_final,
            "predicted_change_pct": price_change,
            "prediction_direction": "📈 Bullish" if price_change > 0 else "📉 Bearish",
            "days_ahead": days_ahead,
        }

    # ============================================================
    # ENSEMBLE PREDICTION
    # ============================================================
    @timer
    def ensemble_predict(self, df: pd.DataFrame, coin_id: str, days_ahead: int = 30) -> Dict:
        """
        Run all available models and combine predictions (ensemble).
        """
        models_to_use = ["linear_regression", "decision_tree", "random_forest", "gradient_boosting"]
        all_predictions = {}

        for model_type in models_to_use:
            try:
                result = self.predict_future_prices(df, coin_id, model_type, days_ahead)
                if "error" not in result:
                    all_predictions[model_type] = result
            except Exception as e:
                logger.warning(f"Failed to predict with {model_type}: {e}")

        if not all_predictions:
            return {"error": "All models failed"}

        # Average predictions across models
        ensemble_predictions = []
        for day in range(days_ahead):
            day_prices = []
            for model_type, result in all_predictions.items():
                if day < len(result.get("predictions", [])):
                    day_prices.append(result["predictions"][day]["predicted_price"])

            if day_prices:
                ensemble_predictions.append({
                    "date": all_predictions[list(all_predictions.keys())[0]]["predictions"][day]["date"],
                    "predicted_price": float(np.mean(day_prices)),
                    "min_prediction": float(min(day_prices)),
                    "max_prediction": float(max(day_prices)),
                    "std_prediction": float(np.std(day_prices)),
                    "day": day + 1,
                })

        current_price = float(df["price"].iloc[-1])
        final_price = ensemble_predictions[-1]["predicted_price"] if ensemble_predictions else current_price

        return {
            "coin_id": coin_id,
            "model_type": "ensemble",
            "current_price": current_price,
            "predictions": ensemble_predictions,
            "individual_models": {k: v.get("predicted_price_final") for k, v in all_predictions.items()},
            "predicted_price_final": final_price,
            "predicted_change_pct": ((final_price / current_price) - 1) * 100,
            "prediction_direction": "📈 Bullish" if final_price > current_price else "📉 Bearish",
            "model_metrics": {k: v.get("metrics") for k, v in all_predictions.items() if "metrics" in v},
        }

    # ============================================================
    # HELPER METHODS
    # ============================================================
    def _calculate_metrics(self, y_true, y_pred) -> Dict:
        """Calculate regression metrics."""
        return {
            "mae": float(mean_absolute_error(y_true, y_pred)),
            "rmse": float(np.sqrt(mean_squared_error(y_true, y_pred))),
            "r2_score": float(r2_score(y_true, y_pred)),
            "mape": float(np.mean(np.abs((y_true - y_pred) / y_true)) * 100),
        }

    def _save_model(self, model, scaler, model_key: str):
        """Save model and scaler to disk."""
        model_path = MODELS_DIR / f"{model_key}_model.pkl"
        scaler_path = MODELS_DIR / f"{model_key}_scaler.pkl"

        with open(model_path, "wb") as f:
            pickle.dump(model, f)
        with open(scaler_path, "wb") as f:
            pickle.dump(scaler, f)

        logger.info(f"Model saved: {model_path}")

    def _load_model(self, model_key: str) -> bool:
        """Load model and scaler from disk."""
        model_path = MODELS_DIR / f"{model_key}_model.pkl"
        scaler_path = MODELS_DIR / f"{model_key}_scaler.pkl"

        if model_path.exists() and scaler_path.exists():
            with open(model_path, "rb") as f:
                self.models[model_key] = pickle.load(f)
            with open(scaler_path, "rb") as f:
                self.scalers[model_key] = pickle.load(f)
            logger.info(f"Model loaded: {model_key}")
            return True
        return False


if __name__ == "__main__":
    from backend.data_collector import generate_sample_data

    print("🤖 Training prediction models...\n")
    datasets = generate_sample_data(["bitcoin", "ethereum"], days=365)
    predictor = CryptoPricePredictor()

    for coin_id, df in datasets.items():
        print(f"\n{'='*60}")
        print(f"🔮 Predictions for {coin_id.upper()}")
        print(f"{'='*60}")

        result = predictor.ensemble_predict(df, coin_id, days_ahead=14)
        if "error" not in result:
            print(f"  Current Price: ${result['current_price']:,.2f}")
            print(f"  Predicted (14d): ${result['predicted_price_final']:,.2f}")
            print(f"  Change: {result['predicted_change_pct']:.2f}%")
            print(f"  Direction: {result['prediction_direction']}")
            print(f"\n  Model Performance:")
            for model, metrics in result.get("model_metrics", {}).items():
                if metrics:
                    print(f"    {model}: MAE=${metrics['mae']:,.2f}, R²={metrics['r2_score']:.3f}")
