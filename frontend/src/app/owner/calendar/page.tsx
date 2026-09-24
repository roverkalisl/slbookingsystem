/**
 * Owner Calendar - real availability data per property/room type.
 * Reuses the existing Booking/Availability backend - no mock data.
 */

'use client'

import { useEffect, useState } from 'react'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import { api } from '@/lib/api'
import type { Property, RoomType } from '@/types'

interface CalendarDay {
  date: string
  total_rooms: number
  booked_count: number
  available_count: number
  is_blocked: boolean
}

export default function OwnerCalendar() {
  const [properties, setProperties] = useState<Property[]>([])
  const [selectedPropertyId, setSelectedPropertyId] = useState('')
  const [rooms, setRooms] = useState<RoomType[]>([])
  const [selectedRoomId, setSelectedRoomId] = useState('')
  const [currentMonth, setCurrentMonth] = useState(new Date())
  const [days, setDays] = useState<CalendarDay[]>([])
  const [selectedDate, setSelectedDate] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [loadingCalendar, setLoadingCalendar] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [actionMessage, setActionMessage] = useState<string | null>(null)

  useEffect(() => {
    loadProperties()
  }, [])

  const loadProperties = async () => {
    try {
      setLoading(true)
      const response = await api.getOwnerProperties()
      setProperties(response.results)
      if (response.results.length > 0) setSelectedPropertyId(response.results[0].id)
    } catch (err) {
      console.error('Failed to load properties:', err)
      setError('Failed to load properties')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (!selectedPropertyId) return
    api.getPropertyRooms(selectedPropertyId).then((data) => {
      setRooms(data)
      setSelectedRoomId(data.length > 0 ? data[0].id : '')
    }).catch(() => setRooms([]))
  }, [selectedPropertyId])

  useEffect(() => {
    if (!selectedRoomId) {
      setDays([])
      return
    }
    loadCalendar()
  }, [selectedRoomId, currentMonth])

  const loadCalendar = async () => {
    try {
      setLoadingCalendar(true)
      setError(null)
      const start = new Date(currentMonth.getFullYear(), currentMonth.getMonth(), 1)
      const end = new Date(currentMonth.getFullYear(), currentMonth.getMonth() + 1, 0)
      const iso = (d: Date) => d.toISOString().split('T')[0]
      const result = await api.getRoomCalendar(selectedRoomId, iso(start), iso(end))
      setDays(result.days)
    } catch (err) {
      console.error('Failed to load calendar:', err)
      setError('Failed to load calendar data')
    } finally {
      setLoadingCalendar(false)
    }
  }

  const handleToggleBlock = async (day: CalendarDay) => {
    if (!selectedRoomId) return
    setActionMessage(null)
    try {
      if (day.is_blocked) {
        await api.unblockRoomDates(selectedRoomId, day.date, day.date)
        setActionMessage(`Unblocked ${day.date}`)
      } else {
        await api.blockRoomDates(selectedRoomId, day.date, day.date)
        setActionMessage(`Blocked ${day.date}`)
      }
      await loadCalendar()
    } catch (err: any) {
      setActionMessage(err.response?.data?.error || 'Action failed')
    }
  }

  const getDaysInMonth = (date: Date) => new Date(date.getFullYear(), date.getMonth() + 1, 0).getDate()
  const getFirstDayOfMonth = (date: Date) => new Date(date.getFullYear(), date.getMonth(), 1).getDay()
  const formatDate = (day: number) => `${currentMonth.getFullYear()}-${String(currentMonth.getMonth() + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`
  const getDayInfo = (day: number) => days.find((d) => d.date === formatDate(day))
  const daysArray = Array.from({ length: getDaysInMonth(currentMonth) }, (_, index) => index + 1)
  const emptyDays = Array.from({ length: getFirstDayOfMonth(currentMonth) })
  const monthName = currentMonth.toLocaleString('default', { month: 'long', year: 'numeric' })
  const selectedDayInfo = selectedDate ? days.find((d) => d.date === selectedDate) : null

  if (loading) {
    return <div className="flex items-center justify-center min-h-screen"><p className="text-gray-600">Loading...</p></div>
  }

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-4xl font-bold text-gray-900">Calendar</h1>
        <p className="text-gray-600 mt-2">Manage availability and view bookings</p>
      </div>

      {error && <div className="mb-6 rounded-lg border border-red-200 bg-red-50 p-4 text-red-800">{error}</div>}

      {properties.length === 0 ? (
        <div className="bg-white rounded-lg shadow p-8 text-center text-gray-500">
          You don't have any properties yet.
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-2xl font-bold text-gray-900">{monthName}</h2>
              <div className="flex gap-2">
                <button type="button" onClick={() => setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() - 1))} className="p-2 hover:bg-gray-100 rounded-lg" aria-label="Previous month"><ChevronLeft className="w-5 h-5" /></button>
                <button type="button" onClick={() => setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() + 1))} className="p-2 hover:bg-gray-100 rounded-lg" aria-label="Next month"><ChevronRight className="w-5 h-5" /></button>
              </div>
            </div>

            {loadingCalendar ? (
              <p className="text-center text-gray-500 py-12">Loading calendar...</p>
            ) : (
              <>
                <div className="grid grid-cols-7 gap-2 mb-4">
                  {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map((day) => <div key={day} className="text-center font-semibold text-gray-600 py-2 text-sm">{day}</div>)}
                </div>
                <div className="grid grid-cols-7 gap-2">
                  {emptyDays.map((_, index) => <div key={`empty-${index}`} className="aspect-square" />)}
                  {daysArray.map((day) => {
                    const info = getDayInfo(day)
                    const dateStr = formatDate(day)
                    const isFullyBooked = info && info.available_count === 0 && !info.is_blocked
                    return (
                      <button
                        key={dateStr}
                        type="button"
                        onClick={() => setSelectedDate(dateStr)}
                        className={`aspect-square p-1 rounded-lg text-sm flex flex-col items-center justify-center font-semibold ${
                          info?.is_blocked ? 'bg-gray-300 text-gray-700'
                          : isFullyBooked ? 'bg-red-100 text-red-700'
                          : selectedDate === dateStr ? 'bg-blue-600 text-white'
                          : 'hover:bg-blue-50'
                        }`}
                      >
                        <span>{day}</span>
                        {info && !info.is_blocked && <span className="text-[10px] font-normal">{info.available_count}/{info.total_rooms}</span>}
                      </button>
                    )
                  })}
                </div>
                <div className="flex gap-4 mt-4 text-xs text-gray-600">
                  <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-gray-300 inline-block" /> Blocked</span>
                  <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-red-100 inline-block" /> Fully booked</span>
                </div>
              </>
            )}
          </div>

          <div className="space-y-6">
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="font-semibold text-gray-900 mb-4">Property</h3>
              <select
                value={selectedPropertyId}
                onChange={(e) => setSelectedPropertyId(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg"
              >
                {properties.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
              </select>

              {rooms.length > 0 && (
                <>
                  <h3 className="font-semibold text-gray-900 mb-2 mt-4">Room Type</h3>
                  <select
                    value={selectedRoomId}
                    onChange={(e) => setSelectedRoomId(e.target.value)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg"
                  >
                    {rooms.map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}
                  </select>
                </>
              )}
              {rooms.length === 0 && selectedPropertyId && (
                <p className="mt-4 text-sm text-gray-500">This property has no rooms yet.</p>
              )}
            </div>

            {selectedDayInfo && (
              <div className="bg-blue-50 border border-blue-100 rounded-lg p-6">
                <p className="text-sm text-blue-700">Selected date</p>
                <p className="font-semibold text-blue-900 mt-1">{selectedDayInfo.date}</p>
                <p className="text-sm text-blue-800 mt-2">
                  {selectedDayInfo.booked_count} of {selectedDayInfo.total_rooms} room(s) booked
                </p>
                {selectedDayInfo.is_blocked && <p className="text-sm text-gray-700 mt-1">This date is currently blocked.</p>}
                {actionMessage && <p className="text-xs text-blue-700 mt-2">{actionMessage}</p>}
                <button
                  onClick={() => handleToggleBlock(selectedDayInfo)}
                  className={`mt-4 w-full px-4 py-2 rounded-lg text-sm font-semibold ${selectedDayInfo.is_blocked ? 'bg-green-600 text-white hover:bg-green-700' : 'bg-gray-800 text-white hover:bg-gray-900'}`}
                >
                  {selectedDayInfo.is_blocked ? 'Unblock This Date' : 'Block This Date'}
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
