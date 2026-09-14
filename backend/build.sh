#!/bin/bash
set -e

echo "=== SL Booking Build Script ==="
echo "Current directory: $(pwd)"
echo "Backend directory: $(cd .. && pwd && cd - > /dev/null)"

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

# Step 4: Collect Django static files (creates staticfiles directory)
echo "Step 4: Collecting Django static files..."
python manage.py collectstatic --noinput --clear

# Step 5: Copy Next.js frontend build to Django static directory
echo "Step 5: Copying Next.js frontend build to Django staticfiles..."

# Use absolute paths to avoid path confusion
FRONTEND_OUT="$(cd .. && pwd)/frontend/out"
STATICFILES="$(pwd)/staticfiles"

echo "Frontend out path: $FRONTEND_OUT"
echo "Staticfiles path: $STATICFILES"

if [ -d "$FRONTEND_OUT" ]; then
  echo "✓ Found frontend/out directory"

  # Copy ALL files from frontend/out to staticfiles
  # Next.js static export generates HTML files for each route:
  # - index.html for /
  # - login.html for /login
  # - register.html for /register
  # - search.html for /search
  # - property/0/index.html for /property/0
  # - _next/static/ for all JS/CSS assets
  #
  # Django serve_frontend() will serve the correct HTML file for each route

  echo "Copying all files from frontend/out..."
  cp -r "$FRONTEND_OUT"/* "$STATICFILES/" || true

  echo "Verifying copy..."
  # Verify the copy worked
  if [ -d "$STATICFILES/_next" ]; then
    echo "✓ Successfully copied _next/ directory"
    FILE_COUNT=$(find "$STATICFILES/_next" -type f 2>/dev/null | wc -l)
    echo "✓ Found $FILE_COUNT files in _next/"
  else
    echo "✗ ERROR: _next/ directory not found after copy!"
    exit 1
  fi

  # Verify HTML files were copied
  echo "Verifying HTML files..."
  for html_file in index login register search bookings; do
    if [ -f "$STATICFILES/${html_file}.html" ]; then
      echo "✓ $html_file.html found"
    else
      echo "⚠ $html_file.html not found (might be OK if route doesn't exist)"
    fi
  done

else
  echo "✗ ERROR: frontend/out directory not found at: $FRONTEND_OUT"
  exit 1
fi

echo "=== Build Complete ==="
