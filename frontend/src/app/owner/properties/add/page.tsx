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
  { number: 4, title: 'Rooms & Units', description: 'Add and configure room types' },
  { number: 5, title: 'House Rules', description: 'Rules and policies' },
]

interface RoomType {
  id: string
  name: string
  description: string
  room_type: string
  bed_configuration: string
  bathroom_type: string
  room_size: number
  room_amenities: string[]
  view_type: string
  room_photos: string[]
  max_adults: number
  max_children: number
  number_of_beds: number
  total_rooms: number
}

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
  const [rooms, setRooms] = useState<RoomType[]>([])
  const [showAddRoom, setShowAddRoom] = useState(false)
  const [newRoom, setNewRoom] = useState<Partial<RoomType>>({
    name: '',
    description: '',
    room_type: 'bedroom',
    bed_configuration: 'double',
    bathroom_type: 'private',
    room_size: 0,
    room_amenities: [],
    view_type: '',
    room_photos: [],
    max_adults: 2,
    max_children: 0,
    number_of_beds: 1,
    total_rooms: 1,
  })

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
    { label: 'Room types', done: rooms.length > 0 },
    { label: 'House rules', done: Boolean(formValues.house_rules) },
  ]

  const isFormComplete = templateChecklist.every(item => item.done)

  const toggleAmenity = (label: string) => {
    setSelectedAmenities((current) =>
      current.includes(label)
        ? current.filter((item) => item !== label)
        : [...current, label]
    )
  }

  const addRoom = () => {
    if (!newRoom.name || !newRoom.max_adults || !newRoom.room_type || !newRoom.bed_configuration) {
      setError('Please fill in required room details (name, adults, room type, bed configuration)')
      return
    }
    const room: RoomType = {
      id: Date.now().toString(),
      name: newRoom.name,
      description: newRoom.description || '',
      room_type: newRoom.room_type,
      bed_configuration: newRoom.bed_configuration,
      bathroom_type: newRoom.bathroom_type || 'private',
      room_size: newRoom.room_size || 0,
      room_amenities: newRoom.room_amenities || [],
      view_type: newRoom.view_type || '',
      room_photos: newRoom.room_photos || [],
      max_adults: newRoom.max_adults,
      max_children: newRoom.max_children || 0,
      number_of_beds: newRoom.number_of_beds || 1,
      total_rooms: newRoom.total_rooms || 1,
    }
    setRooms([...rooms, room])
    setNewRoom({
      name: '',
      description: '',
      room_type: 'bedroom',
      bed_configuration: 'double',
      bathroom_type: 'private',
      room_size: 0,
      room_amenities: [],
      view_type: '',
      room_photos: [],
      max_adults: 2,
      max_children: 0,
      number_of_beds: 1,
      total_rooms: 1,
    })
    setShowAddRoom(false)
    setError(null)
  }

  const deleteRoom = (id: string) => {
    setRooms(rooms.filter(r => r.id !== id))
  }

  // Helper to extract error message from DRF response
  const getErrorMessage = (err: any): string => {
    if (!err.response?.data) {
      return 'Failed to save draft'
    }

    const data = err.response.data
    console.log('Error response data:', data)

    // Check for top-level error/detail/message fields (non-field errors)
    if (data.detail) {
      if (typeof data.detail === 'string') return data.detail
      if (Array.isArray(data.detail)) return data.detail.map((d: any) => d.detail || d).join(', ')
    }
    if (data.error) {
      if (typeof data.error === 'string') return data.error
    }
    if (data.message) {
      if (typeof data.message === 'string') return data.message
    }
    if (typeof data === 'string') return data

    // Check for nested field_errors object
    if (data.field_errors && typeof data.field_errors === 'object') {
      const fieldErrors = []
      for (const [field, errors] of Object.entries(data.field_errors)) {
        if (Array.isArray(errors)) {
          fieldErrors.push(`${field}: ${errors.join(', ')}`)
        } else if (typeof errors === 'object' && errors !== null) {
          fieldErrors.push(`${field}: ${JSON.stringify(errors)}`)
        } else if (typeof errors === 'string') {
          fieldErrors.push(`${field}: ${errors}`)
        }
      }
      if (fieldErrors.length > 0) {
        return fieldErrors.slice(0, 3).join(' | ')
      }
    }

    // Check for field validation errors (DRF default format)
    if (typeof data === 'object') {
      const fieldErrors = []
      for (const [field, errors] of Object.entries(data)) {
        // Skip non-error fields
        if (['detail', 'error', 'message', 'field_errors'].includes(field)) continue

        if (Array.isArray(errors)) {
          const errorMsgs = errors.map((e: any) => {
            if (typeof e === 'string') return e
            if (e.detail) return e.detail
            return JSON.stringify(e)
          })
          fieldErrors.push(`${field}: ${errorMsgs.join(', ')}`)
        } else if (typeof errors === 'object' && errors !== null) {
          if ((errors as any).detail) {
            fieldErrors.push(`${field}: ${(errors as any).detail}`)
          } else {
            fieldErrors.push(`${field}: ${JSON.stringify(errors)}`)
          }
        } else if (typeof errors === 'string') {
          fieldErrors.push(`${field}: ${errors}`)
        }
      }
      if (fieldErrors.length > 0) {
        return fieldErrors.slice(0, 3).join(' | ')
      }
    }

    return 'Failed to save draft'
  }

  // Save draft automatically
  const saveDraft = async (data: PropertyFormData) => {
    try {
      setSavingDraft(true)
      setError(null)

      console.log('[PROPERTY WIZARD] saveDraft called', {
        step: currentStep,
        hasPropertyId: !!propertyId,
        propertyIdPrefix: propertyId ? propertyId.substring(0, 8) + '...' : 'null',
        hasRooms: rooms.length > 0,
        roomCount: rooms.length,
      })

      const propertyData = {
        ...data,
        property_type: data.property_type === '' ? null : data.property_type,
        status: 'draft',
        room_types: rooms.map(room => ({
          name: room.name,
          description: room.description,
          room_type: room.room_type,
          max_adults: room.max_adults,
          max_children: room.max_children,
          bed_configuration: room.bed_configuration,
          bathroom_type: room.bathroom_type,
          number_of_beds: room.number_of_beds,
          total_rooms: room.total_rooms,
          room_size_sqft: room.room_size,
          view_type: room.view_type,
          amenity_ids: [], // Room amenities will be handled separately if needed
        })),
      }

      if (propertyId) {
        // Update existing property
        console.log('[PROPERTY WIZARD] Updating property', {
          propertyIdPrefix: propertyId.substring(0, 8) + '...',
          method: 'PUT',
        })
        await api.updateProperty(propertyId, propertyData)
        console.log('[PROPERTY WIZARD] Update succeeded')
        setSuccess('Draft saved successfully!')
      } else {
        // Create new property
        console.log('[PROPERTY WIZARD] Creating property', {
          method: 'POST',
        })
        const response = await api.createProperty(propertyData)
        console.log('[PROPERTY WIZARD] Create succeeded', {
          newPropertyIdPrefix: response.id.substring(0, 8) + '...',
        })
        setPropertyId(response.id)
        setSuccess('Property created! Draft saved.')
      }

      setTimeout(() => setSuccess(null), 3000)
    } catch (err: any) {
      const errorMsg = getErrorMessage(err)
      console.error('[PROPERTY WIZARD] Save draft error:', {
        step: currentStep,
        hasPropertyId: !!propertyId,
        status: err.response?.status,
        errorMsg,
      })
      setError(errorMsg)
    } finally {
      setSavingDraft(false)
    }
  }

  const onSubmit = async (data: PropertyFormData) => {
    try {
      setLoading(true)
      setError(null)

      // Validate that at least one room is added
      if (rooms.length === 0) {
        setError('At least one room type is required before submitting')
        setCurrentStep(4) // Go to Rooms & Units step
        setLoading(false)
        return
      }

      console.log('[PROPERTY WIZARD] onSubmit called', {
        hasPropertyId: !!propertyId,
        propertyIdPrefix: propertyId ? propertyId.substring(0, 8) + '...' : 'null',
      })

      const propertyData = {
        ...data,
        property_type: data.property_type === '' ? null : data.property_type,
        status: 'draft',
        room_types: rooms.map(room => ({
          name: room.name,
          description: room.description,
          room_type: room.room_type,
          max_adults: room.max_adults,
          max_children: room.max_children,
          bed_configuration: room.bed_configuration,
          bathroom_type: room.bathroom_type,
          number_of_beds: room.number_of_beds,
          total_rooms: room.total_rooms,
          room_size_sqft: room.room_size,
          view_type: room.view_type,
          amenity_ids: [], // Room amenities will be handled separately if needed
        })),
      }

      // If we don't have a property ID yet, create it first
      if (!propertyId) {
        console.log('[PROPERTY WIZARD] Creating new property before submit')
        const newProperty = await api.createProperty(propertyData)
        console.log('[PROPERTY WIZARD] New property created, submitting for approval', {
          propertyIdPrefix: newProperty.id.substring(0, 8) + '...',
        })
        setPropertyId(newProperty.id)

        // Then submit for approval
        await api.submitPropertyForApproval(newProperty.id)
        setSuccess('Property submitted for approval!')

        setTimeout(() => {
          router.push('/owner/properties')
        }, 1500)
      } else {
        // Update and submit
        console.log('[PROPERTY WIZARD] Updating and submitting existing property', {
          propertyIdPrefix: propertyId.substring(0, 8) + '...',
        })
        await api.updateProperty(propertyId, propertyData)
        console.log('[PROPERTY WIZARD] Property updated, submitting for approval')
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
      console.error('[PROPERTY WIZARD] Submit error:', {
        hasPropertyId: !!propertyId,
        status: err.response?.status,
        errorMsg,
      })
      setError(errorMsg)
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
                  onClick={() => {
                    setError(null)
                    setCurrentStep(step.number)
                  }}
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
                  <RoomManagementForm
                    rooms={rooms}
                    newRoom={newRoom}
                    setNewRoom={setNewRoom}
                    showAddRoom={showAddRoom}
                    setShowAddRoom={setShowAddRoom}
                    addRoom={addRoom}
                    deleteRoom={deleteRoom}
                    error={error}
                    setError={setError}
                  />
                )}
                {currentStep === 5 && (
                  <Step4Form
                    register={register}
                    basePrice={basePrice}
                    setBasePrice={setBasePrice}
                    isFormComplete={isFormComplete}
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
                    onClick={() => {
                      setError(null)
                      setCurrentStep(currentStep - 1)
                    }}
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
                    onClick={() => {
                      setError(null)
                      setCurrentStep(currentStep + 1)
                    }}
                    className="flex items-center gap-2 px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                  >
                    Next
                    <ChevronRight className="w-5 h-5" />
                  </button>
                ) : (
                  <button
                    type="submit"
                    disabled={loading || rooms.length === 0 || !isFormComplete}
                    className="flex items-center gap-2 px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    {loading ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin" />
                        Submitting...
                      </>
                    ) : rooms.length === 0 ? (
                      <>
                        <AlertCircle className="w-4 h-4" />
                        Add Rooms to Submit
                      </>
                    ) : !isFormComplete ? (
                      <>
                        <AlertCircle className="w-4 h-4" />
                        Complete All Steps
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

// Step 4: Room Management
function RoomManagementForm({ rooms, showAddRoom, setShowAddRoom, newRoom, setNewRoom, addRoom, deleteRoom, error, setError }: any) {
  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Room Types & Units</h3>
        <p className="text-sm text-gray-600 mb-4">
          Add at least one room type to your property. Guests will choose from these options when booking.
        </p>
      </div>

      {rooms.length > 0 && (
        <div className="space-y-3">
          <h4 className="font-medium text-gray-700">Current Rooms ({rooms.length})</h4>
          {rooms.map((room: RoomType) => (
            <div key={room.id} className="flex items-start justify-between bg-gray-50 p-4 rounded-lg border border-gray-200">
              <div className="flex-1">
                <p className="font-medium text-gray-900">{room.name}</p>
                <p className="text-sm text-gray-600 mt-1">{room.description || 'No description'}</p>
                <div className="grid grid-cols-2 gap-3 mt-3 text-xs text-gray-600">
                  <div>
                    <span className="font-medium">Type:</span> {room.room_type}
                  </div>
                  <div>
                    <span className="font-medium">Beds:</span> {room.bed_configuration}
                  </div>
                  <div>
                    <span className="font-medium">Bathroom:</span> {room.bathroom_type}
                  </div>
                  <div>
                    <span className="font-medium">Size:</span> {room.room_size > 0 ? `${room.room_size} sqft` : 'N/A'}
                  </div>
                  {room.view_type && (
                    <div>
                      <span className="font-medium">View:</span> {room.view_type}
                    </div>
                  )}
                  <div>
                    <span className="font-medium">Capacity:</span> {room.max_adults} adults • {room.max_children} children
                  </div>
                  <div>
                    <span className="font-medium">Units:</span> {room.total_rooms}
                  </div>
                </div>
                {room.room_amenities && room.room_amenities.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1">
                    {room.room_amenities.map((amenity, idx) => (
                      <span key={idx} className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded">
                        {amenity}
                      </span>
                    ))}
                  </div>
                )}
              </div>
              <button
                type="button"
                onClick={() => deleteRoom(room.id)}
                className="ml-4 text-red-600 hover:text-red-700 font-medium text-sm whitespace-nowrap"
              >
                Delete
              </button>
            </div>
          ))}
        </div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-3">
          <p className="text-sm text-red-700">{error}</p>
        </div>
      )}

      {showAddRoom ? (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 space-y-6 max-h-96 overflow-y-auto">
          <h4 className="font-medium text-gray-900 sticky top-0 bg-blue-50">Add New Room Type</h4>

          {/* Basic Information */}
          <div className="space-y-4 pb-4 border-b border-blue-200">
            <h5 className="text-sm font-semibold text-gray-800">Basic Information</h5>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Room Name *</label>
                <input
                  type="text"
                  value={newRoom.name || ''}
                  onChange={(e) => setNewRoom({ ...newRoom, name: e.target.value })}
                  placeholder="e.g., Deluxe Suite"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Room Type *</label>
                <select
                  value={newRoom.room_type || 'bedroom'}
                  onChange={(e) => setNewRoom({ ...newRoom, room_type: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="bedroom">Bedroom</option>
                  <option value="living_room">Living Room</option>
                  <option value="studio">Studio</option>
                  <option value="suite">Suite</option>
                  <option value="dormitory">Dormitory</option>
                  <option value="bungalow">Bungalow</option>
                  <option value="villa">Villa</option>
                </select>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
              <textarea
                value={newRoom.description || ''}
                onChange={(e) => setNewRoom({ ...newRoom, description: e.target.value })}
                placeholder="e.g., Spacious suite with ocean view..."
                rows={2}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
          </div>

          {/* Room Configuration */}
          <div className="space-y-4 pb-4 border-b border-blue-200">
            <h5 className="text-sm font-semibold text-gray-800">Configuration</h5>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Bed Configuration *</label>
                <select
                  value={newRoom.bed_configuration || 'double'}
                  onChange={(e) => setNewRoom({ ...newRoom, bed_configuration: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="single">Single</option>
                  <option value="double">Double</option>
                  <option value="queen">Queen</option>
                  <option value="king">King</option>
                  <option value="twin">Twin</option>
                  <option value="bunk">Bunk</option>
                  <option value="futon">Futon</option>
                  <option value="mixed">Mixed</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Bathroom Type</label>
                <select
                  value={newRoom.bathroom_type || 'private'}
                  onChange={(e) => setNewRoom({ ...newRoom, bathroom_type: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="private">Private</option>
                  <option value="en-suite">En-Suite</option>
                  <option value="shared">Shared</option>
                  <option value="ensuite_partial">Ensuite Partial</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Room Size (sqft)</label>
                <input
                  type="number"
                  value={newRoom.room_size || 0}
                  onChange={(e) => setNewRoom({ ...newRoom, room_size: parseInt(e.target.value) || 0 })}
                  placeholder="e.g., 350"
                  min="0"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">View Type</label>
                <select
                  value={newRoom.view_type || ''}
                  onChange={(e) => setNewRoom({ ...newRoom, view_type: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="">No specific view</option>
                  <option value="ocean_view">Ocean View</option>
                  <option value="mountain_view">Mountain View</option>
                  <option value="garden_view">Garden View</option>
                  <option value="city_view">City View</option>
                  <option value="pool_view">Pool View</option>
                  <option value="balcony">Balcony</option>
                  <option value="terrace">Terrace</option>
                </select>
              </div>
            </div>
          </div>

          {/* Amenities */}
          <div className="space-y-3 pb-4 border-b border-blue-200">
            <h5 className="text-sm font-semibold text-gray-800">Room Amenities</h5>
            <div className="grid grid-cols-2 gap-2">
              {['AC', 'WiFi', 'TV', 'Minibar', 'Hairdryer', 'Workspace', 'Safe', 'Heater'].map((amenity) => (
                <label key={amenity} className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={newRoom.room_amenities?.includes(amenity) || false}
                    onChange={(e) => {
                      const current = newRoom.room_amenities || []
                      if (e.target.checked) {
                        setNewRoom({ ...newRoom, room_amenities: [...current, amenity] })
                      } else {
                        setNewRoom({ ...newRoom, room_amenities: current.filter((a: string) => a !== amenity) })
                      }
                    }}
                    className="rounded"
                  />
                  <span className="text-gray-700">{amenity}</span>
                </label>
              ))}
            </div>
          </div>

          {/* Capacity & Inventory */}
          <div className="space-y-4 pb-4">
            <h5 className="text-sm font-semibold text-gray-800">Capacity & Inventory</h5>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Max Adults *</label>
                <input
                  type="number"
                  value={newRoom.max_adults || 2}
                  onChange={(e) => setNewRoom({ ...newRoom, max_adults: parseInt(e.target.value) })}
                  min="1"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Max Children</label>
                <input
                  type="number"
                  value={newRoom.max_children || 0}
                  onChange={(e) => setNewRoom({ ...newRoom, max_children: parseInt(e.target.value) })}
                  min="0"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Number of Beds</label>
                <input
                  type="number"
                  value={newRoom.number_of_beds || 1}
                  onChange={(e) => setNewRoom({ ...newRoom, number_of_beds: parseInt(e.target.value) })}
                  min="1"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Total Units Available *</label>
                <input
                  type="number"
                  value={newRoom.total_rooms || 1}
                  onChange={(e) => setNewRoom({ ...newRoom, total_rooms: parseInt(e.target.value) })}
                  min="1"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
                <p className="text-xs text-gray-500 mt-1">Number of identical rooms for booking inventory</p>
              </div>
            </div>
          </div>

          <div className="flex gap-2 sticky bottom-0 bg-blue-50 pt-4">
            <button
              type="button"
              onClick={addRoom}
              className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium"
            >
              Add Room
            </button>
            <button
              type="button"
              onClick={() => {
                setShowAddRoom(false)
                setError(null)
              }}
              className="flex-1 px-4 py-2 bg-gray-200 text-gray-800 rounded-lg hover:bg-gray-300 font-medium"
            >
              Cancel
            </button>
          </div>
        </div>
      ) : (
        <button
          type="button"
          onClick={() => setShowAddRoom(true)}
          className="w-full px-4 py-3 border-2 border-dashed border-blue-300 text-blue-600 rounded-lg hover:bg-blue-50 font-medium"
        >
          + Add Room Type
        </button>
      )}

      {rooms.length === 0 && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
          <p className="text-sm text-yellow-800">
            <strong>Required:</strong> You must add at least one room type before submitting your property.
          </p>
        </div>
      )}
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
function Step4Form({ register, basePrice, setBasePrice, isFormComplete }: any) {
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

      {isFormComplete && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4 mt-6">
          <p className="text-sm text-green-900">
            <strong>✓ Ready to submit!</strong> Your property details are complete.
            Click "Submit for Approval" to send to our admin team for review.
          </p>
        </div>
      )}
    </>
  )
}
