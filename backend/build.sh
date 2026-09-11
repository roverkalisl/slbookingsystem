#!/bin/bash
set -o errexit

echo "==> Starting production build..."

# Step 1: Upgrade pip, setuptools, wheel
echo "==> Upgrading pip, setuptools, wheel..."
pip install --upgrade pip setuptools wheel

# Step 2: Install dependencies with BINARY wheels ONLY (no compilation)
echo "==> Installing production dependencies (binary wheels only)..."
pip install --no-cache-dir --only-binary=:all: -r requirements.txt

# Step 3: Verify Django configuration
echo "==> Verifying Django configuration..."
python manage.py check --settings=config.settings.production

# Step 4: Collect static files
echo "==> Collecting static files..."
python manage.py collectstatic --noinput --clear --settings=config.settings.production

# Step 5: Run database migrations
echo "==> Running database migrations..."
python manage.py migrate --settings=config.settings.production

echo "✓ Build complete and verified for production deployment"
