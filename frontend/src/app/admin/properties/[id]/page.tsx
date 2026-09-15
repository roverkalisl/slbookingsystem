import AdminPropertyDetailClient from './admin-property-detail-client'

export async function generateStaticParams() {
  return [{ id: '0' }]
}

export default function AdminPropertyDetailPage({ params }: { params: { id: string } }) {
  return <AdminPropertyDetailClient propertyId={params.id} />
}
