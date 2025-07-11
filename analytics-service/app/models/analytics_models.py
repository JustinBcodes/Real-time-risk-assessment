from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from decimal import Decimal
import json

class Order(BaseModel):
    orderId: str
    userId: str
    symbol: str
    side: str
    quantity: float
    price: float
    orderType: str
    timestamp: datetime

class RiskAnalysis(BaseModel):
    orderId: str
    userId: str
    symbol: str
    riskScore: float = Field(ge=0, le=100)
    verdict: str  # ACCEPT, REJECT, WARN
    volatility: float
    slippage: float
    reasons: List[str]
    processingTimeMs: int
    timestamp: datetime = Field(default_factory=datetime.now)

class VolatilityData(BaseModel):
    symbol: str
    currentPrice: float
    volatility: float
    priceHistory: List[float]
    timestamp: datetime = Field(default_factory=datetime.now)

class HealthStatus(BaseModel):
    status: str
    service: str
    version: str
    timestamp: datetime = Field(default_factory=datetime.now)

class MarketData(BaseModel):
    symbol: str
    price: float
    volume: float
    timestamp: datetime
    change24h: float = 0.0
    
class SlippageModel(BaseModel):
    symbol: str
    orderSize: float
    estimatedSlippage: float
    bidAskSpread: float
    marketDepth: float

class UserExposure(BaseModel):
    userId: str
    totalExposure: float
    symbolExposures: Dict[str, float]
    riskLevel: str
    lastUpdated: datetime = Field(default_factory=datetime.now) 