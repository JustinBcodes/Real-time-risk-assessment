#!/bin/bash

# Real-Time Risk Assessment Engine Startup Script
# This script will start the entire risk assessment engine stack

set -e

echo "🚀 Starting Real-Time Risk Assessment Engine..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "❌ docker-compose is not installed. Please install docker-compose first."
    exit 1
fi

# Create necessary directories
mkdir -p logs data

# Pull the latest images
echo "📦 Pulling latest images..."
docker-compose pull

# Start the services
echo "🔧 Starting services..."
docker-compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 10

# Check service health
echo "🔍 Checking service health..."

# Check Risk Service
if curl -s http://localhost:8080/api/v1/health > /dev/null; then
    echo "✅ Risk Service is running (http://localhost:8080)"
else
    echo "❌ Risk Service is not responding"
fi

# Check Analytics Service
if curl -s http://localhost:8000/health > /dev/null; then
    echo "✅ Analytics Service is running (http://localhost:8000)"
else
    echo "❌ Analytics Service is not responding"
fi

# Check Grafana
if curl -s http://localhost:3000 > /dev/null; then
    echo "✅ Grafana is running (http://localhost:3000)"
else
    echo "❌ Grafana is not responding"
fi

# Check Prometheus
if curl -s http://localhost:9090 > /dev/null; then
    echo "✅ Prometheus is running (http://localhost:9090)"
else
    echo "❌ Prometheus is not responding"
fi

echo ""
echo "🎉 Risk Assessment Engine is ready!"
echo ""
echo "📊 Access Points:"
echo "   • Risk Service:      http://localhost:8080"
echo "   • Analytics Service: http://localhost:8000"
echo "   • Grafana Dashboard: http://localhost:3000 (admin/admin)"
echo "   • Prometheus:        http://localhost:9090"
echo ""
echo "🧪 Quick Test:"
echo "   curl -X POST http://localhost:8080/api/v1/order \\"
echo "     -H \"Content-Type: application/json\" \\"
echo "     -d '{\"orderId\":\"test-123\",\"userId\":\"user-001\",\"symbol\":\"BTC-USD\",\"side\":\"BUY\",\"quantity\":0.1,\"price\":45000,\"orderType\":\"LIMIT\",\"timestamp\":\"2024-01-15T10:30:00Z\"}'"
echo ""
echo "📈 Load Testing:"
echo "   docker-compose --profile testing up k6"
echo ""
echo "🔧 View Logs:"
echo "   docker-compose logs -f [service-name]"
echo ""
echo "🛑 Stop Services:"
echo "   docker-compose down" 