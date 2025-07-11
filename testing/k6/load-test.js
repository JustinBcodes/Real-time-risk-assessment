import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Counter, Trend } from 'k6/metrics';

// Custom metrics
const successRate = new Rate('success_rate');
const orderCounter = new Counter('orders_sent');
const responseTime = new Trend('response_time_ms');

// Test configuration
export let options = {
  stages: [
    { duration: '30s', target: 50 },   // Ramp up to 50 users
    { duration: '1m', target: 100 },   // Stay at 100 users
    { duration: '30s', target: 200 },  // Ramp up to 200 users
    { duration: '2m', target: 200 },   // Stay at 200 users
    { duration: '30s', target: 0 },    // Ramp down
  ],
  thresholds: {
    'success_rate': ['rate>0.95'],
    'response_time_ms': ['p(95)<20'],
    'http_req_duration': ['p(95)<20'],
  },
};

// Base URL for the risk service
const BASE_URL = 'http://risk-service:8080';

// Sample order data templates
const orderTemplates = [
  {
    symbol: 'BTC-USD',
    side: 'BUY',
    orderType: 'LIMIT',
    quantity: 0.1,
    price: 45000
  },
  {
    symbol: 'BTC-USD',
    side: 'SELL',
    orderType: 'LIMIT',
    quantity: 0.05,
    price: 45100
  },
  {
    symbol: 'ETH-USD',
    side: 'BUY',
    orderType: 'MARKET',
    quantity: 1.0,
    price: 3000
  },
  {
    symbol: 'ETH-USD',
    side: 'SELL',
    orderType: 'LIMIT',
    quantity: 0.5,
    price: 3010
  }
];

// Generate random order
function generateOrder(userId) {
  const template = orderTemplates[Math.floor(Math.random() * orderTemplates.length)];
  const timestamp = new Date().toISOString();
  
  return {
    orderId: `order-${userId}-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
    userId: `user-${userId}`,
    symbol: template.symbol,
    side: template.side,
    quantity: template.quantity * (0.5 + Math.random()),
    price: template.price * (0.95 + Math.random() * 0.1),
    orderType: template.orderType,
    timestamp: timestamp
  };
}

// Main test function
export default function() {
  const userId = Math.floor(Math.random() * 1000) + 1;
  const order = generateOrder(userId);
  
  const params = {
    headers: {
      'Content-Type': 'application/json',
    },
  };
  
  const startTime = Date.now();
  
  // Send order to risk service
  const response = http.post(`${BASE_URL}/api/v1/order`, JSON.stringify(order), params);
  
  const endTime = Date.now();
  const duration = endTime - startTime;
  
  // Record metrics
  orderCounter.add(1);
  responseTime.add(duration);
  
  // Check response
  const success = check(response, {
    'status is 200': (r) => r.status === 200,
    'response time < 50ms': (r) => r.timings.duration < 50,
    'has risk assessment': (r) => {
      if (r.body) {
        const body = JSON.parse(r.body);
        return body.verdict && body.riskScore !== undefined;
      }
      return false;
    },
  });
  
  successRate.add(success);
  
  if (!success) {
    console.log(`Failed request for user ${userId}: ${response.status} ${response.body}`);
  }
  
  // Random sleep between 0.1 and 0.5 seconds
  sleep(0.1 + Math.random() * 0.4);
}

// Setup function (runs once)
export function setup() {
  console.log('Starting Risk Engine Load Test');
  console.log(`Target: ${BASE_URL}`);
  
  // Health check
  const response = http.get(`${BASE_URL}/api/v1/health`);
  if (response.status !== 200) {
    console.error('Health check failed:', response.status);
    return;
  }
  
  console.log('Health check passed');
  return { baseUrl: BASE_URL };
}

// Teardown function (runs once)
export function teardown(data) {
  console.log('Load test completed');
  console.log(`Total orders sent: ${orderCounter.count}`);
} 