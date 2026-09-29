import Link from 'next/link'
import { InfoPage } from '@/components/InfoPage'
import { pageMetadata } from '@/lib/seo'

export const metadata = pageMetadata({
  title: 'Terms of Service',
  description: 'The terms for using SL Booking to find, book and list accommodation in Sri Lanka.',
  path: '/terms',
})

// LEGAL REVIEW: these terms describe how the platform currently works. They have not been
// reviewed by a lawyer - in particular liability, cancellation/refund rules, commission and
// governing law must be confirmed before relying on them. Remove the draft notice afterwards.
export default function TermsPage() {
  return (
    <InfoPage
      title="Terms of Service"
      intro="These terms apply when you use SL Booking to search, book or list accommodation."
      draftNotice="These terms are being reviewed and may be updated. If you have questions, please see our Contact page."
    >
      <section>
        <h2>Our service</h2>
        <p>
          SL Booking is an online marketplace that connects guests with accommodation providers in Sri Lanka. The
          properties are owned and operated by their owners, not by SL Booking. Each owner is responsible for their
          property, its description and photos, its prices and availability, and the stay itself.
        </p>
      </section>
      <section>
        <h2>Accounts</h2>
        <ul>
          <li>You must give accurate information and keep your login details secure.</li>
          <li>You are responsible for activity on your account.</li>
        </ul>
      </section>
      <section>
        <h2>Bookings</h2>
        <ul>
          <li>Prices are shown in Sri Lankan Rupees (LKR). The total for your booking is shown before you book.</li>
          <li>A booking request is pending until the property confirms it. You can follow its status in My Bookings.</li>
          <li>Payment options and any cancellation or refund terms that apply are shown with your booking.</li>
        </ul>
      </section>
      <section>
        <h2>Property owners</h2>
        <ul>
          <li>Listings must be accurate and kept up to date, including photos, amenities, prices and availability.</li>
          <li>Owners must have the right to offer the property and must honour confirmed bookings.</li>
          <li>SL Booking reviews listings before publishing them and may decline, suspend or remove a listing.</li>
        </ul>
      </section>
      <section>
        <h2>Reviews</h2>
        <p>
          Guests can review a stay after a confirmed booking. Reviews must be honest and relevant. SL Booking may hide
          reviews that break these rules.
        </p>
      </section>
      <section>
        <h2>Acceptable use</h2>
        <p>
          Do not misuse the site - for example by giving false information, interfering with its security or operation,
          or using it for anything unlawful.
        </p>
      </section>
      <section>
        <h2>Questions and changes</h2>
        <p>
          We may update these terms from time to time; the current version is always on this page. For questions, see
          our <Link href="/contact">Contact page</Link>. Our <Link href="/privacy">Privacy Policy</Link> explains how we
          handle personal information.
        </p>
      </section>
    </InfoPage>
  )
}
