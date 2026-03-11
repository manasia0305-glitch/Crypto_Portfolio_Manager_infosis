from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional
from pathlib import Path
import sys
import os

# Adjust sys.path to root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from fastapi import FastAPI, HTTPException, Query, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
import socketio
import bson
from bson import ObjectId
import asyncio
import numpy as np

from config.settings import API_HOST, API_PORT, MAX_WORKERS, DEFAULT_CRYPTOS, SECRET_KEY, JWT_ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
from database.mongo_connection import connect_to_mongo, close_mongo_connection, get_database
from backend.models.schemas import User, Portfolio, Transaction, PyObjectId
from backend.services.data_collector import CryptoDataCollector, generate_sample_data
from backend.services.portfolio_manager import PortfolioManager
from backend.services.alert_system import AlertSystem
from backend.services.report_generator import ReportGenerator
from ai_models.risk_analyzer import RiskAnalyzer
from ai_models.predictor import CryptoPricePredictor
from ai_models.investment_optimizer import InvestmentOptimizer
from utils.helpers import logger
from config.settings import REPORTS_DIR

# Initialize FastAPI app
print("🚀 STARTING SERVER with UPDATED CODE")
app = FastAPI(
    title="AI Crypto Investment Intelligence Platform",
    description="Advanced cryptocurrency analytics, predictions, and portfolio management",
    version="1.0.0",
)

# Ensure reports directory exists
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/reports", StaticFiles(directory=str(REPORTS_DIR)), name="reports")

# Socket.io setup
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')
socket_app = socketio.ASGIApp(sio, app)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"])

@app.get("/")
async def root():
    """Root endpoint to verify API is running."""
    return {
        "status": "online",
        "message": "AI Crypto Investment Intelligence Platform API is running",
        "version": "1.0.0",
        "docs": "/docs"
    }

# Socket.io events
@sio.event
async def connect(sid, environ):
    print(f"Client connected: {sid}")

@sio.event
async def disconnect(sid):
    print(f"Client disconnected: {sid}")

# Default User for Seeding/Dev
PARAMESH_USER_ID = ObjectId("65e9b1e8a1d2c3b4e5f6a7b9")

# Initialize services
collector = CryptoDataCollector()
portfolio_mgr = PortfolioManager()
risk_analyzer = RiskAnalyzer()
predictor = CryptoPricePredictor()
optimizer = InvestmentOptimizer()
alert_system = AlertSystem()
report_gen = ReportGenerator()

class HoldingRequest(BaseModel):
    coin_id: str
    quantity: float
    purchase_price: float
    purchase_date: str = ""
    notes: str = ""

class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str = ""

class LoginRequest(BaseModel):
    email: str
    password: str

class UserResponse(BaseModel):
    id: str
    email: str
    name: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

class ChatRequest(BaseModel):
    message: str
    context: Optional[Dict] = None

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=JWT_ALGORITHM)

async def get_current_user(request: Request) -> User:
    auth = request.headers.get("authorization", "")
    parts = auth.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        token = parts[1]
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[JWT_ALGORITHM])
            sub = payload.get("sub")
            email = payload.get("email")
            if sub is None:
                raise HTTPException(401, "Invalid token: missing subject")
            
            db = get_database()
            user_data = None
            
            # Try finding by ID first
            try:
                user_id = ObjectId(sub)
                user_data = await db["users"].find_one({"_id": user_id})
            except (bson.errors.InvalidId, TypeError):
                pass
            
            # Fallback to email if ID lookup failed
            if not user_data and email:
                user_data = await db["users"].find_one({"email": email})
            
            # Final fallback: if sub itself looks like an email
            if not user_data and "@" in sub:
                user_data = await db["users"].find_one({"email": sub})
            
            if not user_data:
                raise HTTPException(401, "User not found")
            return User(**user_data)
        except JWTError as e:
            print(f"JWT decode error: {e}")
            raise HTTPException(401, "Invalid token or session expired")
        except Exception as e:
            if isinstance(e, HTTPException): raise e
            print(f"Auth error: {e}")
            raise HTTPException(401, "Authentication failed")
    raise HTTPException(401, "Not authenticated")

class AlertRequest(BaseModel):
    coin_id: str = ""
    alert_type: str = "price_above"
    threshold: float = 5.0

class PortfolioCreate(BaseModel):
    name: str = "My Portfolio"
    description: str = ""

# ============================================================
# MARKET DATA ENDPOINTS
# ============================================================
@app.get("/api/market")
async def get_market_data(per_page: int = 50):
    data = await collector.get_latest_market_data(limit=per_page)
    if not data:
        data = await collector.fetch_and_store_market_data(per_page=per_page)
    return {"status": "success", "data": sanitize_for_json(data or [])}

@app.get("/api/market/summary")
async def get_market_summary():
    """Get global market stats for the dashboard header."""
    data = await collector.get_market_summary()
    return {"status": "success", "data": sanitize_for_json(data)}

@app.get("/api/market/{coin_id}")
async def get_coin_details(coin_id: str):
    data = collector.fetch_coin_details(coin_id)
    if data:
        return {"status": "success", "data": sanitize_for_json(data)}
    raise HTTPException(404, f"Coin {coin_id} not found")

def sanitize_for_json(obj):
    """Recursively convert non-JSON compliant values (NaN, Inf, ObjectId, numpy types) to compliant ones."""
    if isinstance(obj, dict):
        res = {}
        for k, v in obj.items():
            if k == "_id":
                res["id"] = str(v)
            else:
                res[k] = sanitize_for_json(v)
        return res
    elif isinstance(obj, list):
        return [sanitize_for_json(v) for v in obj]
    elif isinstance(obj, float):
        if np.isnan(obj) or np.isinf(obj):
            return 0.0
        return obj
    elif isinstance(obj, np.bool_):
        return bool(obj)
    elif isinstance(obj, (np.int64, np.int32)):
        return int(obj)
    elif isinstance(obj, (np.float64, np.float32)):
        val = float(obj)
        if np.isnan(val) or np.isinf(val):
            return 0.0
        return val
    elif hasattr(obj, 'isoformat'):
        return obj.isoformat()
    elif str(type(obj)).find('ObjectId') >= 0:
        return str(obj)
    return obj

@app.get("/api/market/{coin_id}/history")
async def get_price_history(coin_id: str, days: int = 365):
    try:
        df = await collector.get_price_history_from_db(coin_id, days=days)
        if df.empty:
            df = await collector.fetch_historical_prices(coin_id, days=days)
            if df is not None:
                await collector.save_price_history_to_db(coin_id, df)
                return {"status": "success", "data": sanitize_for_json(df.to_dict(orient="records"))}
        
        return {"status": "success", "data": sanitize_for_json(df.to_dict(orient="records"))}
    except Exception as e:
        logger.error(f"Error in get_price_history: {e}", exc_info=True)
        raise HTTPException(500, str(e))

# ============================================================
# AUTH ENDPOINTS
# ============================================================
@app.post("/api/auth/register")
async def register(req: RegisterRequest):
    db = get_database()
    existing = await db["users"].find_one({"email": req.email})
    if existing:
        raise HTTPException(400, "Email already registered")
    
    hpw = hash_password(req.password)
    name = req.name or (req.email.split("@")[0] if "@" in req.email else req.email)
    new_user = {"email": req.email, "name": name, "hashed_password": hpw, "created_at": datetime.utcnow()}
    result = await db["users"].insert_one(new_user)
    return {"status": "success", "data": {"id": str(result.inserted_id), "email": req.email, "name": name}}

@app.post("/api/auth/login", response_model=LoginResponse)
async def login(req: LoginRequest):
    print(f"Login request received for email: {req.email}")
    db = get_database()
    user_data = await db["users"].find_one({"email": req.email})
    if not user_data or not verify_password(req.password, user_data["hashed_password"]):
        raise HTTPException(401, "Invalid credentials")
    token = create_access_token({"sub": str(user_data["_id"]), "email": user_data["email"]})
    return LoginResponse(access_token=token, user=UserResponse(id=str(user_data["_id"]), email=user_data["email"], name=user_data["name"]))

@app.get("/api/auth/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)):
    return UserResponse(id=str(current_user.id), email=current_user.email, name=current_user.name)

# ============================================================
# PORTFOLIO ENDPOINTS
# ============================================================
@app.post("/api/portfolio")
async def create_portfolio(req: PortfolioCreate, current_user: User = Depends(get_current_user)):
    pid = await portfolio_mgr.create_portfolio(str(current_user.id), req.name, req.description)
    return {"status": "success", "portfolio_id": pid}

@app.get("/api/portfolios")
async def list_portfolios(current_user: User = Depends(get_current_user)):
    data = await portfolio_mgr.list_portfolios(str(current_user.id))
    return {"status": "success", "data": sanitize_for_json(data)}

@app.get("/api/portfolio/{portfolio_id}")
async def get_portfolio(portfolio_id: str, current_user: User = Depends(get_current_user)):
    portfolio = await portfolio_mgr.get_portfolio(portfolio_id)
    return {"status": "success", "data": sanitize_for_json(portfolio)}

@app.post("/api/portfolio/sample")
async def create_sample_portfolio(current_user: User = Depends(get_current_user)):
    """Create a sample portfolio with demo data."""
    pid = await portfolio_mgr.create_portfolio(str(current_user.id), "Demo Portfolio", "Automatically generated sample assets")
    
    # Add some sample assets
    samples = [
        {"coin_id": "bitcoin", "qty": 0.5, "price": 45000},
        {"coin_id": "ethereum", "qty": 5.0, "price": 2400},
        {"coin_id": "solana", "qty": 50.0, "price": 95}
    ]
    
    for s in samples:
        await portfolio_mgr.add_asset(pid, s["coin_id"], s["qty"], s["price"])
        
    return {"status": "success", "portfolio_id": pid}

@app.post("/api/portfolio/{portfolio_id}/holding")
async def add_holding(portfolio_id: str, req: HoldingRequest, current_user: User = Depends(get_current_user)):
    await portfolio_mgr.add_asset(portfolio_id, req.coin_id, req.quantity, req.purchase_price)
    return {"status": "success"}

@app.delete("/api/portfolio/{portfolio_id}/holding/{coin_id}")
async def remove_holding(portfolio_id: str, coin_id: str, current_user: User = Depends(get_current_user)):
    success = await portfolio_mgr.remove_asset(portfolio_id, coin_id)
    if success:
        return {"status": "success"}
    raise HTTPException(500, f"Failed to remove asset {coin_id}")

# ============================================================
# ALERT ENDPOINTS
# ============================================================
@app.post("/api/alerts")
async def create_alert(req: AlertRequest, current_user: User = Depends(get_current_user)):
    alert_id = await alert_system.create_price_alert(
        str(current_user.id), 
        req.coin_id, 
        req.alert_type, 
        req.threshold
    )
    if alert_id:
        return {"status": "success", "alert_id": alert_id}
    raise HTTPException(500, "Failed to create alert")

@app.get("/api/alerts")
async def list_alerts(current_user: User = Depends(get_current_user)):
    db = get_database()
    alerts = await db["alerts"].find({"user_id": ObjectId(current_user.id)}).to_list(length=100)
    return {"status": "success", "data": sanitize_for_json(alerts)}

@app.delete("/api/alerts/{alert_id}")
async def delete_alert(alert_id: str, current_user: User = Depends(get_current_user)):
    db = get_database()
    result = await db["alerts"].delete_one({"_id": ObjectId(alert_id), "user_id": ObjectId(current_user.id)})
    if result.deleted_count:
        return {"status": "success"}
    raise HTTPException(404, "Alert not found")

# ============================================================
# AI & RISK ENDPOINTS
# ============================================================
@app.get("/api/risk/{coin_id}")
async def analyze_risk(coin_id: str, days: int = 365):
    try:
        df = await collector.get_price_history_from_db(coin_id, days=days)
        if get_database().is_mock:
            db = get_database()
            result = await db["risk_analysis"].find_one({"coin_id": coin_id})
            return {"status": "success", "data": sanitize_for_json(result)}

    except Exception as e:
        logger.error(f"Error in analyze_risk: {e}", exc_info=True)
        raise HTTPException(500, str(e))

@app.get("/api/predict/{coin_id}")
async def predict_price(coin_id: str, days: int = 30, model: str = "random_forest"):
    try:
        df = await collector.get_price_history_from_db(coin_id, days=365)
        if df.empty:
            raise HTTPException(404, "No historical data found for prediction")
        
        if get_database().is_mock:
            db = get_database()
            result = await db["predictions"].find_one({"coin_id": coin_id, "model": model})
            return {"status": "success", "data": sanitize_for_json(result)}

    except Exception as e:
        logger.error(f"Error in predict_price: {e}", exc_info=True)
        raise HTTPException(500, str(e))

# ============================================================
# OPTIMIZATION ENDPOINTS
# ============================================================
@app.get("/api/optimize")
async def optimize_portfolio_endpoint(
    objective: str = "max_sharpe",
    current_user: User = Depends(get_current_user)
):
    """Optimize portfolio using Scipy minimization."""
    # Get user's current portfolio assets
    portfolios = await portfolio_mgr.list_portfolios(str(current_user.id))
    if not portfolios:
        raise HTTPException(404, "No portfolio found to optimize")
    
    portfolio = await portfolio_mgr.get_portfolio(portfolios[0]["id"])
    if not portfolio.get("assets") or len(portfolio["assets"]) < 2:
        raise HTTPException(400, "Need at least 2 assets to optimize")
    
    # Get price data for these assets
    price_data = {}
    for asset in portfolio["assets"]:
        coin_id = asset["coin_id"]
        df = await collector.get_price_history_from_db(coin_id, days=365)
        if not df.empty:
            price_data[coin_id] = df["price"]
    
    if len(price_data) < 2:
        raise HTTPException(400, "Insufficient historical data for optimization")
    
    result = optimizer.optimize_portfolio(price_data, objective=objective)
    if "error" in result:
        raise HTTPException(400, result["error"])
        
    return {"status": "success", "data": sanitize_for_json(result)}

@app.get("/api/optimize/monte-carlo")
async def monte_carlo_optimization_endpoint(
    num_portfolios: int = 5000,
    current_user: User = Depends(get_current_user)
):
    """Optimize portfolio using Monte Carlo simulation."""
    portfolios = await portfolio_mgr.list_portfolios(str(current_user.id))
    if not portfolios:
        raise HTTPException(404, "No portfolio found to optimize")
    
    portfolio = await portfolio_mgr.get_portfolio(portfolios[0]["id"])
    if not portfolio.get("assets") or len(portfolio["assets"]) < 2:
        raise HTTPException(400, "Need at least 2 assets to optimize")
    
    price_data = {}
    for asset in portfolio["assets"]:
        coin_id = asset["coin_id"]
        df = await collector.get_price_history_from_db(coin_id, days=365)
        if not df.empty:
            price_data[coin_id] = df["price"]
            
    if len(price_data) < 2:
        raise HTTPException(400, "Insufficient historical data for optimization")
    
    result = optimizer.monte_carlo_optimization(price_data, num_portfolios=num_portfolios)
    if "error" in result:
        raise HTTPException(400, result["error"])
        
    return {"status": "success", "data": sanitize_for_json(result)}

# ============================================================
# REPORT ENDPOINTS
# ============================================================
@app.get("/api/report/portfolio/{portfolio_id}")
async def get_portfolio_report(
    portfolio_id: str,
    current_user: User = Depends(get_current_user)
):
    """Generate and return a portfolio report."""
    portfolio = await portfolio_mgr.get_portfolio(portfolio_id)
    if not portfolio:
        raise HTTPException(404, "Portfolio not found")
        
    # Gather additional context for report
    risk_results = {}
    prediction_results = {}
    
    for asset in portfolio.get("assets", []):
        coin_id = asset["coin_id"]
        df = await collector.get_price_history_from_db(coin_id, days=365)
        if not df.empty:
            risk_results[coin_id] = risk_analyzer.analyze_asset_risk(df["price"], coin_id)
            prediction_results[coin_id] = predictor.predict_future_prices(df, coin_id, "random_forest", 14)
            
    report = report_gen.generate_portfolio_report(portfolio, risk_results, prediction_results)
    return {"status": "success", "data": sanitize_for_json(report)}

@app.get("/api/report/market")
async def get_market_report(current_user: User = Depends(get_current_user)):
    """Generate and return a market report."""
    market_data = await collector.get_latest_market_data(limit=50)
    if not market_data:
        market_data = await collector.fetch_and_store_market_data(per_page=50)
        
    # For a full report, we'd want risk analysis for top coins
    # but that's slow, so we'll just do it for top 5
    risk_analyses = {}
    for coin in market_data[:5]:
        coin_id = coin["coin_id"]
        df = await collector.get_price_history_from_db(coin_id, days=365)
        if not df.empty:
            risk_analyses[coin_id] = risk_analyzer.analyze_asset_risk(df["price"], coin_id)
            
    report = report_gen.generate_market_report(market_data, risk_analyses)
    return {"status": "success", "data": sanitize_for_json(report)}

@app.post("/api/ai/chat")
async def ai_chat(req: ChatRequest, current_user: User = Depends(get_current_user)):
    """AI Chatbot endpoint with long-term memory learning."""
    msg = req.message.lower()
    db = get_database()
    
    # 1. Retrieve Past Memory for this User
    past_interactions = await db["chat_memory"].find({"user_id": ObjectId(current_user.id)}).sort("timestamp", -1).to_list(length=5)
    memory_context = [m['message'] for m in past_interactions]
    
    # 2. Market and Portfolio Data
    market_data = await db["market_data"].find().to_list(length=20)
    user_portfolios = await portfolio_mgr.list_portfolios(str(current_user.id))
    
    response = ""
    learning_note = ""
    
    # Check if user is repeating a topic (Simple Learning)
    if any(kw in msg for kw in ["bitcoin", "btc"]) and any("bitcoin" in prev or "btc" in prev for prev in memory_context):
        learning_note = "As we discussed earlier, "
    elif any(kw in msg for kw in ["portfolio", "holdings"]) and any("portfolio" in prev or "holdings" in prev for prev in memory_context):
        learning_note = "Following up on your portfolio interest, "

    # 3. Response Generation Logic
    if "price" in msg or "market" in msg:
        top_coins = [f"{c['coin_id'].capitalize()}: ${c['price']:,.2f}" for c in market_data[:3]]
        response = f"{learning_note}The current market snapshot is: " + ", ".join(top_coins) + "."
    
    elif "volatility" in msg or "movers" in msg or "gainers" in msg:
        gainers = sorted(market_data, key=lambda x: x.get('change_24h', 0), reverse=True)[:3]
        response = f"{learning_note}The top 24h gainers are: " + ", ".join([f"{c['coin_id'].capitalize()} (+{c.get('change_24h', 0):.2f}%)" for c in gainers])
    
    elif "volume" in msg:
        volume_leaders = sorted(market_data, key=lambda x: x.get('total_volume', 0), reverse=True)[:3]
        response = f"The highest volume assets today are: " + ", ".join([f"{c['coin_id'].capitalize()} (${c.get('total_volume', 0)/1e9:.1f}B)" for c in volume_leaders])
    
    elif "sentiment" in msg or "bull" in msg or "bear" in msg:
        avg_change = sum([c.get('change_24h', 0) for c in market_data[:10]]) / 10
        sentiment = "Bullish" if avg_change > 1 else "Bearish" if avg_change < -1 else "Neutral"
        response = f"Market sentiment is {sentiment} ({avg_change:+.2f}% avg). Traders are currently {'optimistic' if sentiment == 'Bullish' else 'cautious'}."

    elif "portfolio" in msg or "holdings" in msg or "risk" in msg:
        if user_portfolios:
            p = user_portfolios[0]
            risk_summary = "low" if p['total_pl_pct'] > -5 else "moderate" if p['total_pl_pct'] > -15 else "high"
            response = f"{learning_note}Your portfolio '{p['name']}' is valued at ${p['total_value']:,.2f} with a {risk_summary} risk level."
        else:
            response = "You don't have a portfolio yet. Let's create one to start tracking!"
            
    elif "bitcoin" in msg or "btc" in msg:
        btc = next((c for c in market_data if c['coin_id'] == 'bitcoin'), None)
        if btc:
            response = f"{learning_note}Bitcoin is trading at ${btc['price']:,.2f}. Models show support at ${btc['price']*0.95:,.2f}."
    else:
        response = "I'm your learning AI Assistant. Ask me about prices, gainers, market volume, sentiment, or your portfolio!"

    # 4. Store this interaction in Long-Term Memory
    await db["chat_memory"].insert_one({
        "user_id": ObjectId(current_user.id),
        "message": msg,
        "response": response,
        "timestamp": datetime.utcnow()
    })

    return {"status": "success", "response": response}

# Background task for real-time updates
async def market_update_task():
    while True:
        try:
            data = await collector.fetch_and_store_market_data(per_page=20)
            if data:
                await sio.emit('market_update', data)
                
                # Check for triggered alerts
                triggered = await alert_system.check_alerts(data)
                for alert in triggered:
                    logger.info(f"🔔 ALERT TRIGGERED: {alert['message']}")
                    # In a real app, we would emit a specific event or send email
                    await sio.emit('alert_notification', alert)
                    
        except Exception as e:
            print(f"Error in market update task: {e}")
        await asyncio.sleep(60)

@app.get("/api/ping")
async def ping():
    from database.mongo_connection import db as db_obj
    return {"status": "ok", "timestamp": datetime.utcnow(), "db_mock": get_database().is_mock}

async def seed_initial_data():
    """Seed initial demo data for offline storage."""
    from database.mongo_connection import db as db_obj
    user_count = await db_obj.db["users"].count_documents({})
    if user_count == 0:
        print("🌱 Seeding initial demo data for offline storage...")
        # Use static IDs so sessions persist across server restarts in dev mode
        DEMO_USER_ID = ObjectId("65e9b1e8a1d2c3b4e5f6a7b8")
        
        # 1. Seed Users
        demo_user = {
            "_id": DEMO_USER_ID,
            "email": "demo@example.com",
            "name": "Demo User",
            "hashed_password": hash_password("demo123"),
            "created_at": datetime.utcnow()
        }
        await db_obj.db["users"].insert_one(demo_user)
        
        user_account = {
            "_id": PARAMESH_USER_ID,
            "email": "bhupathipramesh2025@gmail.com",
            "name": "Paramesh",
            "hashed_password": hash_password("Paramesh@453"),
            "created_at": datetime.utcnow()
        }
        await db_obj.db["users"].insert_one(user_account)
        print(f"✅ Demo users seeded")

        # 2. Seed Initial Market Data
        print("📊 Seeding initial market data...")
        timestamp = datetime.utcnow()
        initial_market = [
            {"coin_id": "bitcoin", "price": 67000.0, "change_24h": 2.5, "symbol": "btc", "name": "Bitcoin", "timestamp": timestamp},
            {"coin_id": "ethereum", "price": 3500.0, "change_24h": 1.8, "symbol": "eth", "name": "Ethereum", "timestamp": timestamp},
            {"coin_id": "solana", "price": 145.0, "change_24h": -0.5, "symbol": "sol", "name": "Solana", "timestamp": timestamp},
            {"coin_id": "cardano", "price": 0.45, "change_24h": 0.2, "symbol": "ada", "name": "Cardano", "timestamp": timestamp},
            {"coin_id": "polkadot", "price": 7.2, "change_24h": 1.1, "symbol": "dot", "name": "Polkadot", "timestamp": timestamp}
        ]
        await get_database()["market_data"].insert_many(initial_market)
        
        # Also seed metadata
        for m in initial_market:
            await get_database()["cryptocurrencies"].update_one(
                {"coin_id": m["coin_id"]},
                {"$set": {"symbol": m["symbol"], "name": m["name"], "last_updated": timestamp}},
                upsert=True
            )
        
        # 3. Seed Coin History (for the AI models and dashboard)
        print("📈 Seeding 500 days of history for BTC, ETH, and SOL into market_data...")
        history = []
        assets = [
            {"id": "bitcoin", "base": 65000.0, "symbol": "btc", "name": "Bitcoin"},
            {"id": "ethereum", "base": 3400.0, "symbol": "eth", "name": "Ethereum"},
            {"id": "solana", "base": 140.0, "symbol": "sol", "name": "Solana"},
            {"id": "cardano", "base": 0.45, "symbol": "ada", "name": "Cardano"}
        ]
        
        for asset in assets:
            for i in range(500, 0, -1):
                day_ts = timestamp - timedelta(days=i)
                # Add some simulated price fluctuation
                price = asset["base"] + (np.random.normal(0, 0.05) * asset["base"]) 
                history.append({
                    "coin_id": asset["id"],
                    "symbol": asset["symbol"],
                    "name": asset["name"],
                    "price": price,
                    "timestamp": day_ts,
                    "date": day_ts.strftime("%Y-%m-%d"),
                    "change_24h": np.random.normal(0, 2.0),
                    "market_cap": asset["base"] * 20000000,
                    "total_volume": asset["base"] * 500000
                })
        await db_obj.db["market_data"].insert_many(history)
        
        # 4. Seed Portfolios for Paramesh
        print("💼 Seeding initial portfolio for Paramesh...")
        paramesh_portfolio = {
            "_id": ObjectId("65e9b1e8a1d2c3b4e5f6a7c1"),
            "user_id": PARAMESH_USER_ID,
            "name": "Main Portfolio",
            "description": "Primary long-term holdings",
            "assets": [
                {"coin_id": "bitcoin", "quantity": 0.45, "purchase_price": 52000.0, "purchase_date": timestamp - timedelta(days=60)},
                {"coin_id": "ethereum", "quantity": 4.2, "purchase_price": 2800.0, "purchase_date": timestamp - timedelta(days=45)},
                {"coin_id": "solana", "quantity": 120.0, "purchase_price": 95.0, "purchase_date": timestamp - timedelta(days=30)}
            ],
            "created_at": timestamp,
            "updated_at": timestamp
        }
        await get_database()["portfolios"].insert_one(paramesh_portfolio)
        
        print("✅ Initial market data and 500-day history seeded")

@app.on_event("startup")
async def startup():
    await connect_to_mongo()
    
    # Seed mock data if using in-memory DB and it's empty
    from database.mongo_connection import db as db_obj
    if db_obj.is_mock:
        await seed_initial_data()
    else:
        print("📁 Using existing offline data from storage file.")

    asyncio.create_task(market_update_task())
    logger.info("🚀 AI Crypto Platform Started!")

@app.on_event("shutdown")
async def shutdown():
    await close_mongo_connection()

if __name__ == "__main__":
    uvicorn.run(socket_app, host=API_HOST, port=API_PORT)
