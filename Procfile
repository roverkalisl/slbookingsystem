release: python manage.py collectstatic --noinput --clear --settings=config.settings.production && python manage.py migrate --noinput --settings=config.settings.production
web: /opt/render/project/src/.venv/bin/python -m gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --timeout 120 --access-logfile - --error-logfile -
