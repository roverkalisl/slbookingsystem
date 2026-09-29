/**
 * SL Booking Partner Network - trusted local professionals shown to property
 * owners on the Owner Dashboard. Static configuration for now (no API/model);
 * add a partner by appending to PARTNERS.
 */

export type PartnerIcon = 'camera' | 'garden' | 'social'

export interface Partner {
  id: string
  name: string
  category: string
  description: string
  services: string[]
  icon: PartnerIcon
  /** Phone number exactly as displayed to owners. */
  phone: string
  whatsapp: string
  facebookPageName?: string
  /** Official Facebook page URL. Leave null until the partner provides one - never guess it. */
  facebookUrl: string | null
}

export const PARTNER_WHATSAPP_MESSAGE =
  'Hello, I am a property owner on SL Booking. I would like to know more about your property support services.'

export const PARTNERS: Partner[] = [
  {
    id: 'pristine-moment-photography',
    name: 'Pristine Moment Photography',
    category: 'Property Photography & Visual Content',
    description: 'Professional property photography and visual content for villas, hotels and holiday homes.',
    services: [
      'Villa / Hotel Photography',
      'Interior & Exterior Photography',
      'Pool & Garden Photography',
      'Promotional Property Content',
    ],
    icon: 'camera',
    phone: '077 960 6117',
    whatsapp: '0779606117',
    facebookPageName: 'Pristine Moment Photography',
    facebookUrl: null,
  },
  {
    id: 'southern-garden-design-maintain',
    name: 'Southern Garden Design & Maintain',
    category: 'Garden & Landscape Services',
    description:
      'Garden and landscape support to improve the appearance and outdoor presentation of accommodation properties.',
    services: ['Garden Design', 'Landscape Improvements', 'Garden Maintenance', 'Outdoor Property Presentation'],
    icon: 'garden',
    phone: '+94 77 085 0820',
    whatsapp: '+94770850820',
    facebookPageName: 'Southern Garden Design and Maintain',
    facebookUrl: null,
  },
  {
    id: 'virtue-hub-sri-lanka',
    name: 'Virtue Hub Sri Lanka',
    category: 'Social Media Handling & Promotion',
    description:
      'Social media handling and promotional support to help accommodation properties improve their online visibility.',
    services: [
      'Facebook Page Management',
      'Social Media Content',
      'Promotional Campaigns',
      'Online Property Promotion',
    ],
    icon: 'social',
    phone: '074 094 8966',
    whatsapp: '+94740948966',
    facebookUrl: null,
  },
]

/** Only link to an explicitly configured https Facebook page; anything else gets no button. */
export function partnerFacebookLink(partner: Pick<Partner, 'facebookUrl'>): string | null {
  const url = partner.facebookUrl?.trim()
  return url && /^https:\/\/(www\.|m\.)?facebook\.com\/[^\s"'<>]+$/.test(url) ? url : null
}
