import PropertyManagementClient from './PropertyManagementClient'

export function generateStaticParams() {
  return [{ id: '0' }]
}

export default function OwnerPropertyDetail({ params }: { params: { id: string } }) {
  return <PropertyManagementClient propertyId={params.id} />
}
