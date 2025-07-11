from pydantic import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    # Redis configuration
    redis_host: str = os.getenv("REDIS_HOST", "localhost")
    redis_port: int = int(os.getenv("REDIS_PORT", "6379"))
    redis_db: int = int(os.getenv("REDIS_DB", "0"))
    redis_password: Optional[str] = os.getenv("REDIS_PASSWORD")
    
    # Service configuration
    service_name: str = "analytics-service"
    service_version: str = "1.0.0"
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Analytics configuration
    volatility_window_minutes: int = int(os.getenv("VOLATILITY_WINDOW_MINUTES", "1"))
    price_update_interval_seconds: int = int(os.getenv("PRICE_UPDATE_INTERVAL_SECONDS", "1"))
    
    # Risk thresholds
    high_volatility_threshold: float = float(os.getenv("HIGH_VOLATILITY_THRESHOLD", "0.05"))
    extreme_volatility_threshold: float = float(os.getenv("EXTREME_VOLATILITY_THRESHOLD", "0.10"))
    
    # BTC price simulation
    btc_starting_price: float = float(os.getenv("BTC_STARTING_PRICE", "45000.0"))
    btc_volatility_factor: float = float(os.getenv("BTC_VOLATILITY_FACTOR", "0.02"))
    
    class Config:
        env_file = ".env"
        case_sensitive = False

# Global settings instance
_settings = None

def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings 