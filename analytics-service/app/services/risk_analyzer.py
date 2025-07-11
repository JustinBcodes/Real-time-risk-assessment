import asyncio
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import numpy as np

from app.services.volatility_calculator import VolatilityCalculator
from app.models.analytics_models import RiskAnalysis, Order
from app.config import get_settings

logger = logging.getLogger(__name__)

class RiskAnalyzer:
    def __init__(self, volatility_calculator: VolatilityCalculator):
        self.volatility_calculator = volatility_calculator
        self.settings = get_settings()
        self.user_analytics = {}  # Track user-specific analytics
        
    async def analyze_order(self, order_data: Dict) -> RiskAnalysis:
        """Analyze an order and provide risk assessment"""
        start_time = datetime.now()
        
        try:
            # Parse order data
            order = self._parse_order_data(order_data)
            
            # Initialize risk analysis
            analysis = RiskAnalysis(
                orderId=order.orderId,
                userId=order.userId,
                symbol=order.symbol,
                riskScore=0.0,
                verdict="ACCEPT",
                volatility=0.0,
                slippage=0.0,
                reasons=[],
                processingTimeMs=0
            )
            
            # Calculate risk components
            await self._analyze_volatility_risk(order, analysis)
            await self._analyze_slippage_risk(order, analysis)
            await self._analyze_user_behavior(order, analysis)
            await self._analyze_market_conditions(order, analysis)
            
            # Determine final verdict
            self._determine_verdict(analysis)
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            analysis.processingTimeMs = int(processing_time)
            
            # Update user analytics
            self._update_user_analytics(order, analysis)
            
            logger.info(f"Risk analysis completed for order {order.orderId}: "
                       f"verdict={analysis.verdict}, score={analysis.riskScore:.2f}")
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing order: {e}")
            raise
    
    def _parse_order_data(self, order_data: Dict) -> Order:
        """Parse order data from Redis message"""
        if 'orderData' in order_data:
            # Parse from JSON string
            order_json = json.loads(order_data['orderData'])
            return Order(**order_json)
        else:
            # Parse from direct fields
            return Order(
                orderId=order_data['orderId'],
                userId=order_data['userId'],
                symbol=order_data['symbol'],
                side=order_data['side'],
                quantity=float(order_data['quantity']),
                price=float(order_data['price']),
                orderType=order_data['orderType'],
                timestamp=datetime.fromisoformat(order_data['timestamp'])
            )
    
    async def _analyze_volatility_risk(self, order: Order, analysis: RiskAnalysis):
        """Analyze volatility-related risk"""
        current_vol = self.volatility_calculator.get_current_volatility()
        analysis.volatility = current_vol
        
        # Get volatility percentile
        vol_percentile = self.volatility_calculator.get_volatility_percentile()
        
        # Score volatility risk
        if current_vol > self.settings.extreme_volatility_threshold:
            analysis.riskScore += 30
            analysis.reasons.append(f"Extreme volatility detected: {current_vol:.2%}")
        elif current_vol > self.settings.high_volatility_threshold:
            analysis.riskScore += 15
            analysis.reasons.append(f"High volatility detected: {current_vol:.2%}")
        
        # Check if volatility is unusually high
        if vol_percentile > 90:
            analysis.riskScore += 10
            analysis.reasons.append(f"Volatility in top 10% of recent range ({vol_percentile:.1f}th percentile)")
        
        logger.debug(f"Volatility analysis: vol={current_vol:.2%}, percentile={vol_percentile:.1f}")
    
    async def _analyze_slippage_risk(self, order: Order, analysis: RiskAnalysis):
        """Analyze slippage risk"""
        order_size = order.quantity * order.price
        slippage_bps = self.volatility_calculator.calculate_slippage(order_size, order.symbol)
        analysis.slippage = slippage_bps / 10000  # Convert to decimal
        
        # Score slippage risk
        if slippage_bps > 25:  # > 25 bps
            analysis.riskScore += 20
            analysis.reasons.append(f"High slippage risk: {slippage_bps:.1f} bps")
        elif slippage_bps > 15:  # > 15 bps
            analysis.riskScore += 10
            analysis.reasons.append(f"Moderate slippage risk: {slippage_bps:.1f} bps")
        
        logger.debug(f"Slippage analysis: {slippage_bps:.1f} bps for ${order_size:.2f} order")
    
    async def _analyze_user_behavior(self, order: Order, analysis: RiskAnalysis):
        """Analyze user behavior patterns"""
        user_id = order.userId
        
        # Initialize user analytics if not exists
        if user_id not in self.user_analytics:
            self.user_analytics[user_id] = {
                'total_orders': 0,
                'total_volume': 0.0,
                'recent_orders': [],
                'risk_events': 0,
                'last_activity': datetime.now()
            }
        
        user_data = self.user_analytics[user_id]
        
        # Check recent order frequency
        recent_orders = [
            o for o in user_data['recent_orders'] 
            if o['timestamp'] > datetime.now() - timedelta(minutes=5)
        ]
        
        if len(recent_orders) > 10:  # More than 10 orders in 5 minutes
            analysis.riskScore += 25
            analysis.reasons.append(f"High order frequency: {len(recent_orders)} orders in 5 minutes")
        
        # Check for unusual order size
        order_size = order.quantity * order.price
        if user_data['total_orders'] > 0:
            avg_order_size = user_data['total_volume'] / user_data['total_orders']
            if order_size > avg_order_size * 5:  # 5x larger than average
                analysis.riskScore += 15
                analysis.reasons.append(f"Unusually large order: {order_size/avg_order_size:.1f}x average size")
        
        # Check for first-time user
        if user_data['total_orders'] == 0:
            analysis.riskScore += 5
            analysis.reasons.append("First-time user")
        
        logger.debug(f"User behavior analysis: recent_orders={len(recent_orders)}, "
                    f"total_orders={user_data['total_orders']}")
    
    async def _analyze_market_conditions(self, order: Order, analysis: RiskAnalysis):
        """Analyze current market conditions"""
        current_hour = datetime.now().hour
        
        # Check for off-hours trading
        if current_hour < 9 or current_hour > 16:
            analysis.riskScore += 5
            analysis.reasons.append("Trading outside market hours - reduced liquidity")
        
        # Check for weekend trading
        if datetime.now().weekday() >= 5:  # Saturday or Sunday
            analysis.riskScore += 10
            analysis.reasons.append("Weekend trading - limited market oversight")
        
        # Check price history for recent large moves
        price_history = self.volatility_calculator.get_price_history(5)  # Last 5 minutes
        if len(price_history) > 1:
            recent_changes = [abs(p['change']) for p in price_history[-10:]]
            if recent_changes:
                max_recent_change = max(recent_changes)
                if max_recent_change > order.price * 0.005:  # 0.5% move
                    analysis.riskScore += 10
                    analysis.reasons.append(f"Recent large price movement: {max_recent_change/order.price:.2%}")
        
        logger.debug(f"Market conditions analysis: hour={current_hour}, "
                    f"weekend={datetime.now().weekday() >= 5}")
    
    def _determine_verdict(self, analysis: RiskAnalysis):
        """Determine final risk verdict based on risk score"""
        if analysis.riskScore >= 70:
            analysis.verdict = "REJECT"
        elif analysis.riskScore >= 30:
            analysis.verdict = "WARN"
        else:
            analysis.verdict = "ACCEPT"
        
        # Add summary reason
        if analysis.verdict == "REJECT":
            analysis.reasons.insert(0, f"High risk score: {analysis.riskScore:.1f}/100")
        elif analysis.verdict == "WARN":
            analysis.reasons.insert(0, f"Moderate risk score: {analysis.riskScore:.1f}/100")
        else:
            analysis.reasons.insert(0, f"Low risk score: {analysis.riskScore:.1f}/100")
    
    def _update_user_analytics(self, order: Order, analysis: RiskAnalysis):
        """Update user analytics with new order data"""
        user_id = order.userId
        user_data = self.user_analytics[user_id]
        
        # Update counters
        user_data['total_orders'] += 1
        user_data['total_volume'] += order.quantity * order.price
        user_data['last_activity'] = datetime.now()
        
        # Add to recent orders
        user_data['recent_orders'].append({
            'orderId': order.orderId,
            'timestamp': order.timestamp,
            'size': order.quantity * order.price,
            'riskScore': analysis.riskScore
        })
        
        # Keep only last 100 orders
        if len(user_data['recent_orders']) > 100:
            user_data['recent_orders'] = user_data['recent_orders'][-100:]
        
        # Track risk events
        if analysis.verdict in ['REJECT', 'WARN']:
            user_data['risk_events'] += 1
    
    def get_user_analytics(self, user_id: str) -> Optional[Dict]:
        """Get analytics for a specific user"""
        return self.user_analytics.get(user_id) 