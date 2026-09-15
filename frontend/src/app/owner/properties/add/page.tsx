/**
 * Property Wizard - 11-step form for creating/editing properties
 */

'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useForm } from 'react-hook-form'
import { api } from '@/lib/api'
import {
  ChevronLeft,
  ChevronRight,
  Save,
  Check,
  AlertCircle,
  X,
  Plus,
  Upload,
} from 'lucide-react'

interface PropertyFormData {
  name: string
  property_type: number | ''
  short_description: string
  description: string
  address: string
  city: string
  district: string
  province: string
  postal_code: string
  latitude: string
  longitude: string
  google_maps_url: string
  nearby_attractions: string
  bedrooms: number
  bathrooms: number
  beds: number
  max_guests: number
  children_allowed: boolean
  pets_allowed: boolean
  smoking_allowed: boolean
  property_size: number
  floors: number
  house_rules: string
}

const STEPS = [
  { number: 1, title: 'Basic Information', description: 'Property name and details' },
  { number: 2, title: 'Location', description: 'Address and coordinates' },
  { number: 3, title: 'Accommodation', description: 'Rooms and capacity' },
  { number: 4, title: 'House Rules', description: 'Rules and policies' },
]

const PROPERTY_TYPES = [
  { id: 1, name: 'Villa' },
  { id: 2, name: 'Hotel' },
  { id: 3, name: 'Guest House' },
  { id: 4, name: 'Apartment' },
  { id: 5, name: 'Holiday Home' },
  { id: 6, name: 'Resort' },
  { id: 7, name: 'Bungalow' },
  { id: 8, name: 'Homestay' },
]

export default function PropertyWizard() {
  const router = useRouter()
  const [currentStep, setCurrentStep] = useState(1)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)

  const { register, handleSubmit, watch, formState: { errors } } = useForm<PropertyFormData>({
    mode: 'onBlur',
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

  const formValues = watch()

  const onSubmit = async (data: PropertyFormData) => {
    try {
      setLoading(true)
      setError(null)

      const propertyData = {
        ...data,
        property_type: data.property_type === '' ? null : data.property_type,
        status: 'draft',
      }

      await api.createProperty(propertyData)
      setSuccess(true)

      setTimeout(() => {
        router.push('/owner/properties')
      }, 1500)
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

  return (
    <div className="max-w-6xl">
      <div className="mb-8">
        <h1 className="text-4xl font-bold text-gray-900">Add New Property</h1>
        <p className="text-gray-600 mt-2">Complete all steps to list your property</p>
      </div>

      <div className="flex gap-8">
        {/* Sidebar */}
        <div className="hidden lg:block w-64">
          <div className="bg-white rounded-lg shadow sticky top-8 p-6">
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
                      ? 'bg-green-50'
                      : 'hover:bg-gray-50'
                  }`}
                >
                  <div className="flex items-start gap-3">
                    <div className={`flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center text-sm font-semibold ${
                      currentStep === step.number
                        ? 'bg-blue-600 text-white'
                        : currentStep > step.number
                        ? 'bg-green-600 text-white'
                        : 'bg-gray-300'
                    }`}>
                      {currentStep > step.number ? <Check className="w-4 h-4" /> : step.number}
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

        {/* Main Content */}
        <div className="flex-1">
          <form onSubmit={handleSubmit(onSubmit)}>
            <div className="bg-white rounded-lg shadow p-8 mb-8">
              {/* Mobile Progress */}
              <div className="lg:hidden mb-6">
                <div className="flex justify-between mb-2">
                  <span className="text-sm font-semibold">Step {currentStep} of {STEPS.length}</span>
                  <span className="text-sm text-gray-600">{Math.round((currentStep / STEPS.length) * 100)}%</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div className="bg-blue-600 h-2 rounded-full transition-all" style={{ width: `${(currentStep / STEPS.length) * 100}%` }} />
                </div>
              </div>

              {/* Step Title */}
              <div className="mb-6">
                <h2 className="text-2xl font-bold text-gray-900">{STEPS[currentStep - 1].title}</h2>
                <p className="text-gray-600 mt-1">{STEPS[currentStep - 1].description}</p>
              </div>

              {/* Errors */}
              {error && (
                <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg flex gap-3">
                  <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0" />
                  <p className="text-red-800">{error}</p>
                </div>
              )}

              {/* Success */}
              {success && (
                <div className="mb-6 p-4 bg-green-50 border border-green-200 rounded-lg flex gap-3">
                  <Check className="w-5 h-5 text-green-600 flex-shrink-0" />
                  <p className="text-green-800">Property created successfully! Redirecting...</p>
                </div>
              )}

              {/* Step Content */}
              <div className="space-y-6">
                {currentStep === 1 && <Step1Form register={register} errors={errors} />}
                {currentStep === 2 && <Step2Form register={register} errors={errors} />}
                {currentStep === 3 && <Step3Form register={register} />}
                {currentStep === 4 && <Step4Form register={register} />}
              </div>
            </div>

            {/* Navigation */}
            <div className="flex items-center justify-between gap-4">
              <div>
                {currentStep > 1 && (
                  <button
                    type="button"
                    onClick={() => setCurrentStep(currentStep - 1)}
                    className="flex items-center gap-2 px-6 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
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
                {currentStep < STEPS.length ? (
                  <button
                    type="button"
                    onClick={() => setCurrentStep(currentStep + 1)}
                    className="flex items-center gap-2 px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                  >
                    Next
                    <ChevronRight className="w-5 h-5" />
                  </button>
                ) : (
                  <button
                    type="submit"
                    disabled={loading}
                    className="flex items-center gap-2 px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50"
                  >
                    {loading ? 'Creating...' : 'Create Property'}
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
function Step1Form({ register, errors }: any) {
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
            {PROPERTY_TYPES.map((type) => (
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
          Short Description *
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
          placeholder="Detailed description of your property..."
          rows={5}
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
        <label className="block text-sm font-medium text-gray-900 mb-2">Address *</label>
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
          <label className="block text-sm font-medium text-gray-900 mb-2">Province *</label>
          <input
            {...register('province', { required: 'Province is required' })}
            type="text"
            placeholder="Western"
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
          {errors.province && <p className="text-red-600 text-sm mt-1">{errors.province.message}</p>}
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-900 mb-2">District *</label>
          <input
            {...register('district', { required: 'District is required' })}
            type="text"
            placeholder="Colombo"
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
          {errors.district && <p className="text-red-600 text-sm mt-1">{errors.district.message}</p>}
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-900 mb-2">City/Town *</label>
          <input
            {...register('city', { required: 'City is required' })}
            type="text"
            placeholder="Colombo"
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
          {errors.city && <p className="text-red-600 text-sm mt-1">{errors.city.message}</p>}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          <label className="block text-sm font-medium text-gray-900 mb-2">Postal Code</label>
          <input
            {...register('postal_code')}
            type="text"
            placeholder="00100"
            className="w-full px-4 py-2 border border-gray-300 rounded-lg"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-900 mb-2">Google Maps URL</label>
          <input
            {...register('google_maps_url')}
            type="url"
            placeholder="https://maps.google.com/..."
            className="w-full px-4 py-2 border border-gray-300 rounded-lg"
          />
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          <label className="block text-sm font-medium text-gray-900 mb-2">Latitude</label>
          <input
            {...register('latitude')}
            type="number"
            step="0.00000001"
            placeholder="6.9271"
            className="w-full px-4 py-2 border border-gray-300 rounded-lg"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-900 mb-2">Longitude</label>
          <input
            {...register('longitude')}
            type="number"
            step="0.00000001"
            placeholder="80.7744"
            className="w-full px-4 py-2 border border-gray-300 rounded-lg"
          />
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-900 mb-2">Nearby Attractions</label>
        <textarea
          {...register('nearby_attractions')}
          placeholder="Nearby landmarks, beaches, attractions..."
          rows={3}
          className="w-full px-4 py-2 border border-gray-300 rounded-lg resize-none"
        />
      </div>
    </>
  )
}

// Step 3: Accommodation
function Step3Form({ register }: any) {
  return (
    <>
      <div className="grid grid-cols-2 md:grid-cols-3 gap-6">
        <div>
          <label className="block text-sm font-medium text-gray-900 mb-2">Bedrooms</label>
          <input
            {...register('bedrooms')}
            type="number"
            min="0"
            className="w-full px-4 py-2 border border-gray-300 rounded-lg"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-900 mb-2">Bathrooms</label>
          <input
            {...register('bathrooms')}
            type="number"
            min="0"
            className="w-full px-4 py-2 border border-gray-300 rounded-lg"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-900 mb-2">Beds</label>
          <input
            {...register('beds')}
            type="number"
            min="0"
            className="w-full px-4 py-2 border border-gray-300 rounded-lg"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-900 mb-2">Max Guests</label>
          <input
            {...register('max_guests')}
            type="number"
            min="1"
            className="w-full px-4 py-2 border border-gray-300 rounded-lg"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-900 mb-2">Property Size (m²)</label>
          <input
            {...register('property_size')}
            type="number"
            min="0"
            className="w-full px-4 py-2 border border-gray-300 rounded-lg"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-900 mb-2">Floors</label>
          <input
            {...register('floors')}
            type="number"
            min="1"
            className="w-full px-4 py-2 border border-gray-300 rounded-lg"
          />
        </div>
      </div>

      <div className="space-y-4 pt-6 border-t border-gray-200">
        <label className="flex items-center gap-3 cursor-pointer">
          <input
            {...register('children_allowed')}
            type="checkbox"
            className="w-4 h-4 rounded"
          />
          <span className="text-sm text-gray-900">Children are allowed</span>
        </label>

        <label className="flex items-center gap-3 cursor-pointer">
          <input
            {...register('pets_allowed')}
            type="checkbox"
            className="w-4 h-4 rounded"
          />
          <span className="text-sm text-gray-900">Pets are allowed</span>
        </label>

        <label className="flex items-center gap-3 cursor-pointer">
          <input
            {...register('smoking_allowed')}
            type="checkbox"
            className="w-4 h-4 rounded"
          />
          <span className="text-sm text-gray-900">Smoking is allowed</span>
        </label>
      </div>
    </>
  )
}

// Step 4: House Rules
function Step4Form({ register }: any) {
  return (
    <>
      <div>
        <label className="block text-sm font-medium text-gray-900 mb-2">House Rules</label>
        <textarea
          {...register('house_rules')}
          placeholder="No loud noise after 10 PM, No parties, Smoking only on balcony..."
          rows={5}
          className="w-full px-4 py-2 border border-gray-300 rounded-lg resize-none"
        />
        <p className="text-xs text-gray-600 mt-1">Help guests understand your house rules</p>
      </div>

      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <p className="text-sm text-blue-900">
          <strong>Note:</strong> You can add more details like amenities, photos, and pricing after creating the property.
        </p>
      </div>
    </>
  )
}

