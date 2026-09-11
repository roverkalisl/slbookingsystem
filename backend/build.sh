#!/bin/bash
set -o errexit

# Upgrade pip and setuptools to support Python 3.12
pip install --upgrade pip setuptools

# Install dependencies
pip install --no-cache-dir -r requirements.txt

# Verify Django configuration
python manage.py check --settings=config.settings.production

# Collect static files
python manage.py collectstatic --noinput --settings=config.settings.production

# Run migrations
python manage.py migrate --settings=config.settings.production

echo "✓ Build complete and ready for production"
