#!/bin/bash
# Start KitchenIQ stack
echo "🚀 Starting KitchenIQ..."
docker compose up -d

echo ""
echo "✅ KitchenIQ is running!"
echo ""
echo "   Frontend:  http://localhost:5500"
echo "   Backend:   http://localhost:5050/api/health"
echo "   Postgres:  localhost:5433"
echo ""
echo "   Logs:      docker compose logs -f backend"
echo "   Stop:      ./stop.sh"
