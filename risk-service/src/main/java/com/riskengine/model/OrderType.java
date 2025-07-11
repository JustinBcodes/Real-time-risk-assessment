package com.riskengine.model;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonValue;

public enum OrderType {
    MARKET("MARKET"),
    LIMIT("LIMIT"),
    STOP("STOP"),
    STOP_LIMIT("STOP_LIMIT");
    
    private final String value;
    
    OrderType(String value) {
        this.value = value;
    }
    
    @JsonValue
    public String getValue() {
        return value;
    }
    
    @JsonCreator
    public static OrderType fromValue(String value) {
        for (OrderType type : OrderType.values()) {
            if (type.value.equalsIgnoreCase(value)) {
                return type;
            }
        }
        throw new IllegalArgumentException("Unknown order type: " + value);
    }
} 