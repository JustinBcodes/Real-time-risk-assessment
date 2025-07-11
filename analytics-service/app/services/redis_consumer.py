import asyncio
import logging
import json
from typing import Dict, Optional
import redis.asyncio as redis
from datetime import datetime

from app.services.risk_analyzer import RiskAnalyzer
from app.config import get_settings

logger = logging.getLogger(__name__)

class RedisConsumer:
    def __init__(self, risk_analyzer: RiskAnalyzer):
        self.risk_analyzer = risk_analyzer
        self.settings = get_settings()
        self.redis_client = None
        self.running = False
        self.consumer_group = "analytics-group"
        self.consumer_name = "analytics-consumer-1"
        self.stream_name = "orders:stream"
        
    async def start_consuming(self):
        """Start consuming messages from Redis stream"""
        self.running = True
        
        try:
            # Connect to Redis
            self.redis_client = redis.Redis(
                host=self.settings.redis_host,
                port=self.settings.redis_port,
                db=self.settings.redis_db,
                password=self.settings.redis_password,
                decode_responses=True
            )
            
            # Test connection
            await self.redis_client.ping()
            logger.info("Connected to Redis successfully")
            
            # Create consumer group if it doesn't exist
            try:
                await self.redis_client.xgroup_create(
                    self.stream_name, 
                    self.consumer_group, 
                    id='0', 
                    mkstream=True
                )
                logger.info(f"Created consumer group: {self.consumer_group}")
            except redis.exceptions.ResponseError as e:
                if "BUSYGROUP" in str(e):
                    logger.info(f"Consumer group {self.consumer_group} already exists")
                else:
                    raise
            
            # Start consuming messages
            logger.info("Starting message consumption...")
            await self._consume_messages()
            
        except Exception as e:
            logger.error(f"Error in Redis consumer: {e}")
            raise
        finally:
            if self.redis_client:
                await self.redis_client.close()
    
    async def _consume_messages(self):
        """Main message consumption loop"""
        while self.running:
            try:
                # Read messages from stream
                messages = await self.redis_client.xreadgroup(
                    self.consumer_group,
                    self.consumer_name,
                    {self.stream_name: '>'},
                    count=10,
                    block=1000  # Block for 1 second
                )
                
                if messages:
                    await self._process_messages(messages)
                    
            except asyncio.CancelledError:
                logger.info("Consumer cancelled")
                break
            except Exception as e:
                logger.error(f"Error consuming messages: {e}")
                await asyncio.sleep(1)
    
    async def _process_messages(self, messages):
        """Process received messages"""
        for stream, msgs in messages:
            for msg_id, fields in msgs:
                try:
                    await self._process_single_message(msg_id, fields)
                    
                    # Acknowledge message
                    await self.redis_client.xack(
                        self.stream_name,
                        self.consumer_group,
                        msg_id
                    )
                    
                except Exception as e:
                    logger.error(f"Error processing message {msg_id}: {e}")
                    # Don't acknowledge failed messages
    
    async def _process_single_message(self, msg_id: str, fields: Dict):
        """Process a single order message"""
        try:
            logger.debug(f"Processing message {msg_id}: {fields}")
            
            # Analyze the order
            risk_analysis = await self.risk_analyzer.analyze_order(fields)
            
            # Store analysis results in Redis for future reference
            await self._store_analysis_result(msg_id, risk_analysis)
            
            logger.info(f"Processed order {fields.get('orderId', 'unknown')}: "
                       f"verdict={risk_analysis.verdict}, score={risk_analysis.riskScore:.2f}")
            
        except Exception as e:
            logger.error(f"Error processing message {msg_id}: {e}")
            raise
    
    async def _store_analysis_result(self, msg_id: str, analysis):
        """Store analysis result in Redis"""
        try:
            analysis_key = f"analysis:{analysis.orderId}"
            analysis_data = {
                'orderId': analysis.orderId,
                'userId': analysis.userId,
                'symbol': analysis.symbol,
                'verdict': analysis.verdict,
                'riskScore': analysis.riskScore,
                'volatility': analysis.volatility,
                'slippage': analysis.slippage,
                'reasons': json.dumps(analysis.reasons),
                'processingTimeMs': analysis.processingTimeMs,
                'timestamp': analysis.timestamp.isoformat(),
                'messageId': msg_id
            }
            
            # Store with 24 hour expiration
            await self.redis_client.hset(analysis_key, mapping=analysis_data)
            await self.redis_client.expire(analysis_key, 86400)  # 24 hours
            
            logger.debug(f"Stored analysis result: {analysis_key}")
            
        except Exception as e:
            logger.error(f"Error storing analysis result: {e}")
    
    async def stop(self):
        """Stop the consumer"""
        self.running = False
        if self.redis_client:
            await self.redis_client.close()
        logger.info("Redis consumer stopped")
    
    async def get_analysis_result(self, order_id: str) -> Optional[Dict]:
        """Get stored analysis result for an order"""
        if not self.redis_client:
            return None
            
        try:
            analysis_key = f"analysis:{order_id}"
            result = await self.redis_client.hgetall(analysis_key)
            
            if result:
                # Parse JSON fields
                result['reasons'] = json.loads(result.get('reasons', '[]'))
                result['riskScore'] = float(result.get('riskScore', 0))
                result['volatility'] = float(result.get('volatility', 0))
                result['slippage'] = float(result.get('slippage', 0))
                result['processingTimeMs'] = int(result.get('processingTimeMs', 0))
                
            return result
            
        except Exception as e:
            logger.error(f"Error getting analysis result for {order_id}: {e}")
            return None
    
    async def get_pending_messages(self) -> int:
        """Get count of pending messages in the stream"""
        if not self.redis_client:
            return 0
            
        try:
            info = await self.redis_client.xinfo_groups(self.stream_name)
            for group_info in info:
                if group_info['name'] == self.consumer_group:
                    return group_info['pending']
            return 0
        except Exception as e:
            logger.error(f"Error getting pending message count: {e}")
            return 0 