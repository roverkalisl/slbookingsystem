#!/bin/bash
set -e

echo "=== SL Booking Build Script ==="
echo "Step 1: Update apt cache..."
apt-get update

echo "Step 2: Install Node.js and npm..."
apt-get install -y nodejs npm

echo "Step 3: Build Next.js frontend..."
cd ../frontend
npm install
npm run build
cd ../backend

echo "Step 4: Install Python dependencies (including gunicorn)..."
python -m pip install -r requirements.txt

echo "Step 5: Collect Django static files..."
python manage.py collectstatic --noinput --clear

echo "Step 6: Copy Next.js frontend build to Django static directory..."
cp -r ../frontend/out/* staticfiles/ 2>/dev/null || echo "Warning: No frontend build found"

echo "=== Build Complete ==="
