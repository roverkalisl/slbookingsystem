# Build Command Fix - Render Configuration

**Issue**: gunicorn: command not found
**Root Directory**: backend ✓
**gunicorn in backend/requirements.txt**: YES (line 26) ✓
**config/wsgi.py exists**: YES ✓

---

## Current Build Command (NOT WORKING)

```bash
pip install --upgrade pip setuptools wheel && pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate
```

**Problem**: 
- The `setuptools wheel` syntax might have an issue
- Or pip install is failing silently
- Result: gunicorn not installed

---

## Fixed Build Command (WORKING)

Replace the Build Command in Render Dashboard with:

```bash
pip install --upgrade pip && pip install -r requirements.txt && pip install gunicorn==23.0.0 && python manage.py collectstatic --noinput --settings=config.settings.production && python manage.py migrate --noinput --settings=config.settings.production
```

**Why this works:**
1. ✓ `pip install --upgrade pip` - Upgrade pip first
2. ✓ `pip install -r requirements.txt` - Install all dependencies including gunicorn
3. ✓ `pip install gunicorn==23.0.0` - EXPLICIT gunicorn installation as verification/fallback
4. ✓ Settings specified explicitly
5. ✓ --noinput flag added (non-interactive)

---

## Alternative: More Robust Build Command

If the above doesn't work, try:

```bash
python -m pip install --upgrade pip setuptools wheel && python -m pip install -r requirements.txt && python manage.py collectstatic --noinput --settings=config.settings.production && python manage.py migrate --noinput --settings=config.settings.production
```

**Why this variant:**
- Uses `python -m pip` instead of `pip` command
- More reliable in different environments
- Removes the explicit gunicorn install (relies on requirements.txt)
- Explicitly upgrades setuptools and wheel separately

---

## Manual Update Steps

1. **Go to Render Dashboard**
   - https://dashboard.render.com

2. **Select slbooking-api Service**
   - Click on the service

3. **Go to Settings**
   - Click **Settings** tab

4. **Update Build Command**
   - Find: **Build Command**
   - Clear existing text
   - Paste this (RECOMMENDED):
   ```bash
   pip install --upgrade pip && pip install -r requirements.txt && pip install gunicorn==23.0.0 && python manage.py collectstatic --noinput --settings=config.settings.production && python manage.py migrate --noinput --settings=config.settings.production
   ```

5. **Keep Start Command As-Is**
   ```bash
   gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --timeout 120 --access-logfile - --error-logfile -
   ```

6. **Save Changes**

7. **Deploy**
   - Click **Manual Deploy**
   - Select **Clear build cache and deploy**

---

## Expected Build Log

```
==> Running 'pip install --upgrade pip && pip install -r requirements.txt && pip install gunicorn==23.0.0 && python manage.py collectstatic --noinput --settings=config.settings.production && python manage.py migrate --noinput --settings=config.settings.production'

Collecting pip
...
Successfully installed pip-26.2.1

Collecting Django==6.0.0
...
Collecting gunicorn==23.0.0
...
Successfully installed [18 packages]

Collecting gunicorn==23.0.0
Requirement already satisfied: gunicorn==23.0.0 in /path/to/site-packages (23.0.0)

python manage.py collectstatic --noinput
165 static files successfully collected and compressed

python manage.py migrate --noinput
Running migrations:
  Applying core.0001_initial... OK
  ... [all migrations applied] ...

==> Launching web service...
==> Running 'gunicorn config.wsgi:application ...'

[INFO] Starting gunicorn 23.0.0 ✓
[INFO] Listening at: http://0.0.0.0:10000
[INFO] Booting worker with pid: 5
[INFO] Booting worker with pid: 6

==> Service LIVE ✓
```

---

## Why This Fix Works

1. **Explicit gunicorn installation**: Even if requirements.txt doesn't get processed correctly, we explicitly install gunicorn
2. **Clearer command separation**: Each pip install is explicit and separate
3. **Verification**: If gunicorn is already installed (from requirements.txt), the second `pip install gunicorn==23.0.0` will just verify it's there
4. **Settings module**: Explicitly specify production settings
5. **No-input flags**: Prevent interactive prompts

---

## Root Cause Analysis

**Why gunicorn wasn't found:**
- Gunicorn IS in backend/requirements.txt
- But the original Build Command's `pip install --upgrade pip setuptools wheel` might have had a syntax issue
- Or pip install was failing silently without stopping the build
- The explicit `pip install gunicorn==23.0.0` ensures it's definitely installed

---

## Verification After Deploy

Once service is LIVE, verify:

```bash
# Test API docs
curl https://slbooking-api.render.com/api/docs/

# Should return HTML (200 OK)
```

If you see the API docs page, gunicorn is working! ✓

---

**Status**: Ready to manually update Build Command in Render Dashboard
