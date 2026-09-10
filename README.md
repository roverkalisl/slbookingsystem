# SL Booking - Sri Lankan Accommodation Marketplace

A production-ready accommodation booking platform built with Django, PostgreSQL, and Next.js.

## Project Status

**Phase 1: Foundation** - In Progress

- ✅ Project structure initialized
- ✅ Django backend setup
- ✅ Database models created
- ✅ Authentication system (registration, login, JWT)
- ✅ User roles and permissions (Super Admin, Property Owner, Property Staff, Guest)
- ⏳ Django admin interface
- ⏳ API endpoints implementation
- ⏳ Frontend setup

## Technology Stack

### Backend
- **Framework**: Django 4.2 + Django REST Framework
- **Database**: PostgreSQL 14+
- **Authentication**: JWT tokens (djangorestframework-simplejwt)
- **Async Tasks**: Celery + Redis
- **Media Storage**: Cloudinary
- **Cache**: Redis
- **Email**: SendGrid / Gmail

### Frontend
- **Framework**: Next.js 13+ with TypeScript
- **Styling**: Tailwind CSS
- **State Management**: React Context + React Query
- **Deployment**: Vercel or self-hosted

### Infrastructure
- **Server**: Ubuntu 22.04 LTS
- **Application Server**: Gunicorn
- **Reverse Proxy**: Nginx
- **Containerization**: Docker (optional)

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 14+
- Redis 7+
- Node.js 18+ (for frontend)

### Backend Setup

```bash
# 1. Clone the repository
git clone <repository-url>
cd hotel_booking

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create .env file
cp .env.example .env
# Edit .env with your configuration

# 5. Create PostgreSQL database
createdb slbooking

# 6. Run migrations
cd backend
python manage.py migrate --settings=config.settings.development

# 7. Create superuser
python manage.py createsuperuser --settings=config.settings.development

# 8. Load initial data (optional)
python manage.py loaddata initial_data --settings=config.settings.development

# 9. Run development server
python manage.py runserver --settings=config.settings.development
```

Server will be available at: `http://localhost:8000`
API documentation: `http://localhost:8000/api/docs/`
Django admin: `http://localhost:8000/admin/`

### Frontend Setup

```bash
# Create Next.js frontend (in root directory)
npx create-next-app@latest frontend --typescript --tailwind

# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Create .env.local
cat > .env.local <<EOF
NEXT_PUBLIC_API_URL=http://localhost:8000/api
EOF

# Run development server
npm run dev
```

Frontend will be available at: `http://localhost:3000`

## API Documentation

Full API documentation is auto-generated at `/api/docs/` (Swagger/OpenAPI)

### Authentication Endpoints

```
POST   /api/auth/register              # Register new user
POST   /api/auth/login                 # Login (returns JWT)
POST   /api/auth/logout                # Logout
POST   /api/auth/refresh               # Refresh token
GET    /api/auth/me                    # Get current user
PUT    /api/auth/update-profile/       # Update profile
POST   /api/auth/change-password/      # Change password
POST   /api/auth/password-reset-request/
POST   /api/auth/password-reset-confirm/
```

### User Roles

1. **Super Admin** - Full system access
2. **Property Owner** - Can manage own properties and bookings
3. **Property Staff** - Limited permissions for property operations
4. **Guest** - Can search, book, and review properties

## Project Structure

```
hotel_booking/
├── backend/
│   ├── apps/
│   │   ├── core/              # Authentication & user management
│   │   ├── properties/        # Properties, rooms, amenities
│   │   ├── bookings/          # Bookings & availability
│   │   ├── payments/          # Payment processing
│   │   ├── reviews/           # Guest reviews
│   │   └── notifications/     # Email, SMS, notifications
│   ├── config/
│   │   ├── settings/          # Django settings
│   │   ├── urls.py            # URL routing
│   │   └── wsgi.py
│   ├── manage.py
│   └── requirements.txt
├── frontend/                  # Next.js frontend (to be created)
├── docs/                      # Documentation
├── ARCHITECTURE.md            # System design document
└── README.md                  # This file
```

## Development Phases

### Phase 1: Foundation ✅ (In Progress)
- Project setup
- Django + PostgreSQL
- Authentication system
- User roles & permissions
- Core models

### Phase 2: Property Management (Coming Next)
- Owner dashboard
- Property CRUD
- Photos upload
- Room management
- Pricing configuration

### Phase 3: Search & Discovery
- Homepage
- Search functionality
- Filters
- Property detail pages
- Destination pages

### Phase 4: Booking Engine
- Availability calendar
- Booking creation (with double-booking prevention)
- Price calculation
- Booking confirmation

### Phase 5: Payments & Notifications
- Payment gateway integration
- Email notifications
- Booking confirmations
- Review request emails

### Phase 6: Reviews & Admin
- Guest review system
- Admin dashboards
- Property verification
- Revenue reports

### Phase 7: Production & Deployment
- Security audit
- Performance optimization
- Automated tests
- Production deployment

## Database Schema

### Core Entities

**Users & Authentication**
- User (custom user model with email)
- UserProfile (extended profile information)
- Role (super_admin, property_owner, property_staff, guest)
- UserRole (user-role relationships)
- Permission (fine-grained permissions)

**Properties**
- Property (main property model)
- PropertyType (hotel, villa, resort, etc.)
- PropertyPhoto (property photos)
- PropertyAmenity (property amenities)
- Amenity (available amenities)
- Destination (destination pages)

**Rooms & Pricing**
- RoomType (room types within property)
- RoomTypePhoto (room photos)
- RoomTypeAmenity (room amenities)
- Pricing (base pricing)
- SeasonalRate (seasonal pricing)
- Availability (daily availability)

**Bookings & Payments**
- Booking (main booking record)
- BookingGuest (guest information)
- Payment (payment records)
- Refund (refund records)

**Reviews**
- Review (guest reviews)
- ReviewResponse (owner responses)

**Admin**
- Notification (notification log)
- SystemSetting (configuration)

## Authentication

The system uses JWT (JSON Web Tokens) for API authentication:

```bash
# Login
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password123"}'

# Response
{
  "success": true,
  "data": {
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "user": { ... }
  }
}

# Use access token in requests
curl -H "Authorization: Bearer <access_token>" \
  http://localhost:8000/api/auth/me/
```

## Database Migrations

```bash
# Create new migration
python manage.py makemigrations --settings=config.settings.development

# Apply migrations
python manage.py migrate --settings=config.settings.development

# Show migration status
python manage.py showmigrations --settings=config.settings.development

# Revert to specific migration
python manage.py migrate apps.bookings 0001 --settings=config.settings.development
```

## Testing

```bash
# Run all tests
pytest

# Run specific app tests
pytest apps/core/

# Run with coverage
pytest --cov=apps

# Run specific test file
pytest apps/core/tests/test_auth.py

# Run with verbose output
pytest -v
```

## Deployment

### Production Setup

```bash
# 1. Create production .env file
cp .env.example .env.production
# Edit with production values

# 2. Collect static files
python manage.py collectstatic --noinput --settings=config.settings.production

# 3. Run migrations
python manage.py migrate --settings=config.settings.production

# 4. Start Gunicorn
gunicorn config.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers 4 \
  --env DJANGO_SETTINGS_MODULE=config.settings.production

# 5. Configure Nginx (reverse proxy)
# See deployment/nginx.conf
```

### Docker Deployment

```bash
# Build image
docker build -t slbooking:latest .

# Run container
docker run -p 8000:8000 slbooking:latest
```

## Important Features (Phase 1 Foundation)

### Double-Booking Prevention ✅
- Database-level locking
- Transaction-safe booking creation
- Availability constraint checks

### Authentication ✅
- User registration (guest/owner)
- Email-based login
- JWT token generation
- Role-based access control

### User Roles ✅
- Super Admin - full system access
- Property Owner - property management
- Property Staff - limited permissions
- Guest - search & booking

## Common Issues & Solutions

### PostgreSQL Connection Error
```bash
# Make sure PostgreSQL is running
# Check .env DATABASE values
# Verify PostgreSQL user and database exist
createdb slbooking
```

### Port Already in Use
```bash
# Change Django port
python manage.py runserver 8001 --settings=config.settings.development

# Kill process on port 8000 (Linux/Mac)
lsof -ti :8000 | xargs kill -9
```

### Migration Errors
```bash
# Reset database (development only)
python manage.py flush --settings=config.settings.development
python manage.py migrate --settings=config.settings.development
```

## Contributing

1. Create feature branch
2. Make changes
3. Write tests
4. Submit pull request

## Security

- ✅ Password hashing (PBKDF2)
- ✅ CSRF protection
- ✅ XSS protection
- ✅ SQL injection prevention (ORM)
- ✅ HTTPS support
- ✅ Secure cookies
- ⏳ Rate limiting
- ⏳ Input validation

## License

MIT License - see LICENSE file

## Support

For issues, questions, or suggestions:
- GitHub Issues: [Project Issues]
- Email: support@slbooking.hotel.lk
- Documentation: [ARCHITECTURE.md](ARCHITECTURE.md)

## Roadmap

- ✅ Phase 1: Foundation
- ⏳ Phase 2: Property Management
- ⏳ Phase 3: Search & Discovery
- ⏳ Phase 4: Booking Engine
- ⏳ Phase 5: Payments & Notifications
- ⏳ Phase 6: Reviews & Admin
- ⏳ Phase 7: Production & Deployment

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed system design and technical specifications.
