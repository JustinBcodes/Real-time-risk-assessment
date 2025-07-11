package com.riskengine.model;

import com.fasterxml.jackson.annotation.JsonProperty;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;

public class RiskAssessment {
    
    @JsonProperty("orderId")
    private String orderId;
    
    @JsonProperty("userId")
    private String userId;
    
    @JsonProperty("verdict")
    private RiskVerdict verdict;
    
    @JsonProperty("riskScore")
    private BigDecimal riskScore;
    
    @JsonProperty("reasons")
    private List<String> reasons;
    
    @JsonProperty("timestamp")
    private LocalDateTime timestamp;
    
    @JsonProperty("processingTimeMs")
    private Long processingTimeMs;
    
    @JsonProperty("notionalAmount")
    private BigDecimal notionalAmount;
    
    @JsonProperty("userExposure")
    private BigDecimal userExposure;
    
    @JsonProperty("volatility")
    private BigDecimal volatility;
    
    public RiskAssessment() {
        this.timestamp = LocalDateTime.now();
    }
    
    public RiskAssessment(String orderId, String userId, RiskVerdict verdict, 
                         BigDecimal riskScore, List<String> reasons) {
        this.orderId = orderId;
        this.userId = userId;
        this.verdict = verdict;
        this.riskScore = riskScore;
        this.reasons = reasons;
        this.timestamp = LocalDateTime.now();
    }
    
    // Getters and setters
    public String getOrderId() { return orderId; }
    public void setOrderId(String orderId) { this.orderId = orderId; }
    
    public String getUserId() { return userId; }
    public void setUserId(String userId) { this.userId = userId; }
    
    public RiskVerdict getVerdict() { return verdict; }
    public void setVerdict(RiskVerdict verdict) { this.verdict = verdict; }
    
    public BigDecimal getRiskScore() { return riskScore; }
    public void setRiskScore(BigDecimal riskScore) { this.riskScore = riskScore; }
    
    public List<String> getReasons() { return reasons; }
    public void setReasons(List<String> reasons) { this.reasons = reasons; }
    
    public LocalDateTime getTimestamp() { return timestamp; }
    public void setTimestamp(LocalDateTime timestamp) { this.timestamp = timestamp; }
    
    public Long getProcessingTimeMs() { return processingTimeMs; }
    public void setProcessingTimeMs(Long processingTimeMs) { this.processingTimeMs = processingTimeMs; }
    
    public BigDecimal getNotionalAmount() { return notionalAmount; }
    public void setNotionalAmount(BigDecimal notionalAmount) { this.notionalAmount = notionalAmount; }
    
    public BigDecimal getUserExposure() { return userExposure; }
    public void setUserExposure(BigDecimal userExposure) { this.userExposure = userExposure; }
    
    public BigDecimal getVolatility() { return volatility; }
    public void setVolatility(BigDecimal volatility) { this.volatility = volatility; }
    
    @Override
    public String toString() {
        return "RiskAssessment{" +
                "orderId='" + orderId + '\'' +
                ", userId='" + userId + '\'' +
                ", verdict=" + verdict +
                ", riskScore=" + riskScore +
                ", reasons=" + reasons +
                ", timestamp=" + timestamp +
                ", processingTimeMs=" + processingTimeMs +
                '}';
    }
} 