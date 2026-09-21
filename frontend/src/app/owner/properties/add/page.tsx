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
  website: string
  address: string
  city: string
  district: string
  province: string
  postal_code: string
  latitude: string
  longitude: string
  google_maps_url: string
  house_rules: string
}

const propertyTypes = [
  { id: 1, name: 'Villa' }, { id: 2, name: 'Hotel' }, { id: 3, name: 'Guest House' },
  { id: 4, name: 'Apartment' }, { id: 5, name: 'Resort' }, { id: 6, name: 'Other' },
]
const amenities = ['WiFi', 'Swimming Pool', 'Parking', 'Air Conditioning', 'Kitchen', 'Breakfast', 'Restaurant', 'Garden', 'Beach Access', 'Hot Water', 'TV', 'Washing Machine', 'Airport Transfer', 'BBQ', 'Private Pool']

function errorMessage(error: any) {
  const status = error.response?.status
  const data = error.response?.data
  if (status === 401) return 'Please login again.'
  if (status === 403) return 'You do not have permission to create this property.'
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
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const { register, handleSubmit, formState: { errors } } = useForm<PropertyFormData>({ defaultValues: { property_type: '', house_rules: '' } })

  useEffect(() => {
    const draftId = new URLSearchParams(window.location.search).get('propertyId')
    if (draftId) setPropertyId(draftId)
  }, [])

  const saveDraft = async (data: PropertyFormData) => {
    setSaving(true); setError(null); setMessage(null)
    try {
      const payload = { ...data, property_type: data.property_type === '' ? null : data.property_type, latitude: data.latitude || null, longitude: data.longitude || null, google_maps_url: data.google_maps_url || null, status: 'draft', amenity_ids: selectedAmenities }
      const saved = propertyId ? await api.updateProperty(propertyId, payload) : await api.createProperty(payload)
      if (!saved.id) throw new Error('The backend did not return a property ID.')
      setPropertyId(saved.id)
      setMessage('Property saved successfully. Status: DRAFT')
      window.setTimeout(() => router.push(`/owner/properties/manage?propertyId=${encodeURIComponent(saved.id)}`), 700)
    } catch (saveError: any) {
      console.error('[PROPERTY DRAFT]', saveError)
      setError(errorMessage(saveError))
    } finally { setSaving(false) }
  }

  return (
    <div className="mx-auto max-w-5xl">
      <div className="mb-8"><p className="text-sm font-semibold uppercase tracking-wide text-blue-700">Property details</p><h1 className="mt-2 text-4xl font-bold text-gray-900">Create property</h1><p className="mt-2 text-gray-600">Save the property as a draft first. Rooms, photos, pricing, and approval are managed afterwards.</p></div>
      {error && <div className="mb-6 rounded-lg border border-red-200 bg-red-50 p-4 text-red-800">{error}</div>}
      {message && <div className="mb-6 rounded-lg border border-green-200 bg-green-50 p-4 text-green-800">{message}</div>}
      <form onSubmit={handleSubmit(saveDraft)} className="space-y-6">
        <section className="rounded-lg bg-white p-6 shadow"><h2 className="mb-5 text-xl font-semibold">Basic property information</h2><div className="grid gap-4 md:grid-cols-2">
          <label className="md:col-span-2">Property name *<input {...register('name', { required: 'Property name is required' })} className="form-input" />{errors.name && <small className="text-red-600">{errors.name.message}</small>}</label>
          <label>Property type *<select {...register('property_type', { required: 'Property type is required', valueAsNumber: true })} className="form-input"><option value="">Select type</option>{propertyTypes.map(type => <option key={type.id} value={type.id}>{type.name}</option>)}</select></label>
          <label>Contact phone<input {...register('contact_phone')} className="form-input" /></label><label>Contact email<input type="email" {...register('contact_email')} className="form-input" /></label><label>Website<input type="url" {...register('website')} className="form-input" /></label>
          <label className="md:col-span-2">Short description<input {...register('short_description')} className="form-input" /></label><label className="md:col-span-2">Description *<textarea {...register('description', { required: 'Description is required' })} rows={5} className="form-input" /></label>
        </div></section>
        <section className="rounded-lg bg-white p-6 shadow"><h2 className="mb-5 text-xl font-semibold">Location</h2><div className="grid gap-4 md:grid-cols-2">
          <label className="md:col-span-2">Address *<input {...register('address', { required: 'Address is required' })} className="form-input" /></label><label>City *<input {...register('city', { required: 'City is required' })} className="form-input" /></label><label>District *<input {...register('district', { required: 'District is required' })} className="form-input" /></label><label>Province *<input {...register('province', { required: 'Province is required' })} className="form-input" /></label><label>Country<input defaultValue="Sri Lanka" className="form-input" readOnly /></label><label>Latitude<input {...register('latitude')} className="form-input" /></label><label>Longitude<input {...register('longitude')} className="form-input" /></label><label className="md:col-span-2">Google Maps URL<input type="url" {...register('google_maps_url')} className="form-input" /></label>
        </div></section>
        <section className="rounded-lg bg-white p-6 shadow"><h2 className="mb-5 text-xl font-semibold">Property amenities</h2><div className="grid gap-3 sm:grid-cols-2 md:grid-cols-3">{amenities.map((amenity, index) => <label key={amenity} className="flex items-center gap-2"><input type="checkbox" checked={selectedAmenities.includes(index + 1)} onChange={() => setSelectedAmenities(current => current.includes(index + 1) ? current.filter(id => id !== index + 1) : [...current, index + 1])} />{amenity}</label>)}</div><p className="mt-3 text-sm text-gray-500">Selected amenities use the existing amenity relationship.</p></section>
        <section className="rounded-lg bg-white p-6 shadow"><h2 className="mb-5 text-xl font-semibold">House rules</h2><label>Rules, check-in/out, smoking, pets, events, children, and additional information<textarea {...register('house_rules')} rows={6} className="form-input" /></label></section>
        <div className="flex flex-wrap items-center justify-between gap-4 pb-10"><span className="text-sm text-gray-500">{propertyId ? `Draft ID: ${propertyId}` : 'No property has been created yet.'}</span><button type="submit" disabled={saving} className="rounded-lg bg-blue-600 px-6 py-3 font-semibold text-white hover:bg-blue-700 disabled:opacity-50">{saving ? 'Saving...' : 'Save draft'}</button></div>
      </form>
      <style jsx>{`.form-input { margin-top: .35rem; display: block; width: 100%; border: 1px solid #d1d5db; border-radius: .5rem; padding: .65rem .75rem; } label { display: block; color: #374151; font-size: .9rem; }`}</style>
    </div>
  )
}
