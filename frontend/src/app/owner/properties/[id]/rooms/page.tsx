import PropertyRoomsClient from './PropertyRoomsClient'

export function generateStaticParams() { return [{ id: '0' }] }

export default function PropertyRoomsPage({ params }: { params: { id: string } }) {
  return <PropertyRoomsClient propertyId={params.id} />
}