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

# Step 4: Collect Django static files (creates staticfiles directory)
echo "Step 4: Collecting Django static files..."
python manage.py collectstatic --noinput --clear

# Step 5: Copy Next.js frontend build to Django static directory
echo "Step 5: Copying Next.js frontend build to Django staticfiles..."
if [ -d "../frontend/out" ]; then
  echo "Found frontend/out directory, copying files..."
  # Copy all files from frontend/out to staticfiles
  # This includes: index.html, _next/, and other HTML files
  cp -r ../frontend/out/* staticfiles/

  # Verify the copy worked
  if [ -d "staticfiles/_next" ]; then
    echo "✓ Successfully copied _next/ directory"
    # Count files to verify
    FILE_COUNT=$(find staticfiles/_next -type f | wc -l)
    echo "✓ Found $FILE_COUNT files in staticfiles/_next/"
  else
    echo "✗ ERROR: _next/ directory not found after copy!"
    echo "Listing frontend/out contents:"
    ls -la ../frontend/out/
    exit 1
  fi

  # Verify index.html was copied
  if [ -f "staticfiles/index.html" ]; then
    echo "✓ Successfully copied index.html"
  else
    echo "✗ WARNING: index.html not found in staticfiles/"
  fi
else
  echo "✗ ERROR: ../frontend/out directory not found!"
  echo "Available frontend directories:"
  ls -la ../frontend/ | grep -E "^d"
  exit 1
fi

echo "=== Build Complete ==="
