package com.riskengine.service;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.time.Duration;

@Service
public class ExposureTracker {
    
    private static final Logger logger = LoggerFactory.getLogger(ExposureTracker.class);
    private static final String USER_EXPOSURE_KEY_PREFIX = "user:exposure:";
    private static final Duration EXPOSURE_TTL = Duration.ofHours(24);
    
    private final RedisTemplate<String, Object> redisTemplate;
    
    @Autowired
    public ExposureTracker(RedisTemplate<String, Object> redisTemplate) {
        this.redisTemplate = redisTemplate;
    }
    
    public BigDecimal getUserExposure(String userId) {
        String key = USER_EXPOSURE_KEY_PREFIX + userId;
        String exposureStr = (String) redisTemplate.opsForValue().get(key);
        
        if (exposureStr == null) {
            return BigDecimal.ZERO;
        }
        
        try {
            return new BigDecimal(exposureStr);
        } catch (NumberFormatException e) {
            logger.warn("Invalid exposure value for user {}: {}", userId, exposureStr);
            return BigDecimal.ZERO;
        }
    }
    
    public void updateUserExposure(String userId, BigDecimal newExposure) {
        String key = USER_EXPOSURE_KEY_PREFIX + userId;
        redisTemplate.opsForValue().set(key, newExposure.toString(), EXPOSURE_TTL);
        logger.debug("Updated exposure for user {} to {}", userId, newExposure);
    }
    
    public void incrementUserExposure(String userId, BigDecimal amount) {
        BigDecimal currentExposure = getUserExposure(userId);
        BigDecimal newExposure = currentExposure.add(amount);
        updateUserExposure(userId, newExposure);
    }
    
    public void decrementUserExposure(String userId, BigDecimal amount) {
        BigDecimal currentExposure = getUserExposure(userId);
        BigDecimal newExposure = currentExposure.subtract(amount);
        updateUserExposure(userId, newExposure);
    }
    
    public void resetUserExposure(String userId) {
        String key = USER_EXPOSURE_KEY_PREFIX + userId;
        redisTemplate.delete(key);
        logger.info("Reset exposure for user {}", userId);
    }
} 