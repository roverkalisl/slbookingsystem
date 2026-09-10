# SL Booking - System Architecture & Design Document

**Version:** 1.0  
**Date:** 2026-09-10  
**Status:** Design Phase  

---

## Table of Contents

1. [System Architecture Overview](#system-architecture-overview)
2. [Technology Stack Rationale](#technology-stack-rationale)
3. [Database Schema Design](#database-schema-design)
4. [API Architecture](#api-architecture)
5. [Frontend Component Architecture](#frontend-component-architecture)
6. [Critical: Booking & Availability Logic](#critical-booking--availability-logic)
7. [Payment Architecture](#payment-architecture)
8. [Authentication & Authorization](#authentication--authorization)
9. [Notification System](#notification-system)
10. [Performance & Scalability](#performance--scalability)
11. [Technical Decisions & Trade-offs](#technical-decisions--trade-offs)
12. [Security Architecture](#security-architecture)
13. [Development Roadmap](#development-roadmap)
14. [Deployment Architecture](#deployment-architecture)

---

## System Architecture Overview

### High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     CLIENT LAYER (Mobile & Desktop)         │
│  ┌──────────────────┐         ┌──────────────────┐          │
│  │   Next.js App    │         │   Admin Panel    │          │
│  │  (Guest Portal)  │         │  (Super Admin)   │          │
│  └────────┬─────────┘         └────────┬─────────┘          │
└───────────┼───────────────────────────┼────────────────────┘
            │ HTTPS                     │ HTTPS
            │                           │
┌───────────┴───────────────────────────┴────────────────────┐
│               API GATEWAY & REVERSE PROXY (Nginx)          │
│  ├─ Rate limiting                                          │
│  ├─ Request validation                                     │
│  ├─ CORS configuration                                     │
│  └─ Static file serving                                    │
└─────────────────────┬──────────────────────────────────────┘
                      │
┌─────────────────────┴──────────────────────────────────────┐
│              APPLICATION LAYER (Django/DRF)                │
│  ┌──────────────────────────────────────────────────┐      │
│  │  Authentication Service                          │      │
│  │  ├─ JWT tokens (access + refresh)                │      │
│  │  ├─ Password hashing (PBKDF2)                    │      │
│  │  └─ Social login (future)                        │      │
│  └──────────────────────────────────────────────────┘      │
│  ┌──────────────────────────────────────────────────┐      │
│  │  Core Business Logic                             │      │
│  │  ├─ Property Management Service                  │      │
│  │  ├─ Booking Service (with TX safety)             │      │
│  │  ├─ Availability Service                         │      │
│  │  ├─ Pricing Service                              │      │
│  │  ├─ Payment Service (abstraction layer)          │      │
│  │  ├─ Review Service                               │      │
│  │  └─ Notification Service                         │      │
│  └──────────────────────────────────────────────────┘      │
│  ┌──────────────────────────────────────────────────┐      │
│  │  API Endpoints (REST)                            │      │
│  │  ├─ /api/auth/                                   │      │
│  │  ├─ /api/properties/                             │      │
│  │  ├─ /api/bookings/                               │      │
│  │  ├─ /api/search/                                 │      │
│  │  ├─ /api/payments/                               │      │
│  │  ├─ /api/admin/                                  │      │
│  │  └─ ...                                          │      │
│  └──────────────────────────────────────────────────┘      │
└─────────────────────┬──────────────────────────────────────┘
                      │
        ┌─────────────┼─────────────┐
        │             │             │
┌───────▼────┐  ┌─────▼──────┐  ┌──▼──────────┐
│ PostgreSQL │  │ Cloudinary │  │ Redis Cache │
│ (Data)     │  │ (Media)    │  │ (Sessions)  │
└────────────┘  └────────────┘  └─────────────┘

Background Jobs:
  ├─ Celery / Django-Q (async tasks)
  ├─ Email notifications
  ├─ Payment webhooks
  └─ Report generation
```

### Architectural Principles

1. **Separation of Concerns** — clear boundaries between frontend, API, business logic, and data layers
2. **Service-Oriented** — core features as independent services
3. **Transaction Safety** — database transactions for critical operations (bookings, payments)
4. **Scalability** — designed for growth (stateless API, caching, async jobs)
5. **Security First** — authentication, authorization, input validation at every layer
6. **Extensibility** — payment gateway abstraction, notification types, future integrations
7. **Mobile First** — API designed for mobile clients, responsive frontend

---

## Technology Stack Rationale

### Frontend: Next.js + TypeScript + Tailwind CSS

**Why Next.js?**
- ✓ Server-side rendering for SEO (property pages, destinations, homepage)
- ✓ Static site generation for performance (FAQs, Terms & Conditions)
- ✓ API routes for simple operations (can reduce backend load)
- ✓ Image optimization built-in
- ✓ Deployment to Vercel or self-hosted
- ✓ File-based routing reduces configuration

**Why TypeScript?**
- ✓ Type safety catches errors at compile time
- ✓ Better IDE support and autocomplete
- ✓ Self-documenting code
- ✓ Easier refactoring

**Why Tailwind CSS?**
- ✓ Utility-first, fast to build custom designs
- ✓ Dark mode support built-in
- ✓ Responsive design (mobile-first)
- ✓ No additional CSS files to manage
- ✓ Consistent spacing and colors

### Backend: Python + Django + Django REST Framework

**Why Django?**
- ✓ Batteries included (auth, admin, ORM)
- ✓ Django ORM with excellent PostgreSQL support
- ✓ Built-in migrations system
- ✓ Strong security defaults (CSRF, XSS, SQL injection protection)
- ✓ Mature ecosystem
- ✓ Excellent documentation

**Why Django REST Framework?**
- ✓ Standardized REST API development
- ✓ Built-in authentication (JWT via third-party)
- ✓ Permissions and throttling
- ✓ Automatic API documentation

### Database: PostgreSQL

**Why PostgreSQL?**
- ✓ ACID compliance ensures data integrity (critical for bookings)
- ✓ JSON/JSONB for flexible data (amenities, room features)
- ✓ Full-text search for property descriptions
- ✓ Excellent scalability
- ✓ Row-level locking prevents race conditions
- ✓ Array and range types (for availability)
- ✓ Transactional support essential for double-booking prevention

### Media: Cloudinary

**Why Cloudinary?**
- ✓ Offload image storage and processing
- ✓ Responsive image generation
- ✓ CDN for fast delivery
- ✓ Image optimization and formats (WebP)
- ✓ No need for local file storage at scale

### Cache: Redis

**Why Redis?**
- ✓ Session storage
- ✓ Cache search results
- ✓ Cache property listings
- ✓ Rate limiting
- ✓ Pub/sub for real-time notifications (future)

---

## Database Schema Design

### Entity-Relationship Model

#### 1. Users & Authentication

```sql
-- Core user account
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email VARCHAR(255) UNIQUE NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  first_name VARCHAR(100),
  last_name VARCHAR(100),
  phone VARCHAR(20),
  is_active BOOLEAN DEFAULT TRUE,
  is_staff BOOLEAN DEFAULT FALSE,  -- Super admin
  created_at TIMESTAMP DEFAULT now(),
  updated_at TIMESTAMP DEFAULT now(),
  last_login TIMESTAMP,
  INDEX idx_email (email),
  INDEX idx_created_at (created_at)
);

-- User profile (extended info)
CREATE TABLE user_profiles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  avatar_url VARCHAR(500),
  bio TEXT,
  phone_verified BOOLEAN DEFAULT FALSE,
  email_verified BOOLEAN DEFAULT FALSE,
  preferred_language VARCHAR(10) DEFAULT 'en',
  notification_email BOOLEAN DEFAULT TRUE,
  notification_sms BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP DEFAULT now(),
  updated_at TIMESTAMP DEFAULT now(),
  FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Roles for RBAC
CREATE TABLE roles (
  id SERIAL PRIMARY KEY,
  name VARCHAR(50) UNIQUE NOT NULL,  -- 'super_admin', 'property_owner', 'property_staff', 'guest'
  description TEXT,
  created_at TIMESTAMP DEFAULT now()
);

-- User roles (many-to-many)
CREATE TABLE user_roles (
  id SERIAL PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  role_id INT NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
  created_at TIMESTAMP DEFAULT now(),
  UNIQUE(user_id, role_id),
  INDEX idx_user_id (user_id)
);

-- Permissions (for future fine-grained control)
CREATE TABLE permissions (
  id SERIAL PRIMARY KEY,
  name VARCHAR(100) UNIQUE NOT NULL,  -- 'create_property', 'approve_property', etc.
  description TEXT
);

-- Role-permission mapping
CREATE TABLE role_permissions (
  id SERIAL PRIMARY KEY,
  role_id INT NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
  permission_id INT NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
  UNIQUE(role_id, permission_id)
);
```

#### 2. Properties & Rooms

```sql
-- Property types (configurable)
CREATE TABLE property_types (
  id SERIAL PRIMARY KEY,
  name VARCHAR(50) UNIQUE NOT NULL,  -- 'hotel', 'villa', 'resort', etc.
  description TEXT,
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT now()
);

-- Amenities (configurable)
CREATE TABLE amenities (
  id SERIAL PRIMARY KEY,
  name VARCHAR(100) NOT NULL,
  slug VARCHAR(100) UNIQUE NOT NULL,  -- 'wifi', 'pool', 'ac', etc.
  icon_url VARCHAR(500),
  category VARCHAR(50),  -- 'facility', 'service', 'safety', etc.
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT now(),
  INDEX idx_slug (slug)
);

-- Main property
CREATE TABLE properties (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  owner_id UUID NOT NULL REFERENCES users(id),
  property_type_id INT NOT NULL REFERENCES property_types(id),
  name VARCHAR(255) NOT NULL,
  slug VARCHAR(255) UNIQUE NOT NULL,
  description TEXT,
  short_description VARCHAR(500),
  
  -- Location
  address VARCHAR(255),
  city VARCHAR(100),
  district VARCHAR(100),
  province VARCHAR(100),
  postal_code VARCHAR(20),
  latitude DECIMAL(10, 8),
  longitude DECIMAL(11, 8),
  google_maps_url VARCHAR(500),
  
  -- Status workflow
  status VARCHAR(50) DEFAULT 'pending',  -- 'pending', 'under_review', 'verified', 'published', 'suspended', 'rejected'
  
  -- Media
  cover_photo_url VARCHAR(500),
  
  -- Ratings
  average_rating DECIMAL(3, 2),
  total_reviews INT DEFAULT 0,
  
  -- Meta
  created_at TIMESTAMP DEFAULT now(),
  updated_at TIMESTAMP DEFAULT now(),
  published_at TIMESTAMP,
  
  INDEX idx_owner_id (owner_id),
  INDEX idx_city (city),
  INDEX idx_status (status),
  INDEX idx_slug (slug),
  FULLTEXT INDEX idx_name_description (name, description)
);

-- Property photos
CREATE TABLE property_photos (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  property_id UUID NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
  cloudinary_url VARCHAR(500),
  cloudinary_public_id VARCHAR(255),
  caption VARCHAR(255),
  display_order INT,
  is_cover BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP DEFAULT now(),
  INDEX idx_property_id (property_id),
  INDEX idx_display_order (display_order)
);

-- Property-amenity relationships
CREATE TABLE property_amenities (
  id SERIAL PRIMARY KEY,
  property_id UUID NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
  amenity_id INT NOT NULL REFERENCES amenities(id),
  UNIQUE(property_id, amenity_id)
);

-- Room types (e.g., Deluxe Double, Family Room, Entire Villa)
CREATE TABLE room_types (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  property_id UUID NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
  name VARCHAR(255) NOT NULL,  -- "Deluxe Double Room"
  slug VARCHAR(255),
  description TEXT,
  
  -- Occupancy
  max_adults INT NOT NULL DEFAULT 2,
  max_children INT NOT NULL DEFAULT 0,
  total_occupancy INT NOT NULL DEFAULT 2,
  
  -- Bed configuration
  bed_type VARCHAR(50),  -- 'single', 'double', 'queen', 'king'
  number_of_beds INT DEFAULT 1,
  
  -- Room inventory
  total_rooms INT DEFAULT 1,  -- Number of this room type available
  
  -- Physical
  room_size_sqm DECIMAL(8, 2),
  
  -- Status
  is_active BOOLEAN DEFAULT TRUE,
  
  -- Metadata
  created_at TIMESTAMP DEFAULT now(),
  updated_at TIMESTAMP DEFAULT now(),
  
  INDEX idx_property_id (property_id),
  INDEX idx_is_active (is_active)
);

-- Room photos
CREATE TABLE room_type_photos (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  room_type_id UUID NOT NULL REFERENCES room_types(id) ON DELETE CASCADE,
  cloudinary_url VARCHAR(500),
  cloudinary_public_id VARCHAR(255),
  display_order INT,
  is_cover BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP DEFAULT now(),
  INDEX idx_room_type_id (room_type_id)
);

-- Room-amenity relationships
CREATE TABLE room_type_amenities (
  id SERIAL PRIMARY KEY,
  room_type_id UUID NOT NULL REFERENCES room_types(id) ON DELETE CASCADE,
  amenity_id INT NOT NULL REFERENCES amenities(id),
  UNIQUE(room_type_id, amenity_id)
);
```

#### 3. Pricing & Availability

```sql
-- Base pricing
CREATE TABLE pricing (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  room_type_id UUID NOT NULL REFERENCES room_types(id) ON DELETE CASCADE,
  base_price DECIMAL(12, 2) NOT NULL,
  weekend_price DECIMAL(12, 2),  -- Friday-Sunday
  extra_guest_fee DECIMAL(10, 2),
  child_fee DECIMAL(10, 2),
  service_fee_percent DECIMAL(5, 2) DEFAULT 5.0,  -- 5% platform fee
  tax_percent DECIMAL(5, 2) DEFAULT 10.0,  -- 10% VAT
  currency VARCHAR(3) DEFAULT 'LKR',
  
  created_at TIMESTAMP DEFAULT now(),
  updated_at TIMESTAMP DEFAULT now(),
  
  UNIQUE(room_type_id)
);

-- Seasonal pricing (overrides base pricing for date ranges)
CREATE TABLE seasonal_rates (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  room_type_id UUID NOT NULL REFERENCES room_types(id) ON DELETE CASCADE,
  name VARCHAR(100),  -- "High Season", "Off Season", "New Year"
  price_per_night DECIMAL(12, 2) NOT NULL,
  start_date DATE NOT NULL,
  end_date DATE NOT NULL,
  
  created_at TIMESTAMP DEFAULT now(),
  updated_at TIMESTAMP DEFAULT now(),
  
  INDEX idx_room_type_id (room_type_id),
  INDEX idx_date_range (start_date, end_date)
);

-- Daily availability (true = available, false = blocked or booked)
CREATE TABLE availability (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  room_type_id UUID NOT NULL REFERENCES room_types(id) ON DELETE CASCADE,
  date DATE NOT NULL,
  status VARCHAR(20) DEFAULT 'available',  -- 'available', 'booked', 'blocked', 'maintenance'
  available_count INT,  -- How many rooms of this type are available on this date
  
  created_at TIMESTAMP DEFAULT now(),
  updated_at TIMESTAMP DEFAULT now(),
  
  UNIQUE(room_type_id, date),
  INDEX idx_room_type_date (room_type_id, date),
  INDEX idx_date (date)
);

-- Discounts & promotions
CREATE TABLE promotions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  property_id UUID NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
  name VARCHAR(255),
  description TEXT,
  discount_type VARCHAR(20),  -- 'percentage', 'fixed'
  discount_value DECIMAL(10, 2),
  max_discount DECIMAL(12, 2),
  
  start_date DATE,
  end_date DATE,
  
  min_nights INT DEFAULT 1,  -- Minimum night stay to apply
  max_uses INT,
  times_used INT DEFAULT 0,
  
  is_active BOOLEAN DEFAULT TRUE,
  
  created_at TIMESTAMP DEFAULT now(),
  updated_at TIMESTAMP DEFAULT now(),
  
  INDEX idx_property_id (property_id),
  INDEX idx_is_active (is_active)
);

-- Coupon codes
CREATE TABLE coupons (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  code VARCHAR(50) UNIQUE NOT NULL,
  description TEXT,
  discount_type VARCHAR(20),  -- 'percentage', 'fixed'
  discount_value DECIMAL(10, 2),
  max_discount DECIMAL(12, 2),
  
  min_booking_value DECIMAL(12, 2),
  
  start_date DATE,
  end_date DATE,
  
  max_uses INT,
  times_used INT DEFAULT 0,
  max_per_user INT DEFAULT 1,
  
  is_active BOOLEAN DEFAULT TRUE,
  
  created_at TIMESTAMP DEFAULT now(),
  updated_at TIMESTAMP DEFAULT now(),
  
  INDEX idx_code (code),
  INDEX idx_is_active (is_active)
);
```

#### 4. Bookings & Payments (CRITICAL)

```sql
-- Core booking (represents a guest's booking)
CREATE TABLE bookings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  booking_reference VARCHAR(50) UNIQUE NOT NULL,  -- "SLB-2026-000001"
  
  property_id UUID NOT NULL REFERENCES properties(id),
  room_type_id UUID NOT NULL REFERENCES room_types(id),
  guest_id UUID NOT NULL REFERENCES users(id),
  
  -- Dates (inclusive)
  check_in_date DATE NOT NULL,
  check_out_date DATE NOT NULL,
  number_of_nights INT NOT NULL,
  
  -- Guests
  number_of_adults INT NOT NULL,
  number_of_children INT DEFAULT 0,
  number_of_rooms INT DEFAULT 1,  -- For multi-room bookings
  
  -- Pricing breakdown
  room_price DECIMAL(12, 2) NOT NULL,  -- Per night
  subtotal DECIMAL(12, 2) NOT NULL,  -- room_price * nights
  discount DECIMAL(12, 2) DEFAULT 0,
  service_fee DECIMAL(12, 2) DEFAULT 0,
  tax DECIMAL(12, 2) DEFAULT 0,
  total_price DECIMAL(12, 2) NOT NULL,
  
  -- Applied discounts
  promotion_id UUID REFERENCES promotions(id) ON DELETE SET NULL,
  coupon_id UUID REFERENCES coupons(id) ON DELETE SET NULL,
  
  -- Booking status
  status VARCHAR(50) DEFAULT 'pending',
  -- Statuses: pending, confirmed, payment_pending, paid, completed, cancelled, rejected, no_show, refunded, partially_refunded
  
  -- Payment status
  payment_status VARCHAR(50) DEFAULT 'pending',
  -- Statuses: pending, processing, paid, failed, cancelled, refunded, partially_refunded
  
  special_requests TEXT,
  
  created_at TIMESTAMP DEFAULT now(),
  updated_at TIMESTAMP DEFAULT now(),
  
  INDEX idx_booking_reference (booking_reference),
  INDEX idx_guest_id (guest_id),
  INDEX idx_property_id (property_id),
  INDEX idx_room_type_id (room_type_id),
  INDEX idx_check_in_date (check_in_date),
  INDEX idx_check_out_date (check_out_date),
  INDEX idx_status (status),
  INDEX idx_payment_status (payment_status),
  
  -- CRITICAL: Unique constraint to prevent double bookings
  -- This alone is not enough; must use transactions
  CONSTRAINT check_dates CHECK (check_in_date < check_out_date)
);

-- Booking guests (for multiple guests per booking)
CREATE TABLE booking_guests (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  booking_id UUID NOT NULL REFERENCES bookings(id) ON DELETE CASCADE,
  
  first_name VARCHAR(100) NOT NULL,
  last_name VARCHAR(100) NOT NULL,
  email VARCHAR(255),
  phone VARCHAR(20),
  
  is_primary_guest BOOLEAN DEFAULT FALSE,
  
  created_at TIMESTAMP DEFAULT now()
);

-- Payment records
CREATE TABLE payments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  booking_id UUID NOT NULL REFERENCES bookings(id) ON DELETE CASCADE,
  
  amount DECIMAL(12, 2) NOT NULL,
  status VARCHAR(50) DEFAULT 'pending',  -- 'pending', 'processing', 'paid', 'failed', 'cancelled'
  
  -- Payment method abstraction
  payment_method VARCHAR(50),  -- 'card', 'bank_transfer', 'pay_at_property', etc.
  
  -- Transaction reference (for reconciliation)
  transaction_reference VARCHAR(255),
  
  -- Gateway response
  gateway_name VARCHAR(100),  -- 'stripe', 'paypal', 'local_gateway', etc.
  gateway_response JSONB,  -- Raw response from payment gateway
  
  error_message TEXT,  -- If failed
  
  created_at TIMESTAMP DEFAULT now(),
  updated_at TIMESTAMP DEFAULT now(),
  
  INDEX idx_booking_id (booking_id),
  INDEX idx_status (status),
  INDEX idx_transaction_reference (transaction_reference)
);

-- Refunds
CREATE TABLE refunds (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  booking_id UUID NOT NULL REFERENCES bookings(id) ON DELETE CASCADE,
  payment_id UUID NOT NULL REFERENCES payments(id),
  
  amount DECIMAL(12, 2) NOT NULL,
  reason VARCHAR(255),
  status VARCHAR(50) DEFAULT 'pending',  -- 'pending', 'processing', 'completed', 'failed'
  
  created_at TIMESTAMP DEFAULT now(),
  updated_at TIMESTAMP DEFAULT now(),
  
  INDEX idx_booking_id (booking_id),
  INDEX idx_status (status)
);
```

#### 5. Reviews & Ratings

```sql
-- Guest reviews
CREATE TABLE reviews (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  booking_id UUID NOT NULL UNIQUE REFERENCES bookings(id),  -- One review per booking
  property_id UUID NOT NULL REFERENCES properties(id),
  guest_id UUID NOT NULL REFERENCES users(id),
  
  -- Ratings (1-5 stars)
  overall_rating INT NOT NULL CHECK (overall_rating >= 1 AND overall_rating <= 5),
  cleanliness_rating INT CHECK (cleanliness_rating >= 1 AND cleanliness_rating <= 5),
  location_rating INT CHECK (location_rating >= 1 AND location_rating <= 5),
  facilities_rating INT CHECK (facilities_rating >= 1 AND facilities_rating <= 5),
  service_rating INT CHECK (service_rating >= 1 AND service_rating <= 5),
  value_rating INT CHECK (value_rating >= 1 AND value_rating <= 5),
  
  comment TEXT,
  
  is_verified BOOLEAN DEFAULT TRUE,  -- True if guest actually stayed
  is_published BOOLEAN DEFAULT TRUE,
  is_flagged BOOLEAN DEFAULT FALSE,  -- For moderation
  
  created_at TIMESTAMP DEFAULT now(),
  updated_at TIMESTAMP DEFAULT now(),
  
  INDEX idx_property_id (property_id),
  INDEX idx_guest_id (guest_id),
  INDEX idx_overall_rating (overall_rating),
  INDEX idx_is_published (is_published)
);

-- Owner responses to reviews
CREATE TABLE review_responses (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  review_id UUID NOT NULL UNIQUE REFERENCES reviews(id) ON DELETE CASCADE,
  owner_id UUID NOT NULL REFERENCES users(id),
  
  response_text TEXT NOT NULL,
  
  created_at TIMESTAMP DEFAULT now(),
  updated_at TIMESTAMP DEFAULT now()
);
```

#### 6. Notifications & Messaging

```sql
-- Email templates (for future admin management)
CREATE TABLE email_templates (
  id SERIAL PRIMARY KEY,
  code VARCHAR(100) UNIQUE NOT NULL,  -- 'booking_confirmation', 'review_request', etc.
  name VARCHAR(255),
  subject VARCHAR(255),
  body_html TEXT,
  
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT now(),
  updated_at TIMESTAMP DEFAULT now()
);

-- Notification log
CREATE TABLE notifications (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  recipient_id UUID NOT NULL REFERENCES users(id),
  
  notification_type VARCHAR(100),  -- 'booking_confirmation', 'payment_received', etc.
  title VARCHAR(255),
  message TEXT,
  
  -- Related objects
  related_booking_id UUID REFERENCES bookings(id),
  related_property_id UUID REFERENCES properties(id),
  
  channel VARCHAR(50),  -- 'email', 'sms', 'push', 'in_app'
  status VARCHAR(50) DEFAULT 'sent',  -- 'pending', 'sent', 'failed', 'read'
  
  created_at TIMESTAMP DEFAULT now(),
  
  INDEX idx_recipient_id (recipient_id),
  INDEX idx_created_at (created_at),
  INDEX idx_status (status)
);

-- Admin & staff messaging
CREATE TABLE messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  sender_id UUID NOT NULL REFERENCES users(id),
  recipient_id UUID NOT NULL REFERENCES users(id),
  
  subject VARCHAR(255),
  body TEXT,
  
  is_read BOOLEAN DEFAULT FALSE,
  is_archived BOOLEAN DEFAULT FALSE,
  
  created_at TIMESTAMP DEFAULT now(),
  updated_at TIMESTAMP DEFAULT now(),
  
  INDEX idx_recipient_id (recipient_id),
  INDEX idx_is_read (is_read)
);
```

#### 7. Admin & Operations

```sql
-- Destination pages (for SEO)
CREATE TABLE destinations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(100) NOT NULL,
  slug VARCHAR(100) UNIQUE NOT NULL,
  description TEXT,
  cover_image_url VARCHAR(500),
  
  city VARCHAR(100),
  district VARCHAR(100),
  province VARCHAR(100),
  
  -- SEO
  seo_title VARCHAR(255),
  seo_description VARCHAR(500),
  seo_keywords VARCHAR(500),
  
  is_published BOOLEAN DEFAULT TRUE,
  
  created_at TIMESTAMP DEFAULT now(),
  updated_at TIMESTAMP DEFAULT now(),
  
  INDEX idx_slug (slug),
  INDEX idx_is_published (is_published)
);

-- Staff members (property staff)
CREATE TABLE staff (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  property_id UUID NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  
  role VARCHAR(50),  -- 'manager', 'receptionist', 'maintenance', etc.
  permissions JSONB,  -- Fine-grained permissions
  
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT now(),
  
  UNIQUE(property_id, user_id)
);

-- Commission configuration
CREATE TABLE commissions (
  id SERIAL PRIMARY KEY,
  name VARCHAR(100),
  percentage DECIMAL(5, 2) NOT NULL,  -- e.g., 7.0 for 7%
  is_default BOOLEAN DEFAULT FALSE,
  
  created_at TIMESTAMP DEFAULT now(),
  updated_at TIMESTAMP DEFAULT now()
);

-- Commission records (what owner owes)
CREATE TABLE owner_commissions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  owner_id UUID NOT NULL REFERENCES users(id),
  booking_id UUID NOT NULL REFERENCES bookings(id),
  
  booking_amount DECIMAL(12, 2),
  commission_percent DECIMAL(5, 2),
  commission_amount DECIMAL(12, 2),
  
  status VARCHAR(50) DEFAULT 'pending',  -- 'pending', 'calculated', 'payout_pending', 'paid'
  
  created_at TIMESTAMP DEFAULT now(),
  updated_at TIMESTAMP DEFAULT now(),
  
  INDEX idx_owner_id (owner_id),
  INDEX idx_status (status)
);

-- Owner payouts
CREATE TABLE payouts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  owner_id UUID NOT NULL REFERENCES users(id),
  
  amount DECIMAL(12, 2) NOT NULL,
  status VARCHAR(50) DEFAULT 'pending',  -- 'pending', 'processing', 'completed', 'failed'
  
  payout_method VARCHAR(50),  -- 'bank_transfer', 'wallet', etc.
  payout_reference VARCHAR(255),
  
  created_at TIMESTAMP DEFAULT now(),
  updated_at TIMESTAMP DEFAULT now(),
  
  INDEX idx_owner_id (owner_id),
  INDEX idx_status (status)
);

-- Audit log
CREATE TABLE audit_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id),
  action VARCHAR(255),  -- 'create_property', 'approve_booking', etc.
  
  object_type VARCHAR(100),  -- 'property', 'booking', 'user', etc.
  object_id UUID,
  
  previous_values JSONB,
  new_values JSONB,
  
  ip_address VARCHAR(45),
  user_agent TEXT,
  
  created_at TIMESTAMP DEFAULT now(),
  
  INDEX idx_user_id (user_id),
  INDEX idx_created_at (created_at),
  INDEX idx_object_type (object_type)
);

-- System settings
CREATE TABLE system_settings (
  id SERIAL PRIMARY KEY,
  setting_key VARCHAR(255) UNIQUE NOT NULL,
  setting_value TEXT,
  
  created_at TIMESTAMP DEFAULT now(),
  updated_at TIMESTAMP DEFAULT now()
);
```

### Key Database Design Decisions

1. **UUID for entities** — Provides better security and distributed system support
2. **Status fields** — Explicit status tracking for auditing and workflow
3. **Timestamps** — created_at and updated_at for all records
4. **Indexes** — On foreign keys, search fields, date ranges, status
5. **JSONB fields** — For flexible data (permissions, gateway responses)
6. **Constraints** — Database-level integrity (check_dates, unique constraints)
7. **Partitioning ready** — Booking tables can be partitioned by date range at scale

---

## API Architecture

### Authentication Endpoints

```
POST   /api/auth/register              # Register user (guest/owner)
POST   /api/auth/login                 # Login (returns JWT access + refresh tokens)
POST   /api/auth/refresh               # Refresh access token
POST   /api/auth/logout                # Logout
POST   /api/auth/password-reset        # Request password reset
POST   /api/auth/password-reset/confirm  # Confirm password reset
GET    /api/auth/me                    # Current user profile
PUT    /api/auth/me                    # Update user profile
```

### Guest-Facing Endpoints

#### Search & Discovery

```
GET    /api/properties/                    # List all published properties (with pagination)
GET    /api/properties/<id>/               # Property detail page
GET    /api/properties/<id>/photos/        # Property photos
GET    /api/properties/<id>/reviews/       # Property reviews

GET    /api/search/                        # Advanced search
  Query params:
  - destination (city/area)
  - check_in (date)
  - check_out (date)
  - guests (adults, children)
  - rooms
  - price_min, price_max
  - property_type
  - amenities (comma-separated)
  - rating_min
  - sort_by (price_asc, price_desc, rating, newest)
  Returns: [{ property, room_type, available_rooms }]

GET    /api/availability/<room-type-id>/   # Check availability for date range
  Query params:
  - check_in
  - check_out
  Returns: { available: boolean, available_count: int }

GET    /api/destinations/                  # All destinations
GET    /api/destinations/<slug>/           # Destination detail
GET    /api/amenities/                     # All amenities
```

#### Booking

```
POST   /api/bookings/                      # Create booking
  Body: {
    room_type_id,
    check_in_date,
    check_out_date,
    number_of_adults,
    number_of_children,
    number_of_rooms,
    guests: [{first_name, last_name, email, phone, is_primary}],
    special_requests,
    promotion_id (optional),
    coupon_id (optional)
  }
  Returns: { booking_id, booking_reference, total_price }

GET    /api/bookings/<id>/                 # Get booking details
GET    /api/bookings/                      # List guest's bookings

POST   /api/bookings/<id>/cancel/          # Cancel booking
POST   /api/bookings/<id>/reviews/         # Submit review for completed booking

GET    /api/price-calculation/             # Calculate price for dates/guests
  Query params:
  - room_type_id
  - check_in
  - check_out
  - guests
  Returns: { room_price, nights, subtotal, discount, service_fee, tax, total }
```

#### Reviews

```
GET    /api/reviews/                       # List all reviews (with filters)
POST   /api/reviews/                       # Create review (after booking completion)
GET    /api/reviews/<id>/                  # Review detail
PUT    /api/reviews/<id>/                  # Edit own review

POST   /api/reviews/<id>/responses/        # Owner response to review
GET    /api/reviews/<id>/responses/        # Get owner response
```

### Property Owner Endpoints

```
# Property Management
POST   /api/owner/properties/              # Create property
GET    /api/owner/properties/              # List my properties
GET    /api/owner/properties/<id>/         # Property detail
PUT    /api/owner/properties/<id>/         # Update property
DELETE /api/owner/properties/<id>/         # Delete property (if not published)

# Photos
POST   /api/owner/properties/<id>/photos/  # Upload photo
DELETE /api/owner/properties/<id>/photos/<photo-id>/
PUT    /api/owner/properties/<id>/photos/<photo-id>/reorder/

# Room Management
POST   /api/owner/properties/<id>/rooms/   # Create room type
GET    /api/owner/properties/<id>/rooms/   # List room types
PUT    /api/owner/properties/<id>/rooms/<room-id>/
DELETE /api/owner/properties/<id>/rooms/<room-id>/

# Pricing
GET    /api/owner/properties/<id>/pricing/ # Get pricing
PUT    /api/owner/properties/<id>/pricing/ # Update pricing
POST   /api/owner/properties/<id>/seasonal-rates/
DELETE /api/owner/properties/<id>/seasonal-rates/<rate-id>/

# Availability Calendar
GET    /api/owner/properties/<id>/availability/
  Query params: month, year
  Returns: [{ date, status, available_count, booked_count }]

PUT    /api/owner/properties/<id>/availability/<date>/
  Body: { status, available_count }

# Bookings
GET    /api/owner/bookings/                # My bookings
GET    /api/owner/bookings/<id>/           # Booking detail
PUT    /api/owner/bookings/<id>/           # Update status
POST   /api/owner/bookings/<id>/message/   # Send message to guest

# Reviews
GET    /api/owner/reviews/                 # Reviews of my properties
POST   /api/owner/reviews/<id>/respond/    # Respond to review

# Analytics
GET    /api/owner/analytics/dashboard/     # Dashboard stats
GET    /api/owner/analytics/revenue/       # Revenue reports
GET    /api/owner/analytics/occupancy/     # Occupancy reports

# Staff Management
POST   /api/owner/staff/                   # Add staff member
GET    /api/owner/staff/                   # List staff
PUT    /api/owner/staff/<id>/              # Update staff
DELETE /api/owner/staff/<id>/              # Remove staff
```

### Admin Endpoints

```
# User Management
GET    /api/admin/users/                   # List all users (with filters)
GET    /api/admin/users/<id>/              # User detail
PUT    /api/admin/users/<id>/              # Suspend/unsuspend
DELETE /api/admin/users/<id>/              # Delete user

# Property Verification
GET    /api/admin/properties/pending/      # Properties pending review
GET    /api/admin/properties/<id>/         # Property detail
PUT    /api/admin/properties/<id>/approve/ # Approve property
PUT    /api/admin/properties/<id>/reject/  # Reject property
PUT    /api/admin/properties/<id>/suspend/ # Suspend property

# Booking Management
GET    /api/admin/bookings/                # All bookings
GET    /api/admin/bookings/<id>/           # Booking detail
PUT    /api/admin/bookings/<id>/           # Update status
POST   /api/admin/bookings/<id>/refund/    # Issue refund

# Configuration
GET    /api/admin/property-types/          # Property types
POST   /api/admin/property-types/
PUT    /api/admin/property-types/<id>/
DELETE /api/admin/property-types/<id>/

GET    /api/admin/amenities/               # Amenities
POST   /api/admin/amenities/
PUT    /api/admin/amenities/<id>/
DELETE /api/admin/amenities/<id>/

GET    /api/admin/destinations/            # Destinations
POST   /api/admin/destinations/
PUT    /api/admin/destinations/<id>/
DELETE /api/admin/destinations/<id>/

GET    /api/admin/settings/                # System settings
PUT    /api/admin/settings/                # Update settings

# Commission
GET    /api/admin/commissions/             # Commission configuration
PUT    /api/admin/commissions/             # Update commissions

# Reports
GET    /api/admin/reports/daily/           # Daily report
GET    /api/admin/reports/weekly/
GET    /api/admin/reports/monthly/
GET    /api/admin/reports/yearly/
GET    /api/admin/reports/revenue/
GET    /api/admin/reports/commission/

# Audit
GET    /api/admin/audit-logs/              # Audit log viewer
```

### Payment Endpoints

```
POST   /api/payments/initiate/             # Initiate payment
POST   /api/payments/webhook/              # Payment gateway webhook (external)
GET    /api/payments/<booking-id>/status/  # Check payment status
POST   /api/payments/<booking-id>/retry/   # Retry failed payment
```

### API Response Format

All responses follow consistent structure:

```json
{
  "success": true,
  "data": { /* actual data */ },
  "meta": {
    "page": 1,
    "per_page": 20,
    "total": 100,
    "total_pages": 5
  },
  "errors": null
}
```

Error response:

```json
{
  "success": false,
  "data": null,
  "errors": [
    {
      "field": "email",
      "message": "User with this email already exists"
    }
  ]
}
```

### HTTP Status Codes

- `200` — Success
- `201` — Created
- `204` — No Content
- `400` — Bad Request (validation)
- `401` — Unauthorized
- `403` — Forbidden (permission denied)
- `404` — Not Found
- `409` — Conflict (e.g., double booking)
- `422` — Unprocessable Entity (business logic violation)
- `429` — Too Many Requests (rate limiting)
- `500` — Server Error

---

## Frontend Component Architecture

### Directory Structure

```
sl-booking/
├── public/
│   ├── images/
│   ├── icons/
│   └── robots.txt
├── src/
│   ├── app/
│   │   ├── (auth)/
│   │   │   ├── login/
│   │   │   ├── register/
│   │   │   └── password-reset/
│   │   ├── (guest)/
│   │   │   ├── page.tsx               # Homepage
│   │   │   ├── search/page.tsx
│   │   │   ├── properties/[id]/page.tsx
│   │   │   ├── destinations/[slug]/page.tsx
│   │   │   └── bookings/
│   │   ├── (owner)/
│   │   │   ├── dashboard/page.tsx
│   │   │   ├── properties/
│   │   │   ├── calendar/
│   │   │   ├── bookings/
│   │   │   ├── reviews/
│   │   │   └── analytics/
│   │   ├── admin/
│   │   │   ├── dashboard/
│   │   │   ├── users/
│   │   │   ├── properties/
│   │   │   ├── settings/
│   │   │   └── reports/
│   │   └── layout.tsx
│   ├── components/
│   │   ├── common/
│   │   │   ├── Header.tsx
│   │   │   ├── Footer.tsx
│   │   │   ├── Navigation.tsx
│   │   │   ├── Button.tsx
│   │   │   └── Modal.tsx
│   │   ├── search/
│   │   │   ├── SearchBar.tsx
│   │   │   ├── FilterPanel.tsx
│   │   │   └── PropertyCard.tsx
│   │   ├── property/
│   │   │   ├── PhotoGallery.tsx
│   │   │   ├── RoomSelector.tsx
│   │   │   ├── AmenityList.tsx
│   │   │   └── ReviewList.tsx
│   │   ├── booking/
│   │   │   ├── BookingForm.tsx
│   │   │   ├── PriceBreakdown.tsx
│   │   │   ├── GuestDetails.tsx
│   │   │   └── BookingConfirmation.tsx
│   │   ├── owner/
│   │   │   ├── PropertyForm.tsx
│   │   │   ├── PricingPanel.tsx
│   │   │   ├── AvailabilityCalendar.tsx
│   │   │   └── BookingList.tsx
│   │   └── admin/
│   │       ├── PropertyVerification.tsx
│   │       ├── UserManagement.tsx
│   │       └── ReportGenerator.tsx
│   ├── context/
│   │   ├── AuthContext.tsx
│   │   ├── SearchContext.tsx
│   │   └── BookingContext.tsx
│   ├── hooks/
│   │   ├── useAuth.ts
│   │   ├── useBooking.ts
│   │   ├── useAvailability.ts
│   │   └── usePricing.ts
│   ├── lib/
│   │   ├── api.ts                  # API client
│   │   ├── auth.ts                 # Auth utilities
│   │   ├── validators.ts
│   │   └── formatters.ts
│   ├── services/
│   │   ├── propertyService.ts
│   │   ├── bookingService.ts
│   │   ├── paymentService.ts
│   │   └── searchService.ts
│   ├── styles/
│   │   ├── globals.css
│   │   └── theme.ts
│   ├── types/
│   │   ├── index.ts
│   │   ├── api.ts
│   │   ├── domain.ts
│   │   └── forms.ts
│   ├── utils/
│   │   ├── dateHelpers.ts
│   │   ├── priceCalculation.ts
│   │   └── validation.ts
│   └── middleware.ts
├── tailwind.config.ts
├── tsconfig.json
├── next.config.js
└── package.json
```

### Key Components

#### SearchBar Component

```typescript
// Components that handle guest search with:
// - Destination input (autocomplete)
// - Check-in/out date picker
// - Guest selector
// - Submit button
// - Form validation
```

#### PropertyCard Component

```typescript
// Reusable card showing:
// - Property image
// - Name, type, rating
// - Price per night
// - Quick details (beds, amenities)
// - "View Details" CTA
```

#### RoomSelector Component

```typescript
// Shows available rooms with:
// - Room name and photos
// - Occupancy details
// - Bed configuration
// - Amenities
// - Price
// - "Book Now" button
```

#### AvailabilityCalendar Component

```typescript
// Owner view showing:
// - Monthly calendar
// - Booked/available dates
// - Price overlays
// - Blocking interface
// - Seasonal pricing editor
```

#### BookingForm Component

```typescript
// Multi-step checkout:
// 1. Guest details (name, email, phone)
// 2. Special requests
// 3. Price breakdown review
// 4. Payment method selection
// 5. Confirmation
```

### State Management Strategy

**Use Context API + hooks for:**
- Authentication state
- User profile
- Search filters
- Current booking

**Use React Query for:**
- API data fetching with caching
- Automatic refetching
- Background sync
- Optimistic updates

**Example:**

```typescript
// hooks/useAvailability.ts
export function useAvailability(roomTypeId: string, checkIn: Date, checkOut: Date) {
  return useQuery(
    ['availability', roomTypeId, checkIn, checkOut],
    () => API.checkAvailability(roomTypeId, checkIn, checkOut),
    { staleTime: 5 * 60 * 1000 } // 5 minute cache
  );
}
```

---

## Critical: Booking & Availability Logic

### Booking Process Flow

```
1. GUEST INITIATES BOOKING
   ├─ Selects property
   ├─ Selects room type
   ├─ Enters dates (check-in, check-out)
   ├─ Enters guest count
   └─ Proceeds to checkout

2. SYSTEM CALCULATES PRICE
   ├─ Determine pricing for each night
   │  ├─ Check seasonal rates (match date ranges)
   │  ├─ Check day of week (weekend vs weekday)
   │  └─ Fall back to base price
   ├─ Calculate subtotal (price × nights)
   ├─ Apply discounts (promotions, coupons)
   ├─ Calculate service fee (5% of subtotal)
   ├─ Calculate tax (10% of subtotal)
   └─ Return total

3. GUEST REVIEWS BREAKDOWN & PAYS
   ├─ Displays price breakdown
   ├─ Enters guest details
   ├─ Selects payment method
   └─ Initiates payment

4. SYSTEM CREATES BOOKING (CRITICAL TRANSACTION)
   ├─ BEGIN TRANSACTION
   ├─ Lock room availability for date range
   ├─ Check no overlapping confirmed/paid bookings exist
   ├─ If conflict: ROLLBACK and return 409 error
   ├─ Create booking record
   ├─ Create payment record
   ├─ Update availability status
   ├─ COMMIT TRANSACTION
   └─ Generate booking reference

5. SYSTEM PROCESSES PAYMENT
   ├─ Call payment gateway
   ├─ If payment succeeds:
   │  ├─ Update payment status to "paid"
   │  ├─ Update booking status to "confirmed"
   │  └─ Send confirmation email
   └─ If payment fails:
       ├─ Update booking status to "payment_failed"
       └─ Allow retry

6. OWNER RECEIVES NOTIFICATION
   └─ Booking confirmed email

7. GUEST RECEIVES CONFIRMATION
   └─ Confirmation email with booking reference
```

### Double-Booking Prevention Strategy

**The Problem:**
Two guests try to book the same room for overlapping dates simultaneously. Without proper locking, both transactions might succeed, creating a double booking.

**The Solution:**

#### 1. Application-Level Checks (First Defense)

```python
# Django service
def validate_availability(room_type_id, check_in, check_out):
    """
    Check if room is available for date range.
    This is informational only - not the final check.
    """
    booked_dates = Booking.objects.filter(
        room_type_id=room_type_id,
        status__in=['confirmed', 'paid'],  # Only count confirmed bookings
        check_in_date__lt=check_out,
        check_out_date__gt=check_in
    ).values_list('date', flat=True)
    
    available_count = room_type.total_rooms - len(booked_dates)
    return available_count > 0
```

#### 2. Database-Level Locking (Critical Defense)

```python
# Django ORM with row-level locking
from django.db import transaction

@transaction.atomic
def create_booking(room_type_id, check_in, check_out, guest_id, **kwargs):
    """
    Create booking with database-level protection.
    Uses SELECT FOR UPDATE to lock rows during transaction.
    """
    
    # Lock the room type row for the duration of this transaction
    room_type = RoomType.objects.select_for_update().get(id=room_type_id)
    
    # Check availability INSIDE transaction (before lock released)
    overlapping = Booking.objects.filter(
        room_type_id=room_type_id,
        status__in=['confirmed', 'paid'],
        check_in_date__lt=check_out,
        check_out_date__gt=check_in
    ).count()
    
    if overlapping >= room_type.total_rooms:
        raise BookingConflictError("Room not available for selected dates")
    
    # Create booking
    booking = Booking.objects.create(
        room_type_id=room_type_id,
        check_in_date=check_in,
        check_out_date=check_out,
        guest_id=guest_id,
        booking_reference=generate_booking_reference(),
        status='pending',
        **kwargs
    )
    
    # Update availability
    for date in generate_date_range(check_in, check_out):
        availability = Availability.objects.select_for_update().get(
            room_type_id=room_type_id,
            date=date
        )
        availability.booked_count += 1
        availability.save()
    
    return booking
```

#### 3. Unique Constraints

Database-level constraints prevent impossible states:

```sql
-- Constraint: No overlapping bookings for same room
ALTER TABLE bookings ADD CONSTRAINT no_overlapping_bookings
CHECK (
  NOT EXISTS (
    SELECT 1 FROM bookings b2
    WHERE b2.room_type_id = bookings.room_type_id
    AND b2.status IN ('confirmed', 'paid')
    AND b2.id != bookings.id
    AND b2.check_in_date < bookings.check_out_date
    AND b2.check_out_date > bookings.check_in_date
  )
);
```

#### 4. Availability Table (Optimization)

```sql
-- Pre-calculated daily availability (denormalized for performance)
CREATE TABLE availability (
  id UUID PRIMARY KEY,
  room_type_id UUID NOT NULL,
  date DATE NOT NULL,
  booked_count INT DEFAULT 0,
  available_count INT GENERATED ALWAYS AS (room_type.total_rooms - booked_count),
  UNIQUE(room_type_id, date),
  FOREIGN KEY (room_type_id) REFERENCES room_types(id)
);
```

This allows fast lookups without scanning all bookings.

### Concurrent Booking Test Scenario

```python
# Test case: Two guests try to book last room simultaneously
import concurrent.futures
import time

def test_concurrent_bookings():
    room_type = RoomType.objects.create(name="Double Room", total_rooms=1)
    check_in = date(2026, 9, 15)
    check_out = date(2026, 9, 17)
    
    guest1 = User.objects.create(email="guest1@example.com")
    guest2 = User.objects.create(email="guest2@example.com")
    
    results = []
    
    def attempt_booking(guest_id, name):
        try:
            booking = create_booking(
                room_type_id=room_type.id,
                check_in_date=check_in,
                check_out_date=check_out,
                guest_id=guest_id
            )
            results.append({'guest': name, 'success': True, 'booking_id': booking.id})
        except BookingConflictError as e:
            results.append({'guest': name, 'success': False, 'error': str(e)})
    
    # Execute concurrently
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        executor.submit(attempt_booking, guest1.id, 'Guest 1')
        executor.submit(attempt_booking, guest2.id, 'Guest 2')
    
    # Verify only one booking succeeded
    assert sum(1 for r in results if r['success']) == 1
    assert sum(1 for r in results if not r['success']) == 1
    print("✓ Double-booking prevented successfully")
```

### Pricing Calculation Logic

```python
# Service for calculating booking price
class PricingService:
    
    def calculate_price(self, room_type_id, check_in, check_out, 
                       num_adults, num_children):
        """
        Calculate total price for a booking.
        
        Returns: {
            room_price_per_night: float,
            nights: int,
            subtotal: float,
            discount: float,
            service_fee: float,
            tax: float,
            total: float
        }
        """
        
        # 1. Get pricing config
        pricing = Pricing.objects.get(room_type_id=room_type_id)
        
        # 2. Calculate nights
        delta = check_out - check_in
        nights = delta.days
        
        # 3. Determine nightly rate (per-day calculation)
        nightly_rates = []
        for i in range(nights):
            current_date = check_in + timedelta(days=i)
            rate = self._get_rate_for_date(room_type_id, current_date)
            nightly_rates.append(rate)
        
        # 4. Calculate subtotal
        subtotal = sum(nightly_rates)
        
        # 5. Add guest fees
        guest_fee = 0
        if num_adults > pricing.included_adults:
            extra_adults = num_adults - pricing.included_adults
            guest_fee += extra_adults * pricing.extra_guest_fee * nights
        
        if num_children > 0:
            guest_fee += num_children * pricing.child_fee * nights
        
        subtotal += guest_fee
        
        # 6. Apply discounts (promotions, coupons)
        discount = 0
        # (discount calculation logic here)
        
        # 7. Calculate service fee (5% of subtotal)
        service_fee = subtotal * (pricing.service_fee_percent / 100)
        
        # 8. Calculate tax (10% of subtotal + service fee)
        taxable = subtotal + service_fee
        tax = taxable * (pricing.tax_percent / 100)
        
        # 9. Total
        total = subtotal + service_fee + tax - discount
        
        return {
            'room_price_per_night': nightly_rates[0],  # First night for display
            'nights': nights,
            'subtotal': subtotal,
            'discount': discount,
            'service_fee': service_fee,
            'tax': tax,
            'total': total,
            'nightly_breakdown': nightly_rates
        }
    
    def _get_rate_for_date(self, room_type_id, date):
        """
        Get price for specific date.
        Priority: Seasonal Rate > Weekend Rate > Base Price
        """
        
        # Check seasonal rates first
        seasonal = SeasonalRate.objects.filter(
            room_type_id=room_type_id,
            start_date__lte=date,
            end_date__gte=date
        ).first()
        
        if seasonal:
            return seasonal.price_per_night
        
        # Check weekend
        pricing = Pricing.objects.get(room_type_id=room_type_id)
        if date.weekday() >= 4:  # Friday (4) or Saturday (5)
            if pricing.weekend_price:
                return pricing.weekend_price
        
        # Fall back to base price
        return pricing.base_price
```

### Booking Cancellation & Refund Logic

```python
# Cancellation with refund rules
class BookingService:
    
    def cancel_booking(self, booking_id, reason='guest_request'):
        """
        Cancel booking and calculate refund based on cancellation policy.
        """
        booking = Booking.objects.select_for_update().get(id=booking_id)
        
        if booking.status == 'cancelled':
            raise InvalidStateError("Booking already cancelled")
        
        # Determine refund policy
        property_policy = booking.property.cancellation_policy
        days_until_checkin = (booking.check_in_date - date.today()).days
        
        if days_until_checkin >= property_policy.full_refund_days:
            refund_percent = 100
        elif days_until_checkin >= property_policy.partial_refund_days:
            refund_percent = property_policy.partial_refund_percent
        else:
            refund_percent = 0  # Non-refundable
        
        # Calculate refund
        refund_amount = booking.total_price * (refund_percent / 100)
        
        # Create refund record
        if refund_amount > 0:
            refund = Refund.objects.create(
                booking_id=booking_id,
                amount=refund_amount,
                reason=reason,
                status='pending'
            )
            # Process refund (call payment gateway)
            process_refund_payment(refund)
        
        # Update booking status
        booking.status = 'cancelled'
        booking.save()
        
        # Release availability
        for date in self._date_range(booking.check_in_date, booking.check_out_date):
            availability = Availability.objects.get(
                room_type_id=booking.room_type_id,
                date=date
            )
            availability.booked_count -= 1
            availability.save()
        
        # Notify guest and owner
        send_cancellation_notifications(booking, refund_amount, refund_percent)
```

---

## Payment Architecture

### Payment Abstraction Layer

Design goal: Support multiple payment gateways without changing application code.

```python
# Abstract payment processor
from abc import ABC, abstractmethod

class PaymentProcessor(ABC):
    """Base class for all payment processors"""
    
    @abstractmethod
    def initiate_payment(self, booking_id, amount, currency):
        """Initiate payment and return payment URL"""
        pass
    
    @abstractmethod
    def verify_payment(self, transaction_reference):
        """Verify if payment was successful"""
        pass
    
    @abstractmethod
    def refund_payment(self, transaction_reference, amount):
        """Refund a payment"""
        pass
    
    @abstractmethod
    def process_webhook(self, raw_data):
        """Process webhook from payment gateway"""
        pass


# Concrete implementations
class StripePaymentProcessor(PaymentProcessor):
    def __init__(self, api_key):
        self.client = stripe.Client(api_key)
    
    def initiate_payment(self, booking_id, amount, currency='LKR'):
        session = self.client.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': currency,
                    'unit_amount': int(amount * 100),
                    'product_data': {
                        'name': f'SL Booking - Reservation {booking_id[:8]}'
                    }
                },
                'quantity': 1
            }],
            mode='payment',
            success_url='https://slbooking.hotel.lk/booking/success?session_id={CHECKOUT_SESSION_ID}',
            cancel_url='https://slbooking.hotel.lk/booking/cancel'
        )
        return session.url

class PayAtPropertyPaymentProcessor(PaymentProcessor):
    """No payment processing - guest pays at property"""
    
    def initiate_payment(self, booking_id, amount, currency='LKR'):
        return None  # No payment URL
    
    def verify_payment(self, transaction_reference):
        return True  # Always verified (owner confirms)

# Payment service factory
class PaymentService:
    PROCESSORS = {
        'stripe': StripePaymentProcessor,
        'paypal': PayPalPaymentProcessor,  # Future
        'pay_at_property': PayAtPropertyPaymentProcessor,
        'bank_transfer': BankTransferPaymentProcessor,  # Future
    }
    
    @staticmethod
    def get_processor(method_name):
        processor_class = PaymentService.PROCESSORS.get(method_name)
        if not processor_class:
            raise ValueError(f"Unknown payment method: {method_name}")
        
        return processor_class(
            api_key=settings.get(f'{method_name.upper()}_API_KEY')
        )
    
    @staticmethod
    def initiate_payment(booking, payment_method):
        processor = PaymentService.get_processor(payment_method)
        payment_url = processor.initiate_payment(
            booking.id,
            booking.total_price
        )
        
        payment = Payment.objects.create(
            booking=booking,
            amount=booking.total_price,
            payment_method=payment_method,
            status='pending'
        )
        
        return {
            'payment_id': payment.id,
            'payment_url': payment_url,
            'payment_method': payment_method
        }
```

### Payment Webhook Handling

```python
# Handle payment gateway webhooks
from django.views.decorators.http import csrf_exempt
import hashlib
import hmac

@csrf_exempt
@require_http_methods(['POST'])
def payment_webhook(request):
    """
    Universal webhook endpoint for all payment gateways.
    Each gateway posts here with verified signatures.
    """
    
    # Verify webhook authenticity
    signature = request.META.get('HTTP_X_SIGNATURE')
    if not verify_webhook_signature(request.body, signature):
        return JsonResponse({'status': 'unauthorized'}, status=401)
    
    data = json.loads(request.body)
    gateway_name = data.get('gateway')
    
    processor = PaymentService.get_processor(gateway_name)
    result = processor.process_webhook(data)
    
    if result['status'] == 'success':
        transaction_ref = result['transaction_reference']
        payment = Payment.objects.get(transaction_reference=transaction_ref)
        booking = payment.booking
        
        # Update payment
        payment.status = 'paid'
        payment.gateway_response = data
        payment.save()
        
        # Update booking
        booking.status = 'confirmed'
        booking.payment_status = 'paid'
        booking.save()
        
        # Send confirmation notifications
        send_booking_confirmation_email(booking)
        send_owner_notification(booking)
        
        return JsonResponse({'status': 'processed'})
    else:
        payment = Payment.objects.get(
            transaction_reference=result['transaction_reference']
        )
        payment.status = 'failed'
        payment.error_message = result.get('error_message')
        payment.save()
        
        return JsonResponse({'status': 'processed'})
```

---

## Authentication & Authorization

### JWT Token Strategy

```python
# settings.py
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': settings.SECRET_KEY,
}

# Usage
from rest_framework_simplejwt.tokens import RefreshToken

def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }
```

### Permission Classes

```python
from rest_framework.permissions import BasePermission

class IsGuest(BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.roles.filter(name='guest').exists()

class IsPropertyOwner(BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.roles.filter(name='property_owner').exists()

class IsPropertyStaff(BasePermission):
    def has_object_permission(self, request, view, obj):
        staff = Staff.objects.filter(user=request.user, property=obj).exists()
        return staff or obj.owner == request.user

class IsSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_staff

class IsOwnerOfProperty(BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.owner == request.user
```

### Usage in Views

```python
from rest_framework.viewsets import ViewSet
from rest_framework.decorators import action
from rest_framework.response import Response

class BookingViewSet(ViewSet):
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def my_bookings(self, request):
        # Only see own bookings
        bookings = Booking.objects.filter(guest=request.user)
        serializer = BookingSerializer(bookings, many=True)
        return Response(serializer.data)

class PropertyViewSet(ViewSet):
    permission_classes = [IsAuthenticated, IsOwnerOfProperty]
    
    def update(self, request, pk=None):
        # Only owner can update property
        property = Property.objects.get(id=pk)
        self.check_object_permissions(request, property)
        
        serializer = PropertySerializer(property, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
```

---

## Notification System

### Email Notification Architecture

```python
# Notification service
from django.template.loader import render_to_string
from django.core.mail import send_html_email

class NotificationService:
    
    TEMPLATES = {
        'booking_confirmation': 'emails/booking_confirmation.html',
        'booking_cancellation': 'emails/booking_cancellation.html',
        'payment_received': 'emails/payment_received.html',
        'review_request': 'emails/review_request.html',
        'password_reset': 'emails/password_reset.html',
    }
    
    @staticmethod
    def send_booking_confirmation(booking):
        context = {
            'booking_reference': booking.booking_reference,
            'property_name': booking.property.name,
            'check_in': booking.check_in_date,
            'check_out': booking.check_out_date,
            'total_price': booking.total_price,
            'guest_name': booking.booking_guests.first().first_name,
        }
        
        template = NotificationService.TEMPLATES['booking_confirmation']
        html_content = render_to_string(template, context)
        
        notification = Notification.objects.create(
            recipient=booking.guest,
            notification_type='booking_confirmation',
            channel='email',
            status='pending'
        )
        
        # Send asynchronously via Celery
        send_email_task.delay(
            to_email=booking.guest.email,
            subject='Booking Confirmed',
            html_content=html_content,
            notification_id=notification.id
        )
        
        return notification
    
    @staticmethod
    def send_owner_notification(booking):
        # Notify property owner of new booking
        pass
    
    @staticmethod
    def send_review_request(booking):
        # Send review request email 1 day after checkout
        pass
```

### Async Email Task (Celery)

```python
# tasks.py
from celery import shared_task
from django.core.mail import send_mail

@shared_task
def send_email_task(to_email, subject, html_content, notification_id):
    """Send email and update notification status"""
    
    try:
        send_html_email(
            subject=subject,
            message=html_content,
            from_email='noreply@slbooking.hotel.lk',
            recipient_list=[to_email],
        )
        
        notification = Notification.objects.get(id=notification_id)
        notification.status = 'sent'
        notification.save()
        
        return f"Email sent to {to_email}"
    
    except Exception as e:
        notification = Notification.objects.get(id=notification_id)
        notification.status = 'failed'
        notification.save()
        
        # Retry after 5 minutes
        raise send_email_task.retry(exc=e, countdown=300)
```

### Push Notification Support (Future)

```python
class NotificationService:
    
    CHANNELS = {
        'email': EmailChannel,
        'sms': SMSChannel,  # Future
        'push': PushNotificationChannel,  # Future
        'whatsapp': WhatsAppChannel,  # Future
    }
    
    @staticmethod
    def send_notification(user, notification_type, channel='email', **context):
        channel_handler = NotificationService.CHANNELS[channel]
        channel_handler.send(user, notification_type, **context)
```

---

## Performance & Scalability

### Database Optimization

1. **Indexes Strategy**
   - Foreign keys: always indexed
   - Search fields: `city`, `property_type`, `status`
   - Date ranges: `check_in_date`, `check_out_date`
   - Frequently filtered: `is_active`, `is_published`

2. **Query Optimization**
   - Use `select_related()` for foreign keys
   - Use `prefetch_related()` for reverse relationships
   - Avoid N+1 queries

Example:

```python
# Bad: N+1 query
bookings = Booking.objects.all()
for booking in bookings:
    owner_name = booking.property.owner.name  # Query per booking!

# Good: Optimized
bookings = Booking.objects.select_related('property__owner')
for booking in bookings:
    owner_name = booking.property.owner.name  # No extra queries
```

3. **Pagination**
   - Use cursor-based pagination for large datasets
   - Default page size: 20 results
   - Max page size: 100 results

4. **Caching Strategy**
   - Cache property listing: 1 hour
   - Cache search results: 30 minutes
   - Cache destination data: 24 hours
   - Cache amenities: 24 hours

```python
from django.core.cache import cache

@cache_result(timeout=3600)  # 1 hour
def get_published_properties():
    return Property.objects.filter(status='published').order_by('-created_at')
```

5. **Full-Text Search**
   - Use PostgreSQL FULLTEXT for property descriptions
   - Indexed on `properties.name` and `properties.description`

### API Performance

1. **Response Compression** — Nginx gzip
2. **CDN for Images** — Cloudinary
3. **API Rate Limiting**
   ```python
   REST_FRAMEWORK = {
       'DEFAULT_THROTTLE_CLASSES': [
           'rest_framework.throttling.AnonRateThrottle',
           'rest_framework.throttling.UserRateThrottle'
       ],
       'DEFAULT_THROTTLE_RATES': {
           'anon': '100/hour',
           'user': '1000/hour'
       }
   }
   ```

4. **Async Celery Tasks**
   - Email sending
   - Report generation
   - Webhook processing
   - Photo processing

### Scalability Roadmap

**Phase 1:** Single server (sufficient for MVP)

**Phase 2:** Horizontal scaling
- Separate database server
- Redis cache
- Celery workers on separate machines
- CDN for static files

**Phase 3:** Database scaling
- Read replicas
- Partition booking table by date range
- Archive old data

---

## Technical Decisions & Trade-offs

### Decision 1: PostgreSQL over NoSQL

**Decision:** Use PostgreSQL (relational) not MongoDB (NoSQL)

**Rationale:**
- Booking data is highly relational (bookings → guests → property → rooms)
- ACID transactions essential for double-booking prevention
- Structured schema matches our domain model
- Joins are frequent and complex

**Trade-off:**
- NoSQL is more flexible for unstructured data
- But hotels/rooms/bookings are inherently structured

### Decision 2: Django ORM vs Raw SQL

**Decision:** Use Django ORM for most queries, raw SQL only when necessary

**Rationale:**
- ORM is safer (prevents SQL injection)
- Migrations system
- Query optimization tools
- More readable code

**Trade-off:**
- Sometimes less performant than raw SQL
- Complex queries harder to optimize
- Solved with raw SQL for critical paths

### Decision 3: JWT Tokens vs Sessions

**Decision:** JWT tokens for stateless API

**Rationale:**
- Stateless scaling (no session storage)
- Works with mobile apps
- Single-page app friendly
- Better for microservices (future)

**Trade-off:**
- Can't revoke instantly (use blacklist for critical cases)
- Slightly larger payload
- Must manage refresh tokens

### Decision 4: Cloudinary for Images vs Local Storage

**Decision:** Use Cloudinary

**Rationale:**
- Automatic image optimization
- CDN delivery (faster worldwide)
- Responsive images
- No server storage costs
- Automatic backup

**Trade-off:**
- External dependency
- Monthly costs at scale
- Privacy concerns (data in third-party)

**Mitigation:** Negotiate data location (EU servers if needed)

### Decision 5: Celery for Async Tasks vs Synchronous

**Decision:** Celery for async tasks

**Rationale:**
- Non-blocking email sending
- User gets response immediately
- Can retry failed tasks
- Distribute load over time

**Trade-off:**
- Added complexity
- Redis dependency
- Harder to debug

**Mitigation:** Use Django-Q as simpler alternative if needed

### Decision 6: SEO via Server-Side Rendering vs Static Generation

**Decision:** Use Next.js SSR for dynamic pages, SSG for static content

**Rationale:**
- Property pages change frequently (need SSR)
- Static pages (Terms, FAQ) can be generated
- Better SEO than SPA
- Better performance with ISR (Incremental Static Regeneration)

---

## Security Architecture

### Authentication Security

1. **Password Storage**
   - Use Django's PBKDF2 hasher (100,000 iterations)
   - Never log passwords
   - Implement password strength requirements

2. **JWT Token Security**
   - Use HS256 with strong SECRET_KEY
   - Implement token blacklist for logout
   - Short expiry (1 hour)
   - Secure refresh tokens (httpOnly cookies)

3. **Multi-Factor Authentication** (Phase 2)
   - Email verification
   - SMS OTP (optional)

### Authorization Security

1. **Role-Based Access Control**
   - Verify permissions on every endpoint
   - Check object ownership for updates
   - Staff members limited by property

2. **API Key Authentication** (for webhooks)
   - Payment gateway webhooks verified with signatures
   - OTA integrations use secure API keys

### Data Security

1. **Input Validation**
   - Validate all form inputs
   - Sanitize user-generated content
   - Use Django's validators

2. **SQL Injection Prevention**
   - Use ORM (parameterized queries)
   - Never concatenate SQL strings
   - Escape raw SQL parameters

3. **XSS Prevention**
   - React auto-escapes by default
   - Use `DOMPurify` for HTML content
   - Content Security Policy headers

4. **CSRF Protection**
   - Django CSRF middleware
   - Include CSRF token in forms
   - SameSite cookies

5. **Secure File Uploads**
   - Validate file type and size
   - Store in Cloudinary (not local)
   - Scan for malware

### Transport Security

1. **HTTPS/TLS**
   - All traffic encrypted
   - Force HTTPS redirect
   - Use strong ciphers

2. **Secure Cookies**
   - HttpOnly flag (no JavaScript access)
   - Secure flag (HTTPS only)
   - SameSite=Strict

3. **CORS Configuration**
   - Whitelist specific domains
   - Only allow necessary methods
   - No credentials in preflight

### PCI Compliance

1. **Never Store Card Data**
   - Use Stripe/payment gateway for card handling
   - Tokenize card for future charges
   - Only store transaction reference

2. **Audit Logging**
   - Log all payment operations
   - Track data access
   - Compliance reports

### Environment Security

1. **Secrets Management**
   - Use environment variables
   - Never commit secrets to git
   - Use `.env.local` for local development
   - Use managed secrets in production (Doppler, HashiCorp Vault)

2. **Debug Settings**
   - DEBUG=False in production
   - Disable error details from API
   - Log errors to monitoring service

---

## Development Roadmap

### Detailed Phase Breakdown

#### PHASE 1: Foundation (Weeks 1-2)

**Goal:** Project setup, authentication, core models, basic admin

Deliverables:
1. ✅ Initialize Next.js + Django projects
2. ✅ PostgreSQL schema created
3. ✅ Authentication system (registration, login, JWT)
4. ✅ User roles and permissions system
5. ✅ Django admin interface
6. ✅ Basic role-based API endpoints
7. ✅ Frontend: Login/Register pages
8. ✅ Frontend: Basic navigation

**Database:** Users, Roles, Permissions

**API:** Auth endpoints only

**Testing:** Authentication unit tests

#### PHASE 2: Property Management (Weeks 3-4)

**Goal:** Owners can create properties, upload photos, create rooms, set pricing

Deliverables:
1. ✅ Property creation form (backend + frontend)
2. ✅ Property photo upload (Cloudinary integration)
3. ✅ Room type creation
4. ✅ Pricing configuration
5. ✅ Property type and amenity management
6. ✅ Owner dashboard (basic)
7. ✅ Property status workflow (pending → published)

**Database:** Properties, Rooms, Photos, Pricing, Amenities

**API:** Property CRUD, Photo upload, Room management

**Testing:** Property creation, photo upload

#### PHASE 3: Search & Discovery (Weeks 5-6)

**Goal:** Guests can search properties, view details, filter results

Deliverables:
1. ✅ Homepage with search bar
2. ✅ Search API (by destination, dates, guests)
3. ✅ Filter implementation (price, property type, amenities, rating)
4. ✅ Sorting options
5. ✅ Property detail page
6. ✅ Destination pages
7. ✅ Photo gallery component
8. ✅ Reviews display

**Database:** Destinations, Search indexes

**API:** Search endpoint, Filter endpoints

**Testing:** Search functionality, filter combinations

#### PHASE 4: Booking Engine (Weeks 7-9)

**Goal:** Complete booking flow with double-booking protection

Deliverables:
1. ✅ Availability calendar
2. ✅ Availability API
3. ✅ Booking creation with transaction safety
4. ✅ Double-booking prevention (database locking)
5. ✅ Price calculation service
6. ✅ Booking checkout flow (multi-step)
7. ✅ Booking confirmation page
8. ✅ Booking reference generation
9. ✅ Owner booking management
10. ✅ Concurrent booking tests

**Database:** Bookings, BookingGuests, Availability

**API:** Booking CRUD, Availability check, Price calculation

**Testing:** Double-booking tests, Concurrent scenarios, Price calculations

#### PHASE 5: Payments & Notifications (Weeks 10-11)

**Goal:** Payment processing and notification system

Deliverables:
1. ✅ Payment abstraction layer
2. ✅ Stripe integration (first gateway)
3. ✅ "Pay at Property" option
4. ✅ Payment webhook handling
5. ✅ Email template system
6. ✅ Notification service
7. ✅ Email sending (Celery)
8. ✅ Booking confirmation emails
9. ✅ Owner notifications
10. ✅ Review request emails

**Database:** Payments, Refunds, Notifications, EmailTemplates

**API:** Payment initiation, Webhook endpoint

**Testing:** Payment flow, Webhook handling, Email notifications

#### PHASE 6: Reviews & Admin (Weeks 12-13)

**Goal:** Guest reviews, admin dashboards, reporting

Deliverables:
1. ✅ Review submission form (post-stay)
2. ✅ Review moderation
3. ✅ Owner review responses
4. ✅ Review ratings (overall, cleanliness, location, etc.)
5. ✅ Guest admin dashboard
6. ✅ Super admin dashboard
7. ✅ Property verification workflow
8. ✅ Admin property approval/rejection
9. ✅ Booking management UI
10. ✅ Revenue reports
11. ✅ Commission configuration
12. ✅ Occupancy reports

**Database:** Reviews, AuditLogs, SystemSettings

**API:** Review endpoints, Admin endpoints, Report endpoints

**Testing:** Review workflow, Admin permissions, Report generation

#### PHASE 7: Production & Polish (Weeks 14-16)

**Goal:** Security, performance, testing, deployment

Deliverables:
1. ✅ Security audit
2. ✅ HTTPS/SSL setup
3. ✅ Security headers (CSP, HSTS, etc.)
4. ✅ Rate limiting
5. ✅ Input validation throughout
6. ✅ API documentation (OpenAPI/Swagger)
7. ✅ Performance optimization
8. ✅ Database indexing review
9. ✅ Caching strategy implementation
10. ✅ Mobile responsive testing
11. ✅ Browser compatibility
12. ✅ Automated test suite (unit, integration)
13. ✅ Deployment documentation
14. ✅ Backup strategy
15. ✅ Monitoring setup
16. ✅ SEO optimization
17. ✅ Sitemap generation
18. ✅ robots.txt

**Testing:** Full test suite, Security testing, Performance testing

**Deployment:** Production environment, CI/CD pipeline

### Timeline Summary

```
Phase 1: Foundation        └─ Weeks 1-2   (Core setup)
Phase 2: Properties        └─ Weeks 3-4   (Ownership)
Phase 3: Search            └─ Weeks 5-6   (Discovery)
Phase 4: Bookings          └─ Weeks 7-9   (Transactions)
Phase 5: Payments          └─ Weeks 10-11 (Revenue)
Phase 6: Reviews/Admin     └─ Weeks 12-13 (Operations)
Phase 7: Production        └─ Weeks 14-16 (Launch)

Total: ~16 weeks (4 months)
```

---

## Deployment Architecture

### Production Environment Setup

```
┌─────────────────────────────────────┐
│  Domain: slbooking.hotel.lk         │
│  DNS: Route53 / Cloudflare          │
└────────────────┬────────────────────┘
                 │
         ┌───────▼────────┐
         │ Cloudflare CDN │
         └────────┬───────┘
                  │
        ┌─────────▼─────────┐
        │  Load Balancer    │
        │  (Nginx)          │
        └────┬────────┬─────┘
             │        │
     ┌───────▼──┐  ┌──▼────────┐
     │ Django   │  │ Django    │
     │ App #1   │  │ App #2    │
     │ :8001    │  │ :8002     │
     └──┬───────┘  └──┬────────┘
        │             │
        └─────┬───────┘
              │
    ┌─────────▼──────────┐
    │  PostgreSQL Master │
    │  Primary Database  │
    └────────────────────┘
              │
    ┌─────────▼──────────┐
    │ PostgreSQL Replica │
    │ Read-only copies   │
    └────────────────────┘

External Services:
  ├─ Cloudinary (Images)
  ├─ Stripe (Payments)
  ├─ SendGrid (Email)
  ├─ Redis (Cache/Sessions)
  └─ Sentry (Error Tracking)
```

### Server Requirements

**Django Application Server**
- OS: Ubuntu 22.04 LTS
- Python 3.11+
- 2GB RAM minimum
- Gunicorn (4 workers)

**Database Server**
- PostgreSQL 14+
- 4GB RAM minimum
- SSD storage
- Automated backups (daily)

**Cache/Session Server**
- Redis 7+
- 1GB RAM

### Deployment Steps

1. **Server Setup**
   ```bash
   # Ubuntu server with firewall
   ufw allow 22/tcp
   ufw allow 80/tcp
   ufw allow 443/tcp
   ufw enable
   ```

2. **Database Setup**
   ```bash
   # PostgreSQL installation and initialization
   psql createdb slbooking_prod
   psql < db_backup.sql  # Load schema
   ```

3. **Django Deployment**
   ```bash
   git clone repository
   pip install -r requirements.txt
   python manage.py migrate --settings=config.settings.production
   python manage.py collectstatic --noinput
   gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 4
   ```

4. **Nginx Configuration**
   - Reverse proxy to Gunicorn
   - SSL/TLS termination
   - Static file serving
   - Gzip compression

5. **SSL Certificate**
   - Let's Encrypt (free)
   - Auto-renewal (certbot)

6. **Monitoring**
   - Sentry (error tracking)
   - New Relic / DataDog (APM)
   - CloudWatch / Prometheus (metrics)

---

## Conclusion

This architecture provides:

✅ **Scalability** — Designed to grow from 1000 to 1M bookings  
✅ **Reliability** — Transaction safety, backup strategy, monitoring  
✅ **Security** — Authentication, authorization, data protection  
✅ **Maintainability** — Clean separation of concerns, modular design  
✅ **Extensibility** — Payment gateway abstraction, notification channels  
✅ **Performance** — Caching, indexing, optimized queries  

The 7-phase roadmap is realistic and achievable within 4 months with a small team. Each phase builds on the previous one, and critical features (double-booking protection, pricing calculation) are prioritized in Phase 4.

Ready to begin Phase 1 implementation!
