package com.riskengine.model;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonValue;

public enum OrderSide {
    BUY("BUY"),
    SELL("SELL");
    
    private final String value;
    
    OrderSide(String value) {
        this.value = value;
    }
    
    @JsonValue
    public String getValue() {
        return value;
    }
    
    @JsonCreator
    public static OrderSide fromValue(String value) {
        for (OrderSide side : OrderSide.values()) {
            if (side.value.equalsIgnoreCase(value)) {
                return side;
            }
        }
        throw new IllegalArgumentException("Unknown order side: " + value);
    }
} 