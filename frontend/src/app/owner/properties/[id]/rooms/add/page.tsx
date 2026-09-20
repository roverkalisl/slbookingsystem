import AddRoomClient from './AddRoomClient'

export function generateStaticParams() { return [{ id: '0' }] }

export default function AddRoomPage({ params }: { params: { id: string } }) {
  return <AddRoomClient propertyId={params.id} />
}