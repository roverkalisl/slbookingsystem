#!/bin/bash

# First, get an auth token
RESPONSE=$(curl -s -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "testpass123"
  }')

TOKEN=$(echo $RESPONSE | grep -o '"access":"[^"]*"' | cut -d'"' -f4)

echo "Token: $TOKEN"
echo ""

if [ -z "$TOKEN" ]; then
  echo "Failed to get auth token"
  exit 1
fi

# Now test property creation
echo "Creating property..."
curl -v -X POST http://localhost:8000/api/properties/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "name": "Test Villa",
    "property_type": 1,
    "description": "Beautiful test property",
    "short_description": "Test",
    "address": "123 Beach Rd",
    "city": "Colombo",
    "district": "Colombo",
    "province": "Western",
    "postal_code": "00100",
    "status": "draft"
  }' 2>&1 | head -100

