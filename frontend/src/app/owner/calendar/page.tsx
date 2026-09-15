/**
 * Owner Calendar - Manage property availability and bookings
 */

'use client'

import { useState } from 'react'
import { ChevronLeft, ChevronRight } from 'lucide-react'

export default function OwnerCalendar() {
  const [currentMonth, setCurrentMonth] = useState(new Date())
  const [selectedDate, setSelectedDate] = useState<string | null>(null)

  const events = [
    { date: '2026-09-15', type: 'booked' },
    { date: '2026-09-20', type: 'blocked' },
  ]

  const getDaysInMonth = (date: Date) => new Date(date.getFullYear(), date.getMonth() + 1, 0).getDate()
  const getFirstDayOfMonth = (date: Date) => new Date(date.getFullYear(), date.getMonth(), 1).getDay()
  const formatDate = (day: number) => `${currentMonth.getFullYear()}-${String(currentMonth.getMonth() + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`
  const getEventForDate = (day: number) => events.find((event) => event.date === formatDate(day))
  const daysArray = Array.from({ length: getDaysInMonth(currentMonth) }, (_, index) => index + 1)
  const emptyDays = Array.from({ length: getFirstDayOfMonth(currentMonth) })
  const monthName = currentMonth.toLocaleString('default', { month: 'long', year: 'numeric' })

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-4xl font-bold text-gray-900">Calendar</h1>
        <p className="text-gray-600 mt-2">Manage availability and view bookings</p>
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-2xl font-bold text-gray-900">{monthName}</h2>
            <div className="flex gap-2">
              <button type="button" onClick={() => setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() - 1))} className="p-2 hover:bg-gray-100 rounded-lg" aria-label="Previous month"><ChevronLeft className="w-5 h-5" /></button>
              <button type="button" onClick={() => setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() + 1))} className="p-2 hover:bg-gray-100 rounded-lg" aria-label="Next month"><ChevronRight className="w-5 h-5" /></button>
            </div>
          </div>
          <div className="grid grid-cols-7 gap-2 mb-4">
            {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map((day) => <div key={day} className="text-center font-semibold text-gray-600 py-2 text-sm">{day}</div>)}
          </div>
          <div className="grid grid-cols-7 gap-2">
            {emptyDays.map((_, index) => <div key={`empty-${index}`} className="aspect-square" />)}
            {daysArray.map((day) => {
              const event = getEventForDate(day)
              const date = formatDate(day)
              return <button key={date} type="button" onClick={() => setSelectedDate(date)} className={`aspect-square p-1 rounded-lg text-sm flex items-center justify-center font-semibold ${event?.type === 'booked' ? 'bg-red-100 text-red-700' : event?.type === 'blocked' ? 'bg-gray-200 text-gray-600' : selectedDate === date ? 'bg-blue-600 text-white' : 'hover:bg-blue-50'}`}>{day}</button>
            })}
          </div>
        </div>
        <div className="space-y-6">
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="font-semibold text-gray-900 mb-4">Property</h3>
            <select className="w-full px-4 py-2 border border-gray-300 rounded-lg"><option>My Property</option></select>
          </div>
          {selectedDate && <div className="bg-blue-50 border border-blue-100 rounded-lg p-6"><p className="text-sm text-blue-700">Selected date</p><p className="font-semibold text-blue-900 mt-1">{selectedDate}</p></div>}
        </div>
      </div>
    </div>
  )
}
