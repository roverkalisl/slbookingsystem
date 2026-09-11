# SL Booking Frontend - Complete Setup Guide

## Overview

Modern Next.js 14+ frontend for SL Booking accommodation marketplace with TypeScript, Tailwind CSS, and Zustand state management.

**Tech Stack:**
- Next.js 14+ (React 18)
- TypeScript
- Tailwind CSS
- Zustand (state management)
- Axios (API client)
- React Hook Form (form handling)

---

## Project Structure

```
frontend/
├── src/
│   ├── app/                 # Next.js app directory
│   │   ├── page.tsx        # Home page
│   │   ├── layout.tsx      # Root layout
│   │   ├── globals.css     # Global styles
│   │   ├── login/          # Login page
│   │   ├── register/       # Registration page
│   │   ├── search/         # Search results page
│   │   ├── property/       # Property details
│   │   └── bookings/       # Bookings management
│   ├── components/          # Reusable components
│   │   ├── Navbar.tsx      # Navigation bar
│   │   ├── PropertyCard.tsx # Property listing card
│   │   ├── SearchBar.tsx   # Search form
│   │   └── BookingForm.tsx # Booking form
│   ├── lib/                 # Utilities
│   │   └── api.ts          # API client
│   ├── stores/              # Zustand stores
│   │   ├── auth.ts         # Auth state
│   │   └── search.ts       # Search state
│   └── types/               # TypeScript types
│       └── index.ts        # All types
├── public/                  # Static files
├── package.json
├── tsconfig.json
├── tailwind.config.ts
├── postcss.config.js
└── next.config.js
```

---

## Setup Instructions

### 1. Install Dependencies

```bash
cd frontend
npm install
```

### 2. Environment Configuration

Create `.env.local`:

```env
# API Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000/api

# Optional: Stripe Public Key (for payments)
NEXT_PUBLIC_STRIPE_PUBLIC_KEY=pk_test_your_key_here
```

### 3. Development Server

```bash
npm run dev
```

Server runs at `http://localhost:3000`

### 4. Build for Production

```bash
npm run build
npm start
```

---

## Key Components & Pages

### Pages

#### Home (`/`)
- Hero section with search bar
- Featured properties grid
- Why choose SL Booking section

#### Search (`/search`)
- Advanced property search with filters
- Results grid with pagination
- Sort and filter options

#### Property Details (`/property/[id]`)
- Full property information
- Photo gallery
- Room types and pricing
- Reviews section
- Booking form

#### Login (`/login`)
- Email/password authentication
- Redirect to bookings if logged in
- Registration link

#### Register (`/register`)
- New user registration
- Form validation
- Auto-login after registration

#### Bookings (`/bookings`)
- My bookings list
- Booking status tracking
- Cancel booking option
- View booking details

### Components

#### Navbar
- Logo and navigation links
- User menu (when authenticated)
- Mobile responsive hamburger menu

#### PropertyCard
- Property image
- Name, location, rating
- Price range display
- Link to details

#### SearchBar
- Destination input
- Check-in/check-out dates
- Number of guests
- Search submission

#### BookingForm
- Room type selection
- Date picker (check-in/check-out)
- Guest count
- Price calculation
- Payment method selection

---

## Authentication Flow

### Login/Registration
1. User submits email and password
2. Backend validates and returns JWT access token
3. Token stored in localStorage
4. User context updated via Zustand store
5. Redirect to home or bookings page

### Protected Routes
```typescript
// Check authentication before rendering
if (!isAuthenticated) {
  redirect('/login')
}
```

---

## API Integration

### Axios Instance
Located in `src/lib/api.ts`:

```typescript
// Automatically adds Bearer token to all requests
// Handles 401 errors (unauthorized)
// Provides typed responses

// Usage:
const properties = await api.getProperties(filters)
const booking = await api.createBooking(data)
```

### API Methods

```typescript
// Auth
await api.login(email, password)
await api.register(data)
await api.logout()
await api.getCurrentUser()

// Properties
await api.getProperties(filters)
await api.getProperty(id)
await api.searchProperties(destination, checkIn, checkOut, guests)
await api.getFeaturedProperties()

// Bookings
await api.createBooking(data)
await api.getBookings()
await api.getBooking(id)
await api.cancelBooking(id)
await api.calculatePrice(data)
await api.checkAvailability(roomTypeId, checkIn, checkOut)

// Payments
await api.initiatePayment(data)
await api.confirmPayment(id)
await api.processRefund(id, amount, reason)

// Notifications
await api.getNotifications()
await api.markNotificationAsRead(id)
```

---

## State Management (Zustand)

### Auth Store
```typescript
import { useAuth } from '@/stores/auth'

export function MyComponent() {
  const { user, isAuthenticated, login, logout } = useAuth()
  
  return (
    <>
      {isAuthenticated && <p>Welcome, {user?.first_name}</p>}
    </>
  )
}
```

### Search Store (Optional)
```typescript
const { filters, setFilters, results } = useSearch()
```

---

## Styling with Tailwind

### Global Utilities
Defined in `globals.css`:

```css
.btn-primary     /* Primary button style */
.btn-secondary   /* Secondary button style */
.btn-danger      /* Danger/delete button style */
.card            /* Card container */
.badge           /* Badge element */
.container       /* Max-width container */
```

### Color Palette
```css
primary:   #2563eb (blue-600)
secondary: #1e40af (blue-800)
accent:    #dc2626 (red-600)
success:   #16a34a (green-600)
warning:   #ea580c (orange-600)
error:     #dc2626 (red-600)
```

---

## Form Handling

Using React Hook Form for type-safe forms:

```typescript
import { useForm } from 'react-hook-form'

export function LoginForm() {
  const { register, handleSubmit, formState: { errors } } = useForm()
  
  const onSubmit = async (data) => {
    await api.login(data.email, data.password)
  }
  
  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <input {...register('email', { required: true })} />
      {errors.email && <span>Email required</span>}
    </form>
  )
}
```

---

## Type Safety

All API responses are typed in `src/types/index.ts`:

```typescript
interface Property {
  id: string
  name: string
  price_range_min: number
  // ... all fields
}

interface Booking {
  id: string
  booking_reference: string
  // ... all fields
}
```

TypeScript will catch type mismatches at compile time!

---

## Common Tasks

### Add a New Page

1. Create `src/app/[name]/page.tsx`
2. Export default React component
3. Link from Navbar or other pages

### Add a New Component

1. Create `src/components/[Name].tsx`
2. Export as function component
3. Import and use in pages

### Fetch Data

```typescript
'use client'

import { useEffect, useState } from 'react'
import { api } from '@/lib/api'

export default function MyPage() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function load() {
      try {
        const result = await api.getProperties()
        setData(result)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  if (loading) return <div>Loading...</div>
  return <div>{/* render data */}</div>
}
```

### Use Authentication

```typescript
'use client'

import { useAuth } from '@/stores/auth'
import { useEffect } from 'react'
import { useRouter } from 'next/navigation'

export default function ProtectedPage() {
  const router = useRouter()
  const { isAuthenticated, user } = useAuth()

  useEffect(() => {
    if (!isAuthenticated) {
      router.push('/login')
    }
  }, [isAuthenticated, router])

  if (!isAuthenticated) return null

  return <div>Welcome, {user?.first_name}</div>
}
```

---

## Features Implemented

✅ **Authentication**
- Login/Registration
- JWT token management
- Protected routes
- User profile

✅ **Property Search**
- Advanced filters
- Sorting options
- Featured properties
- Property details

✅ **Booking Management**
- Create bookings
- View booking history
- Cancel bookings
- Price calculation

✅ **Responsive Design**
- Mobile-first approach
- Tailwind breakpoints
- Touch-friendly navigation

✅ **Type Safety**
- Full TypeScript coverage
- Typed API responses
- Zustand store typing

---

## Performance Optimizations

- Image optimization (Next.js Image component)
- Code splitting (automatic with Next.js)
- Lazy loading components
- Memoization of expensive components
- Efficient state management

---

## SEO

- Meta tags in layout
- Structured data ready
- Open Graph support
- Mobile-friendly

---

## Testing

Add testing framework (optional):

```bash
npm install --save-dev @testing-library/react @testing-library/jest-dom
```

---

## Deployment

### Vercel (Recommended)
```bash
npm install -g vercel
vercel
```

### Docker
```dockerfile
FROM node:20-alpine
WORKDIR /app
COPY . .
RUN npm install
RUN npm run build
CMD ["npm", "start"]
```

### Environment Variables (Production)
```env
NEXT_PUBLIC_API_URL=https://api.slbooking.hotel.lk
NEXT_PUBLIC_STRIPE_PUBLIC_KEY=pk_live_...
```

---

## Troubleshooting

### Port 3000 in use?
```bash
npm run dev -- -p 3001
```

### Clear Next.js cache
```bash
rm -rf .next
npm run dev
```

### API connection issues?
- Check `NEXT_PUBLIC_API_URL` in `.env.local`
- Ensure backend is running (http://localhost:8000)
- Check browser console for CORS errors

### TypeScript errors?
```bash
npm run type-check
```

---

## Next Steps

1. **Complete missing pages** (search, bookings, payment)
2. **Add Stripe integration** for payment processing
3. **Implement notifications** with WebSocket
4. **Add image galleries** with Lightbox
5. **Create admin dashboard** (for owners)
6. **Add real-time chat** with property owners
7. **Implement reviews system**
8. **Add analytics** with Google Analytics

---

## Documentation References

- [Next.js Docs](https://nextjs.org/docs)
- [Tailwind CSS](https://tailwindcss.com/docs)
- [React Hook Form](https://react-hook-form.com)
- [Zustand](https://github.com/pmndrs/zustand)

---

**Status:** ✅ Ready for development

**Next:** Follow setup instructions above to start building! 🚀
