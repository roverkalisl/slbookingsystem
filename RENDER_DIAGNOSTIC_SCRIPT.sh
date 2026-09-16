#!/bin/bash
#
# RENDER PRODUCTION DIAGNOSTIC SCRIPT - READ-ONLY
# DO NOT MODIFY ANYTHING
# DO NOT RUN MIGRATIONS
# DO NOT CHANGE DATABASE
#
# Run this script on Render via SSH to collect diagnostic information
# Paste all output into the diagnostic report
#

echo "=========================================="
echo "RENDER PRODUCTION DIAGNOSTIC - START"
echo "=========================================="
echo ""

# ==========================================
# 1. DEPLOYED COMMIT
# ==========================================
echo "=========================================="
echo "1. DEPLOYED COMMIT"
echo "=========================================="
echo ""
echo "Current Git commit:"
git log -1 --oneline
echo ""
echo "Full commit details:"
git log -1 --pretty=format:"%H %an %ae %ad %s"
echo ""
echo ""

# ==========================================
# 2. MIGRATION FILE EXISTENCE
# ==========================================
echo "=========================================="
echo "2. MIGRATION FILE EXISTENCE"
echo "=========================================="
echo ""
echo "Checking for migration 0003:"
if [ -f "backend/apps/properties/migrations/0003_*.py" ]; then
    echo "Migration file found:"
    ls -la backend/apps/properties/migrations/0003_*.py
else
    echo "Migration file NOT found"
fi
echo ""
echo ""

# ==========================================
# 3. MIGRATION STATUS
# ==========================================
echo "=========================================="
echo "3. MIGRATION STATUS"
echo "=========================================="
echo ""
python manage.py showmigrations properties --settings=config.settings.production
echo ""
echo ""

# ==========================================
# 4. DJANGO MIGRATIONS TABLE
# ==========================================
echo "=========================================="
echo "4. DJANGO MIGRATIONS TABLE"
echo "=========================================="
echo ""
python manage.py shell --settings=config.settings.production << 'SHELL'
from django.db import connection
cursor = connection.cursor()
cursor.execute("SELECT app, name FROM django_migrations WHERE app='properties' ORDER BY name;")
for row in cursor.fetchall():
    print(f"{row[0]:<20} {row[1]}")
SHELL
echo ""
echo ""

# ==========================================
# 5. ROOMTYPE MODEL FIELDS
# ==========================================
echo "=========================================="
echo "5. ROOMTYPE MODEL FIELDS (Django)"
echo "=========================================="
echo ""
python manage.py shell --settings=config.settings.production << 'SHELL'
from apps.properties.models import RoomType
from django.db import connection

print("Django RoomType model fields:")
for field in RoomType._meta.fields:
    print(f"  {field.name}: {field.get_internal_type()}")

print("\nRoomType M2M relationships:")
for field in RoomType._meta.many_to_many:
    print(f"  {field.name}: ManyToManyField")
SHELL
echo ""
echo ""

# ==========================================
# 6. ROOMTYPE DATABASE TABLE SCHEMA
# ==========================================
echo "=========================================="
echo "6. ROOMTYPE DATABASE TABLE SCHEMA"
echo "=========================================="
echo ""
python manage.py shell --settings=config.settings.production << 'SHELL'
from django.db import connection
from apps.properties.models import RoomType

# Get actual table name
table_name = RoomType._meta.db_table
print(f"Table name: {table_name}")
print("")
print("Columns:")

cursor = connection.cursor()
cursor.execute(f"""
    SELECT column_name, data_type, is_nullable
    FROM information_schema.columns
    WHERE table_name = %s
    ORDER BY ordinal_position;
""", [table_name])

for row in cursor.fetchall():
    nullable = "NULL" if row[2] == "YES" else "NOT NULL"
    print(f"  {row[0]:<30} {row[1]:<20} {nullable}")
SHELL
echo ""
echo ""

# ==========================================
# 7. PRODUCTION SETTINGS CHECK
# ==========================================
echo "=========================================="
echo "7. PRODUCTION SETTINGS CHECK"
echo "=========================================="
echo ""
python manage.py shell --settings=config.settings.production << 'SHELL'
from django.conf import settings

print("DEBUG:", settings.DEBUG)
print("DATABASES configured:", "YES" if settings.DATABASES else "NO")
print("DEFAULT_AUTO_FIELD:", settings.DEFAULT_AUTO_FIELD)
print("DATABASE ENGINE:", settings.DATABASES['default']['ENGINE'])
print("ALLOWED_HOSTS:", len(settings.ALLOWED_HOSTS), "hosts configured")
SHELL
echo ""
echo ""

# ==========================================
# 8. MODEL VS DATABASE COMPARISON
# ==========================================
echo "=========================================="
echo "8. MODEL VS DATABASE COMPARISON"
echo "=========================================="
echo ""
python manage.py shell --settings=config.settings.production << 'SHELL'
from django.db import connection
from apps.properties.models import RoomType

table_name = RoomType._meta.db_table
cursor = connection.cursor()
cursor.execute(f"""
    SELECT column_name
    FROM information_schema.columns
    WHERE table_name = %s;
""", [table_name])

db_columns = set(row[0] for row in cursor.fetchall())

expected_fields = {
    'bed_configuration', 'bathroom_type', 'room_size_sqft',
    'view_type', 'room_type', 'amenities'
}
old_fields = {'bed_type', 'room_size_sqm'}

print("NEW FIELDS (should exist):")
for field in expected_fields:
    exists = "YES" if field in db_columns else "NO"
    print(f"  {field:<30} {exists}")

print("\nOLD FIELDS (should NOT exist):")
for field in old_fields:
    exists = "YES" if field in db_columns else "NO"
    print(f"  {field:<30} {exists}")
SHELL
echo ""
echo ""

# ==========================================
# 9. RECENT ERRORS IN LOGS
# ==========================================
echo "=========================================="
echo "9. CHECK LAST 50 DJANGO LOGS"
echo "=========================================="
echo ""
echo "Note: You must manually check Render dashboard → Logs"
echo "Look for 'Traceback', 'ERROR', '500', or 'Exception' messages"
echo "around the time of property submission requests"
echo ""
echo ""

# ==========================================
# DONE
# ==========================================
echo "=========================================="
echo "DIAGNOSTIC COMPLETE"
echo "=========================================="
echo ""
echo "NEXT STEPS:"
echo "1. Copy all output above"
echo "2. Manually check Render logs for HTTP 500 traceback"
echo "3. Provide both to Claude for analysis"
echo ""
