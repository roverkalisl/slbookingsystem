#!/bin/bash

# SL Booking - Production Build Script
# Builds Next.js frontend and prepares Django for deployment
# Called by Render during build phase

set -e  # Exit on error

echo "=========================================="
echo "SL Booking - Production Build"
echo "=========================================="

# ============================================
# STEP 1: Build Next.js Frontend
# ============================================
echo ""
echo "Step 1: Building Next.js frontend..."
echo "========================================"

cd frontend

# Install dependencies
echo "Installing frontend dependencies..."
npm install --prefer-offline --no-audit

# Build static export
echo "Building frontend (Next.js static export)..."
npm run build

# Verify build output exists
if [ ! -d "out" ]; then
    echo "ERROR: Frontend build failed - out/ directory not created"
    exit 1
fi

echo "✓ Frontend build complete"
echo "✓ Generated files in: frontend/out/"

# ============================================
# STEP 2: Prepare Django Static Root
# ============================================
echo ""
echo "Step 2: Preparing Django staticfiles..."
echo "========================================"

cd ..

# Ensure staticfiles directory exists
mkdir -p backend/staticfiles

# Clear old frontend files (keep other static files)
# We'll let collectstatic handle this, but we need to copy our frontend files
echo "Copying frontend files to Django staticfiles..."

# Copy all frontend/out files to staticfiles/
# This includes: HTML files, _next/ directory, etc.
cp -r frontend/out/* backend/staticfiles/ 2>/dev/null || true

echo "✓ Frontend files copied to backend/staticfiles/"

# List what was copied
echo ""
echo "Generated static files:"
ls -la backend/staticfiles/ | head -20

# ============================================
# STEP 3: Verify Backend Structure
# ============================================
echo ""
echo "Step 3: Verifying backend..."
echo "========================================"

cd backend

# Ensure requirements.txt exists
if [ ! -f "requirements.txt" ]; then
    echo "ERROR: requirements.txt not found"
    exit 1
fi

echo "✓ Backend structure verified"

# ============================================
# STEP 4: Verify Key Frontend Routes
# ============================================
echo ""
echo "Step 4: Verifying frontend routes..."
echo "========================================"

REQUIRED_FILES=(
    "index.html"
    "login.html"
    "register.html"
    "search.html"
    "bookings.html"
    "owner/dashboard.html"
    "owner/properties.html"
    "owner/properties/add.html"
    "owner/properties/manage.html"
    "admin/dashboard.html"
    "admin/properties.html"
)

MISSING_FILES=()

for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "staticfiles/$file" ]; then
        echo "✓ $file"
    else
        echo "✗ $file MISSING"
        MISSING_FILES+=("$file")
    fi
done

if [ ${#MISSING_FILES[@]} -gt 0 ]; then
    echo ""
    echo "WARNING: Some frontend files are missing:"
    printf '%s\n' "${MISSING_FILES[@]}"
    echo "This may cause 404 errors on those routes"
fi

# ============================================
# STEP 5: Build Complete
# ============================================
echo ""
echo "=========================================="
echo "Build Complete!"
echo "=========================================="
echo ""
echo "Summary:"
echo "  ✓ Frontend built and copied"
echo "  ✓ Backend ready for deployment"
echo ""
echo "Next steps (handled by Render):"
echo "  - Migrate database"
echo "  - Collect static files"
echo "  - Start Gunicorn"
echo ""
