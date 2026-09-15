/**
 * Property Wizard - 11-step form for creating/editing properties
 * Steps:
 * 1. Basic Information
 * 2. Location
 * 3. Accommodation
 * 4. Rooms/Units
 * 5. Amenities
 * 6. Photos/Media
 * 7. Pricing
 * 8. Availability
 * 9. House Rules
 * 10. Contact Information
 * 11. Preview & Submit
 */

'use client'

import { useState, useRef } from 'react'
import React from 'react'
import { useRouter } from 'next/navigation'
import { useForm, Controller } from 'react-hook-form'
import Link from 'next/link'
import { api } from '@/lib/api'
import {
  ChevronLeft,
  ChevronRight,
  Save,
  Check,
  AlertCircle,
} from 'lucide-react'

interface PropertyFormData {
  // Step 1: Basic Info
  name: string
  property_type: number | ''
  short_description: string
  description: string

  // Step 2: Location
  address: string
  city: string
  district: string
  province: string
  postal_code: string
  latitude: string
  longitude: string
  nearby_attractions: string

  // Step 3: Accommodation
  bedrooms: number
  bathrooms: number
  beds: number
  max_guests: number
  children_allowed: boolean
  pets_allowed: boolean
  smoking_allowed: boolean
  property_size: number
  floors: number

  // Step 4-10: Will be handled separately
}

const STEPS = [
  {
    number: 1,
    title: 'Basic Information',
    description: 'Property name and basic details',
  },
  {
    number: 2,
    title: 'Location',
    description: 'Where is your property located',
  },
  {
    number: 3,
    title: 'Accommodation',
    description: 'Bedrooms, bathrooms, and capacity',
  },
  {
    number: 4,
    title: 'Rooms/Units',
    description: 'Add different room types',
  },
  {
    number: 5,
    title: 'Amenities',
    description: 'Select available amenities',
  },
  {
    number: 6,
    title: 'Photos & Media',
    description: 'Upload property photos',
  },
  {
    number: 7,
    title: 'Pricing',
    description: 'Set your rates',
  },
  {
    number: 8,
    title: 'Availability',
    description: 'Manage availability calendar',
  },
  {
    number: 9,
    title: 'House Rules',
    description: 'Check-in/out times and policies',
  },
  {
    number: 10,
    title: 'Contact Information',
    description: 'Owner contact and WhatsApp',
  },
  {
    number: 11,
    title: 'Review & Submit',
    description: 'Preview and submit for approval',
  },
]

export default function PropertyWizard() {
  const router = useRouter()
  const [currentStep, setCurrentStep] = useState(1)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)

  const { control, register, handleSubmit, watch, formState: { errors } } = useForm<PropertyFormData>({
    defaultValues: {
      property_type: '',
      bedrooms: 1,
      bathrooms: 1,
      beds: 1,
      max_guests: 2,
      children_allowed: true,
      pets_allowed: false,
      smoking_allowed: false,
      property_size: 0,
      floors: 1,
    },
  })

  const onSubmit = async (data: PropertyFormData) => {
    try {
      setLoading(true)
      setError(null)

      // Create property with status='draft'
      const propertyData = {
        ...data,
        property_type: data.property_type === '' ? null : data.property_type,
        status: 'draft',
      }

      await api.createProperty(propertyData)
      setSuccess(true)

      // Redirect after 1 second
      setTimeout(() => {
        router.push('/owner/properties')
      }, 1000)
    } catch (err: any) {
      console.error('Failed to create property:', err)
      setError(
        err.response?.data?.detail ||
        err.response?.data?.message ||
        'Failed to create property. Please try again.'
      )
    } finally {
      setLoading(false)
    }
  }

  const propertyTypes = [
    { id: 1, name: 'Villa' },
    { id: 2, name: 'Hotel' },
    { id: 3, name: 'Guest House' },
    { id: 4, name: 'Apartment' },
    { id: 5, name: 'Holiday Home' },
    { id: 6, name: 'Resort' },
    { id: 7, name: 'Bungalow' },
    { id: 8, name: 'Homestay' },
  ]

  return (
    <div className="max-w-6xl">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-4xl font-bold text-gray-900">Add New Property</h1>
        <p className="text-gray-600 mt-2">Complete all steps to list your property</p>
      </div>

      <div className="flex gap-8">
        {/* Sidebar with Steps */}
        <div className="hidden lg:block w-64">
          <div className="bg-white rounded-lg shadow sticky top-8">
            <div className="p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-6">Steps</h3>
              <div className="space-y-3">
                {STEPS.map((step) => (
                  <button
                    key={step.number}
                    onClick={() => setCurrentStep(step.number)}
                    className={`w-full text-left p-3 rounded-lg transition-colors ${
                      currentStep === step.number
                        ? 'bg-blue-100 border-l-4 border-blue-600'
                        : currentStep > step.number
                        ? 'bg-green-50 text-gray-600'
                        : 'hover:bg-gray-50 text-gray-600'
                    }`}
                  >
                    <div className="flex items-start gap-3">
                      <div
                        className={`flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center text-sm font-semibold ${
                          currentStep === step.number
                            ? 'bg-blue-600 text-white'
                            : currentStep > step.number
                            ? 'bg-green-600 text-white'
                            : 'bg-gray-300 text-gray-700'
                        }`}
                      >
                        {currentStep > step.number ? (
                          <Check className="w-4 h-4" />
                        ) : (
                          step.number
                        )}
                      </div>
                      <div>
                        <p className="font-medium text-sm">{step.title}</p>
                        <p className="text-xs text-gray-600">{step.description}</p>
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Main Content */}
        <div className="flex-1">
          <form onSubmit={handleSubmit(onSubmit)}>
            {/* Step Content */}
            <div className="bg-white rounded-lg shadow p-8 mb-8">
              {/* Progress Bar (Mobile) */}
              <div className="lg:hidden mb-6">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-semibold text-gray-900">
                    Step {currentStep} of {STEPS.length}
                  </span>
                  <span className="text-sm text-gray-600">
                    {Math.round((currentStep / STEPS.length) * 100)}%
                  </span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-blue-600 h-2 rounded-full transition-all"
                    style={{ width: `${(currentStep / STEPS.length) * 100}%` }}
                  />
                </div>
              </div>

              {/* Step Title */}
              <div className="mb-6">
                <h2 className="text-2xl font-bold text-gray-900">
                  {STEPS[currentStep - 1].title}
                </h2>
                <p className="text-gray-600 mt-1">
                  {STEPS[currentStep - 1].description}
                </p>
              </div>

              {/* Error Alert */}
              {error && (
                <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg flex gap-3">
                  <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0" />
                  <p className="text-red-800">{error}</p>
                </div>
              )}

              {/* Success Alert */}
              {success && (
                <div className="mb-6 p-4 bg-green-50 border border-green-200 rounded-lg flex gap-3">
                  <Check className="w-5 h-5 text-green-600 flex-shrink-0" />
                  <p className="text-green-800">Property created successfully! Redirecting...</p>
                </div>
              )}

              {/* Step Content */}
              <div className="space-y-6">
                {currentStep === 1 && (
                  <Step1Form register={register} errors={errors} propertyTypes={propertyTypes} />
                )}
                {currentStep === 2 && (
                  <Step2Form register={register} errors={errors} />
                )}
                {currentStep === 3 && (
                  <Step3Form register={register} control={control} />
                )}
                {currentStep === 4 && (
                  <Step4Form />
                )}
                {currentStep === 5 && (
                  <Step5Form />
                )}
                {currentStep === 6 && (
                  <Step6Form />
                )}
                {currentStep === 7 && (
                  <Step7Form />
                )}
                {currentStep === 8 && (
                  <Step8Form />
                )}
                {currentStep === 9 && (
                  <Step9Form />
                )}
                {currentStep === 10 && (
                  <Step10Form />
                )}
                {currentStep === 11 && (
                  <Step11Form />
                )}
              </div>
            </div>

            {/* Navigation Buttons */}
            <div className="flex items-center justify-between gap-4">
              <div>
                {currentStep > 1 && (
                  <button
                    type="button"
                    onClick={() => setCurrentStep(currentStep - 1)}
                    className="flex items-center gap-2 px-6 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
                  >
                    <ChevronLeft className="w-5 h-5" />
                    Previous
                  </button>
                )}
              </div>

              <div className="text-sm text-gray-600">
                Step {currentStep} of {STEPS.length}
              </div>

              <div className="flex gap-4">
                <button
                  type="button"
                  className="flex items-center gap-2 px-6 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
                >
                  <Save className="w-5 h-5" />
                  Save Draft
                </button>

                {currentStep < STEPS.length ? (
                  <button
                    type="button"
                    onClick={() => setCurrentStep(currentStep + 1)}
                    className="flex items-center gap-2 px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                  >
                    Next
                    <ChevronRight className="w-5 h-5" />
                  </button>
                ) : (
                  <button
                    type="submit"
                    disabled={loading}
                    className="flex items-center gap-2 px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50"
                  >
                    {loading ? 'Submitting...' : 'Submit for Approval'}
                  </button>
                )}
              </div>
            </div>
          </form>
        </div>
      </div>
    </div>
  )
}

// Step 1: Basic Information
function Step1Form({ register, errors, propertyTypes }: any) {
  return (
    <>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          <label className="block text-sm font-medium text-gray-900 mb-2">
            Property Name *
          </label>
          <input
            {...register('name', { required: 'Property name is required' })}
            type="text"
            placeholder="e.g., Mountain View Villa"
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
          {errors.name && <p className="text-red-600 text-sm mt-1">{errors.name.message}</p>}
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-900 mb-2">
            Property Type *
          </label>
          <select
            {...register('property_type', { required: 'Property type is required' })}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="">Select a type</option>
            {propertyTypes.map((type: any) => (
              <option key={type.id} value={type.id}>
                {type.name}
              </option>
            ))}
          </select>
          {errors.property_type && (
            <p className="text-red-600 text-sm mt-1">{errors.property_type.message}</p>
          )}
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-900 mb-2">
          Short Description (for search results) *
        </label>
        <textarea
          {...register('short_description', {
            required: 'Short description is required',
            maxLength: { value: 500, message: 'Maximum 500 characters' },
          })}
          placeholder="A catchy one-liner about your property..."
          rows={2}
          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
        />
        {errors.short_description && (
          <p className="text-red-600 text-sm mt-1">{errors.short_description.message}</p>
        )}
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-900 mb-2">
          Full Description *
        </label>
        <textarea
          {...register('description', { required: 'Description is required' })}
          placeholder="Detailed description of your property, amenities, and unique features..."
          rows={6}
          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
        />
        {errors.description && (
          <p className="text-red-600 text-sm mt-1">{errors.description.message}</p>
        )}
      </div>
    </>
  )
}

// Step 2: Location
function Step2Form({ register, errors }: any) {
  return (
    <>
      <div>
        <label className="block text-sm font-medium text-gray-900 mb-2">
          Address *
        </label>
        <input
          {...register('address', { required: 'Address is required' })}
          type="text"
          placeholder="123 Main Street"
          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />
        {errors.address && <p className="text-red-600 text-sm mt-1">{errors.address.message}</p>}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div>
          <label className="block text-sm font-medium text-gray-900 mb-2">
            Province *
          </label>
          <input
            {...register('province', { required: 'Province is required' })}
            type="text"
            placeholder="e.g., Western"
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
          {errors.province && (
            <p className="text-red-600 text-sm mt-1">{errors.province.message}</p>
          )}
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-900 mb-2">
            District *
          </label>
          <input
            {...register('district', { required: 'District is required' })}
            type="text"
            placeholder="e.g., Colombo"
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
          {errors.district && (
            <p className="text-red-600 text-sm mt-1">{errors.district.message}</p>
          )}
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-900 mb-2">
            City/Town *
          </label>
          <input
            {...register('city', { required: 'City is required' })}
            type="text"
            placeholder="e.g., Colombo"
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
          {errors.city && <p className="text-red-600 text-sm mt-1">{errors.city.message}</p>}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          <label className="block text-sm font-medium text-gray-900 mb-2">
            Postal Code
          </label>
          <input
            {...register('postal_code')}
            type="text"
            placeholder="e.g., 00100"
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-900 mb-2">
            Google Maps URL
          </label>
          <input
            type="url"
            placeholder="https://maps.google.com/..."
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          <label className="block text-sm font-medium text-gray-900 mb-2">
            Latitude
          </label>
          <input
            {...register('latitude')}
            type="number"
            step="0.00000001"
            placeholder="e.g., 6.9271"
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-900 mb-2">
            Longitude
          </label>
          <input
            {...register('longitude')}
            type="number"
            step="0.00000001"
            placeholder="e.g., 80.7744"
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-900 mb-2">
          Nearby Attractions
        </label>
        <textarea
          {...register('nearby_attractions')}
          placeholder="e.g., Close to Colombo Fort, near beaches, shopping malls..."
          rows={3}
          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
        />
      </div>
    </>
  )
}

// Step 3: Accommodation
function Step3Form({ register, control }: any) {
  return (
    <>
      <div className="grid grid-cols-2 md:grid-cols-3 gap-6">
        <div>
          <label className="block text-sm font-medium text-gray-900 mb-2">
            Bedrooms
          </label>
          <input
            {...register('bedrooms')}
            type="number"
            min="0"
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-900 mb-2">
            Bathrooms
          </label>
          <input
            {...register('bathrooms')}
            type="number"
            min="0"
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-900 mb-2">
            Beds
          </label>
          <input
            {...register('beds')}
            type="number"
            min="0"
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-900 mb-2">
            Max Guests
          </label>
          <input
            {...register('max_guests')}
            type="number"
            min="1"
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-900 mb-2">
            Property Size (m²)
          </label>
          <input
            {...register('property_size')}
            type="number"
            min="0"
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-900 mb-2">
            Floors
          </label>
          <input
            {...register('floors')}
            type="number"
            min="1"
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>
      </div>

      <div className="space-y-4 pt-6 border-t border-gray-200">
        <label className="flex items-center gap-3">
          <input
            {...register('children_allowed')}
            type="checkbox"
            className="w-4 h-4"
          />
          <span className="text-sm text-gray-900">Children are allowed</span>
        </label>

        <label className="flex items-center gap-3">
          <input
            {...register('pets_allowed')}
            type="checkbox"
            className="w-4 h-4"
          />
          <span className="text-sm text-gray-900">Pets are allowed</span>
        </label>

        <label className="flex items-center gap-3">
          <input
            {...register('smoking_allowed')}
            type="checkbox"
            className="w-4 h-4"
          />
          <span className="text-sm text-gray-900">Smoking is allowed</span>
        </label>
      </div>
    </>
  )
}

// Step 4: Rooms/Units
function Step4Form() {
  const [rooms, setRooms] = React.useState([
    { id: 1, name: '', type: '', quantity: 1, beds: 1, max_guests: 2, price_per_night: 0 }
  ])

  const addRoom = () => {
    setRooms([...rooms, {
      id: rooms.length + 1,
      name: '',
      type: '',
      quantity: 1,
      beds: 1,
      max_guests: 2,
      price_per_night: 0
    }])
  }

  const updateRoom = (id: number, field: string, value: any) => {
    setRooms(rooms.map(r => r.id === id ? { ...r, [field]: value } : r))
  }

  const removeRoom = (id: number) => {
    setRooms(rooms.filter(r => r.id !== id))
  }

  const roomTypes = ['Standard', 'Deluxe', 'Suite', 'Studio', 'Bungalow', 'Villa']

  return (
    <div className="space-y-6">
      <p className="text-gray-600 text-sm">Define different room types available in your property</p>

      {rooms.map((room) => (
        <div key={room.id} className="p-6 border border-gray-200 rounded-lg">
          <div className="flex justify-between items-start mb-4">
            <h3 className="font-semibold text-gray-900">Room {room.id}</h3>
            {rooms.length > 1 && (
              <button
                type="button"
                onClick={() => removeRoom(room.id)}
                className="text-red-600 hover:text-red-700 text-sm font-medium"
              >
                Remove
              </button>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-900 mb-1">Room Name</label>
              <input
                type="text"
                value={room.name}
                onChange={(e) => updateRoom(room.id, 'name', e.target.value)}
                placeholder="e.g., Ocean View Suite"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-900 mb-1">Room Type</label>
              <select
                value={room.type}
                onChange={(e) => updateRoom(room.id, 'type', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
              >
                <option value="">Select type</option>
                {roomTypes.map(t => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-900 mb-1">Quantity</label>
              <input
                type="number"
                min="1"
                value={room.quantity}
                onChange={(e) => updateRoom(room.id, 'quantity', parseInt(e.target.value))}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-900 mb-1">Beds</label>
              <input
                type="number"
                min="1"
                value={room.beds}
                onChange={(e) => updateRoom(room.id, 'beds', parseInt(e.target.value))}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-900 mb-1">Max Guests</label>
              <input
                type="number"
                min="1"
                value={room.max_guests}
                onChange={(e) => updateRoom(room.id, 'max_guests', parseInt(e.target.value))}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-900 mb-1">Price/Night (LKR)</label>
              <input
                type="number"
                min="0"
                value={room.price_per_night}
                onChange={(e) => updateRoom(room.id, 'price_per_night', parseInt(e.target.value))}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
              />
            </div>
          </div>
        </div>
      ))}

      <button
        type="button"
        onClick={addRoom}
        className="px-4 py-2 border border-blue-600 text-blue-600 rounded-lg hover:bg-blue-50 font-medium text-sm"
      >
        + Add Room Type
      </button>
    </div>
  )
}

// Step 5: Amenities
function Step5Form() {
  const [selectedAmenities, setSelectedAmenities] = React.useState<string[]>([])

  const amenities = [
    'WiFi', 'TV', 'Air Conditioning', 'Heating', 'Kitchen', 'Washing Machine',
    'Dryer', 'Dishwasher', 'Parking', 'Pool', 'Hot Tub', 'Gym', 'Garden',
    'Balcony', 'Patio', 'BBQ', 'Elevator', 'Accessible', 'Pet Friendly',
    'Crib', 'High Chair', 'Desk', 'Iron', 'Safe', 'Refrigerator'
  ]

  const toggleAmenity = (amenity: string) => {
    setSelectedAmenities(prev =>
      prev.includes(amenity)
        ? prev.filter(a => a !== amenity)
        : [...prev, amenity]
    )
  }

  return (
    <div className="space-y-4">
      <p className="text-gray-600 text-sm">Select all amenities available at your property</p>
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
        {amenities.map((amenity) => (
          <label key={amenity} className="flex items-center gap-3 p-3 border rounded-lg cursor-pointer hover:bg-blue-50" onClick={() => toggleAmenity(amenity)}>
            <input
              type="checkbox"
              checked={selectedAmenities.includes(amenity)}
              onChange={() => {}}
              className="w-4 h-4 rounded"
            />
            <span className="text-sm text-gray-900">{amenity}</span>
          </label>
        ))}
      </div>
      <p className="text-xs text-gray-600 mt-4">Selected: {selectedAmenities.length} amenities</p>
    </div>
  )
}

// Step 6: Photos & Media
function Step6Form() {
  const [photos, setPhotos] = React.useState<File[]>([])
  const fileInputRef = React.useRef<HTMLInputElement>(null)

  const handlePhotoSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setPhotos([...photos, ...Array.from(e.target.files)])
    }
  }

  const removePhoto = (index: number) => {
    setPhotos(photos.filter((_, i) => i !== index))
  }

  return (
    <div className="space-y-6">
      <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center cursor-pointer hover:border-blue-500" onClick={() => fileInputRef.current?.click()}>
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept="image/*"
          onChange={handlePhotoSelect}
          className="hidden"
        />
        <p className="text-gray-600">Click to upload property photos</p>
        <p className="text-xs text-gray-500 mt-1">JPEG, PNG up to 10MB each</p>
      </div>

      {photos.length > 0 && (
        <div className="space-y-3">
          <h3 className="font-semibold text-gray-900">Uploaded Photos ({photos.length})</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {photos.map((photo, idx) => (
              <div key={idx} className="relative">
                <img
                  src={URL.createObjectURL(photo)}
                  alt={`Photo ${idx + 1}`}
                  className="w-full h-32 object-cover rounded-lg"
                />
                <button
                  type="button"
                  onClick={() => removePhoto(idx)}
                  className="absolute -top-2 -right-2 w-6 h-6 bg-red-600 text-white rounded-full text-sm flex items-center justify-center hover:bg-red-700"
                >
                  ×
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

// Step 7: Pricing
function Step7Form() {
  const [pricing, setPricing] = React.useState({
    base_price: 0,
    weekend_price: 0,
    seasonal_discount: 0,
    guest_fee: 0,
    cleaning_fee: 0,
    service_fee: 0,
  })

  const handlePricingChange = (field: string, value: number) => {
    setPricing({ ...pricing, [field]: value })
  }

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          <label className="block text-sm font-medium text-gray-900 mb-2">
            Base Price per Night (LKR) *
          </label>
          <input
            type="number"
            min="0"
            value={pricing.base_price}
            onChange={(e) => handlePricingChange('base_price', parseInt(e.target.value))}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-900 mb-2">
            Weekend Price per Night (LKR)
          </label>
          <input
            type="number"
            min="0"
            value={pricing.weekend_price}
            onChange={(e) => handlePricingChange('weekend_price', parseInt(e.target.value))}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg"
          />
          <p className="text-xs text-gray-600 mt-1">Leave blank to use base price</p>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-900 mb-2">
            Cleaning Fee (LKR)
          </label>
          <input
            type="number"
            min="0"
            value={pricing.cleaning_fee}
            onChange={(e) => handlePricingChange('cleaning_fee', parseInt(e.target.value))}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-900 mb-2">
            Service Fee (%)
          </label>
          <input
            type="number"
            min="0"
            max="100"
            value={pricing.service_fee}
            onChange={(e) => handlePricingChange('service_fee', parseInt(e.target.value))}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-900 mb-2">
            Extra Guest Fee (LKR)
          </label>
          <input
            type="number"
            min="0"
            value={pricing.guest_fee}
            onChange={(e) => handlePricingChange('guest_fee', parseInt(e.target.value))}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-900 mb-2">
            Seasonal Discount (%)
          </label>
          <input
            type="number"
            min="0"
            max="100"
            value={pricing.seasonal_discount}
            onChange={(e) => handlePricingChange('seasonal_discount', parseInt(e.target.value))}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg"
          />
        </div>
      </div>

      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <p className="text-sm text-blue-900">
          <strong>Example:</strong> Base 5,000 LKR + Cleaning 500 LKR + Service 10% = Guest pays 5,950 LKR
        </p>
      </div>
    </div>
  )
}

// Step 8: Availability
function Step8Form() {
  const [availability, setAvailability] = React.useState({
    min_stay: 1,
    max_stay: 365,
    check_in_time: '14:00',
    check_out_time: '11:00',
    instant_booking: false,
  })

  const handleAvailabilityChange = (field: string, value: any) => {
    setAvailability({ ...availability, [field]: value })
  }

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          <label className="block text-sm font-medium text-gray-900 mb-2">
            Minimum Stay (nights)
          </label>
          <input
            type="number"
            min="1"
            value={availability.min_stay}
            onChange={(e) => handleAvailabilityChange('min_stay', parseInt(e.target.value))}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-900 mb-2">
            Maximum Stay (nights)
          </label>
          <input
            type="number"
            min="1"
            value={availability.max_stay}
            onChange={(e) => handleAvailabilityChange('max_stay', parseInt(e.target.value))}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-900 mb-2">
            Check-in Time
          </label>
          <input
            type="time"
            value={availability.check_in_time}
            onChange={(e) => handleAvailabilityChange('check_in_time', e.target.value)}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-900 mb-2">
            Check-out Time
          </label>
          <input
            type="time"
            value={availability.check_out_time}
            onChange={(e) => handleAvailabilityChange('check_out_time', e.target.value)}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg"
          />
        </div>
      </div>

      <div className="border border-gray-300 rounded-lg p-4">
        <label className="flex items-center gap-3 cursor-pointer">
          <input
            type="checkbox"
            checked={availability.instant_booking}
            onChange={(e) => handleAvailabilityChange('instant_booking', e.target.checked)}
            className="w-4 h-4 rounded"
          />
          <div>
            <p className="font-medium text-gray-900">Enable Instant Booking</p>
            <p className="text-sm text-gray-600">Allow guests to book without your approval</p>
          </div>
        </label>
      </div>

      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
        <p className="text-sm text-yellow-900">
          <strong>Tip:</strong> You can set specific blocked dates and availability in your calendar after listing
        </p>
      </div>
    </div>
  )
}

// Step 9: House Rules
function Step9Form({ register }: any) {
  return (
    <div className="space-y-6">
      <div>
        <label className="block text-sm font-medium text-gray-900 mb-2">
          House Rules
        </label>
        <textarea
          {...register('house_rules')}
          placeholder="e.g., No loud noise after 10 PM, No parties, Smoking only on balcony..."
          rows={5}
          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
        />
        <p className="text-xs text-gray-600 mt-1">Guests should know these important rules</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="p-4 border border-gray-200 rounded-lg">
          <label className="flex items-start gap-3 cursor-pointer">
            <input type="checkbox" className="w-4 h-4 rounded mt-1" />
            <div>
              <p className="font-medium text-gray-900">No Smoking Inside</p>
              <p className="text-sm text-gray-600">Enforce non-smoking indoors</p>
            </div>
          </label>
        </div>

        <div className="p-4 border border-gray-200 rounded-lg">
          <label className="flex items-start gap-3 cursor-pointer">
            <input type="checkbox" className="w-4 h-4 rounded mt-1" />
            <div>
              <p className="font-medium text-gray-900">No Pets</p>
              <p className="text-sm text-gray-600">Do not allow animals</p>
            </div>
          </label>
        </div>

        <div className="p-4 border border-gray-200 rounded-lg">
          <label className="flex items-start gap-3 cursor-pointer">
            <input type="checkbox" className="w-4 h-4 rounded mt-1" />
            <div>
              <p className="font-medium text-gray-900">No Parties</p>
              <p className="text-sm text-gray-600">Prohibit large gatherings</p>
            </div>
          </label>
        </div>

        <div className="p-4 border border-gray-200 rounded-lg">
          <label className="flex items-start gap-3 cursor-pointer">
            <input type="checkbox" className="w-4 h-4 rounded mt-1" />
            <div>
              <p className="font-medium text-gray-900">Quiet Hours</p>
              <p className="text-sm text-gray-600">Enforce quiet time (10 PM - 8 AM)</p>
            </div>
          </label>
        </div>
      </div>
    </div>
  )
}

// Step 10: Contact Information
function Step10Form({ register }: any) {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          <label className="block text-sm font-medium text-gray-900 mb-2">
            Contact Person Name *
          </label>
          <input
            {...register('contact.contact_person_name', { required: 'Contact person name is required' })}
            type="text"
            placeholder="e.g., John Doe"
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-900 mb-2">
            Email Address
          </label>
          <input
            {...register('contact.email')}
            type="email"
            placeholder="your@email.com"
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-900 mb-2">
            Phone Number *
          </label>
          <input
            {...register('contact.contact_phone', { required: 'Phone number is required' })}
            type="tel"
            placeholder="+94 11 123 4567"
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-900 mb-2">
            WhatsApp Number
          </label>
          <input
            {...register('contact.whatsapp_number')}
            type="tel"
            placeholder="+94 71 123 4567"
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
          <p className="text-xs text-gray-600 mt-1">Include country code for WhatsApp</p>
        </div>
      </div>

      <div className="bg-green-50 border border-green-200 rounded-lg p-4">
        <p className="text-sm text-green-900">
          <strong>WhatsApp Integration:</strong> Guests can message you directly on WhatsApp for inquiries and check-in details
        </p>
      </div>
    </div>
  )
}

// Step 11: Preview & Submit
function Step11Form({ watch }: any) {
  const formData = watch()

  return (
    <div className="space-y-6">
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <p className="text-sm text-blue-900">
          <strong>Review your property details before submitting for approval.</strong> You can make changes by going back to previous steps.
        </p>
      </div>

      {/* Property Summary */}
      <div className="space-y-4">
        <div className="bg-gray-50 rounded-lg p-4">
          <h3 className="font-semibold text-gray-900 mb-2">{formData.name || 'Property Name'}</h3>
          <p className="text-sm text-gray-600">{formData.short_description}</p>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="p-3 bg-white border rounded-lg text-center">
            <p className="text-2xl font-bold text-gray-900">{formData.bedrooms}</p>
            <p className="text-xs text-gray-600">Bedrooms</p>
          </div>
          <div className="p-3 bg-white border rounded-lg text-center">
            <p className="text-2xl font-bold text-gray-900">{formData.bathrooms}</p>
            <p className="text-xs text-gray-600">Bathrooms</p>
          </div>
          <div className="p-3 bg-white border rounded-lg text-center">
            <p className="text-2xl font-bold text-gray-900">{formData.max_guests}</p>
            <p className="text-xs text-gray-600">Max Guests</p>
          </div>
          <div className="p-3 bg-white border rounded-lg text-center">
            <p className="text-2xl font-bold text-gray-900">{formData.property_type}</p>
            <p className="text-xs text-gray-600">Type</p>
          </div>
        </div>

        <div className="p-4 bg-white border rounded-lg">
          <p className="text-sm font-medium text-gray-900 mb-2">Location</p>
          <p className="text-sm text-gray-600">
            {formData.address}, {formData.city}, {formData.district}, {formData.province}
          </p>
        </div>

        <div className="p-4 bg-white border rounded-lg">
          <p className="text-sm font-medium text-gray-900 mb-2">Description</p>
          <p className="text-sm text-gray-600 whitespace-pre-wrap">{formData.description}</p>
        </div>
      </div>

      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
        <p className="text-sm text-yellow-900">
          <strong>What happens next:</strong> Your property will be reviewed by our admin team within 24-48 hours. You'll receive an email notification once it's approved.
        </p>
      </div>
    </div>
  )
}
