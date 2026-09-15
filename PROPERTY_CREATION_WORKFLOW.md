# Property Creation Workflow - Testing Guide

## 📋 **Workflow Overview**

```
Owner Login
    ↓
Dashboard (/owner/dashboard)
    ↓
Add Property (/owner/properties/add)
    ↓
Step 1: Basic Info → Save Draft
    ↓
Step 2: Location → Save Draft
    ↓
Step 3: Accommodation → Save Draft
    ↓
Step 4: House Rules → Submit for Approval
    ↓
Property Status: draft → pending_approval
    ↓
Admin Dashboard (/admin/dashboard)
    ↓
Property Approval Queue (/admin/properties)
    ↓
Review Property (/admin/properties/[id])
    ↓
Click "Approve"
    ↓
Property Status: pending_approval → approved
    ↓
Published to Guests
```

---

## 🧪 **Step-by-Step Testing Instructions**

### **Phase 1: Owner Creates Property**

#### **Step 1: Login as Owner**
1. Go to `/login`
2. Email: `owner@example.com`
3. Password: (your test password)
4. Click "Login"
5. ✓ Should see Owner Dashboard

#### **Step 2: Navigate to Add Property**
1. From Dashboard, click "Add Property" button
2. OR navigate to `/owner/properties/add`
3. ✓ Should see 4-step wizard with Progress sidebar

#### **Step 3: Fill Step 1 - Basic Information**
Fill the following fields:
- **Property Name**: "Test Villa Colombo"
- **Property Type**: Select "Villa"
- **Short Description**: "Beautiful beachside villa with ocean views"
- **Full Description**: "Spacious villa with modern amenities, perfect for families. Features private beach access, pool, and garden..."

Click **"Save Draft"** button
- ✓ Should see "Property created! Draft saved." message
- ✓ Property ID should appear in sidebar
- ✓ Sidebar shows "Step 1" complete with checkmark

**Verify in Database:**
```bash
psql slbooking
SELECT id, name, status, created_at FROM properties ORDER BY created_at DESC LIMIT 1;
```
Expected: Record with `status = 'draft'`

#### **Step 4: Refresh Browser**
Press `F5` or click refresh
- ✓ Page should reload
- ✓ **ALL data from Step 1 should still be there**
- ✓ Property name should still show
- ✓ Sidebar still shows Property ID

This proves **persistent storage is working!**

#### **Step 5: Fill Step 2 - Location**
Click "Next" to proceed to Step 2

Fill the following fields:
- **Address**: "123 Beach Road"
- **Province**: "Western"
- **District**: "Colombo"
- **City/Town**: "Colombo"
- **Postal Code**: "00100"
- **Google Maps URL**: "https://maps.google.com/maps?q=6.9271,80.7744"
- **Latitude**: "6.9271"
- **Longitude**: "80.7744"
- **Nearby Attractions**: "Colombo Fort, Mt. Lavinia Beach, Shopping malls nearby"

Click **"Save Draft"** button
- ✓ Should see "Draft saved successfully!" message
- ✓ Sidebar shows "Step 2" complete with checkmark

**Verify in Database:**
```bash
SELECT id, name, city, district, address FROM properties ORDER BY created_at DESC LIMIT 1;
```
Expected: Data updated with location info

#### **Step 6: Fill Step 3 - Accommodation**
Click "Next" to proceed to Step 3

Fill the following fields:
- **Bedrooms**: "3"
- **Bathrooms**: "2"
- **Beds**: "5"
- **Max Guests**: "6"
- **Property Size**: "250"
- **Floors**: "2"
- **Checkboxes**:
  - ✓ Children are allowed
  - ✓ Pets are allowed
  - ☐ Smoking is allowed (leave unchecked)

Click **"Save Draft"** button
- ✓ Should see "Draft saved successfully!" message
- ✓ Sidebar shows "Step 3" complete with checkmark

#### **Step 7: Fill Step 4 - House Rules**
Click "Next" to proceed to Step 4

Fill the following fields:
- **House Rules**: 
```
No loud noise after 10 PM
No parties or events
Smoking only on balcony
Check-in: 2:00 PM
Check-out: 11:00 AM
Children welcome
Pets allowed with permission
```

Click **"Save Draft"** button
- ✓ Should see "Draft saved successfully!" message
- ✓ Sidebar shows "Step 4" complete with checkmark

#### **Step 8: Submit for Approval**
Click **"Submit for Approval"** button
- ✓ Should see loading state ("Submitting...")
- ✓ Success message: "Property submitted for approval!"
- ✓ Auto-redirects to `/owner/properties` after 1.5 seconds
- ✓ Property should appear in list with **"PENDING APPROVAL"** badge

**Verify in Database:**
```bash
SELECT id, name, status, submitted_at FROM properties ORDER BY created_at DESC LIMIT 1;
```
Expected: Status should now be `'pending_approval'` and `submitted_at` should have timestamp

---

### **Phase 2: Admin Approves Property**

#### **Step 1: Login as Super Admin**
1. Go to `/login`
2. Email: `admin@example.com`
3. Password: (your test password)
4. Click "Login"
5. ✓ Should see Admin Dashboard (burgundy sidebar)

#### **Step 2: View Approval Queue**
1. Click "Properties" in sidebar
2. OR navigate to `/admin/properties`
3. ✓ Should see property list with filters
4. ✓ Should see the property we just created with **"PENDING APPROVAL"** status
5. ✓ Should see search bar and filter buttons

#### **Step 3: Review Property Details**
Click **"Review"** button for the test property
- OR click on the property row
- ✓ Should navigate to `/admin/properties/[id]`
- ✓ Should see complete property details:
  - Name: "Test Villa Colombo"
  - Location: Full address
  - Bedrooms, Bathrooms, Beds, Max Guests
  - Description and house rules
  - Owner contact information
  - Sidebar with "Approve" and "Reject" buttons

#### **Step 4: Approve Property**
1. Look at the right sidebar
2. Click **"Approve Property"** button (green button)
3. ✓ Should see loading state ("Approving...")
4. ✓ Success message appears
5. ✓ Page should show updated status: **"APPROVED"**
6. ✓ Property description box should now show green status badge

**Verify in Database:**
```bash
SELECT id, name, status, reviewed_at, reviewed_by_id FROM properties ORDER BY created_at DESC LIMIT 1;
```
Expected: 
- Status: `'approved'`
- `reviewed_at` has timestamp
- `reviewed_by_id` has admin user ID

#### **Step 5: View Back in Approval Queue**
1. Click back to Properties list
2. ✓ Property should NO LONGER show in "Pending" view (or if viewing "All")
3. ✓ Status badge should show **"APPROVED"** in green
4. ✓ If you filter by "Pending", property should disappear

---

### **Phase 3: Guest Sees Published Property**

#### **Step 1: Logout and Login as Guest**
1. Logout (top right)
2. Go to `/login`
3. Email: `guest@example.com`
4. Password: (your test password)
5. ✓ Should see Guest Dashboard

#### **Step 2: Search for Property**
1. Go to home page `/`
2. Use search/filter to search for properties in Colombo
3. ✓ The "Test Villa Colombo" should appear in search results
4. ✓ Should see property card with:
   - Photo placeholder (no photos yet)
   - Property name
   - Location
   - Bedrooms, bathrooms, max guests
   - Rating (0 initially)

#### **Step 3: View Property Details**
Click on the property card
- ✓ Should navigate to property details page
- ✓ Should see complete information:
  - Full description
  - House rules
  - Accommodations
  - Location on map (if implemented)

---

## ✅ **Checklist - What Should Work**

### **Frontend**
- [ ] Wizard displays 4 steps
- [ ] All form fields render correctly
- [ ] Validation errors show when submitting empty fields
- [ ] Save Draft button works on each step
- [ ] Error messages display prominently
- [ ] Success messages appear
- [ ] Loading states ("Saving...", "Submitting...")
- [ ] Step sidebar shows completion with checkmarks
- [ ] Mobile progress bar works on small screens
- [ ] Next/Previous buttons navigate correctly
- [ ] Property ID persists in sidebar

### **Backend API**
- [ ] POST `/api/properties/` creates property successfully
- [ ] PUT `/api/properties/{id}/` updates property
- [ ] POST `/api/properties/{id}/submit-for-approval/` changes status to `pending_approval`
- [ ] POST `/api/properties/{id}/approve/` changes status to `approved`
- [ ] POST `/api/properties/{id}/reject/` changes status to `rejected`
- [ ] All endpoints return updated property object
- [ ] Timestamps (`submitted_at`, `reviewed_at`) are set correctly
- [ ] `reviewed_by` field captures admin user ID

### **Database**
- [ ] Property created with `status='draft'`
- [ ] All form fields saved in property record
- [ ] On refresh, data loads from database (not lost)
- [ ] On submit, `submitted_at` timestamp is set
- [ ] On admin approve, `reviewed_at` and `reviewed_by_id` are set
- [ ] Status transitions work correctly: draft → pending_approval → approved

### **Permissions**
- [ ] Only property owner can edit their draft property
- [ ] Owner cannot edit approved properties
- [ ] Only super admin can approve/reject properties
- [ ] Owner cannot see other owners' draft properties
- [ ] Guests can only see approved properties

---

## 🐛 **Troubleshooting**

### **"Failed to create property" error**
**Problem**: Form submission fails
**Check**:
1. Are all required fields filled? (Name, Type, Description, Address, Province, District, City)
2. Is the API endpoint working? Try in Postman/curl:
   ```bash
   curl -X POST http://localhost:8000/api/properties/ \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"name":"Test","property_type":1,"description":"Test desc","city":"Colombo","district":"Colombo","province":"Western"}'
   ```
3. Check browser console for detailed error
4. Check Django server logs

### **Data disappears after refresh**
**Problem**: Form data is lost when page refreshes
**Root Cause**: Property wasn't created/saved to database
**Check**:
1. Did you click "Save Draft"?
2. Did you see "Draft saved successfully!" message?
3. Is property ID visible in sidebar?
4. Query database to verify record exists

### **Can't submit for approval**
**Problem**: Submit button doesn't work
**Check**:
1. Are you on Step 4 (final step)?
2. Have all steps been saved at least once?
3. Try checking browser console for errors
4. Check that `/api/properties/{id}/submit-for-approval/` endpoint exists

### **Admin can't see pending properties**
**Problem**: Approval queue is empty
**Check**:
1. Did owner submit property? (Status should be `pending_approval`)
2. Is admin logged in as super admin? (is_staff=True)
3. Query database: `SELECT * FROM properties WHERE status='pending_approval'`
4. Check admin permissions

---

## 📊 **Database Queries for Verification**

### **View all properties:**
```sql
SELECT id, name, status, owner_id, created_at, submitted_at FROM properties ORDER BY created_at DESC;
```

### **View property details:**
```sql
SELECT * FROM properties WHERE name='Test Villa Colombo';
```

### **View approval workflow:**
```sql
SELECT id, name, status, submitted_at, reviewed_at, reviewed_by_id, rejection_reason 
FROM properties 
WHERE status IN ('draft', 'pending_approval', 'approved', 'rejected')
ORDER BY submitted_at DESC;
```

### **Count properties by status:**
```sql
SELECT status, COUNT(*) FROM properties GROUP BY status;
```

---

## 🎯 **Next Phases (After Wizard Works)**

Once this basic wizard is confirmed working, the following can be added:

1. **Phase 5A: Photos Upload**
   - Integrate Cloudinary
   - Photo upload UI
   - Cover photo selection
   - Photo reordering

2. **Phase 5B: Rooms Management**
   - Add/edit/delete room types
   - Room amenities
   - Room photos
   - Room pricing

3. **Phase 5C: Amenities Selection**
   - Checkbox list of 20+ amenities
   - Property-level amenities
   - Save to database

4. **Phase 5D: Pricing & Availability**
   - Set base price
   - Weekend pricing
   - Seasonal rates
   - Availability calendar
   - Block dates

---

## 📝 **Notes**

- **All timestamps are in UTC** (Django setting: USE_TZ=True)
- **Draft properties are visible only to owner** (not other owners, not guests)
- **Approved properties are visible to everyone** (guests can book)
- **Admin can see ALL properties** regardless of status
- **Property owner can edit** only DRAFT and REJECTED properties
- **Approved properties cannot be edited** by owner (must contact support)

---

**Last Updated**: 2026-09-15  
**Status**: ✅ Property Wizard Working - Ready for Testing
