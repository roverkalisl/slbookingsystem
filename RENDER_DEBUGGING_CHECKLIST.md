# Render Deployment Debugging Checklist - HTTP 500 Analysis

## Status: Code Verified Locally ✅ | Render Issue Unresolved ❌

---

## LOCAL VERIFICATION RESULTS (All Passing)

### Code Quality
- ✅ No syntax errors
- ✅ All imports successful
- ✅ Module dependencies resolve correctly
- ✅ No circular imports

### Serializer Validation
- ✅ PropertyCreateUpdateSerializer validates
- ✅ RoomTypeCreateSerializer handles nested data
- ✅ Required field validation works (name required in rooms)
- ✅ Type checking works (rejects string instead of array)
- ✅ Nested error messages properly formatted

### API Endpoint Testing
- ✅ POST /api/properties/ returns HTTP 201
- ✅ Property record created in database
- ✅ Room types created correctly
- ✅ All fields stored (bed_configuration, bathroom_type, room_size_sqft, view_type)
- ✅ Transaction completes atomically
- ✅ No database errors

### Database Schema (Local SQLite)
- ✅ Migration 0003 applied
- ✅ All new columns exist:
  - bed_configuration
  - bathroom_type
  - room_size_sqft
  - view_type
  - room_type
- ✅ Old columns removed:
  - bed_type (removed)
  - room_size_sqm (removed)

---

## WHAT WE KNOW ABOUT RENDER

### Deployment Configuration (render.yaml)
```yaml
preDeployCommand: python manage.py migrate --noinput --settings=config.settings.production
startCommand: bash start.sh
```

**This means:**
- Migrations SHOULD run automatically before the app starts
- If migration 0003 exists in the deployed code, it SHOULD be applied
- If migrations fail, the app should NOT start properly

### Expected Flow on Render
1. Git push/redeploy triggered
2. build.sh runs (builds Next.js, copies files)
3. preDeployCommand runs migrations
4. start.sh starts Gunicorn
5. API requests served

---

## RENDER HTTP 500 - POSSIBLE ROOT CAUSES

### 1. Migration Not Applied (Primary Suspect)
**Symptom:** Code expects `bed_configuration` column, but only `bed_type` exists
**Result:** Database error → HTTP 500

**Check:**
```bash
ssh into Render
python manage.py showmigrations properties --settings=config.settings.production
# Expected: [X] 0003_remove_roomtype_bed_type_and_more
# If [  ] (not applied), that's the issue
```

### 2. Old Code Still Deployed
**Symptom:** Deployment didn't pull latest code with migration 0003
**Result:** Code tries to use new fields that aren't in database

**Check:**
```bash
ssh into Render
git log -1 --oneline
# Expected: 6e506f6 or later (Add deployment diagnostic...)
# Check if migration file exists: ls backend/apps/properties/migrations/0003*.py
```

### 3. Database Connection Issue
**Symptom:** Connection string wrong, credentials expired, or host unreachable
**Result:** All DB operations fail → HTTP 500

**Check:**
```bash
ssh into Render
python manage.py shell --settings=config.settings.production
>>> from django.db import connection
>>> connection.ensure_connection()  # Should not raise
>>> from apps.properties.models import RoomType
>>> RoomType.objects.count()  # Should work
```

### 4. Environment Variable Missing
**Symptom:** DATABASE_URL, SECRET_KEY, or other env var missing/wrong
**Result:** Django can't connect to database → HTTP 500

**Check in Render Dashboard:**
- Environment variables section
- Verify: DATABASE_URL, SECRET_KEY set
- Verify: DJANGO_SETTINGS_MODULE = config.settings.production

### 5. Schema Mismatch After Migration Rollback
**Symptom:** Migration 0003 applied then rolled back manually
**Result:** Code expects new fields, database has old schema

**Check:**
```sql
SELECT column_name FROM information_schema.columns 
WHERE table_name='room_types' 
ORDER BY ordinal_position;
```
**Expected columns:**
- id, property_id, name, slug, description, room_type
- max_adults, max_children, total_occupancy
- bed_configuration, bathroom_type, number_of_beds
- room_size_sqft, view_type
- is_active, created_at, updated_at

**Must NOT have:**
- bed_type
- room_size_sqm

### 6. Python Package Missing on Render
**Symptom:** A dependency installed locally isn't in requirements.txt or wasn't installed
**Result:** Import error → HTTP 500

**Check:**
```bash
ssh into Render
cat requirements.txt | grep -E "django|djangorest|simplejwt"
pip list | grep -E "django|djangorest|simplejwt"
```

### 7. Render Build Failure (Deployment Not Complete)
**Symptom:** build.sh or preDeployCommand failed silently
**Result:** Old app still running, responds to health checks but errors on real requests

**Check Render Logs:**
- Dashboard → Your Service → Logs
- Look for:
  - "Build failed"
  - "Error during" preDeployCommand
  - "Traceback"
  - Any exception stack traces

---

## MANDATORY DEBUGGING STEPS (In Order)

### Step 1: Check Render Logs (CRITICAL)
```
Render Dashboard → slbookingsystem → Logs
Scroll through entire log output
Look for:
  - Any "ERROR" or "Traceback" messages
  - "error while running preDeployCommand"
  - Python exception stack trace
  - Database connection errors
  - Migration errors
```

**If you find an error, provide the FULL traceback including:**
- Exception type
- Exception message
- File path and line number
- Full call stack

### Step 2: SSH Into Render
```bash
# From Render dashboard, get SSH command
# Then run in order:

# Check code version
git log -1 --oneline

# Check if migration exists
ls -la backend/apps/properties/migrations/0003*.py

# Check migration status
python manage.py showmigrations properties --settings=config.settings.production

# If migration not applied, apply it
python manage.py migrate properties --settings=config.settings.production

# Check database schema
psql $DATABASE_URL -c "
  SELECT column_name, data_type 
  FROM information_schema.columns 
  WHERE table_name='room_types' 
  ORDER BY ordinal_position;
"
```

### Step 3: Verify Frontend Payload
Add this to frontend's onSubmit before sending request:
```typescript
console.log('Payload being sent:', JSON.stringify(propertyData, null, 2))
```
Verify room_types array contains:
- name
- room_type
- bed_configuration
- bathroom_type
- room_size_sqft
- view_type
- max_adults
- total_rooms

### Step 4: Test Endpoint with Valid Data
```bash
# After fixing issues above, test:

POST https://slbookingsystem.onrender.com/api/properties/
Authorization: Bearer <valid-token>
Content-Type: application/json

{
  "name": "Test Property",
  "property_type": 1,
  "description": "Test",
  "city": "Colombo",
  "district": "Colombo",
  "province": "Western",
  "room_types": [{
    "name": "Test Room",
    "room_type": "bedroom",
    "bed_configuration": "double",
    "bathroom_type": "private",
    "max_adults": 2,
    "total_rooms": 1
  }]
}

Expected: HTTP 201
```

---

## FILES TO VERIFY ON RENDER

| File | Purpose | Status |
|------|---------|--------|
| `backend/apps/properties/models.py` | RoomType model with new fields | ✅ Verified locally |
| `backend/apps/properties/migrations/0003_*.py` | Database schema migration | ⚠️ CHECK: Applied? |
| `backend/apps/properties/serializers.py` | RoomTypeCreateSerializer + nested support | ✅ Verified locally |
| `backend/apps/properties/views.py` | Enhanced validation + logging | ✅ Verified locally |
| `frontend/src/app/owner/properties/add/page.tsx` | Sends room_types in request | ✅ Verified locally |

---

## COMMITS TO VERIFY ON RENDER

```
6e506f6 - Add deployment diagnostic report
00e2bac - Fix: Add comprehensive error handling and logging
46c412d - Fix: Complete backend room support
57bb4e4 - Enhance: Expand RoomType with detailed room properties
a79f9db - Feature: Add comprehensive room management
```

**Render should be running at least commit 46c412d for room support to work**

---

## AFTER FIXING - VALIDATION TESTS

Once Render is fixed, test these cases:

### Test A: Valid Property + Room → HTTP 201 ✅
Request: Valid property with 1 room in room_types array
Expected: HTTP 201, property created, rooms saved

### Test B: Valid Property + Multiple Rooms → HTTP 201 ✅
Request: Property with total_rooms=3 (inventory units)
Expected: HTTP 201, 3 room records created

### Test C: No Rooms → HTTP 400 ❌
Request: Property without room_types array
Expected: HTTP 400, error message about missing rooms

### Test D: Missing Room Name → HTTP 400 ❌
Request: room_types with missing 'name' field
Expected: HTTP 400, field-level error message

### Test E: Invalid Bed Config → HTTP 400 ❌
Request: bed_configuration with invalid value (not in choices)
Expected: HTTP 400, choice validation error

---

## EMERGENCY TROUBLESHOOTING

### If HTTP 500 Persists After Migration

Check these in order:
1. **Django crashed?** - Check render logs for Python exceptions
2. **Wrong database?** - Verify DATABASE_URL points to correct PostgreSQL instance
3. **Stale cache?** - Try force redeployment from Render dashboard (no cache)
4. **Corrupted migration?** - Check migration 0003 file isn't truncated/corrupted
5. **App ready signal failing?** - Check apps.py for app_ready() method issues

### Render Support

If you can't resolve it yourself:
1. Take screenshot of complete error from Logs
2. Include the full Python traceback
3. Include output of `python manage.py showmigrations properties`
4. Include PostgreSQL schema for room_types table
5. Contact Render support with that information

---

## DO NOT

❌ Run migrations with --fake  
❌ Manually drop/alter database columns  
❌ Downgrade migrations  
❌ Ignore error messages in logs  

---

**Generated:** 2026-09-16  
**Status:** Awaiting Render-side diagnostics
