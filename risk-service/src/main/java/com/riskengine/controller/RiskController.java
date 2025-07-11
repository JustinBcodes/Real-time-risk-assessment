package com.riskengine.controller;

import com.riskengine.model.Order;
import com.riskengine.model.RiskAssessment;
import com.riskengine.service.RiskService;
import io.micrometer.core.annotation.Timed;
import io.micrometer.core.instrument.Counter;
import io.micrometer.core.instrument.MeterRegistry;
import jakarta.validation.Valid;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api/v1")
public class RiskController {
    
    private static final Logger logger = LoggerFactory.getLogger(RiskController.class);
    
    private final RiskService riskService;
    private final Counter orderCounter;
    private final Counter acceptedOrderCounter;
    private final Counter rejectedOrderCounter;
    private final Counter warnOrderCounter;
    
    @Autowired
    public RiskController(RiskService riskService, MeterRegistry meterRegistry) {
        this.riskService = riskService;
        this.orderCounter = Counter.builder("orders.total")
                .description("Total number of orders processed")
                .register(meterRegistry);
        this.acceptedOrderCounter = Counter.builder("orders.accepted")
                .description("Number of orders accepted")
                .register(meterRegistry);
        this.rejectedOrderCounter = Counter.builder("orders.rejected")
                .description("Number of orders rejected")
                .register(meterRegistry);
        this.warnOrderCounter = Counter.builder("orders.warned")
                .description("Number of orders with warnings")
                .register(meterRegistry);
    }
    
    @PostMapping("/order")
    @Timed(value = "order.processing.time", description = "Time taken to process order")
    public ResponseEntity<RiskAssessment> processOrder(@Valid @RequestBody Order order) {
        logger.info("Processing order: {}", order.getOrderId());
        
        try {
            orderCounter.increment();
            
            RiskAssessment assessment = riskService.assessOrder(order);
            
            // Update metrics based on verdict
            switch (assessment.getVerdict()) {
                case ACCEPT:
                    acceptedOrderCounter.increment();
                    break;
                case REJECT:
                    rejectedOrderCounter.increment();
                    break;
                case WARN:
                    warnOrderCounter.increment();
                    break;
            }
            
            logger.info("Order {} processed with verdict: {}", 
                       order.getOrderId(), assessment.getVerdict());
            
            return ResponseEntity.ok(assessment);
            
        } catch (Exception e) {
            logger.error("Error processing order {}: {}", order.getOrderId(), e.getMessage(), e);
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                    .body(createErrorAssessment(order, e.getMessage()));
        }
    }
    
    @GetMapping("/health")
    public ResponseEntity<Map<String, String>> health() {
        return ResponseEntity.ok(Map.of(
                "status", "UP",
                "service", "risk-service"
        ));
    }
    
    @GetMapping("/metrics")
    public ResponseEntity<Map<String, Object>> metrics() {
        return ResponseEntity.ok(Map.of(
                "ordersProcessed", orderCounter.count(),
                "ordersAccepted", acceptedOrderCounter.count(),
                "ordersRejected", rejectedOrderCounter.count(),
                "ordersWarned", warnOrderCounter.count()
        ));
    }
    
    private RiskAssessment createErrorAssessment(Order order, String errorMessage) {
        RiskAssessment assessment = new RiskAssessment();
        assessment.setOrderId(order.getOrderId());
        assessment.setUserId(order.getUserId());
        assessment.setVerdict(com.riskengine.model.RiskVerdict.REJECT);
        assessment.setReasons(java.util.List.of("Internal error: " + errorMessage));
        return assessment;
    }
} 