from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import asyncio
from prometheus_client import Counter, Histogram, Gauge, start_http_server
import uvicorn
import os

from app.services.redis_consumer import RedisConsumer
from app.services.volatility_calculator import VolatilityCalculator
from app.services.risk_analyzer import RiskAnalyzer
from app.models.analytics_models import RiskAnalysis, HealthStatus
from app.config import get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/app/logs/analytics-service.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Prometheus metrics
processed_orders_counter = Counter('analytics_orders_processed_total', 'Total orders processed')
risk_calculations_counter = Counter('analytics_risk_calculations_total', 'Total risk calculations')
processing_time_histogram = Histogram('analytics_processing_time_seconds', 'Order processing time')
active_connections_gauge = Gauge('analytics_active_connections', 'Active Redis connections')

# Global instances
redis_consumer = None
volatility_calculator = None
risk_analyzer = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    global redis_consumer, volatility_calculator, risk_analyzer
    
    logger.info("Starting Analytics Service...")
    
    # Initialize services
    settings = get_settings()
    volatility_calculator = VolatilityCalculator()
    risk_analyzer = RiskAnalyzer(volatility_calculator)
    redis_consumer = RedisConsumer(risk_analyzer)
    
    # Start Prometheus metrics server
    start_http_server(9091)
    logger.info("Prometheus metrics server started on port 9091")
    
    # Start Redis consumer
    consumer_task = asyncio.create_task(redis_consumer.start_consuming())
    
    # Start volatility feed simulator
    volatility_task = asyncio.create_task(volatility_calculator.start_btc_feed())
    
    logger.info("Analytics Service started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Analytics Service...")
    consumer_task.cancel()
    volatility_task.cancel()
    if redis_consumer:
        await redis_consumer.stop()
    logger.info("Analytics Service stopped")

app = FastAPI(
    title="Risk Analytics Service",
    description="Real-time risk assessment analytics engine",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health", response_model=HealthStatus)
async def health_check():
    """Health check endpoint"""
    return HealthStatus(
        status="healthy",
        service="analytics-service",
        version="1.0.0"
    )

@app.get("/metrics")
async def get_metrics():
    """Get analytics metrics"""
    return {
        "ordersProcessed": processed_orders_counter._value._value,
        "riskCalculations": risk_calculations_counter._value._value,
        "activeConnections": active_connections_gauge._value._value,
        "volatilityCalculator": {
            "btcPrice": volatility_calculator.get_current_price() if volatility_calculator else 0,
            "volatility": volatility_calculator.get_current_volatility() if volatility_calculator else 0
        }
    }

@app.get("/volatility/btc")
async def get_btc_volatility():
    """Get current BTC volatility data"""
    if not volatility_calculator:
        return {"error": "Volatility calculator not initialized"}
    
    return {
        "symbol": "BTC-USD",
        "currentPrice": volatility_calculator.get_current_price(),
        "volatility": volatility_calculator.get_current_volatility(),
        "timestamp": volatility_calculator.get_last_update()
    }

@app.post("/analyze")
async def analyze_order(order_data: dict):
    """Manually analyze an order (for testing)"""
    if not risk_analyzer:
        return {"error": "Risk analyzer not initialized"}
    
    try:
        analysis = await risk_analyzer.analyze_order(order_data)
        return analysis
    except Exception as e:
        logger.error(f"Error analyzing order: {e}")
        return {"error": str(e)}

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        log_level="info",
        reload=False
    ) 