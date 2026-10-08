#!/bin/bash
# ⚠️  DANGER: Deletes ALL data (Postgres volumes)
read -p "This will DELETE all data. Type YES to continue: " confirm

if [ "$confirm" != "YES" ]; then
    echo "Cancelled."
    exit 0
fi

echo "🗑️  Removing containers and volumes..."
docker compose down -v

echo "🏗️  Rebuilding..."
docker compose build --no-cache

echo "🚀 Starting fresh..."
docker compose up -d

echo "✅ Fresh KitchenIQ running"
