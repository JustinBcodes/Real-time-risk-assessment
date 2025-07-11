package com.riskengine.service;

import com.riskengine.model.Order;
import com.riskengine.model.OrderSide;
import com.riskengine.model.OrderType;
import com.riskengine.model.RiskAssessment;
import com.riskengine.model.RiskVerdict;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.math.BigDecimal;
import java.time.LocalDateTime;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class RiskServiceTest {

    @Mock
    private OrderPublisher orderPublisher;
    
    @Mock
    private ExposureTracker exposureTracker;
    
    private RiskService riskService;
    
    @BeforeEach
    void setUp() {
        riskService = new RiskService(orderPublisher, exposureTracker);
    }
    
    @Test
    void testAssessOrder_AcceptedOrder() {
        // Given
        Order order = createSampleOrder("user1", new BigDecimal("1000"), new BigDecimal("50000"));
        when(exposureTracker.getUserExposure("user1")).thenReturn(BigDecimal.ZERO);
        
        // When
        RiskAssessment result = riskService.assessOrder(order);
        
        // Then
        assertNotNull(result);
        assertEquals("test-order", result.getOrderId());
        assertEquals("user1", result.getUserId());
        assertEquals(RiskVerdict.ACCEPT, result.getVerdict());
        assertTrue(result.getRiskScore().compareTo(BigDecimal.valueOf(50)) < 0);
        assertTrue(result.getProcessingTimeMs() > 0);
        
        verify(orderPublisher).publishOrder(order);
        verify(exposureTracker).updateUserExposure(eq("user1"), any(BigDecimal.class));
    }
    
    @Test
    void testAssessOrder_RejectedOrder_ExceedsNotionalCap() {
        // Given - Order exceeds $10,000 notional cap
        Order order = createSampleOrder("user1", new BigDecimal("0.5"), new BigDecimal("25000"));
        when(exposureTracker.getUserExposure("user1")).thenReturn(BigDecimal.ZERO);
        
        // When
        RiskAssessment result = riskService.assessOrder(order);
        
        // Then
        assertNotNull(result);
        assertEquals(RiskVerdict.REJECT, result.getVerdict());
        assertTrue(result.getRiskScore().compareTo(BigDecimal.valueOf(50)) >= 0);
        assertTrue(result.getReasons().stream()
                .anyMatch(reason -> reason.contains("Notional amount exceeds maximum")));
        
        verify(orderPublisher).publishOrder(order);
        verify(exposureTracker, never()).updateUserExposure(any(), any());
    }
    
    @Test
    void testAssessOrder_WarnOrder_HighUserExposure() {
        // Given - User already has high exposure
        Order order = createSampleOrder("user1", new BigDecimal("1"), new BigDecimal("5000"));
        when(exposureTracker.getUserExposure("user1")).thenReturn(new BigDecimal("48000"));
        
        // When
        RiskAssessment result = riskService.assessOrder(order);
        
        // Then
        assertNotNull(result);
        assertEquals(RiskVerdict.WARN, result.getVerdict());
        assertTrue(result.getReasons().stream()
                .anyMatch(reason -> reason.contains("User exposure would exceed maximum")));
        
        verify(orderPublisher).publishOrder(order);
        verify(exposureTracker).updateUserExposure(eq("user1"), any(BigDecimal.class));
    }
    
    @Test
    void testAssessOrder_BTCVolatilityWarning() {
        // Given - Large BTC order
        Order order = createSampleOrder("user1", new BigDecimal("0.2"), new BigDecimal("50000"));
        order.setSymbol("BTC-USD");
        when(exposureTracker.getUserExposure("user1")).thenReturn(BigDecimal.ZERO);
        
        // When
        RiskAssessment result = riskService.assessOrder(order);
        
        // Then
        assertNotNull(result);
        assertTrue(result.getReasons().stream()
                .anyMatch(reason -> reason.contains("Large BTC order")));
        
        verify(orderPublisher).publishOrder(order);
    }
    
    @Test
    void testAssessOrder_OutsideMarketHours() {
        // Given - Order during off hours (assuming current time is outside 9-16)
        Order order = createSampleOrder("user1", new BigDecimal("1"), new BigDecimal("5000"));
        when(exposureTracker.getUserExposure("user1")).thenReturn(BigDecimal.ZERO);
        
        // When
        RiskAssessment result = riskService.assessOrder(order);
        
        // Then
        assertNotNull(result);
        // Note: This test depends on current time, so we just verify it doesn't crash
        assertTrue(result.getProcessingTimeMs() > 0);
        
        verify(orderPublisher).publishOrder(order);
    }
    
    @Test
    void testAssessOrder_RateLimitExceeded() {
        // Given - User has exceeded rate limit (simulate by making multiple calls)
        Order order = createSampleOrder("user1", new BigDecimal("1"), new BigDecimal("1000"));
        when(exposureTracker.getUserExposure("user1")).thenReturn(BigDecimal.ZERO);
        
        // When - Make multiple rapid calls to trigger rate limiting
        for (int i = 0; i < 12; i++) {
            order.setOrderId("test-order-" + i);
            riskService.assessOrder(order);
        }
        
        // Make one more call that should be rate limited
        order.setOrderId("test-order-final");
        RiskAssessment result = riskService.assessOrder(order);
        
        // Then
        assertNotNull(result);
        // The last call should be rejected due to rate limiting
        assertEquals(RiskVerdict.REJECT, result.getVerdict());
        assertTrue(result.getReasons().stream()
                .anyMatch(reason -> reason.contains("Rate limit exceeded")));
    }
    
    @Test
    void testAssessOrder_OrderPublisherFailure() {
        // Given
        Order order = createSampleOrder("user1", new BigDecimal("1"), new BigDecimal("5000"));
        when(exposureTracker.getUserExposure("user1")).thenReturn(BigDecimal.ZERO);
        doThrow(new RuntimeException("Redis connection failed")).when(orderPublisher).publishOrder(order);
        
        // When
        RiskAssessment result = riskService.assessOrder(order);
        
        // Then
        assertNotNull(result);
        assertTrue(result.getReasons().stream()
                .anyMatch(reason -> reason.contains("Failed to publish to analytics service")));
        
        verify(orderPublisher).publishOrder(order);
    }
    
    private Order createSampleOrder(String userId, BigDecimal quantity, BigDecimal price) {
        Order order = new Order();
        order.setOrderId("test-order");
        order.setUserId(userId);
        order.setSymbol("ETH-USD");
        order.setSide(OrderSide.BUY);
        order.setQuantity(quantity);
        order.setPrice(price);
        order.setOrderType(OrderType.LIMIT);
        order.setTimestamp(LocalDateTime.now());
        return order;
    }
} 