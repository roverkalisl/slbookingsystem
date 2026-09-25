'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useForm } from 'react-hook-form'
import { api } from '@/lib/api'

interface PropertyFormData {
  name: string
  property_type: number | ''
  description: string
  short_description: string
  contact_phone: string
  contact_email: string
  whatsapp_number: string
  website: string
  address: string
  city: string
  district: string
  province: string
  postal_code: string
  latitude: string
  longitude: string
  google_maps_url: string
  nearby_attractions: string
  house_rules: string
}

// Same rule as the backend (PropertyViewSet.perform_update): owners edit only these statuses
const OWNER_EDITABLE_STATUSES = ['draft', 'rejected']

/** Existing property -> form values (edit mode). WhatsApp is stored as digits (94771234567). */
function formValuesFrom(property: any): PropertyFormData {
  const whatsapp = property.contact?.whatsapp_number || ''
  return {
    name: property.name || '',
    property_type: property.property_type?.id ? Number(property.property_type.id) : '',
    description: property.description || '',
    short_description: property.short_description || '',
    contact_phone: property.contact?.contact_phone || '',
    contact_email: property.contact?.email || '',
    whatsapp_number: whatsapp && /^\d+$/.test(whatsapp) ? `+${whatsapp}` : whatsapp,
    website: '',
    address: property.address || '',
    city: property.city || '',
    district: property.district || '',
    province: property.province || '',
    postal_code: property.postal_code || '',
    latitude: property.latitude != null ? String(property.latitude) : '',
    longitude: property.longitude != null ? String(property.longitude) : '',
    google_maps_url: property.google_maps_url || '',
    nearby_attractions: property.nearby_attractions || '',
    house_rules: property.house_rules || '',
  }
}

interface PropertyType {
  id: number
  name: string
}

interface Amenity {
  id: number
  name: string
  category: string | null
}

// Display order of the master amenity categories (seed_master_data). Any other
// category from the API (e.g. older records) is shown after these, never hidden.
const CATEGORY_ORDER = [
  'Property Basics', 'Kitchen & Dining', 'Bathroom', 'Outdoor', 'Family', 'Services',
  'Security', 'Wellness', 'Activities', 'Accessibility', 'Pet Policy',
]

function groupAmenitiesByCategory(amenities: Amenity[]): [string, Amenity[]][] {
  const groups = new Map<string, Amenity[]>()
  for (const amenity of amenities) {
    const raw = amenity.category?.trim() || 'Other'
    const label = raw.charAt(0).toUpperCase() + raw.slice(1)
    groups.set(label, [...(groups.get(label) || []), amenity])
  }
  const rank = (label: string) => {
    const index = CATEGORY_ORDER.indexOf(label)
    return index === -1 ? CATEGORY_ORDER.length : index
  }
  return Array.from(groups.entries()).sort(([a], [b]) => rank(a) - rank(b) || a.localeCompare(b))
}

function errorMessage(error: any) {
  const status = error.response?.status
  const data = error.response?.data
  if (status === 401) return 'Please login again.'
  if (status === 403) return data?.detail ? String(data.detail) : 'You do not have permission to save this property.'
  if (status === 404) return 'The property endpoint was not found.'
  if (status === 409) return 'This property conflicts with an existing record.'
  if (status >= 500) return 'Server error. Please try again.'
  if (typeof data === 'string') return data
  if (data?.detail) return String(data.detail)
  if (data && typeof data === 'object') return Object.entries(data).map(([field, value]) => `${field}: ${Array.isArray(value) ? value.join(', ') : value}`).join(' | ')
  return 'Unable to save the property draft.'
}

export default function AddPropertyPage() {
  const router = useRouter()
  const [propertyId, setPropertyId] = useState<string | null>(null)
  const [selectedAmenities, setSelectedAmenities] = useState<number[]>([])
  const [propertyTypes, setPropertyTypes] = useState<PropertyType[]>([])
  const [amenities, setAmenities] = useState<Amenity[]>([])
  const [loadingOptions, setLoadingOptions] = useState(true)
  const [optionsError, setOptionsError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  // Edit mode (?propertyId=...): the owner's existing property, loaded via the owner-only endpoint
  const [existing, setExisting] = useState<any | null>(null)
  const [loadingExisting, setLoadingExisting] = useState(false)
  const { register, handleSubmit, reset, formState: { errors } } = useForm<PropertyFormData>({ defaultValues: { property_type: '', house_rules: '' } })

  useEffect(() => {
    const draftId = new URLSearchParams(window.location.search).get('propertyId')
    if (!draftId) return
    setPropertyId(draftId)
    setLoadingExisting(true)
    // Owner-only load: another owner's property id answers 404
    api.getOwnedProperty(draftId)
      .then((property: any) => {
        setExisting(property)
        setSelectedAmenities((property.amenities || []).map((amenity: any) => Number(amenity.id)))
      })
      .catch((loadError: any) => {
        setError(loadError.response?.status === 404 ? 'Property not found.' : 'Unable to load this property.')
      })
      .finally(() => setLoadingExisting(false))
  }, [])

  // Fill the form once the property AND the select options are loaded, so the
  // property type <option> exists when its value is set.
  useEffect(() => {
    if (existing && !loadingOptions) reset(formValuesFrom(existing))
  }, [existing, loadingOptions, reset])

  const isEdit = propertyId !== null
  const editable = !existing || OWNER_EDITABLE_STATUSES.includes(existing.status)

  useEffect(() => {
    Promise.all([api.getPropertyTypes(), api.getAmenities()])
      .then(([types, amenityList]) => {
        setPropertyTypes(types)
        setAmenities(amenityList)
        setOptionsError(null)
      })
      .catch((err: any) => {
        console.error('[PROPERTY OPTIONS]', err)
        setOptionsError('Unable to load property types and amenities. Please refresh the page.')
      })
      .finally(() => setLoadingOptions(false))
  }, [])

  const saveDraft = async (data: PropertyFormData) => {
    setSaving(true); setError(null); setMessage(null)
    try {
      const payload = { ...data, property_type: data.property_type === '' ? null : data.property_type, latitude: data.latitude || null, longitude: data.longitude || null, google_maps_url: data.google_maps_url || null, whatsapp_number: data.whatsapp_number.trim(), status: 'draft', amenity_ids: selectedAmenities }
      const saved = propertyId ? await api.updateProperty(propertyId, payload) : await api.createProperty(payload)
      if (!saved.id) throw new Error('The backend did not return a property ID.')
      setPropertyId(saved.id)
      setMessage(isEdit ? 'Property updated successfully.' : 'Property saved successfully. Status: DRAFT')
      window.setTimeout(() => router.push(`/owner/properties/manage?propertyId=${encodeURIComponent(saved.id)}`), 700)
    } catch (saveError: any) {
      console.error('[PROPERTY DRAFT]', saveError)
      setError(errorMessage(saveError))
    } finally { setSaving(false) }
  }

  return (
    <div className="mx-auto max-w-5xl">
      <div className="mb-8"><p className="text-sm font-semibold uppercase tracking-wide text-blue-700">Property details</p><h1 className="mt-2 text-4xl font-bold text-gray-900">{isEdit ? 'Edit property' : 'Create property'}</h1><p className="mt-2 text-gray-600">{isEdit ? 'Update your property details. Rooms, photos, pricing, and approval are managed from the property page.' : 'Save the property as a draft first. Rooms, photos, pricing, and approval are managed afterwards.'}</p></div>
      {loadingExisting && <p className="mb-6 text-gray-600">Loading property...</p>}
      {existing && !editable && (
        <div className="mb-6 rounded-lg border border-yellow-200 bg-yellow-50 p-4 text-yellow-800">
          This property is {String(existing.status).replace('_', ' ')}. Owners can only edit properties in draft or rejected status - contact support to change an approved property.
        </div>
      )}
      {error && <div className="mb-6 rounded-lg border border-red-200 bg-red-50 p-4 text-red-800">{error}</div>}
      {optionsError && <div className="mb-6 rounded-lg border border-red-200 bg-red-50 p-4 text-red-800">{optionsError}</div>}
      {message && <div className="mb-6 rounded-lg border border-green-200 bg-green-50 p-4 text-green-800">{message}</div>}
      <form onSubmit={handleSubmit(saveDraft)} className="space-y-6">
        <section className="rounded-lg bg-white p-6 shadow"><h2 className="mb-5 text-xl font-semibold">Basic property information</h2><div className="grid gap-4 md:grid-cols-2">
          <label className="md:col-span-2">Property name *<input {...register('name', { required: 'Property name is required' })} className="form-input" />{errors.name && <small className="text-red-600">{errors.name.message}</small>}</label>
          <label>Property type *<select {...register('property_type', { required: 'Property type is required', valueAsNumber: true })} className="form-input" disabled={loadingOptions}><option value="">{loadingOptions ? 'Loading...' : 'Select type'}</option>{propertyTypes.map(type => <option key={type.id} value={type.id}>{type.name}</option>)}</select>{errors.property_type && <small className="text-red-600">{errors.property_type.message}</small>}</label>
          <label>Contact phone<input {...register('contact_phone')} className="form-input" /></label><label>Contact email<input type="email" {...register('contact_email')} className="form-input" /></label>
          <label>WhatsApp number<input type="tel" placeholder="+94771234567" {...register('whatsapp_number', { pattern: { value: /^\+?[\d\s()-]{8,20}$/, message: 'Use international format, e.g. +94771234567' } })} className="form-input" /><small className="text-gray-500">Guests use this to contact you on WhatsApp. International format, e.g. +94771234567.</small>{errors.whatsapp_number && <small className="block text-red-600">{errors.whatsapp_number.message}</small>}</label>
          <label>Website<input type="url" {...register('website')} className="form-input" /></label>
          <label className="md:col-span-2">Short description<input {...register('short_description')} className="form-input" /></label><label className="md:col-span-2">Description *<textarea {...register('description', { required: 'Description is required' })} rows={5} className="form-input" /></label>
        </div></section>
        <section className="rounded-lg bg-white p-6 shadow"><h2 className="mb-5 text-xl font-semibold">Location</h2><div className="grid gap-4 md:grid-cols-2">
          <label className="md:col-span-2">Address *<input {...register('address', { required: 'Address is required' })} className="form-input" /></label><label>City *<input {...register('city', { required: 'City is required' })} className="form-input" /></label><label>District *<input {...register('district', { required: 'District is required' })} className="form-input" /></label><label>Province *<input {...register('province', { required: 'Province is required' })} className="form-input" /></label><label>Country<input defaultValue="Sri Lanka" className="form-input" readOnly /></label><label>Latitude<input {...register('latitude')} className="form-input" /></label><label>Longitude<input {...register('longitude')} className="form-input" /></label><label className="md:col-span-2">Google Maps URL<input type="url" {...register('google_maps_url')} className="form-input" /></label><label className="md:col-span-2">Nearby attractions<textarea {...register('nearby_attractions')} rows={3} className="form-input" placeholder="Beaches, temples, restaurants and travel distances" /></label>
        </div></section>
        <section className="rounded-lg bg-white p-6 shadow"><h2 className="mb-5 text-xl font-semibold">Property amenities</h2>
          {loadingOptions ? (
            <p className="text-sm text-gray-500">Loading amenities...</p>
          ) : amenities.length === 0 ? (
            <p className="rounded-lg bg-gray-50 p-4 text-sm text-gray-600">No amenities are available yet. You can save the property now and add amenities later.</p>
          ) : (
            <div className="space-y-5">
              {groupAmenitiesByCategory(amenities).map(([category, items]) => (
                <div key={category}>
                  <h3 className="mb-2 text-sm font-semibold text-gray-800">{category}</h3>
                  <div className="grid gap-3 sm:grid-cols-2 md:grid-cols-3">
                    {/* Always the database id returned by GET /api/properties/amenities/ - never an index or a hardcoded id */}
                    {items.map(amenity => <label key={amenity.id} className="flex items-center gap-2"><input type="checkbox" checked={selectedAmenities.includes(amenity.id)} onChange={() => setSelectedAmenities(current => current.includes(amenity.id) ? current.filter(id => id !== amenity.id) : [...current, amenity.id])} />{amenity.name}</label>)}
                  </div>
                </div>
              ))}
            </div>
          )}
          <p className="mt-3 text-sm text-gray-500">Amenities are optional. Selections are loaded from the platform's amenity list.</p></section>
        <section className="rounded-lg bg-white p-6 shadow"><h2 className="mb-5 text-xl font-semibold">House rules</h2><label>Rules, check-in/out, smoking, pets, events, children, and additional information<textarea {...register('house_rules')} rows={6} className="form-input" /></label></section>
        <div className="flex flex-wrap items-center justify-between gap-4 pb-10"><span className="text-sm text-gray-500">{propertyId ? `Property ID: ${propertyId}` : 'No property has been created yet.'}</span><button type="submit" disabled={saving || loadingExisting || !editable || (isEdit && !existing)} className="rounded-lg bg-blue-600 px-6 py-3 font-semibold text-white hover:bg-blue-700 disabled:opacity-50">{saving ? 'Saving...' : isEdit ? 'Save changes' : 'Save draft'}</button></div>
      </form>
      <style jsx>{`.form-input { margin-top: .35rem; display: block; width: 100%; border: 1px solid #d1d5db; border-radius: .5rem; padding: .65rem .75rem; } label { display: block; color: #374151; font-size: .9rem; }`}</style>
    </div>
  )
}
