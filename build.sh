#!/usr/bin/env bash
# build.sh - Render build script for Django deployment

# Exit on error
set -o errexit

echo "🚀 Starting Render build process..."

# Install dependencies
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

echo "🗃️ Running Django migrations..."
python manage.py migrate

echo "📁 Collecting static files..."
python manage.py collectstatic --noinput

echo "🔧 Creating cache table (if using database cache)..."
python manage.py createcachetable --dry-run || echo "Cache table creation skipped"

echo "✅ Build completed successfully!"