import Link from 'next/link'
import { InfoPage } from '@/components/InfoPage'
import { pageMetadata } from '@/lib/seo'

export const metadata = pageMetadata({
  title: 'About Us',
  description: 'SL Booking is an online marketplace for villas, hotels, guest houses and holiday homes across Sri Lanka.',
  path: '/about',
})

export default function AboutPage() {
  return (
    <InfoPage
      title="About SL Booking"
      intro="SL Booking is an online marketplace for places to stay in Sri Lanka - villas, hotels, guest houses, apartments, holiday homes and more."
    >
      <section>
        <h2>For guests</h2>
        <ul>
          <li>Search properties by destination, dates and number of guests.</li>
          <li>Compare photos, amenities, rooms and nightly prices before you book.</li>
          <li>Send a booking request; the property confirms it, and you can follow its status in My Bookings.</li>
          <li>Contact the property directly using the contact options on its listing.</li>
        </ul>
      </section>
      <section>
        <h2>For property owners</h2>
        <ul>
          <li>List your property with photos, amenities, rooms and prices.</li>
          <li>Manage availability and bookings from the Owner Portal.</li>
          <li>Every listing is reviewed by the SL Booking team before it is published.</li>
        </ul>
        <p className="mt-3">
          Want to list your property? <Link href="/register">Create a property owner account</Link>.
        </p>
      </section>
      <section>
        <h2>Get in touch</h2>
        <p>
          Questions about SL Booking? See our <Link href="/contact">contact page</Link>.
        </p>
      </section>
    </InfoPage>
  )
}
