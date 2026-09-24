import Link from 'next/link'

/**
 * Shown on the owner room pages for a whole-property listing (Entry Villa):
 * the villa itself is the bookable unit, so there are no rooms to manage.
 */
export default function RoomsNotApplicable({ propertyId }: { propertyId: string }) {
  return (
    <div className="mx-auto max-w-3xl mt-8 rounded-lg bg-white p-8 shadow text-center">
      <h1 className="text-2xl font-bold text-gray-900">Rooms are not applicable for Entry Villa</h1>
      <p className="mt-3 text-gray-600">
        An Entry Villa is booked as a whole. Set its capacity, beds and nightly price in Villa Details instead.
      </p>
      <Link
        href={`/owner/properties/manage?propertyId=${encodeURIComponent(propertyId)}`}
        className="mt-6 inline-block rounded-lg bg-blue-600 px-6 py-2 font-medium text-white hover:bg-blue-700"
      >
        Go to Villa Details
      </Link>
    </div>
  )
}
