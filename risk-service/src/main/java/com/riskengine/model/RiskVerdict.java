package com.riskengine.model;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonValue;

public enum RiskVerdict {
    ACCEPT("ACCEPT"),
    REJECT("REJECT"),
    WARN("WARN");
    
    private final String value;
    
    RiskVerdict(String value) {
        this.value = value;
    }
    
    @JsonValue
    public String getValue() {
        return value;
    }
    
    @JsonCreator
    public static RiskVerdict fromValue(String value) {
        for (RiskVerdict verdict : RiskVerdict.values()) {
            if (verdict.value.equalsIgnoreCase(value)) {
                return verdict;
            }
        }
        throw new IllegalArgumentException("Unknown risk verdict: " + value);
    }
} 