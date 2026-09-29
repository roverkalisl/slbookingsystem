import Link from 'next/link'
import { InfoPage } from '@/components/InfoPage'
import { pageMetadata } from '@/lib/seo'

export const metadata = pageMetadata({
  title: 'Privacy Policy',
  description: 'How SL Booking collects, uses and protects personal information.',
  path: '/privacy',
})

// LEGAL REVIEW: this policy describes how the platform currently works. It has not been
// reviewed by a lawyer - have it checked (incl. Sri Lanka's Personal Data Protection Act,
// No. 9 of 2022) and remove the draft notice before relying on it.
export default function PrivacyPage() {
  return (
    <InfoPage
      title="Privacy Policy"
      intro="This policy explains what personal information SL Booking collects, why, and who it is shared with."
      draftNotice="This policy is being reviewed and may be updated. If you have questions about your information, please see our Contact page."
    >
      <section>
        <h2>Information we collect</h2>
        <ul>
          <li><strong>Account details</strong> - your name, email address and, if you provide it, your phone number.</li>
          <li><strong>Booking details</strong> - the property, dates, number of guests, guest names and contact details you enter, and any special requests.</li>
          <li><strong>Property listings</strong> - for property owners: property details, photos, prices, availability and the contact details you choose to publish (such as a WhatsApp number or email).</li>
          <li><strong>Reviews</strong> - ratings and comments you submit after a stay.</li>
          <li><strong>Technical information</strong> - such as your browser type and the pages you visit, used to run and improve the site.</li>
        </ul>
      </section>
      <section>
        <h2>Payments</h2>
        <p>
          Online card payments are processed by Stripe on its secure payment page. SL Booking does not receive or store
          your full card number.
        </p>
      </section>
      <section>
        <h2>How we use information</h2>
        <ul>
          <li>To create and manage your account and your bookings.</li>
          <li>To pass booking details to the property you book, so it can confirm and host your stay.</li>
          <li>To send booking-related messages, such as confirmations and cancellations.</li>
          <li>To show property listings, photos and reviews on the site.</li>
          <li>To keep the platform secure and to understand how it is used.</li>
        </ul>
      </section>
      <section>
        <h2>Who we share information with</h2>
        <ul>
          <li><strong>Properties</strong> - when you book, the property receives the booking and guest contact details it needs.</li>
          <li><strong>Service providers</strong> - Stripe (payments), Cloudinary (property photo hosting) and our hosting and email providers, only as needed to run the service.</li>
          <li><strong>Google</strong> - see "Cookies, analytics and advertising" below.</li>
        </ul>
        <p className="mt-3">We do not sell your personal information.</p>
      </section>
      <section>
        <h2>Cookies, analytics and advertising</h2>
        <p>
          SL Booking stores a sign-in token in your browser to keep you logged in. We may use Google Analytics to
          understand how the site is used, and Google AdSense to show advertising on public pages.
        </p>
        <p className="mt-3">
          Third-party vendors, including Google, use cookies to serve ads based on your prior visits to this website or
          other websites. Google's use of advertising cookies enables it and its partners to serve ads to you based on
          your visits to this and/or other sites on the Internet. You can opt out of personalised advertising by visiting{' '}
          <a href="https://adssettings.google.com" rel="nofollow noopener">Google Ads Settings</a>, or opt out of some
          third-party vendors' use of cookies for personalised advertising at{' '}
          <a href="https://www.aboutads.info/choices/" rel="nofollow noopener">www.aboutads.info</a>.
        </p>
      </section>
      <section>
        <h2>Your choices</h2>
        <p>
          You can ask us for a copy of your information, or ask us to correct or delete it, using the details on our{' '}
          <Link href="/contact">Contact page</Link>.
        </p>
      </section>
      <section>
        <h2>Changes to this policy</h2>
        <p>We may update this policy from time to time. The current version is always available on this page.</p>
      </section>
    </InfoPage>
  )
}
