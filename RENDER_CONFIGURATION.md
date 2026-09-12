# Render Configuration - Correct Build & Start Commands

**Date**: 2026-09-12
**Issue**: gunicorn: command not found
**Root Cause**: Build/Start Commands not changing to `backend/` directory before running commands

---

## Directory Structure

```
hotel_booking/
├── requirements.txt          ← Root level (for pip install)
├── Procfile                  ← For reference
├── render.yaml               ← Render config
└── backend/
    ├── requirements.txt      ← Duplicate (same as root)
    ├── manage.py             ← Django management (in backend/)
    ├── config/
    │   ├── wsgi.py           ← WSGI module (backend/config/wsgi.py)
    │   └── settings/
    │       └── production.py
    └── apps/
        ├── core/
        ├── properties/
        ├── bookings/
        └── ...
```

---

## Current Broken Configuration

### Build Command (BROKEN)
```bash
pip install --upgrade pip setuptools wheel && pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate
```

**Problems:**
1. ✅ `pip install -r requirements.txt` - Works from root
2. ✅ gunicorn==23.0.0 IS installed
3. ❌ `python manage.py` - FAILS (manage.py is in backend/)
4. ❌ Build fails before collectstatic/migrate run

### Start Command (BROKEN)
```bash
gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --timeout 120 --access-logfile - --error-logfile -
```

**Problems:**
1. ❌ Runs from root directory
2. ❌ Looking for `config.wsgi:application` (should be at backend/config/wsgi.py)
3. ❌ gunicorn IS installed but can't find the WSGI module
4. ❌ Results in: `gunicorn: command not found` (actually: module not found)

---

## Correct Configuration

### Build Command (FIXED)
```bash
pip install --upgrade pip setuptools wheel && pip install -r requirements.txt && cd backend && python manage.py collectstatic --noinput --settings=config.settings.production && python manage.py migrate --noinput --settings=config.settings.production
```

**Why this works:**
1. ✅ `pip install` runs from root (finds requirements.txt)
2. ✅ `cd backend` - Change to Django project directory
3. ✅ `python manage.py` - Now finds manage.py in backend/
4. ✅ collectstatic collects static files
5. ✅ migrate creates database tables
6. ✅ Settings specified explicitly

### Start Command (FIXED)
```bash
cd backend && gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --timeout 120 --access-logfile - --error-logfile -
```

**Why this works:**
1. ✅ `cd backend` - Change to Django project directory
2. ✅ `gunicorn` - Now runs in correct directory
3. ✅ `config.wsgi:application` - Finds backend/config/wsgi.py correctly
4. ✅ WSGI module loads and gunicorn starts

---

## Step-by-Step Fix (in Render Dashboard)

### 1. Go to Service Settings
- Dashboard → slbooking-api → Settings

### 2. Update Build Command
**Find:** Build Command
**Replace with:**
```
pip install --upgrade pip setuptools wheel && pip install -r requirements.txt && cd backend && python manage.py collectstatic --noinput --settings=config.settings.production && python manage.py migrate --noinput --settings=config.settings.production
```

### 3. Update Start Command
**Find:** Start Command
**Replace with:**
```
cd backend && gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --timeout 120 --access-logfile - --error-logfile -
```

### 4. Save Changes

### 5. Deploy
Click: Manual Deploy → Clear build cache and deploy

---

## Expected Build Log

```
==> Running 'pip install --upgrade pip setuptools wheel && pip install -r requirements.txt && cd backend && python manage.py collectstatic --noinput --settings=config.settings.production && python manage.py migrate --noinput --settings=config.settings.production'

Collecting pip
...
Successfully installed pip-26.2.1

Collecting Django==6.0.0
...
Collecting gunicorn==23.0.0
...
Successfully installed [18 packages including gunicorn-23.0.0]

cd backend
python manage.py collectstatic --noinput
165 static files collected...

python manage.py migrate --noinput
Running migrations:
  Applying core.0001_initial... OK
  ... [migrations applied]
  
==> Launching web service...
==> Running 'cd backend && gunicorn config.wsgi:application ...'

[2026-09-12 12:00:00 +0000] [1] [INFO] Starting gunicorn 23.0.0
[2026-09-12 12:00:00 +0000] [1] [INFO] Listening at: http://0.0.0.0:10000 (1)
[2026-09-12 12:00:00 +0000] [1] [INFO] Using worker: sync
[2026-09-12 12:00:01 +0000] [5] [INFO] Booting worker with pid: 5
[2026-09-12 12:00:01 +0000] [6] [INFO] Booting worker with pid: 6

==> Service LIVE at https://slbooking-api.render.com ✓
```

---

## Verification Checklist

- [ ] Build Command updated to include `cd backend &&` before manage.py
- [ ] Start Command updated to include `cd backend &&` before gunicorn
- [ ] Settings module specified: `config.settings.production`
- [ ] Build cache cleared before deploy
- [ ] Deploy initiated
- [ ] Logs show gunicorn starting successfully
- [ ] Service is LIVE at https://slbooking-api.render.com
- [ ] API docs accessible at https://slbooking-api.render.com/api/docs/

---

## Why This Matters

The issue was NOT that gunicorn wasn't installed. gunicorn WAS installed by `pip install -r requirements.txt`, but:

1. **Build Phase Failed Silently**: The build command ran `python manage.py` from the root directory, where manage.py doesn't exist. This caused the build to fail, but Render may have ignored the error or continued anyway.

2. **Start Phase**: When starting, Render tried to run gunicorn from the root directory looking for `config.wsgi:application`, but that module is actually at `backend/config/wsgi.py`.

3. **Symptom vs Cause**: The error message "gunicorn: command not found" was misleading. The actual issue was that the gunicorn process couldn't find the WSGI module, or the environment wasn't set up correctly, or commands were running from the wrong directory.

---

## Summary

**Root Cause**: Build and Start Commands must include `cd backend &&` because Django project (manage.py, config/, etc.) is inside the backend/ directory.

**Fix**: Prefix both commands with `cd backend &&` to ensure they run from the correct directory.

**Result**: gunicorn will find the WSGI module and start successfully.

---

**Status**: Ready for manual update in Render Dashboard
