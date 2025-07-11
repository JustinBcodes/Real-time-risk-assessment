package com.riskengine.service;

import com.riskengine.model.Order;
import com.riskengine.model.RiskAssessment;
import com.riskengine.model.RiskVerdict;
import io.github.bucket4j.Bucket;
import io.github.bucket4j.Bucket4j;
import io.github.bucket4j.Bandwidth;
import io.github.bucket4j.Refill;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.time.Duration;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ConcurrentMap;

@Service
public class RiskService {
    
    private static final Logger logger = LoggerFactory.getLogger(RiskService.class);
    
    // Risk thresholds
    private static final BigDecimal MAX_NOTIONAL_PER_ORDER = new BigDecimal("10000");
    private static final BigDecimal MAX_USER_EXPOSURE = new BigDecimal("50000");
    private static final int MAX_ORDERS_PER_MINUTE = 10;
    
    private final OrderPublisher orderPublisher;
    private final ExposureTracker exposureTracker;
    private final ConcurrentMap<String, Bucket> userRateLimitBuckets = new ConcurrentHashMap<>();
    
    @Autowired
    public RiskService(OrderPublisher orderPublisher, ExposureTracker exposureTracker) {
        this.orderPublisher = orderPublisher;
        this.exposureTracker = exposureTracker;
    }
    
    public RiskAssessment assessOrder(Order order) {
        long startTime = System.currentTimeMillis();
        
        List<String> reasons = new ArrayList<>();
        RiskVerdict verdict = RiskVerdict.ACCEPT;
        BigDecimal riskScore = BigDecimal.ZERO;
        
        // 1. Validate notional cap
        BigDecimal notional = order.getNotional();
        if (notional.compareTo(MAX_NOTIONAL_PER_ORDER) > 0) {
            reasons.add("Notional amount exceeds maximum allowed: " + MAX_NOTIONAL_PER_ORDER);
            verdict = RiskVerdict.REJECT;
            riskScore = riskScore.add(BigDecimal.valueOf(50));
        }
        
        // 2. Check rate limits
        if (!checkRateLimit(order.getUserId())) {
            reasons.add("Rate limit exceeded: maximum " + MAX_ORDERS_PER_MINUTE + " orders per minute");
            verdict = RiskVerdict.REJECT;
            riskScore = riskScore.add(BigDecimal.valueOf(30));
        }
        
        // 3. Check user exposure
        BigDecimal currentExposure = exposureTracker.getUserExposure(order.getUserId());
        BigDecimal newExposure = calculateNewExposure(currentExposure, order);
        if (newExposure.compareTo(MAX_USER_EXPOSURE) > 0) {
            reasons.add("User exposure would exceed maximum allowed: " + MAX_USER_EXPOSURE);
            if (verdict == RiskVerdict.ACCEPT) {
                verdict = RiskVerdict.WARN;
            }
            riskScore = riskScore.add(BigDecimal.valueOf(20));
        }
        
        // 4. Symbol-specific checks
        if (order.getSymbol().startsWith("BTC")) {
            if (notional.compareTo(new BigDecimal("5000")) > 0) {
                reasons.add("Large BTC order - increased volatility risk");
                if (verdict == RiskVerdict.ACCEPT) {
                    verdict = RiskVerdict.WARN;
                }
                riskScore = riskScore.add(BigDecimal.valueOf(15));
            }
        }
        
        // 5. Time-based checks (market hours, etc.)
        LocalDateTime now = LocalDateTime.now();
        int hour = now.getHour();
        if (hour < 9 || hour > 16) {
            reasons.add("Order placed outside market hours - reduced liquidity risk");
            if (verdict == RiskVerdict.ACCEPT) {
                verdict = RiskVerdict.WARN;
            }
            riskScore = riskScore.add(BigDecimal.valueOf(10));
        }
        
        // Update exposure if order is accepted
        if (verdict == RiskVerdict.ACCEPT || verdict == RiskVerdict.WARN) {
            exposureTracker.updateUserExposure(order.getUserId(), newExposure);
        }
        
        // Publish order to analytics service
        try {
            orderPublisher.publishOrder(order);
        } catch (Exception e) {
            logger.error("Failed to publish order to analytics service", e);
            reasons.add("Failed to publish to analytics service");
        }
        
        // Build assessment
        RiskAssessment assessment = new RiskAssessment();
        assessment.setOrderId(order.getOrderId());
        assessment.setUserId(order.getUserId());
        assessment.setVerdict(verdict);
        assessment.setRiskScore(riskScore);
        assessment.setReasons(reasons.isEmpty() ? List.of("All risk checks passed") : reasons);
        assessment.setNotionalAmount(notional);
        assessment.setUserExposure(newExposure);
        assessment.setProcessingTimeMs(System.currentTimeMillis() - startTime);
        
        logger.info("Risk assessment completed for order {}: verdict={}, score={}, time={}ms",
                   order.getOrderId(), verdict, riskScore, assessment.getProcessingTimeMs());
        
        return assessment;
    }
    
    private boolean checkRateLimit(String userId) {
        Bucket bucket = userRateLimitBuckets.computeIfAbsent(userId, this::createRateLimitBucket);
        return bucket.tryConsume(1);
    }
    
    private Bucket createRateLimitBucket(String userId) {
        Bandwidth limit = Bandwidth.classic(MAX_ORDERS_PER_MINUTE, Refill.intervally(MAX_ORDERS_PER_MINUTE, Duration.ofMinutes(1)));
        return Bucket4j.builder()
                .addLimit(limit)
                .build();
    }
    
    private BigDecimal calculateNewExposure(BigDecimal currentExposure, Order order) {
        BigDecimal orderExposure = order.getNotional();
        switch (order.getSide()) {
            case BUY:
                return currentExposure.add(orderExposure);
            case SELL:
                return currentExposure.subtract(orderExposure);
            default:
                return currentExposure;
        }
    }
} 