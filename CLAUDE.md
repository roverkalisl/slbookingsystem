# SL Booking Project Documentation

## Project Overview

**SL Booking** is a production-ready accommodation marketplace for Sri Lanka, serving as an alternative to Airbnb and Booking.com. The platform allows property owners to list accommodations and guests to search, compare, and book properties.

**Website**: slbooking.hotel.lk

## Architecture

Complete system architecture, database design, and technical roadmap documented in `ARCHITECTURE.md`.

Key features:
- Multi-user role system (Super Admin, Property Owner, Property Staff, Guest)
- Double-booking prevention with database-level locking
- Payment gateway abstraction layer
- Comprehensive notification system
- Destination pages for SEO

## Technology Stack

### Backend
- **Framework**: Django 4.2 + Django REST Framework
- **Database**: PostgreSQL 14+ (ACID transactions for booking safety)
- **Authentication**: JWT tokens (djangorestframework-simplejwt)
- **Async**: Celery + Redis
- **Media**: Cloudinary
- **Email**: SendGrid/Gmail

### Frontend (Coming Phase 2)
- **Framework**: Next.js 13+ TypeScript
- **Styling**: Tailwind CSS
- **State**: React Context + React Query
- **Deployment**: Vercel or self-hosted

### Infrastructure
- **Server**: Ubuntu 22.04 LTS + Nginx + Gunicorn
- **Database**: PostgreSQL with automated backups
- **Cache**: Redis for sessions and search results
- **Monitoring**: Sentry for error tracking

## Current Phase: Phase 1 Foundation ✅

### Completed
✅ Project structure (backend Django apps)
✅ Database models (40+ entities)
✅ Authentication system (JWT, registration, login)
✅ User roles and permissions (RBAC)
✅ Admin configuration for all models
✅ API URL routing structure
✅ Settings configuration (development/production)
✅ Environment configuration (.env.example)
✅ Setup scripts (setup.sh, setup.bat)

### In Progress
- 🔄 Running first migrations
- 🔄 Creating initial data fixtures
- 🔄 Testing authentication endpoints

### Next Steps (Phase 2)
- Property management APIs
- Photo upload to Cloudinary
- Room type management
- Pricing configuration

## Key Database Models

### Core
- `User` (custom, email-based)
- `UserProfile` (extended info)
- `Role` (super_admin, property_owner, property_staff, guest)
- `UserRole` (user-role relationships)
- `SystemSetting` (configuration)

### Properties
- `Property` (main property record)
- `PropertyType` (hotel, villa, resort, etc.)
- `PropertyPhoto` (Cloudinary URLs)
- `PropertyAmenity` (many-to-many with Amenity)
- `Amenity` (configurable amenities)
- `Destination` (SEO destination pages)
- `RoomType` (room types within property)
- `RoomTypePhoto`
- `RoomTypeAmenity`

### Bookings & Payments (CRITICAL)
- `Booking` (main booking with transaction safety)
- `BookingGuest` (guest details)
- `Availability` (daily availability tracking)
- `Payment` (payment records - abstraction layer)
- `Refund` (refund records)

### Reviews & Notifications
- `Review` (guest reviews, one per booking)
- `ReviewResponse` (owner responses)
- `Notification` (email/SMS/push log)

## API Structure

All APIs prefixed with `/api/`:

- `/api/auth/` - Authentication (register, login, logout, tokens)
- `/api/properties/` - Property management (coming Phase 2)
- `/api/bookings/` - Booking operations (coming Phase 4)
- `/api/payments/` - Payment processing (coming Phase 5)
- `/api/reviews/` - Guest reviews (coming Phase 6)
- `/api/notifications/` - Notifications (coming Phase 5)

API documentation auto-generated at `/api/docs/` (Swagger/OpenAPI).

## Development Setup

### Requirements
- Python 3.11+
- PostgreSQL 14+
- Redis 7+
- Node.js 18+ (frontend, later)

### Quick Start
```bash
# On Linux/Mac:
bash setup.sh

# On Windows:
setup.bat

# Manually:
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env
cd backend
python manage.py migrate --settings=config.settings.development
python manage.py createsuperuser --settings=config.settings.development
python manage.py runserver --settings=config.settings.development
```

Access at:
- Django: `http://localhost:8000`
- Admin: `http://localhost:8000/admin`
- API Docs: `http://localhost:8000/api/docs/`

## Important Architectural Decisions

1. **PostgreSQL over NoSQL** - Booking data is highly relational; ACID transactions essential for double-booking prevention
2. **Django ORM** - Type safety, migration system, security defaults over raw SQL
3. **JWT tokens** - Stateless scaling, mobile app support
4. **Cloudinary for images** - No local storage costs, automatic CDN delivery
5. **Service abstraction** - Payment system abstracted to support multiple gateways without code changes
6. **Database-level locking** - SELECT FOR UPDATE for booking transaction safety
7. **Normalized schema** - No unnecessary data duplication; proper foreign keys and constraints

## Critical Features

### Double-Booking Prevention (Phase 4)
- **Database-level locking**: SELECT FOR UPDATE on room inventory
- **Transaction safety**: Atomic booking creation
- **Unique constraints**: Database prevents overlapping bookings
- **Test coverage**: Concurrent booking scenarios included

### Pricing Engine (Phase 4)
- **Per-date calculation**: Seasonal rates override weekend rates override base price
- **Flexible fees**: Extra guests, children, service fees, taxes
- **Discount support**: Promotions and coupon codes
- **Breakdown display**: Itemized price shown before booking

### Payment Architecture (Phase 5)
- **Abstraction layer**: Switch payment gateways without code changes
- **Multiple methods**: Card, bank transfer, pay-at-property
- **Webhook handling**: Async payment confirmation
- **Transaction tracking**: Secure reference storage

## File Organization

```
hotel_booking/
├── backend/
│   ├── apps/
│   │   ├── core/              # Users, auth, roles
│   │   ├── properties/        # Properties, rooms, amenities
│   │   ├── bookings/          # Bookings, availability
│   │   ├── payments/          # Payments, refunds
│   │   ├── reviews/           # Reviews, ratings
│   │   └── notifications/     # Email, notifications
│   ├── config/
│   │   ├── settings/
│   │   │   ├── common.py      # Shared settings
│   │   │   ├── development.py # Dev overrides
│   │   │   └── production.py  # Prod overrides
│   │   ├── urls.py            # Main URL router
│   │   └── wsgi.py
│   ├── manage.py
│   └── logs/
├── frontend/                  # Next.js frontend (Phase 2+)
├── docs/                      # Documentation
├── .env.example               # Environment template
├── requirements.txt           # Python dependencies
├── ARCHITECTURE.md            # Full system design
├── CLAUDE.md                  # This file
├── README.md                  # Quick start guide
├── setup.sh                   # Linux/Mac setup
└── setup.bat                  # Windows setup
```

## Authentication

JWT-based authentication:
- **Access tokens**: 1 hour lifetime
- **Refresh tokens**: 7 days lifetime
- **Token rotation**: Refresh tokens rotate on use
- **Blacklisting**: Disabled refresh tokens for logout

Register:
```bash
POST /api/auth/register/
{
  "email": "user@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "password": "SecurePass123!",
  "password2": "SecurePass123!",
  "role": "guest"  # or "property_owner"
}
```

Login:
```bash
POST /api/auth/login/
{
  "email": "user@example.com",
  "password": "SecurePass123!"
}
```

## User Roles

1. **Super Admin**
   - Full system access
   - Manage properties, users, payments, reports
   - Configure system settings
   - Approve/reject properties
   - View all bookings and commissions

2. **Property Owner**
   - Create and manage own properties
   - Upload photos and manage amenities
   - Create room types and set pricing
   - Manage availability and bookings
   - View occupancy and revenue reports
   - Respond to guest reviews
   - Manage staff access

3. **Property Staff**
   - Limited permissions set by owner
   - Manage bookings for assigned property
   - Respond to guests
   - View basic reports

4. **Guest**
   - Search and filter properties
   - View property details
   - Make bookings
   - View booking history
   - Cancel bookings with refunds
   - Submit reviews (post-stay)
   - View own profile

## Testing

Run tests:
```bash
pytest                          # All tests
pytest apps/core/              # Specific app
pytest --cov=apps              # With coverage
pytest apps/core/tests/test_auth.py  # Specific test
```

Critical test scenarios:
- User registration and roles
- Authentication (login/logout)
- Concurrent booking attempts
- Double-booking prevention
- Price calculation
- Refund processing
- Payment webhook handling

## Deployment

### Development
- `DEBUG=True`
- Console email backend
- Eager Celery tasks
- Auto CORS for localhost

### Production
- `DEBUG=False`
- Email via SendGrid
- Async Celery workers
- WhiteNoise for static files
- Gunicorn + Nginx
- SSL/TLS via Let's Encrypt
- Sentry error tracking
- Security headers (CSP, HSTS, etc.)

## Environment Variables

Key variables (see `.env.example`):
- `DEBUG` - Development mode
- `SECRET_KEY` - Django secret
- `DB_*` - PostgreSQL connection
- `CLOUDINARY_*` - Image storage
- `EMAIL_*` - Email configuration
- `CELERY_*` - Async task broker
- `DEFAULT_COMMISSION_PERCENTAGE` - Platform commission

## Common Commands

```bash
# Django management
python manage.py runserver --settings=config.settings.development
python manage.py migrate --settings=config.settings.development
python manage.py makemigrations --settings=config.settings.development
python manage.py createsuperuser --settings=config.settings.development
python manage.py flush --settings=config.settings.development

# Database
python manage.py dbshell
psql slbooking

# Testing
pytest
pytest --cov=apps
pytest -v

# Code quality
black .
flake8 apps/
isort .
```

## Resources

- **ARCHITECTURE.md** - Complete system design, database schema, API spec, technical decisions
- **README.md** - Quick start, setup instructions, project status
- **Requirements.txt** - Python package dependencies
- **.env.example** - Environment configuration template

## Next Phase (Phase 2: Property Management)

Coming soon:
- Property CRUD APIs
- Photo upload to Cloudinary with responsive sizing
- Amenity assignment
- Room type management
- Pricing configuration (base, weekend, seasonal)
- Owner dashboard
- Property status verification workflow
- Admin property approval endpoints

## Notes for Future Development

- All timestamps in UTC (USE_TZ=True)
- Always use database transactions for critical operations
- Implement caching for frequently accessed data
- Add API pagination (PageNumberPagination, default 20 per page)
- Use select_related() and prefetch_related() to avoid N+1 queries
- All user input must be validated
- Never store sensitive data in logs
- Rate limit endpoints to prevent abuse
- Document all API endpoints with OpenAPI/Swagger
- Write tests for all critical business logic

## Troubleshooting

**PostgreSQL connection error**: Check DB_* environment variables
**Port 8000 already in use**: Use `python manage.py runserver 8001` or kill the process
**Migration issues**: Run `python manage.py migrate --settings=config.settings.development` again
**Dependency issues**: Update venv with `pip install --upgrade -r requirements.txt`

## Team Guidelines

- Follow PEP 8 (use `black` for formatting)
- Write docstrings for all classes and methods
- Use type hints for function arguments and returns
- Create model methods for business logic
- Use Django ORM instead of raw SQL
- Test critical paths (authentication, booking, payments)
- Database migrations for all schema changes
- Use meaningful commit messages
- Keep secrets out of version control

---

Last Updated: 2026-09-10
Phase: 1 - Foundation (In Progress)
