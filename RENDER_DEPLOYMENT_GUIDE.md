# 🚀 SL Booking - Render Deployment Guide

**Complete guide to deploy the SL Booking accommodation marketplace to Render cloud platform**

---

## 📊 Project Overview

**SL Booking** is a full-stack accommodation booking platform with:
- **Backend**: Django REST Framework (Python 3.12)
- **Frontend**: Next.js 14 (TypeScript/React)
- **Database**: PostgreSQL (Render managed)
- **Hosting**: Render.com (2 web services)

---

## ✅ Current Status

| Component | Status | URL |
|-----------|--------|-----|
| Backend | ✅ Deployed | https://slbookingsystem.onrender.com |
| Frontend | ⏳ Ready to Deploy | https://slbookingsystem-frontend.onrender.com |
| Database | ✅ Connected | Render PostgreSQL |
| Local Test | ✅ PASS | All services working |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────┐
│   User's Browser                        │
└────────────────┬────────────────────────┘
                 │
                 ↓ HTTPS
    ┌────────────────────────────┐
    │  Frontend (Next.js)         │
    │  slbookingsystem-frontend   │
    │  PORT: 3000 (Render)        │
    │                             │
    │  - Home page                │
    │  - Search properties        │
    │  - Login/Register           │
    │  - Property details         │
    │  - Booking form             │
    └────────────┬────────────────┘
                 │
                 ↓ HTTPS (REST API)
    ┌────────────────────────────┐
    │  Backend (Django REST)      │
    │  slbookingsystem            │
    │  PORT: 8000 (Render)        │
    │                             │
    │  - /api/auth/*              │
    │  - /api/properties/*        │
    │  - /api/bookings/*          │
    │  - /api/payments/*          │
    │  - /api/reviews/*           │
    │  - /api/notifications/*     │
    └────────────┬────────────────┘
                 │
                 ↓ TCP
    ┌────────────────────────────┐
    │  PostgreSQL Database        │
    │  (Render managed)           │
    │                             │
    │  - Users & Authentication   │
    │  - Properties & Rooms       │
    │  - Bookings & Payments      │
    │  - Reviews & Ratings        │
    └─────────────────────────────┘
```

---

## 📋 Deployment Checklist

### Pre-Deployment
- [x] Backend deployed and verified
- [x] Frontend code ready
- [x] Environment variables configured
- [x] Local testing passed
- [x] Git commits pushed
- [x] render.yaml configured

### Deployment Steps
- [ ] Create frontend service in Render
- [ ] Set environment variables
- [ ] Deploy and verify
- [ ] Test communication
- [ ] Verify all pages load

### Post-Deployment
- [ ] Test frontend at service URL
- [ ] Test API documentation
- [ ] Test login/register
- [ ] Test search functionality
- [ ] Monitor logs for errors

---

## 🔧 Backend Service Configuration

### Service Details
- **Name**: `slbookingsystem`
- **Runtime**: Python 3.12
- **Region**: Singapore
- **Root Directory**: `backend/`
- **Status**: ✅ Already Deployed

### Build & Deploy Commands
```bash
Build:       python -m pip install -r requirements.txt && python manage.py collectstatic --noinput
Pre-Deploy:  python manage.py migrate --noinput
Start:       /opt/render/project/src/.venv/bin/gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --timeout 120
```

### Environment Variables
```
DEBUG=False
ALLOWED_HOSTS=slbookingsystem.onrender.com,slbooking.hotel.lk,www.slbooking.hotel.lk
CORS_ALLOWED_ORIGINS=https://slbookingsystem-frontend.onrender.com,https://slbooking.hotel.lk,https://www.slbooking.hotel.lk
CSRF_TRUSTED_ORIGINS=https://slbookingsystem.onrender.com,https://slbookingsystem-frontend.onrender.com,https://slbooking.hotel.lk,https://www.slbooking.hotel.lk
PYTHONUNBUFFERED=1
DATABASE_URL=(auto-set by Render)
SECRET_KEY=(generate in Render dashboard)
```

### Health Check
- **Path**: `/health/`
- **Expected Response**: `{"status": "ok"}`

---

## 🎨 Frontend Service Configuration

### Service Details
- **Name**: `slbookingsystem-frontend`
- **Runtime**: Node
- **Region**: Singapore
- **Root Directory**: `frontend/`
- **Status**: ⏳ Ready to create

### Build & Deploy Commands
```bash
Build:  npm ci && npm run build
Start:  npm start
```

### Environment Variables
```
NEXT_PUBLIC_API_URL=https://slbookingsystem.onrender.com/api
NEXT_PUBLIC_SITE_URL=https://slbookingsystem-frontend.onrender.com
NEXT_PUBLIC_ENABLE_PAYMENTS=true
NEXT_PUBLIC_ENABLE_NOTIFICATIONS=true
```

### Health Check
- **Path**: `/`
- **Expected Response**: HTML page (200 OK)

---

## 📝 Step-by-Step Deployment

### STEP 1: Create Frontend Service

1. Go to **Render Dashboard**
2. Click **New** → **Web Service**
3. Select repository: `roverkalisl/slbookingsystem`
4. Choose branch: `main`

### STEP 2: Configure Service

| Setting | Value |
|---------|-------|
| Name | `slbookingsystem-frontend` |
| Environment | Node |
| Region | Singapore |
| Root Directory | `frontend` |
| Build Command | `npm ci && npm run build` |
| Start Command | `npm start` |

### STEP 3: Add Environment Variables

Click **Advanced** and add:

```
NEXT_PUBLIC_API_URL=https://slbookingsystem.onrender.com/api
NEXT_PUBLIC_SITE_URL=https://slbookingsystem-frontend.onrender.com
NEXT_PUBLIC_ENABLE_PAYMENTS=true
NEXT_PUBLIC_ENABLE_NOTIFICATIONS=true
```

### STEP 4: Configure Health Check

- **Health Check Path**: `/`
- **Protocol**: HTTP

### STEP 5: Create Service

Click **Create Web Service**

- Build begins (3-5 minutes)
- Dependencies installed: `npm ci`
- Frontend built: `npm run build`
- Server starts: `npm start`

---

## ✅ Verification Steps

### A. Frontend Service Live

```bash
# Should return HTML page (Status 200)
curl https://slbookingsystem-frontend.onrender.com/
```

### B. Backend Service Responding

```bash
# Should return {"status": "ok"}
curl https://slbookingsystem.onrender.com/health/
```

### C. API Documentation

Visit: https://slbookingsystem.onrender.com/api/docs/
- Should display Swagger UI
- All endpoints documented

### D. Frontend Pages Load

| URL | Expected |
|-----|----------|
| https://slbookingsystem-frontend.onrender.com/ | Home page |
| https://slbookingsystem-frontend.onrender.com/login | Login form |
| https://slbookingsystem-frontend.onrender.com/register | Registration form |
| https://slbookingsystem-frontend.onrender.com/search | Search results |

### E. API Communication

Open browser DevTools (F12):
1. Go to **Console** tab
2. Reload page at https://slbookingsystem-frontend.onrender.com/
3. Check for API calls to `https://slbookingsystem.onrender.com/api/`
4. No CORS errors should appear

---

## 🐛 Troubleshooting

### Frontend Shows "Not Found"

**Cause**: Service not created or build failed

**Fix**:
1. Check Render Dashboard → slbookingsystem-frontend
2. View build logs
3. Look for `npm install` or `npm run build` errors
4. Common issue: Missing Node modules

**Solution**:
```bash
# In project root
npm ci
npm run build
# Then retry Render deployment
```

### CORS Errors in Console

**Cause**: Frontend calling wrong API domain or backend not configured

**Fix**:
1. Check frontend .env.local: `NEXT_PUBLIC_API_URL=https://slbookingsystem.onrender.com/api`
2. Check backend CORS_ALLOWED_ORIGINS includes frontend domain
3. Redeploy backend service if changed

### API Calls Return 404

**Cause**: API endpoint doesn't exist or wrong URL

**Fix**:
1. Visit https://slbookingsystem.onrender.com/api/docs/
2. Check available endpoints
3. Verify frontend is calling correct URLs

### Database Connection Error

**Cause**: DATABASE_URL not set or invalid

**Fix**:
1. Render Dashboard → slbookingsystem → Environment
2. Ensure DATABASE_URL is set
3. Redeploy service

### Build Timeout

**Cause**: Dependencies taking too long or build command error

**Fix**:
1. Check build logs for errors
2. Increase timeout if needed
3. Verify package.json dependencies are correct

---

## 📊 Monitoring & Logs

### View Logs

1. Render Dashboard → Service Name
2. Click **Logs** tab
3. Watch real-time output during deployment

### Key Logs to Check

**Backend (Django):**
```
Starting gunicorn
Listening at: http://0.0.0.0:PORT
Using worker: sync
Booting worker
```

**Frontend (Next.js):**
```
npm ci
npm run build
npm start
Listening on http://0.0.0.0:PORT
```

### Health Monitoring

**Backend Health Check:**
```bash
# Run periodically
curl https://slbookingsystem.onrender.com/health/
```

**Frontend Status:**
```bash
# Check if service is up
curl -I https://slbookingsystem-frontend.onrender.com/
```

---

## 🔐 Security Configuration

### CORS Settings

Frontend domain must be in `CORS_ALLOWED_ORIGINS`:
```
https://slbookingsystem-frontend.onrender.com
```

### CSRF Protection

Frontend domain must be in `CSRF_TRUSTED_ORIGINS`:
```
https://slbookingsystem-frontend.onrender.com
```

### HTTPS/SSL

- ✅ Render provides free SSL certificates
- ✅ All traffic encrypted with HTTPS
- ✅ Automatic certificate renewal

### Secret Key

- ✅ Generate secure Django SECRET_KEY
- ✅ Store in Render environment variables
- ✅ Never commit to Git

---

## 🔄 Database Migrations

Migrations run automatically on deployment via:

**Backend preDeployCommand:**
```bash
python manage.py migrate --noinput
```

**Models Include:**
- Users & Authentication (JWT)
- Properties & Room Types
- Bookings & Payments
- Reviews & Ratings
- Notifications

---

## 📚 API Endpoints

### Authentication
```
POST   /api/auth/register/          # Register new user
POST   /api/auth/login/             # Login (returns JWT)
POST   /api/auth/logout/            # Logout
GET    /api/auth/me/                # Get current user
```

### Properties
```
GET    /api/properties/             # List properties
GET    /api/properties/{id}/        # Get property details
GET    /api/properties/search/advanced/  # Advanced search
```

### Bookings
```
POST   /api/bookings/               # Create booking
GET    /api/bookings/               # List user bookings
GET    /api/bookings/{id}/          # Get booking details
POST   /api/bookings/{id}/cancel/   # Cancel booking
POST   /api/bookings/calculate-price/  # Calculate price
```

### Payments
```
POST   /api/payments/initiate/      # Initiate payment
POST   /api/payments/{id}/confirm/  # Confirm payment
POST   /api/payments/{id}/refund/   # Process refund
```

### Reviews
```
POST   /api/reviews/                # Submit review
GET    /api/reviews/?property_id=   # Get property reviews
```

---

## 📱 Supported Devices

Frontend is fully responsive:
- ✅ Desktop (1920px+)
- ✅ Laptop (1024px)
- ✅ Tablet (768px)
- ✅ Mobile (375px)

All pages tested and working on mobile browsers.

---

## 🎯 Next Steps After Deployment

1. **Test User Flows**
   - Register new account
   - Search properties
   - View property details
   - Create booking
   - Submit review

2. **Monitor Logs**
   - Check for errors
   - Monitor performance
   - Review API response times

3. **Set Up Monitoring**
   - Enable Render alerts
   - Set up error tracking (Sentry)
   - Monitor database performance

4. **Custom Domains** (Optional)
   - Point `slbooking.hotel.lk` to frontend
   - Point `api.slbooking.hotel.lk` to backend
   - Configure DNS records

---

## 📞 Support & Troubleshooting

### Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| Frontend 404 | Check service created in Render |
| CORS errors | Verify CORS_ALLOWED_ORIGINS set correctly |
| API 500 error | Check backend logs for exceptions |
| Build timeout | Increase timeout or check logs |
| Database error | Verify DATABASE_URL environment variable |

### Render Documentation
- https://render.com/docs/
- https://render.com/docs/deploy-node
- https://render.com/docs/deploy-django

### SL Booking Documentation
- GitHub: https://github.com/roverkalisl/slbookingsystem
- ARCHITECTURE.md: System design
- CLAUDE.md: Project overview

---

## ✨ Summary

**Your complete SL Booking application is ready for cloud deployment!**

- ✅ Backend: Django REST API (Deployed)
- ✅ Frontend: Next.js React App (Ready to deploy)
- ✅ Database: PostgreSQL (Connected)
- ✅ Configuration: All verified
- ✅ Testing: Local tests passed

**Deploy to Render** using the steps above and your booking platform will be live! 🎉

---

**Last Updated**: 2026-09-13  
**Status**: Ready for Production Deployment  
**Commits**: 3 verified and tested  
**Test Result**: ✅ ALL PASS
