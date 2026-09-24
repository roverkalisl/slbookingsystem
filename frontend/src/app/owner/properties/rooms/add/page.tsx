'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { api } from '@/lib/api'

const ROOM_TYPES = ['bedroom', 'living_room', 'studio', 'suite', 'dormitory', 'bungalow', 'villa']
const BED_CONFIGS = ['single', 'double', 'queen', 'king', 'twin', 'bunk', 'futon', 'mixed']
const BATH_TYPES = ['private', 'en-suite', 'shared', 'ensuite_partial']

export default function AddRoomPage() {
  const router = useRouter()
  const [propertyId, setPropertyId] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [form, setForm] = useState({
    name: '',
    description: '',
    room_type: 'bedroom',
    bed_configuration: 'double',
    bathroom_type: 'private',
    room_size_sqft: 300,
    max_adults: 2,
    max_children: 0,
    number_of_beds: 1,
    total_rooms: 1,
    view_type: '',
  })
  // Pricing is stored separately (POST /properties/rooms/{id}/pricing/) and
  // is required before the property can be submitted for approval.
  const [basePrice, setBasePrice] = useState('')
  const [weekendPrice, setWeekendPrice] = useState('')

  useEffect(() => {
    const id = new URLSearchParams(window.location.search).get('propertyId')
    setPropertyId(id)
  }, [])

  const update = (field: string, value: string | number) => {
    setForm(current => ({ ...current, [field]: value }))
  }

  const submit = async (event: React.FormEvent) => {
    event.preventDefault()
    if (!propertyId || saving) return
    setSaving(true)
    setError(null)
    let room: any = null
    try {
      room = await api.createRoom(propertyId, form)
      await api.setRoomPricing(room.id, {
        base_price: basePrice,
        weekend_price: weekendPrice.trim() === '' ? null : weekendPrice,
      })
      router.push(`/owner/properties/rooms?propertyId=${encodeURIComponent(propertyId)}`)
    } catch (err: any) {
      const data = err.response?.data
      const detail = data?.detail || data?.error || data?.base_price?.[0] || data?.weekend_price?.[0]
      setError(
        room
          ? `Room saved, but its price could not be saved${detail ? `: ${detail}` : ''}. Set the price from the Rooms page.`
          : detail || 'Unable to save room.'
      )
    } finally {
      setSaving(false)
    }
  }

  if (!propertyId) return <div className="mx-auto max-w-3xl mt-8"><p className="text-red-700">Property ID required.</p></div>

  return (
    <div className="mx-auto max-w-3xl pb-10">
      <Link
        href={`/owner/properties/rooms?propertyId=${encodeURIComponent(propertyId)}`}
        className="text-sm font-semibold text-blue-600 hover:text-blue-700"
      >
        ← Back to Rooms
      </Link>

      <div className="mb-8 mt-4">
        <h1 className="text-4xl font-bold text-gray-900">Add Room</h1>
        <p className="mt-2 text-gray-600">Create a new room type for this property</p>
      </div>

      {error && <div className="mb-6 rounded-lg border border-red-200 bg-red-50 p-4 text-red-800">{error}</div>}

      <form onSubmit={submit} className="space-y-6 rounded-lg bg-white p-6 shadow">
        {/* Basic Info */}
        <section>
          <h2 className="font-semibold mb-3">Basic Information</h2>
          <div className="space-y-4">
            <label className="block">
              Room Name *
              <input
                required
                type="text"
                value={form.name}
                onChange={e => update('name', e.target.value)}
                className="form-input"
                placeholder="e.g., Deluxe Suite"
              />
            </label>
            <label className="block">
              Description
              <textarea
                value={form.description}
                onChange={e => update('description', e.target.value)}
                className="form-input"
                rows={3}
                placeholder="Describe this room type..."
              />
            </label>
          </div>
        </section>

        {/* Room Configuration */}
        <section>
          <h2 className="font-semibold mb-3">Room Configuration</h2>
          <div className="grid gap-4 md:grid-cols-2">
            <label className="block">
              Room Type *
              <select value={form.room_type} onChange={e => update('room_type', e.target.value)} className="form-input">
                {ROOM_TYPES.map(t => <option key={t} value={t}>{t.replace('_', ' ')}</option>)}
              </select>
            </label>
            <label className="block">
              Number of Rooms *
              <input type="number" min="1" value={form.total_rooms} onChange={e => update('total_rooms', Number(e.target.value))} className="form-input" />
            </label>
            <label className="block">
              Room Size (sqft)
              <input type="number" min="1" value={form.room_size_sqft} onChange={e => update('room_size_sqft', Number(e.target.value))} className="form-input" />
            </label>
            <label className="block">
              View Type
              <select value={form.view_type} onChange={e => update('view_type', e.target.value)} className="form-input">
                <option value="">Select view...</option>
                <option value="ocean_view">Ocean View</option>
                <option value="mountain_view">Mountain View</option>
                <option value="garden_view">Garden View</option>
                <option value="city_view">City View</option>
                <option value="pool_view">Pool View</option>
              </select>
            </label>
          </div>
        </section>

        {/* Bed & Bath Configuration */}
        <section>
          <h2 className="font-semibold mb-3">Bed & Bathroom</h2>
          <div className="grid gap-4 md:grid-cols-2">
            <label className="block">
              Number of Beds *
              <input type="number" min="1" required value={form.number_of_beds} onChange={e => update('number_of_beds', Number(e.target.value))} className="form-input" />
            </label>
            <label className="block">
              Bed Configuration *
              <select value={form.bed_configuration} onChange={e => update('bed_configuration', e.target.value)} className="form-input">
                {BED_CONFIGS.map(b => <option key={b} value={b}>{b.replace('_', ' ')}</option>)}
              </select>
            </label>
            <label className="block md:col-span-2">
              Bathroom Type
              <select value={form.bathroom_type} onChange={e => update('bathroom_type', e.target.value)} className="form-input">
                {BATH_TYPES.map(b => <option key={b} value={b}>{b.replace('_', ' ')}</option>)}
              </select>
            </label>
          </div>
        </section>

        {/* Capacity */}
        <section>
          <h2 className="font-semibold mb-3">Capacity</h2>
          <div className="grid gap-4 md:grid-cols-2">
            <label className="block">
              Maximum Adults *
              <input type="number" min="1" required value={form.max_adults} onChange={e => update('max_adults', Number(e.target.value))} className="form-input" />
            </label>
            <label className="block">
              Maximum Children
              <input type="number" min="0" value={form.max_children} onChange={e => update('max_children', Number(e.target.value))} className="form-input" />
            </label>
          </div>
        </section>

        {/* Pricing */}
        <section>
          <h2 className="font-semibold mb-3">Pricing (LKR per room, per night)</h2>
          <div className="grid gap-4 md:grid-cols-2">
            <label className="block">
              Price per night *
              <input type="number" min="1" step="0.01" required value={basePrice} onChange={e => setBasePrice(e.target.value)} className="form-input" placeholder="e.g., 12000" />
            </label>
            <label className="block">
              Weekend price (Fri-Sun, optional)
              <input type="number" min="1" step="0.01" value={weekendPrice} onChange={e => setWeekendPrice(e.target.value)} className="form-input" placeholder="Same as nightly price if empty" />
            </label>
          </div>
        </section>

        <button type="submit" disabled={saving} className="rounded-lg bg-blue-600 px-6 py-3 font-semibold text-white hover:bg-blue-700 disabled:opacity-50">
          {saving ? 'Saving...' : 'Save Room'}
        </button>
      </form>

      <style jsx>{`
        .form-input {
          margin-top: 0.35rem;
          display: block;
          width: 100%;
          border: 1px solid #d1d5db;
          border-radius: 0.5rem;
          padding: 0.65rem 0.75rem;
        }
        label {
          display: block;
          color: #374151;
          font-size: 0.9rem;
          margin-bottom: 0.5rem;
        }
      `}</style>
    </div>
  )
}
