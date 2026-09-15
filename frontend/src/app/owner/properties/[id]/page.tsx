/**
 * Owner Property Detail/Edit - View and manage a specific property
 */

// Required for static export with dynamic routes
export async function generateStaticParams() {
  return [{ id: '0' }]
}

export default function OwnerPropertyDetail({
  params,
}: {
  params: { id: string }
}) {
  const propertyId = params.id

  return (
    <div>
      <h1 className="text-4xl font-bold text-gray-900">Property Details</h1>
      <p className="text-gray-600 mt-2">ID: {propertyId}</p>
      <div className="mt-8 bg-white rounded-lg shadow p-8">
        <p className="text-gray-600 text-center py-12">Property detail view coming soon...</p>
      </div>
    </div>
  )
}
