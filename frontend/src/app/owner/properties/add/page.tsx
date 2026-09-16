/**
 * Property Add Template - multi-step listing setup form
 * Each step saves to the database immediately and supports draft submissions.
 * Complete workflow: Draft → Save Draft → Submit → Pending Approval → Admin Review → Live
 */

'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useForm } from 'react-hook-form'
import { api } from '@/lib/api'
import {
  ChevronLeft,
  ChevronRight,
  Save,
  Check,
  AlertCircle,
  Loader2,
  Camera,
  Sparkles,
  Star,
  Wifi,
  Car,
  Utensils,
  Waves,
  Trees,
  ShieldCheck,
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

const AMENITY_OPTIONS = [
  { label: 'Free Wi‑Fi', icon: Wifi },
  { label: 'Air conditioning', icon: Sparkles },
  { label: 'Private kitchen', icon: Utensils },
  { label: 'Pool', icon: Waves },
  { label: 'Garden', icon: Trees },
  { label: 'Parking', icon: Car },
  { label: '24/7 security', icon: ShieldCheck },
]

const STEPS = [
  { number: 1, title: 'Basic Information', description: 'Property name and details' },
  { number: 2, title: 'Location', description: 'Address and coordinates' },
  { number: 3, title: 'Accommodation', description: 'Rooms and capacity' },
  { number: 4, title: 'House Rules', description: 'Rules and policies' },
]

export default function PropertyWizard() {
  const router = useRouter()
  const [currentStep, setCurrentStep] = useState(1)
  const [loading, setLoading] = useState(false)
  const [savingDraft, setSavingDraft] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [propertyId, setPropertyId] = useState<string | null>(null)
  const [coverPhotoUrl, setCoverPhotoUrl] = useState(
    'https://images.unsplash.com/photo-1505693416388-ac5ce068fe85?auto=format&fit=crop&w=1200&q=80'
  )
  const [selectedAmenities, setSelectedAmenities] = useState<string[]>([
    'Free Wi‑Fi',
    'Air conditioning',
    'Private kitchen',
  ])
  const [basePrice, setBasePrice] = useState(180)

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors },
    reset,
  } = useForm<PropertyFormData>({
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

  const templateChecklist = [
    { label: 'Basic details', done: Boolean(formValues.name && formValues.property_type) },
    { label: 'Location', done: Boolean(formValues.address && formValues.city && formValues.district) },
    { label: 'Capacity', done: Boolean(formValues.max_guests && formValues.bedrooms) },
    { label: 'House rules', done: Boolean(formValues.house_rules) },
  ]

  const toggleAmenity = (label: string) => {
    setSelectedAmenities((current) =>
      current.includes(label)
        ? current.filter((item) => item !== label)
        : [...current, label]
    )
  }

  // Helper to extract error message from DRF response
  const getErrorMessage = (err: any): string => {
    if (!err.response?.data) {
      return 'Failed to save draft'
    }

    const data = err.response.data

    // Check for detail field (non-field errors)
    if (data.detail) return data.detail
    if (data.message) return data.message
    if (typeof data === 'string') return data

    // Check for field validation errors
    if (typeof data === 'object') {
      const fieldErrors = []
      for (const [field, errors] of Object.entries(data)) {
        if (Array.isArray(errors)) {
          fieldErrors.push(`${field}: ${errors.join(', ')}`)
        } else if (typeof errors === 'string') {
          fieldErrors.push(`${field}: ${errors}`)
        }
      }
      if (fieldErrors.length > 0) {
        return fieldErrors.slice(0, 2).join(' | ')
      }
    }

    return 'Failed to save draft'
  }

  // Save draft automatically
  const saveDraft = async (data: PropertyFormData) => {
    try {
      setSavingDraft(true)
      setError(null)

      const propertyData = {
        ...data,
        property_type: data.property_type === '' ? null : data.property_type,
        status: 'draft',
      }

      if (propertyId) {
        // Update existing property
        await api.updateProperty(propertyId, propertyData)
        setSuccess('Draft saved successfully!')
      } else {
        // Create new property
        const response = await api.createProperty(propertyData)
        setPropertyId(response.id)
        setSuccess('Property created! Draft saved.')
      }

      setTimeout(() => setSuccess(null), 3000)
    } catch (err: any) {
      const errorMsg = getErrorMessage(err)
      setError(errorMsg)
      console.error('Save draft error:', err)
    } finally {
      setSavingDraft(false)
    }
  }

  const onSubmit = async (data: PropertyFormData) => {
    try {
      setLoading(true)
      setError(null)

      const propertyData = {
        ...data,
        property_type: data.property_type === '' ? null : data.property_type,
        status: 'draft',
      }

      // If we don't have a property ID yet, create it first
      if (!propertyId) {
        const newProperty = await api.createProperty(propertyData)
        setPropertyId(newProperty.id)

        // Then submit for approval
        await api.submitPropertyForApproval(newProperty.id)
        setSuccess('Property submitted for approval!')

        setTimeout(() => {
          router.push('/owner/properties')
        }, 1500)
      } else {
        // Update and submit
        await api.updateProperty(propertyId, propertyData)
        await api.submitPropertyForApproval(propertyId)
        setSuccess('Property submitted for approval!')

        setTimeout(() => {
          router.push('/owner/properties')
        }, 1500)
      }
    } catch (err: any) {
      // Use the improved error message extraction
      const errorMsg = getErrorMessage(err)
        .replace('Failed to save draft', 'Failed to submit property')
      setError(errorMsg)
      console.error('Submit error:', err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-6xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <div className="mb-4 inline-flex items-center gap-2 rounded-full bg-blue-100 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-blue-700">
          Property template
        </div>
        <h1 className="text-4xl font-bold text-gray-900">Create Property</h1>
        <p className="text-gray-600 mt-2">
          Use this property listing template to add your space, save progress, and submit for approval.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        {templateChecklist.map((item, index) => (
          <div
            key={item.label}
            className={`rounded-xl border p-4 ${
              item.done ? 'border-green-200 bg-green-50' : 'border-gray-200 bg-white'
            }`}
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold uppercase tracking-wide text-gray-500">
                Step {index + 1}
              </span>
              <span className={`h-2.5 w-2.5 rounded-full ${item.done ? 'bg-green-500' : 'bg-gray-300'}`} />
            </div>
            <p className="font-medium text-gray-900">{item.label}</p>
          </div>
        ))}
      </div>

      <div className="flex gap-8">
        {/* Sidebar */}
        <div className="hidden lg:block w-80">
          <div className="bg-white rounded-lg shadow sticky top-8 p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Template progress</h3>
            <p className="text-sm text-gray-600 mb-6">Complete each section of your property listing.</p>
            <div className="space-y-3">
              {STEPS.map((step) => (
                <button
                  key={step.number}
                  onClick={() => setCurrentStep(step.number)}
                  className={`w-full text-left p-3 rounded-lg transition-colors ${
                    currentStep === step.number
                      ? 'bg-blue-100 border-l-4 border-blue-600'
                      : 'hover:bg-gray-50'
                  }`}
                >
                  <div className="flex items-start gap-3">
                    <div
                      className={`flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center text-sm font-semibold ${
                        currentStep === step.number
                          ? 'bg-blue-600 text-white'
                          : currentStep > step.number
                          ? 'bg-green-600 text-white'
                          : 'bg-gray-300'
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

            <div className="mt-6 pt-6 border-t border-gray-200">
              <p className="text-xs text-gray-600 mb-2">Listing preview</p>
              <div className="overflow-hidden rounded-2xl border border-gray-200 bg-gray-50">
                <div
                  className="h-24 bg-cover bg-center"
                  style={{ backgroundImage: `url(${coverPhotoUrl})` }}
                />
                <div className="p-3">
                  <p className="text-sm font-semibold text-gray-900 truncate">
                    {formValues.name || 'Your property name'}
                  </p>
                  <p className="text-xs text-gray-600 mt-1 truncate">
                    {formValues.city || 'City'}, {formValues.district || 'District'}
                  </p>
                  <p className="mt-2 text-sm font-bold text-blue-700">
                    LKR {basePrice.toLocaleString()} / night
                  </p>
                </div>
              </div>
            </div>

            <div className="mt-6 rounded-xl border border-blue-100 bg-blue-50 p-4">
              <p className="text-xs font-semibold uppercase tracking-wide text-blue-700">Highlights</p>
              <div className="mt-3 space-y-2 text-sm text-gray-700">
                {selectedAmenities.slice(0, 4).map((item) => (
                  <div key={item} className="flex items-center gap-2">
                    <span className="h-2 w-2 rounded-full bg-blue-600" />
                    {item}
                  </div>
                ))}
              </div>
            </div>

            {propertyId && (
              <div className="mt-6 pt-6 border-t border-gray-200">
                <p className="text-xs text-gray-600 mb-2">Property ID</p>
                <p className="text-xs font-mono text-gray-900 break-all">
                  {propertyId.substring(0, 12)}...
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Main Content */}
        <div className="flex-1">
          <form onSubmit={handleSubmit(onSubmit)}>
            <div className="bg-white rounded-lg shadow p-8 mb-8 border border-gray-200">
              {/* Mobile Progress */}
              <div className="lg:hidden mb-6">
                <div className="flex justify-between mb-2">
                  <span className="text-sm font-semibold">
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
              <div className="mb-8">
                <h2 className="text-2xl font-bold text-gray-900">
                  {STEPS[currentStep - 1].title}
                </h2>
                <p className="text-gray-600 mt-2">
                  {STEPS[currentStep - 1].description}
                </p>
              </div>

              {/* Alerts */}
              {error && (
                <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg flex gap-3">
                  <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="text-red-800 font-medium">Error</p>
                    <p className="text-red-700 text-sm mt-1">{error}</p>
                  </div>
                </div>
              )}

              {success && (
                <div className="mb-6 p-4 bg-green-50 border border-green-200 rounded-lg flex gap-3">
                  <Check className="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" />
                  <p className="text-green-800">{success}</p>
                </div>
              )}

              {/* Step Content */}
              <div className="space-y-6">
                {currentStep === 1 && (
                  <Step1Form
                    register={register}
                    errors={errors}
                    coverPhotoUrl={coverPhotoUrl}
                    setCoverPhotoUrl={setCoverPhotoUrl}
                  />
                )}
                {currentStep === 2 && <Step2Form register={register} errors={errors} />}
                {currentStep === 3 && (
                  <Step3Form
                    register={register}
                    selectedAmenities={selectedAmenities}
                    toggleAmenity={toggleAmenity}
                  />
                )}
                {currentStep === 4 && (
                  <Step4Form
                    register={register}
                    basePrice={basePrice}
                    setBasePrice={setBasePrice}
                  />
                )}
              </div>
            </div>

            {/* Navigation */}
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

              <div className="flex gap-3">
                <button
                  type="button"
                  onClick={handleSubmit(saveDraft)}
                  disabled={savingDraft}
                  className="flex items-center gap-2 px-6 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 transition-colors"
                >
                  {savingDraft ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Saving...
                    </>
                  ) : (
                    <>
                      <Save className="w-4 h-4" />
                      Save Draft
                    </>
                  )}
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
                    className="flex items-center gap-2 px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 transition-colors"
                  >
                    {loading ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin" />
                        Submitting...
                      </>
                    ) : (
                      <>
                        <Check className="w-4 h-4" />
                        Submit for Approval
                      </>
                    )}
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
function Step1Form({ register, errors, coverPhotoUrl, setCoverPhotoUrl }: any) {
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
            className={`w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
              errors.name ? 'border-red-500' : 'border-gray-300'
            }`}
          />
          {errors.name && (
            <p className="text-red-600 text-sm mt-1">{errors.name.message}</p>
          )}
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-900 mb-2">
            Property Type *
          </label>
          <select
            {...register('property_type', { required: 'Property type is required' })}
            className={`w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
              errors.property_type ? 'border-red-500' : 'border-gray-300'
            }`}
          >
            <option value="">Select a type</option>
            {PROPERTY_TYPES.map((type) => (
              <option key={type.id} value={type.id}>
                {type.name}
              </option>
            ))}
          </select>
          {errors.property_type && (
            <p className="text-red-600 text-sm mt-1">
              {errors.property_type.message}
            </p>
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
          className={`w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none ${
            errors.short_description ? 'border-red-500' : 'border-gray-300'
          }`}
        />
        {errors.short_description && (
          <p className="text-red-600 text-sm mt-1">
            {errors.short_description.message}
          </p>
        )}
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-900 mb-2">
          Full Description *
        </label>
        <textarea
          {...register('description', { required: 'Description is required' })}
          placeholder="Detailed description of your property, what makes it special..."
          rows={5}
          className={`w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none ${
            errors.description ? 'border-red-500' : 'border-gray-300'
          }`}
        />
        {errors.description && (
          <p className="text-red-600 text-sm mt-1">{errors.description.message}</p>
        )}
      </div>

      <div className="mt-8 rounded-2xl border border-dashed border-gray-300 bg-gray-50 p-6">
        <div className="flex items-center justify-between gap-4 flex-wrap mb-4">
          <div>
            <p className="text-lg font-semibold text-gray-900">Cover photo</p>
            <p className="text-sm text-gray-600">Use a strong hero image for your listing.</p>
          </div>
          <div className="inline-flex items-center gap-2 rounded-full bg-white px-3 py-1 text-sm font-medium text-gray-700 border border-gray-200">
            <Camera className="h-4 w-4" />
            hero image
          </div>
        </div>

        <label className="block text-sm font-medium text-gray-900 mb-2">Image URL</label>
        <input
          type="url"
          value={coverPhotoUrl}
          onChange={(event) => setCoverPhotoUrl(event.target.value)}
          placeholder="https://..."
          className="w-full rounded-lg border border-gray-300 px-4 py-2 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
        />

        <div className="mt-5 overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-sm">
          <div
            className="h-52 bg-cover bg-center"
            style={{ backgroundImage: `url(${coverPhotoUrl})` }}
          />
        </div>
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
          className={`w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
            errors.address ? 'border-red-500' : 'border-gray-300'
          }`}
        />
        {errors.address && (
          <p className="text-red-600 text-sm mt-1">{errors.address.message}</p>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div>
          <label className="block text-sm font-medium text-gray-900 mb-2">
            Province *
          </label>
          <input
            {...register('province', { required: 'Province is required' })}
            type="text"
            placeholder="Western"
            className={`w-full px-4 py-2 border rounded-lg ${
              errors.province ? 'border-red-500' : 'border-gray-300'
            }`}
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
            placeholder="Colombo"
            className={`w-full px-4 py-2 border rounded-lg ${
              errors.district ? 'border-red-500' : 'border-gray-300'
            }`}
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
            placeholder="Colombo"
            className={`w-full px-4 py-2 border rounded-lg ${
              errors.city ? 'border-red-500' : 'border-gray-300'
            }`}
          />
          {errors.city && (
            <p className="text-red-600 text-sm mt-1">{errors.city.message}</p>
          )}
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
            placeholder="00100"
            className="w-full px-4 py-2 border border-gray-300 rounded-lg"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-900 mb-2">
            Google Maps URL
          </label>
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
          <label className="block text-sm font-medium text-gray-900 mb-2">
            Latitude
          </label>
          <input
            {...register('latitude')}
            type="number"
            step="0.00000001"
            placeholder="6.9271"
            className="w-full px-4 py-2 border border-gray-300 rounded-lg"
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
            placeholder="80.7744"
            className="w-full px-4 py-2 border border-gray-300 rounded-lg"
          />
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-900 mb-2">
          Nearby Attractions
        </label>
        <textarea
          {...register('nearby_attractions')}
          placeholder="Close to Colombo Fort, beaches, shopping malls..."
          rows={3}
          className="w-full px-4 py-2 border border-gray-300 rounded-lg resize-none"
        />
      </div>
    </>
  )
}

// Step 3: Accommodation
function Step3Form({ register, selectedAmenities, toggleAmenity }: any) {
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
            className="w-full px-4 py-2 border border-gray-300 rounded-lg"
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
            className="w-full px-4 py-2 border border-gray-300 rounded-lg"
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
            className="w-full px-4 py-2 border border-gray-300 rounded-lg"
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
            className="w-full px-4 py-2 border border-gray-300 rounded-lg"
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
            className="w-full px-4 py-2 border border-gray-300 rounded-lg"
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
            className="w-full px-4 py-2 border border-gray-300 rounded-lg"
          />
        </div>
      </div>

      <div className="mt-8 rounded-2xl border border-gray-200 bg-gradient-to-br from-white to-blue-50 p-5">
        <div className="flex items-center justify-between mb-4">
          <div>
            <p className="text-lg font-semibold text-gray-900">Amenities</p>
            <p className="text-sm text-gray-600">Choose the best features for your listing.</p>
          </div>
          <div className="inline-flex items-center gap-2 rounded-full bg-blue-100 px-2.5 py-1 text-xs font-semibold text-blue-700">
            <Star className="h-3.5 w-3.5" />
            top picks
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {AMENITY_OPTIONS.map(({ label, icon: Icon }) => (
            <button
              key={label}
              type="button"
              onClick={() => toggleAmenity(label)}
              className={`flex items-center justify-between rounded-xl border px-3 py-2 text-left text-sm font-medium transition ${
                selectedAmenities.includes(label)
                  ? 'border-blue-400 bg-blue-50 text-blue-800'
                  : 'border-gray-200 bg-white text-gray-700 hover:border-blue-200 hover:bg-blue-50'
              }`}
            >
              <span className="flex items-center gap-2">
                <Icon className="h-4 w-4 text-blue-600" />
                {label}
              </span>
              <span
                className={`flex h-5 w-5 items-center justify-center rounded-full border text-xs ${
                  selectedAmenities.includes(label)
                    ? 'border-blue-600 bg-blue-600 text-white'
                    : 'border-gray-300 bg-white'
                }`}
              >
                {selectedAmenities.includes(label) ? '✓' : ''}
              </span>
            </button>
          ))}
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
function Step4Form({ register, basePrice, setBasePrice }: any) {
  return (
    <>
      <div>
        <label className="block text-sm font-medium text-gray-900 mb-2">
          House Rules
        </label>
        <textarea
          {...register('house_rules')}
          placeholder="e.g., No loud noise after 10 PM, No parties, Smoking only on balcony..."
          rows={5}
          className="w-full px-4 py-2 border border-gray-300 rounded-lg resize-none"
        />
        <p className="text-xs text-gray-600 mt-2">
          Help guests understand your house rules and policies
        </p>
      </div>

      <div className="mt-8 grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="rounded-2xl border border-gray-200 bg-white p-5">
          <div className="flex items-center justify-between mb-4">
            <p className="text-lg font-semibold text-gray-900">Gallery preview</p>
            <span className="rounded-full bg-gray-100 px-2 py-1 text-xs font-medium text-gray-600">
              4 images
            </span>
          </div>
          <div className="grid grid-cols-2 gap-3">
            {[1, 2, 3, 4].map((item) => (
              <div
                key={item}
                className="h-24 rounded-xl bg-cover bg-center"
                style={{
                  backgroundImage:
                    "url('https://images.unsplash.com/photo-1494526585095-c41746248156?auto=format&fit=crop&w=600&q=80')",
                }}
              />
            ))}
          </div>
        </div>

        <div className="rounded-2xl border border-blue-100 bg-blue-50 p-5">
          <p className="text-lg font-semibold text-gray-900">Pricing preview</p>
          <div className="mt-4 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-gray-600">Base rate</span>
              <label className="flex items-center gap-2 font-semibold text-gray-900">
                <span className="text-sm">LKR</span>
                <input
                  type="number"
                  min="0"
                  value={basePrice}
                  onChange={(event) => setBasePrice(Number(event.target.value))}
                  className="w-24 rounded-lg border border-blue-200 bg-white px-2 py-1 text-right"
                />
                <span className="text-sm">/night</span>
              </label>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-gray-600">Cleaning fee</span>
              <span className="font-semibold text-gray-900">LKR 2,500</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-gray-600">Service fee</span>
              <span className="font-semibold text-gray-900">LKR 3,000</span>
            </div>
            <div className="mt-4 rounded-xl bg-white p-3">
              <p className="text-xs uppercase tracking-wide text-gray-500">Estimated total</p>
              <p className="mt-1 text-2xl font-bold text-blue-700">LKR 5,680</p>
            </div>
          </div>
        </div>
      </div>

      <div className="bg-green-50 border border-green-200 rounded-lg p-4 mt-6">
        <p className="text-sm text-green-900">
          <strong>✓ Ready to submit!</strong> Your property details are complete.
          Click "Submit for Approval" to send to our admin team for review.
        </p>
      </div>
    </>
  )
}
