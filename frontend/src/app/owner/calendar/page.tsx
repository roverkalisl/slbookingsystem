/**
 * Owner Calendar - Manage property availability and bookings
 */

'use client'

import { useState } from 'react'
import { ChevronLeft, ChevronRight, Plus, X } from 'lucide-react'

export default function OwnerCalendar() {
  const [currentMonth, setCurrentMonth] = useState(new Date())
  const [showBlockModal, setShowBlockModal] = useState(false)
  const [selectedDate, setSelectedDate] = useState<string | null>(null)

  const events = [
    { id: '1', date: '2026-09-15', type: 'booked', guestName: 'John Doe' },
    { id: '2', date: '2026-09-20', type: 'blocked' },
  ]

  const getDaysInMonth = (date: Date) => new Date(date.getFullYear(), date.getMonth() + 1, 0).getDate()
  const getFirstDayOfMonth = (date: Date) => new Date(date.getFullYear(), date.getMonth(), 1).getDay()
  const daysArray = Array.from({ length: getDaysInMonth(currentMonth) }, (_, i) => i + 1)
  const emptyDays = Array.from({ length: getFirstDayOfMonth(currentMonth) })

  const getEventForDate = (day: number) => {
    const dateStr = \\-\-\\
    return events.find(e => e.date === dateStr)
  }

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
              <button onClick={() => setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() - 1))} className="p-2 hover:bg-gray-100 rounded-lg"><ChevronLeft className="w-5 h-5" /></button>
              <button onClick={() => setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() + 1))} className="p-2 hover:bg-gray-100 rounded-lg"><ChevronRight className="w-5 h-5" /></button>
            </div>
          </div>

          <div className="grid grid-cols-7 gap-2 mb-4">
            {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map((day) => (<div key={day} className="text-center font-semibold text-gray-600 py-2 text-sm">{day}</div>))}
          </div>

          <div className="grid grid-cols-7 gap-2">
            {emptyDays.map((_, i) => (<div key={\empty-\\} className="aspect-square"></div>))}
            {daysArray.map((day) => {
              const event = getEventForDate(day)
              return (<button key={day} onClick={() => { setSelectedDate(dateStr); setShowBlockModal(true) }} className={\spect-square p-1 rounded-lg text-sm flex items-center justify-center font-semibold \\}>{day}</button>)
            })}
          </div>
        </div>

        <div className="space-y-6">
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="font-semibold text-gray-900 mb-4">Property</h3>
            <select className="w-full px-4 py-2 border border-gray-300 rounded-lg"><option>My Property</option></select>
          </div>
        </div>
      </div>
    </div>
  )
}
