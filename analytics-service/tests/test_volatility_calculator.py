import pytest
import asyncio
from unittest.mock import Mock, patch
from datetime import datetime, timedelta
from collections import deque

from app.services.volatility_calculator import VolatilityCalculator
from app.config import Settings

class TestVolatilityCalculator:
    
    @pytest.fixture
    def calculator(self):
        with patch('app.services.volatility_calculator.get_settings') as mock_settings:
            settings = Settings()
            mock_settings.return_value = settings
            return VolatilityCalculator()
    
    def test_initialization(self, calculator):
        """Test that the calculator initializes with correct values"""
        assert calculator.current_price == 45000.0
        assert len(calculator.price_history) == 0
        assert calculator.running is False
        assert calculator.volatility_cache == {}
    
    def test_get_current_price(self, calculator):
        """Test getting current price"""
        assert calculator.get_current_price() == 45000.0
        
        # Update price and test again
        calculator.current_price = 46000.0
        assert calculator.get_current_price() == 46000.0
    
    def test_get_current_volatility_insufficient_data(self, calculator):
        """Test volatility calculation with insufficient data"""
        # With no price history
        volatility = calculator.get_current_volatility()
        assert volatility == 0.0
        
        # With insufficient price history
        calculator.price_history.append({
            'price': 45000,
            'timestamp': datetime.now(),
            'change': 0
        })
        volatility = calculator.get_current_volatility()
        assert volatility == 0.0
    
    def test_get_current_volatility_with_data(self, calculator):
        """Test volatility calculation with sufficient data"""
        # Add some mock price data
        base_time = datetime.now()
        prices = [45000, 45100, 44900, 45200, 44800, 45300, 44700, 45400, 44600, 45500]
        
        for i, price in enumerate(prices):
            calculator.price_history.append({
                'price': price,
                'timestamp': base_time + timedelta(seconds=i),
                'change': price - (prices[i-1] if i > 0 else price)
            })
        
        volatility = calculator.get_current_volatility()
        assert volatility > 0.0
        assert isinstance(volatility, float)
    
    def test_calculate_slippage(self, calculator):
        """Test slippage calculation"""
        # Test different order sizes
        small_order_slippage = calculator.calculate_slippage(1000, "BTC-USD")
        large_order_slippage = calculator.calculate_slippage(100000, "BTC-USD")
        
        assert small_order_slippage > 0
        assert large_order_slippage > small_order_slippage
        assert isinstance(small_order_slippage, (int, float))
        assert isinstance(large_order_slippage, (int, float))
    
    def test_calculate_slippage_with_volatility(self, calculator):
        """Test slippage calculation with volatility data"""
        # Add some price history to simulate volatility
        base_time = datetime.now()
        prices = [45000, 45500, 44500, 46000, 44000]  # More volatile prices
        
        for i, price in enumerate(prices):
            calculator.price_history.append({
                'price': price,
                'timestamp': base_time + timedelta(seconds=i),
                'change': price - (prices[i-1] if i > 0 else price)
            })
        
        slippage = calculator.calculate_slippage(50000, "BTC-USD")
        assert slippage > 5  # Should be more than base slippage due to volatility
    
    def test_get_volatility_percentile(self, calculator):
        """Test volatility percentile calculation"""
        # Add some price history
        base_time = datetime.now()
        
        # Add varying volatility data
        for i in range(100):
            price = 45000 + (i % 10) * 100  # Create some price variation
            calculator.price_history.append({
                'price': price,
                'timestamp': base_time + timedelta(seconds=i),
                'change': 100 if i % 10 == 0 else -100
            })
        
        percentile = calculator.get_volatility_percentile(10)
        assert 0 <= percentile <= 100
        assert isinstance(percentile, float)
    
    def test_get_price_history(self, calculator):
        """Test getting price history"""
        # Add some price data
        base_time = datetime.now()
        for i in range(10):
            calculator.price_history.append({
                'price': 45000 + i * 100,
                'timestamp': base_time + timedelta(minutes=i),
                'change': 100
            })
        
        # Get last 5 minutes
        history = calculator.get_price_history(5)
        assert len(history) == 6  # 5 minutes + current
        assert all('price' in item for item in history)
        assert all('timestamp' in item for item in history)
    
    def test_get_last_update(self, calculator):
        """Test getting last update timestamp"""
        original_time = calculator.get_last_update()
        assert isinstance(original_time, datetime)
        
        # Update the timestamp
        new_time = datetime.now()
        calculator.last_update = new_time
        
        assert calculator.get_last_update() == new_time
    
    @pytest.mark.asyncio
    async def test_update_price(self, calculator):
        """Test price update functionality"""
        original_price = calculator.current_price
        
        # Call the private method
        await calculator._update_price()
        
        # Price should have changed
        assert calculator.current_price != original_price
        assert len(calculator.price_history) == 1
        
        # Check that price history contains correct data
        latest_entry = calculator.price_history[-1]
        assert 'price' in latest_entry
        assert 'timestamp' in latest_entry
        assert 'change' in latest_entry
    
    def test_price_history_max_length(self, calculator):
        """Test that price history maintains max length"""
        # Add more than max length
        base_time = datetime.now()
        for i in range(1200):  # More than maxlen=1000
            calculator.price_history.append({
                'price': 45000 + i,
                'timestamp': base_time + timedelta(seconds=i),
                'change': 1
            })
        
        # Should be limited to maxlen
        assert len(calculator.price_history) == 1000
    
    @pytest.mark.asyncio
    async def test_stop_feed(self, calculator):
        """Test stopping the price feed"""
        calculator.running = True
        await calculator.stop_feed()
        assert calculator.running is False 