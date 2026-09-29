import Link from 'next/link'
import { InfoPage } from '@/components/InfoPage'
import { pageMetadata } from '@/lib/seo'

export const metadata = pageMetadata({
  title: 'Contact',
  description: 'How to contact SL Booking and the properties listed on SL Booking.',
  path: '/contact',
})

// Official SL Booking support address. NEXT_PUBLIC_SUPPORT_EMAIL (Render, read at build
// time) can override it; the official address is the default so it is always shown.
const OFFICIAL_SUPPORT_EMAIL = 'roverkalisl@gmail.com'
const configuredEmail = (process.env.NEXT_PUBLIC_SUPPORT_EMAIL || '').trim()
const SUPPORT_EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(configuredEmail) ? configuredEmail : OFFICIAL_SUPPORT_EMAIL

export default function ContactPage() {
  return (
    <InfoPage title="Contact Us" intro="We are happy to help. Choose the option that fits your question.">
      <section>
        <h2>SL Booking support</h2>
        <p>
          The official SL Booking contact and support email is{' '}
          <a href={`mailto:${SUPPORT_EMAIL}`}>{SUPPORT_EMAIL}</a>.
        </p>
      </section>
      <section>
        <h2>Questions about a property or a stay</h2>
        <p>
          Each property manages its own rooms, prices and availability. Use the contact options on the property's page
          (for example WhatsApp or email) to ask the property directly.
        </p>
      </section>
      <section>
        <h2>Your bookings</h2>
        <p>
          Signed-in guests can see the status of every booking in <Link href="/bookings">My Bookings</Link>, and contact
          the property from there.
        </p>
      </section>
      <section>
        <h2>Listing your property</h2>
        <p>
          <Link href="/register">Create a property owner account</Link> to add your property. Listings are reviewed by
          the SL Booking team before they are published.
        </p>
      </section>
    </InfoPage>
  )
}
