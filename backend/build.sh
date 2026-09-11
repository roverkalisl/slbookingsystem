#!/bin/bash
set -o errexit

echo "==> Starting production build..."

# Step 1: Confirm the interpreter and upgrade its packaging tools
echo "==> Verifying Python environment..."
pwd
ls -la
ls -l requirements.txt
grep -i gunicorn requirements.txt
which python
which pip
python --version
python -m pip --version

echo "==> Upgrading pip, setuptools, wheel..."
python -m pip install --upgrade pip setuptools wheel

# Step 2: Install dependencies with BINARY wheels ONLY (no compilation)
echo "==> Installing production dependencies (binary wheels only)..."
python -m pip install --no-cache-dir --only-binary=:all: -r requirements.txt

# Step 3: Fail the build if Gunicorn is not available to this interpreter.
echo "==> Verifying Gunicorn installation..."
python -m pip show gunicorn
python -m gunicorn --version
which gunicorn

# Step 4: Verify Django configuration
echo "==> Verifying Django configuration..."
python manage.py check --settings=config.settings.production

# Step 5: Collect static files
echo "==> Collecting static files..."
python manage.py collectstatic --noinput --clear --settings=config.settings.production

# Step 6: Run database migrations
echo "==> Running database migrations..."
python manage.py migrate --settings=config.settings.production

echo "✓ Build complete and verified for production deployment"
