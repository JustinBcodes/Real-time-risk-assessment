package com.riskengine.service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.riskengine.model.Order;
import io.micrometer.core.instrument.Counter;
import io.micrometer.core.instrument.MeterRegistry;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;

import java.util.Map;

@Service
public class OrderPublisher {
    
    private static final Logger logger = LoggerFactory.getLogger(OrderPublisher.class);
    private static final String ORDERS_STREAM = "orders:stream";
    
    private final RedisTemplate<String, Object> redisTemplate;
    private final ObjectMapper objectMapper;
    private final Counter publishedOrdersCounter;
    private final Counter failedPublishCounter;
    
    @Autowired
    public OrderPublisher(RedisTemplate<String, Object> redisTemplate, 
                         ObjectMapper objectMapper, 
                         MeterRegistry meterRegistry) {
        this.redisTemplate = redisTemplate;
        this.objectMapper = objectMapper;
        this.publishedOrdersCounter = Counter.builder("orders.published")
                .description("Number of orders published to Redis")
                .register(meterRegistry);
        this.failedPublishCounter = Counter.builder("orders.publish.failed")
                .description("Number of failed order publications")
                .register(meterRegistry);
    }
    
    public void publishOrder(Order order) {
        try {
            String orderJson = objectMapper.writeValueAsString(order);
            
            Map<String, Object> messageBody = Map.of(
                "orderId", order.getOrderId(),
                "userId", order.getUserId(),
                "symbol", order.getSymbol(),
                "side", order.getSide().getValue(),
                "quantity", order.getQuantity().toString(),
                "price", order.getPrice().toString(),
                "orderType", order.getOrderType().getValue(),
                "timestamp", order.getTimestamp().toString(),
                "orderData", orderJson
            );
            
            redisTemplate.opsForStream().add(ORDERS_STREAM, messageBody);
            
            publishedOrdersCounter.increment();
            logger.debug("Published order {} to Redis stream", order.getOrderId());
            
        } catch (JsonProcessingException e) {
            failedPublishCounter.increment();
            logger.error("Failed to serialize order {} to JSON", order.getOrderId(), e);
            throw new RuntimeException("Failed to publish order", e);
        } catch (Exception e) {
            failedPublishCounter.increment();
            logger.error("Failed to publish order {} to Redis", order.getOrderId(), e);
            throw new RuntimeException("Failed to publish order", e);
        }
    }
} 