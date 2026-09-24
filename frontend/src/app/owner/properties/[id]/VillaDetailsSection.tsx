'use client'

import Link from 'next/link'
import { useEffect, useState } from 'react'
import { api } from '@/lib/api'
import type { VillaDetails } from '@/types'

// Same choices as the add-room form (RoomType model choices)
const BED_CONFIGS = ['single', 'double', 'queen', 'king', 'twin', 'bunk', 'futon', 'mixed']
const BATH_TYPES = ['private', 'en-suite', 'shared', 'ensuite_partial']

/**
 * Villa Details for a whole-property listing (Entry Villa): the villa itself
 * is the bookable unit, so capacity, beds, bathroom and price are set here
 * instead of creating rooms. Saved via PUT /properties/{id}/villa/.
 */
export default function VillaDetailsSection({
  propertyId,
  editable,
  onSaved,
}: {
  propertyId: string
  editable: boolean
  onSaved: () => void
}) {
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [details, setDetails] = useState<VillaDetails | null>(null)
  const [form, setForm] = useState({
    max_adults: 2,
    max_children: 0,
    total_occupancy: 2,
    number_of_beds: 1,
    bed_configuration: 'double',
    bathroom_type: 'private',
    base_price: '',
    weekend_price: '',
  })

  useEffect(() => {
    api.getVillaDetails(propertyId)
      .then((data) => {
        setDetails(data)
        if (data.configured) {
          setForm({
            max_adults: data.max_adults ?? 2,
            max_children: data.max_children ?? 0,
            total_occupancy: data.total_occupancy ?? 2,
            number_of_beds: data.number_of_beds ?? 1,
            bed_configuration: data.bed_configuration || 'double',
            bathroom_type: data.bathroom_type || 'private',
            base_price: data.base_price || '',
            weekend_price: data.weekend_price || '',
          })
        }
      })
      .catch(() => setError('Unable to load the villa details.'))
      .finally(() => setLoading(false))
  }, [propertyId])

  const update = (field: string, value: string | number) => setForm((current) => ({ ...current, [field]: value }))

  const save = async (event: React.FormEvent) => {
    event.preventDefault()
    if (saving) return
    setSaving(true)
    setError(null)
    setMessage(null)
    try {
      const saved = await api.saveVillaDetails(propertyId, {
        ...form,
        weekend_price: form.weekend_price.trim() === '' ? null : form.weekend_price,
      })
      setDetails(saved)
      setMessage('Villa details saved.')
      onSaved()
    } catch (err: any) {
      const data = err.response?.data
      const fieldError = data && typeof data === 'object'
        ? Object.entries(data).find(([key]) => !['error', 'detail'].includes(key))
        : null
      setError(
        data?.error || data?.detail ||
        (fieldError ? `${fieldError[0]}: ${([] as string[]).concat(fieldError[1] as any)[0]}` : 'Unable to save villa details.')
      )
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <section className="rounded-lg bg-white p-6 shadow"><p className="text-gray-600">Loading villa details...</p></section>

  return (
    <section className="rounded-lg bg-white p-6 shadow">
      <h2 className="text-xl font-semibold">Villa Details</h2>
      <p className="mt-2 text-sm text-gray-600">
        An Entry Villa is booked as a whole - guests book the entire villa, so no separate rooms are needed.
        Set the villa&apos;s capacity, beds and nightly price here. Your property photos are the villa&apos;s gallery.
      </p>
      {!details?.configured && (
        <p className="mt-3 text-sm font-semibold text-red-600">Villa details are required before submitting for approval.</p>
      )}

      {error && <div className="mt-4 rounded-lg border border-red-200 bg-red-50 p-3 text-red-800">{error}</div>}
      {message && <div className="mt-4 rounded-lg border border-green-200 bg-green-50 p-3 text-green-800">{message}</div>}

      <form onSubmit={save} className="mt-6 space-y-6">
        <fieldset disabled={!editable || saving} className="space-y-6">
          <div>
            <h3 className="font-semibold mb-3">Capacity</h3>
            <div className="grid gap-4 md:grid-cols-3">
              <label className="block">Maximum adults *
                <input type="number" min="1" required value={form.max_adults} onChange={(e) => update('max_adults', Number(e.target.value))} className="form-input" />
              </label>
              <label className="block">Maximum children
                <input type="number" min="0" value={form.max_children} onChange={(e) => update('max_children', Number(e.target.value))} className="form-input" />
              </label>
              <label className="block">Total occupancy *
                <input type="number" min="1" required value={form.total_occupancy} onChange={(e) => update('total_occupancy', Number(e.target.value))} className="form-input" />
              </label>
            </div>
          </div>

          <div>
            <h3 className="font-semibold mb-3">Beds &amp; Bathroom</h3>
            <div className="grid gap-4 md:grid-cols-3">
              <label className="block">Number of beds *
                <input type="number" min="1" required value={form.number_of_beds} onChange={(e) => update('number_of_beds', Number(e.target.value))} className="form-input" />
              </label>
              <label className="block">Bed configuration *
                <select value={form.bed_configuration} onChange={(e) => update('bed_configuration', e.target.value)} className="form-input">
                  {BED_CONFIGS.map((b) => <option key={b} value={b}>{b.replace('_', ' ')}</option>)}
                </select>
              </label>
              <label className="block">Bathroom *
                <select value={form.bathroom_type} onChange={(e) => update('bathroom_type', e.target.value)} className="form-input">
                  {BATH_TYPES.map((b) => <option key={b} value={b}>{b.replace('_', ' ')}</option>)}
                </select>
              </label>
            </div>
          </div>

          <div>
            <h3 className="font-semibold mb-3">Pricing (LKR per night, whole villa)</h3>
            <div className="grid gap-4 md:grid-cols-2">
              <label className="block">Price per night *
                <input type="number" min="1" step="0.01" required value={form.base_price} onChange={(e) => update('base_price', e.target.value)} className="form-input" placeholder="e.g., 25000" />
              </label>
              <label className="block">Weekend price (Fri-Sun, optional)
                <input type="number" min="1" step="0.01" value={form.weekend_price} onChange={(e) => update('weekend_price', e.target.value)} className="form-input" placeholder="Same as nightly price if empty" />
              </label>
            </div>
          </div>

          {editable && (
            <button type="submit" className="rounded-lg bg-blue-600 px-6 py-3 font-semibold text-white hover:bg-blue-700 disabled:opacity-50">
              {saving ? 'Saving...' : 'Save Villa Details'}
            </button>
          )}
        </fieldset>
      </form>

      {!editable && (
        <p className="mt-4 text-sm text-gray-600">Villa details can only be edited while the property is a draft or after rejection.</p>
      )}
      <p className="mt-6 text-xs text-gray-500 bg-blue-50 p-3 rounded">
        💡 Availability: the villa is bookable by default. Block dates (owner use, maintenance) in the{' '}
        <Link href="/owner/calendar" className="text-blue-600 underline">Calendar</Link>.
      </p>

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
        }
      `}</style>
    </section>
  )
}
