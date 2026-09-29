/**
 * SL Booking Partner Network - owner dashboard section listing trusted local
 * service partners, rendered from the static PARTNERS configuration.
 */

import { Camera, Facebook, MessageCircle, Phone, Megaphone, Trees } from 'lucide-react'
import { PARTNERS, PARTNER_WHATSAPP_MESSAGE, partnerFacebookLink, type Partner, type PartnerIcon } from '@/lib/partnerNetwork'
import { callLink, whatsappLink } from '@/lib/whatsapp'

const ICONS: Record<PartnerIcon, { icon: typeof Camera; color: string }> = {
  camera: { icon: Camera, color: '#3B82F6' },
  garden: { icon: Trees, color: '#10B981' },
  social: { icon: Megaphone, color: '#8B5CF6' },
}

export function PartnerCard({ partner }: { partner: Partner }) {
  const { icon: Icon, color } = ICONS[partner.icon]
  const wa = whatsappLink(partner.whatsapp, PARTNER_WHATSAPP_MESSAGE)
  const tel = callLink(partner.phone)
  const facebook = partnerFacebookLink(partner)

  return (
    <div className="bg-white rounded-lg shadow p-6 flex flex-col min-w-0" data-partner-id={partner.id}>
      <div className="flex items-start gap-3">
        <div className="p-3 rounded-lg flex-shrink-0" style={{ backgroundColor: `${color}15` }}>
          <Icon className="w-6 h-6" style={{ color }} aria-hidden="true" />
        </div>
        <div className="min-w-0">
          <h3 className="font-semibold text-gray-900 break-words">{partner.name}</h3>
          <p className="text-sm text-gray-600 mt-1">{partner.category}</p>
        </div>
      </div>

      <p className="text-sm text-gray-700 mt-4">{partner.description}</p>

      <ul className="mt-4 space-y-1 text-sm text-gray-600 list-disc list-inside">
        {partner.services.map((service) => (
          <li key={service}>{service}</li>
        ))}
      </ul>

      <div className="mt-auto pt-4">
        <p className="text-sm text-gray-600">
          Phone: <span className="font-medium text-gray-900">{partner.phone}</span>
        </p>
        {!facebook && partner.facebookPageName && (
          <p className="text-sm text-gray-600 mt-1">
            Facebook: <span className="text-gray-900">{partner.facebookPageName}</span>
          </p>
        )}

        <div className="mt-4 flex flex-wrap gap-2 border-t pt-4">
          {wa && (
            <a
              href={wa}
              target="_blank"
              rel="noopener noreferrer"
              aria-label={`WhatsApp ${partner.name}`}
              className="inline-flex items-center gap-1 px-4 py-2 bg-green-50 text-green-700 rounded-lg text-sm font-medium hover:bg-green-100"
            >
              <MessageCircle className="w-4 h-4" aria-hidden="true" />
              WhatsApp
            </a>
          )}
          {tel && (
            <a
              href={tel}
              aria-label={`Call ${partner.name}`}
              className="inline-flex items-center gap-1 px-4 py-2 bg-blue-50 text-blue-700 rounded-lg text-sm font-medium hover:bg-blue-100"
            >
              <Phone className="w-4 h-4" aria-hidden="true" />
              Call
            </a>
          )}
          {facebook && (
            <a
              href={facebook}
              target="_blank"
              rel="noopener noreferrer"
              aria-label={`${partner.name} on Facebook`}
              className="inline-flex items-center gap-1 px-4 py-2 bg-gray-50 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-100"
            >
              <Facebook className="w-4 h-4" aria-hidden="true" />
              Facebook
            </a>
          )}
        </div>
      </div>
    </div>
  )
}

export default function PartnerNetwork({ partners = PARTNERS }: { partners?: Partner[] }) {
  if (partners.length === 0) return null

  return (
    <section className="mt-8" aria-labelledby="partner-network-heading">
      <div className="mb-4">
        <h2 id="partner-network-heading" className="text-xl font-bold">
          SL Booking Partner Network
        </h2>
        <p className="text-gray-900 font-medium mt-1">
          Professional support for your property — from trusted local partners.
        </p>
        <p className="text-sm text-gray-600 mt-1">
          SL Booking works with a network of local professionals who can help property owners with Photography,
          Landscaping, Garden Maintenance and Social Media Promotion.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {partners.map((partner) => (
          <PartnerCard key={partner.id} partner={partner} />
        ))}
      </div>

      <p className="text-xs text-gray-500 mt-4">
        Partner services are provided directly by the respective service providers. SL Booking helps connect property
        owners with these local professional partners.
      </p>
    </section>
  )
}
