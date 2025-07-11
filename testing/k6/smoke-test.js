import http from 'k6/http';
import { check, sleep } from 'k6';

// Smoke test with minimal load
export let options = {
  vus: 1,
  duration: '30s',
  thresholds: {
    'http_req_duration': ['p(95)<100'],
    'http_req_failed': ['rate<0.1'],
  },
};

const BASE_URL = 'http://risk-service:8080';

export default function() {
  // Test 1: Health check
  console.log('Testing health endpoint...');
  let response = http.get(`${BASE_URL}/api/v1/health`);
  check(response, {
    'health check status is 200': (r) => r.status === 200,
    'health check has correct response': (r) => {
      const body = JSON.parse(r.body);
      return body.status === 'UP';
    },
  });

  // Test 2: Metrics endpoint
  console.log('Testing metrics endpoint...');
  response = http.get(`${BASE_URL}/api/v1/metrics`);
  check(response, {
    'metrics status is 200': (r) => r.status === 200,
    'metrics has counters': (r) => {
      const body = JSON.parse(r.body);
      return body.ordersProcessed !== undefined;
    },
  });

  // Test 3: Simple order processing
  console.log('Testing order processing...');
  const order = {
    orderId: 'smoke-test-order-' + Date.now(),
    userId: 'smoke-test-user',
    symbol: 'BTC-USD',
    side: 'BUY',
    quantity: 0.1,
    price: 45000,
    orderType: 'LIMIT',
    timestamp: new Date().toISOString()
  };

  const params = {
    headers: {
      'Content-Type': 'application/json',
    },
  };

  response = http.post(`${BASE_URL}/api/v1/order`, JSON.stringify(order), params);
  check(response, {
    'order processing status is 200': (r) => r.status === 200,
    'order has risk assessment': (r) => {
      const body = JSON.parse(r.body);
      return body.verdict && body.riskScore !== undefined;
    },
    'order response time < 100ms': (r) => r.timings.duration < 100,
  });

  if (response.status === 200) {
    const assessment = JSON.parse(response.body);
    console.log(`Order ${order.orderId} -> ${assessment.verdict} (score: ${assessment.riskScore})`);
  }

  sleep(1);
}

export function setup() {
  console.log('Starting Risk Engine Smoke Test');
  return { baseUrl: BASE_URL };
}

export function teardown(data) {
  console.log('Smoke test completed');
} 