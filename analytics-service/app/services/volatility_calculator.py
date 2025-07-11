import asyncio
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Optional
import random
import math
from collections import deque

from app.config import get_settings

logger = logging.getLogger(__name__)

class VolatilityCalculator:
    def __init__(self):
        self.settings = get_settings()
        self.price_history: deque = deque(maxlen=1000)  # Keep last 1000 price points
        self.current_price = self.settings.btc_starting_price
        self.last_update = datetime.now()
        self.volatility_cache = {}
        self.running = False
        
    async def start_btc_feed(self):
        """Start the simulated BTC price feed"""
        self.running = True
        logger.info("Starting BTC price feed simulation")
        
        while self.running:
            try:
                await self._update_price()
                await asyncio.sleep(self.settings.price_update_interval_seconds)
            except Exception as e:
                logger.error(f"Error in BTC price feed: {e}")
                await asyncio.sleep(1)
                
    async def stop_feed(self):
        """Stop the price feed"""
        self.running = False
        logger.info("Stopped BTC price feed")
        
    async def _update_price(self):
        """Update BTC price with realistic volatility simulation"""
        # Geometric Brownian Motion for price simulation
        dt = 1 / 86400  # 1 second in days
        drift = 0.0001  # Small positive drift
        volatility = self.settings.btc_volatility_factor
        
        # Add some market hours effect
        current_hour = datetime.now().hour
        if 2 <= current_hour <= 6:  # Asian market hours - higher volatility
            volatility *= 1.5
        elif 14 <= current_hour <= 18:  # US market hours - moderate volatility
            volatility *= 1.2
            
        # Random walk with occasional jumps
        random_shock = np.random.normal(0, 1)
        
        # Add occasional large moves (fat tails)
        if random.random() < 0.001:  # 0.1% chance of large move
            random_shock *= 5
            
        price_change = self.current_price * (
            drift * dt + volatility * math.sqrt(dt) * random_shock
        )
        
        new_price = max(self.current_price + price_change, 1000)  # Floor at $1000
        
        self.price_history.append({
            'price': new_price,
            'timestamp': datetime.now(),
            'change': price_change
        })
        
        self.current_price = new_price
        self.last_update = datetime.now()
        
        # Log significant price movements
        if abs(price_change) > self.current_price * 0.001:  # 0.1% move
            logger.info(f"BTC price update: ${new_price:.2f} (change: {price_change:+.2f})")
    
    def get_current_price(self) -> float:
        """Get current BTC price"""
        return self.current_price
        
    def get_current_volatility(self) -> float:
        """Calculate current volatility based on recent price movements"""
        if len(self.price_history) < 10:
            return 0.0
            
        # Get price changes for the last minute
        cutoff_time = datetime.now() - timedelta(minutes=self.settings.volatility_window_minutes)
        recent_prices = [
            p for p in self.price_history 
            if p['timestamp'] > cutoff_time
        ]
        
        if len(recent_prices) < 2:
            return 0.0
            
        # Calculate returns
        returns = []
        for i in range(1, len(recent_prices)):
            ret = (recent_prices[i]['price'] - recent_prices[i-1]['price']) / recent_prices[i-1]['price']
            returns.append(ret)
            
        if not returns:
            return 0.0
            
        # Annualized volatility
        volatility = np.std(returns) * np.sqrt(365 * 24 * 60)  # Scale to annual
        return float(volatility)
        
    def get_volatility_percentile(self, lookback_minutes: int = 60) -> float:
        """Get volatility percentile compared to recent history"""
        current_vol = self.get_current_volatility()
        
        # Calculate historical volatilities
        cutoff_time = datetime.now() - timedelta(minutes=lookback_minutes)
        historical_vols = []
        
        for i in range(0, len(self.price_history) - 10, 10):  # Sample every 10 points
            sample_time = self.price_history[i]['timestamp']
            if sample_time < cutoff_time:
                continue
                
            sample_prices = list(self.price_history)[i:i+10]
            if len(sample_prices) < 2:
                continue
                
            returns = []
            for j in range(1, len(sample_prices)):
                ret = (sample_prices[j]['price'] - sample_prices[j-1]['price']) / sample_prices[j-1]['price']
                returns.append(ret)
                
            if returns:
                vol = np.std(returns) * np.sqrt(365 * 24 * 60)
                historical_vols.append(vol)
                
        if not historical_vols:
            return 50.0  # Default to 50th percentile
            
        percentile = (sum(1 for v in historical_vols if v < current_vol) / len(historical_vols)) * 100
        return percentile
        
    def get_last_update(self) -> datetime:
        """Get timestamp of last price update"""
        return self.last_update
        
    def get_price_history(self, minutes: int = 60) -> List[dict]:
        """Get price history for the last N minutes"""
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        return [
            p for p in self.price_history 
            if p['timestamp'] > cutoff_time
        ]
        
    def calculate_slippage(self, order_size: float, symbol: str) -> float:
        """Calculate estimated slippage for an order"""
        # Simplified slippage model based on order size and current volatility
        volatility = self.get_current_volatility()
        
        # Base slippage (in basis points)
        base_slippage = 5  # 5 bps
        
        # Size impact - larger orders have more slippage
        size_impact = min(order_size / 100000, 0.5)  # Max 50 bps from size
        
        # Volatility impact - higher volatility means more slippage
        volatility_impact = min(volatility * 1000, 20)  # Max 20 bps from volatility
        
        # Time of day impact
        current_hour = datetime.now().hour
        if 2 <= current_hour <= 6:  # Low liquidity hours
            time_impact = 5
        else:
            time_impact = 0
            
        total_slippage = base_slippage + size_impact + volatility_impact + time_impact
        
        return total_slippage  # Return in basis points 