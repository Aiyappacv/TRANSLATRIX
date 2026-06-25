#!/bin/bash
set -e

echo "🚀 Starting TRANSLATRIX PRO Backend..."

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ .env file not found!"
    echo "📝 Copying .env.example to .env..."
    cp .env.example .env
    echo "⚠️  Please edit .env with your configuration before continuing."
    exit 1
fi

# Start infrastructure
echo "🐳 Starting Docker services..."
docker-compose up -d postgres redis minio

# Wait for services
echo "⏳ Waiting for services to be ready..."
sleep 5

# Run migrations
echo "🗄️  Running database migrations..."
alembic upgrade head

# Seed roles
echo "🌱 Seeding default roles..."
python app/scripts/seed_roles.py

# Start API server
echo "✅ Starting FastAPI server..."
echo "📖 API Docs will be available at: http://localhost:8000/docs"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
