'use client'
import Link from 'next/link'
import { useEffect, useState } from 'react'
import { api } from '@/lib/api'

export default function PropertyRoomsClient({ propertyId }: { propertyId: string }) {
  const [property, setProperty] = useState<any>(null)
  const [rooms, setRooms] = useState<any[]>([])
  const [error, setError] = useState<string | null>(null)
  useEffect(() => { Promise.all([api.getProperty(propertyId), api.getPropertyRooms(propertyId)]).then(([loadedProperty, loadedRooms]) => { setProperty(loadedProperty); setRooms(loadedRooms) }).catch((requestError: any) => setError(requestError.response?.status === 404 ? 'Property not found.' : 'Unable to load rooms.')) }, [propertyId])
  return <div className="mx-auto max-w-5xl"><Link href={`/owner/properties/${propertyId}`} className="text-sm font-semibold text-blue-600">Back to property</Link><div className="mb-8 mt-4"><h1 className="text-4xl font-bold text-gray-900">Rooms</h1><p className="mt-2 text-gray-600">{property?.name || 'Loading property...'}</p></div>{error && <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-800">{error}</div>}<div className="mb-5 flex items-center justify-between"><h2 className="text-xl font-semibold">Current rooms ({rooms.length})</h2><Link href={`/owner/properties/${propertyId}/rooms/add`} className="rounded-lg bg-blue-600 px-4 py-2 font-semibold text-white">Add room</Link></div><div className="space-y-3">{rooms.map(room => <div key={room.id} className="rounded-lg bg-white p-5 shadow"><div className="flex justify-between"><strong>{room.name}</strong><span>{room.total_rooms} unit(s)</span></div><p className="mt-2 text-sm text-gray-600">{room.max_adults} adults, {room.max_children} children, {room.number_of_beds} {room.bed_configuration} bed(s)</p></div>)}{rooms.length === 0 && <div className="rounded-lg bg-white p-8 text-center text-gray-600">No rooms yet. Add the first room after saving this property.</div>}</div></div>
}
