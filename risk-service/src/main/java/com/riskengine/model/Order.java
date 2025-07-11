package com.riskengine.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Positive;

import java.math.BigDecimal;
import java.time.LocalDateTime;

public class Order {
    
    @JsonProperty("orderId")
    @NotBlank(message = "Order ID is required")
    private String orderId;
    
    @JsonProperty("userId")
    @NotBlank(message = "User ID is required")
    private String userId;
    
    @JsonProperty("symbol")
    @NotBlank(message = "Symbol is required")
    private String symbol;
    
    @JsonProperty("side")
    @NotNull(message = "Side is required")
    private OrderSide side;
    
    @JsonProperty("quantity")
    @NotNull(message = "Quantity is required")
    @Positive(message = "Quantity must be positive")
    private BigDecimal quantity;
    
    @JsonProperty("price")
    @NotNull(message = "Price is required")
    @Positive(message = "Price must be positive")
    private BigDecimal price;
    
    @JsonProperty("orderType")
    @NotNull(message = "Order type is required")
    private OrderType orderType;
    
    @JsonProperty("timestamp")
    private LocalDateTime timestamp;
    
    public Order() {
        this.timestamp = LocalDateTime.now();
    }
    
    public Order(String orderId, String userId, String symbol, OrderSide side, 
                 BigDecimal quantity, BigDecimal price, OrderType orderType) {
        this.orderId = orderId;
        this.userId = userId;
        this.symbol = symbol;
        this.side = side;
        this.quantity = quantity;
        this.price = price;
        this.orderType = orderType;
        this.timestamp = LocalDateTime.now();
    }
    
    // Getters and setters
    public String getOrderId() { return orderId; }
    public void setOrderId(String orderId) { this.orderId = orderId; }
    
    public String getUserId() { return userId; }
    public void setUserId(String userId) { this.userId = userId; }
    
    public String getSymbol() { return symbol; }
    public void setSymbol(String symbol) { this.symbol = symbol; }
    
    public OrderSide getSide() { return side; }
    public void setSide(OrderSide side) { this.side = side; }
    
    public BigDecimal getQuantity() { return quantity; }
    public void setQuantity(BigDecimal quantity) { this.quantity = quantity; }
    
    public BigDecimal getPrice() { return price; }
    public void setPrice(BigDecimal price) { this.price = price; }
    
    public OrderType getOrderType() { return orderType; }
    public void setOrderType(OrderType orderType) { this.orderType = orderType; }
    
    public LocalDateTime getTimestamp() { return timestamp; }
    public void setTimestamp(LocalDateTime timestamp) { this.timestamp = timestamp; }
    
    public BigDecimal getNotional() {
        return quantity.multiply(price);
    }
    
    @Override
    public String toString() {
        return "Order{" +
                "orderId='" + orderId + '\'' +
                ", userId='" + userId + '\'' +
                ", symbol='" + symbol + '\'' +
                ", side=" + side +
                ", quantity=" + quantity +
                ", price=" + price +
                ", orderType=" + orderType +
                ", timestamp=" + timestamp +
                '}';
    }
} 