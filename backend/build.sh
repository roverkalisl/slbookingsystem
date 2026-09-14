#!/bin/bash
set -e

echo "=== SL Booking Build Script ==="

# Step 1: Ensure Node.js is available (use nvm without apt-get)
echo "Step 1: Setting up Node.js environment..."
export NVM_DIR="$HOME/.nvm"
if [ ! -d "$NVM_DIR" ]; then
  echo "Installing nvm..."
  curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
fi

# Source nvm
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"

# Install and use Node.js 20.11.1
echo "Installing Node.js 20.11.1..."
nvm install 20.11.1
nvm use 20.11.1
nvm alias default 20.11.1

# Verify Node.js and npm
echo "Node version: $(node --version)"
echo "npm version: $(npm --version)"

# Step 2: Build Next.js frontend
echo "Step 2: Building Next.js frontend..."
cd ../frontend
if [ -f "package-lock.json" ]; then
  echo "Using npm ci (lock file detected)..."
  npm ci
else
  echo "Using npm install..."
  npm install
fi
npm run build
cd ../backend

# Step 3: Install Python dependencies (including gunicorn)
echo "Step 3: Installing Python dependencies..."
python -m pip install -r requirements.txt

# Step 4: Collect Django static files
echo "Step 4: Collecting Django static files..."
python manage.py collectstatic --noinput --clear

# Step 5: Copy Next.js frontend build to Django static directory
echo "Step 5: Copying Next.js frontend build to Django staticfiles..."
cp -r ../frontend/out/* staticfiles/ 2>/dev/null || echo "Warning: No frontend build found at ../frontend/out/"

echo "=== Build Complete ==="
