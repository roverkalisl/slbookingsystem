release: cd backend && python manage.py migrate --settings=config.settings.production
web: cd backend && gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --timeout 120 --access-logfile - --error-logfile -
