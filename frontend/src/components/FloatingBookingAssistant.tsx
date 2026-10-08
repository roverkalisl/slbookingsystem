'use client'

import Image from 'next/image'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import {
  ArrowUpRight,
  Heart,
  Home,
  MapPin,
  MessageCircle,
  RotateCw,
  Search,
  Send,
  Star,
  Users,
  Waves,
  Wallet,
  X,
} from 'lucide-react'
import { api } from '@/lib/api'
import type { AssistantBookingContext, AssistantPropertyCard } from '@/types'

type Language = 'en' | 'si'
type ChatMessage = {
  role: 'user' | 'assistant'
  content: string
  properties?: AssistantPropertyCard[]
  bookingContext?: AssistantBookingContext
  showRefinements?: boolean
}
type PendingRequest = {
  message: string
  history: Array<{ role: 'user' | 'assistant'; content: string }>
}
type AssistantStatus = 'ready' | 'online' | 'offline'

const copy = {
  en: {
    title: 'Booking Sri Lanka AI',
    subtitle: 'Your personal Sri Lanka stay assistant',
    ready: 'Ready to help',
    online: 'Online',
    offline: 'Temporarily unavailable',
    welcome: '👋 Ayubowan! Welcome to Booking Sri Lanka 🇱🇰\n\nI can help you find villas, hotels and holiday homes across Sri Lanka.\n\nWhat are you looking for today?',
    placeholder: 'Ask about places to stay...',
    send: 'Send message',
    close: 'Close Booking Sri Lanka AI',
    open: 'Ask Booking Sri Lanka AI',
    retry: 'Try again',
    error: "Sorry, I couldn't complete that search right now. Please try again.",
    offlineMessage: "Sorry, I'm temporarily unavailable. Please try again in a moment.",
    disclaimer: 'Availability and prices are confirmed on the property page before booking.',
    view: 'View Property',
    priceFrom: 'From',
    perNight: '/ night',
    priceUnavailable: 'Price unavailable',
    rating: 'reviews',
    noReviews: 'No reviews yet',
    noPhoto: 'No photo yet',
    rooms: 'rooms',
    bestMatches: 'Showing the best matches',
    viewAll: 'View all properties',
    refine: 'Try widening your search',
    suggestions: [
      { label: '📍 Find a stay', prompt: 'Find a stay anywhere in Sri Lanka', icon: Search },
      { label: '🏖️ Beach stay', prompt: 'Find a beach stay in Sri Lanka', icon: Waves },
      { label: '🏊 Pool villa', prompt: 'Find villas with a pool in Sri Lanka', icon: Home },
      { label: '💰 Budget stays', prompt: 'Find budget-friendly stays in Sri Lanka', icon: Wallet },
      { label: '❤️ Romantic getaway', prompt: 'Find a romantic getaway in Sri Lanka', icon: Heart },
      { label: '👨‍👩‍👧 Family stay', prompt: 'Find a family stay in Sri Lanka', icon: Users },
    ],
    refinements: [
      { label: '📍 Nearby locations', prompt: 'Find stays near my preferred destination in Sri Lanka' },
      { label: '📅 Flexible dates', prompt: "I'm flexible with my dates; help me find a stay" },
      { label: '🏡 Another property type', prompt: 'Suggest another type of accommodation in Sri Lanka' },
      { label: '💰 Broaden my budget', prompt: 'Show me stays across a wider price range in Sri Lanka' },
    ],
    language: 'Language',
  },
  si: {
    title: 'Booking Sri Lanka AI',
    subtitle: 'ශ්‍රී ලංකාවේ ඔබේ පුද්ගලික නවාතැන් සහායක',
    ready: 'උදව් කිරීමට සූදානම්',
    online: 'සබැඳිව',
    offline: 'තාවකාලිකව ලබාගත නොහැක',
    welcome: '👋 ආයුබෝවන්! Booking Sri Lanka වෙත සාදරයෙන් පිළිගනිමු 🇱🇰\n\nශ්‍රී ලංකාව පුරා villa, hotel සහ holiday home හොයාගන්න මට ඔබට උදව් කරන්න පුළුවන්.\n\nඔබ අද සොයන්නේ මොන වගේ නවාතැනක්ද?',
    placeholder: 'නවාතැන් ගැන අහන්න...',
    send: 'පණිවිඩය යවන්න',
    close: 'Booking Sri Lanka AI වසන්න',
    open: 'Booking Sri Lanka AIගෙන් අහන්න',
    retry: 'නැවත උත්සාහ කරන්න',
    error: 'සමාවන්න, මේ මොහොතේ ඔබේ සෙවුම සම්පූර්ණ කළ නොහැක. නැවත උත්සාහ කරන්න.',
    offlineMessage: 'සමාවන්න, මම තාවකාලිකව ලබාගත නොහැක. ටික වේලාවකින් නැවත උත්සාහ කරන්න.',
    disclaimer: 'වෙන්කර ගැනීමට පෙර දේපළ පිටුවේ ලබාගත හැකි බව සහ මිල තහවුරු කරන්න.',
    view: 'දේපළ බලන්න',
    priceFrom: 'සිට',
    perNight: '/ රාත්‍රියකට',
    priceUnavailable: 'මිල ලබාගත නොහැක',
    rating: 'සමාලෝචන',
    noReviews: 'සමාලෝචන තවම නැත',
    noPhoto: 'ඡායාරූපයක් තවම නැත',
    rooms: 'කාමර',
    bestMatches: 'හොඳම ගැළපීම් පෙන්වයි',
    viewAll: 'සියලුම දේපළ බලන්න',
    refine: 'සෙවුම පුළුල් කර බලන්න',
    suggestions: [
      { label: '🏡 නවාතැනක් හොයන්න', prompt: 'ශ්‍රී ලංකාවේ ඕනෑම තැනක නවාතැනක් හොයන්න', icon: Search },
      { label: '🏖️ Beach Stay', prompt: 'ශ්‍රී ලංකාවේ වෙරළබඩ නවාතැනක් හොයන්න', icon: Waves },
      { label: '🏊 Pool Villa', prompt: 'ශ්‍රී ලංකාවේ pool එකක් ඇති villa හොයන්න', icon: Home },
      { label: '💰 අඩු මිලට', prompt: 'ශ්‍රී ලංකාවේ අඩු මිලට නවාතැන් හොයන්න', icon: Wallet },
      { label: '❤️ Couple Stay', prompt: 'ශ්‍රී ලංකාවේ couple getaway එකකට නවාතැනක් හොයන්න', icon: Heart },
      { label: '👨‍👩‍👧 Family Stay', prompt: 'ශ්‍රී ලංකාවේ පවුලකට සුදුසු නවාතැනක් හොයන්න', icon: Users },
    ],
    refinements: [
      { label: '📍 ළඟ තැන්', prompt: 'මගේ කැමති ගමනාන්තය අසල නවාතැන් හොයන්න' },
      { label: '📅 දින නම්‍යශීලීයි', prompt: 'මගේ දින නම්‍යශීලීයි; නවාතැනක් හොයා දෙන්න' },
      { label: '🏡 වෙනත් නවාතැන් වර්ගයක්', prompt: 'ශ්‍රී ලංකාවේ වෙනත් නවාතැන් වර්ගයක් යෝජනා කරන්න' },
      { label: '💰 මිල පරාසය පුළුල් කරන්න', prompt: 'පුළුල් මිල පරාසයක නවාතැන් පෙන්වන්න' },
    ],
    language: 'භාෂාව',
  },
} as const

function propertyHref(propertyId: string, context: AssistantBookingContext): string {
  const params = new URLSearchParams()
  if (context.check_in) params.set('check_in', context.check_in)
  if (context.check_out) params.set('check_out', context.check_out)
  const guests = (context.adults || 0) + (context.children || 0)
  if (guests > 0) params.set('guests', String(guests))
  const query = params.toString()
  return `/property/${encodeURIComponent(propertyId)}${query ? `?${query}` : ''}`
}

function searchHref(context: AssistantBookingContext): string {
  const params = new URLSearchParams()
  if (context.check_in) params.set('check_in', context.check_in)
  if (context.check_out) params.set('check_out', context.check_out)
  const guests = (context.adults || 0) + (context.children || 0)
  if (guests > 0) params.set('guests', String(guests))
  const query = params.toString()
  return `/search${query ? `?${query}` : ''}`
}

function isPropertySearch(message: string): boolean {
  return /\b(find|search|show|looking for|recommend|suggest)\b|හොය|සොය|පෙන්ව/u.test(message)
}

function PropertyResultCard({
  property,
  context,
  text,
  onNavigate,
}: {
  property: AssistantPropertyCard
  context: AssistantBookingContext
  text: (typeof copy)[Language]
  onNavigate: () => void
}) {
  const [imageFailed, setImageFailed] = useState(false)
  const rating = Number(property.average_rating)
  const price = Number(property.min_price)
  const hasPrice = property.min_price !== null && property.min_price !== '' && Number.isFinite(price) && price >= 0
  const hasRating = Number.isFinite(rating) && rating > 0

  return (
    <article className="overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-sm">
      <div className="relative h-36 w-full bg-gray-100">
        {property.cover_photo_url && !imageFailed ? (
          <Image
            src={property.cover_photo_url}
            alt={property.name}
            fill
            unoptimized
            sizes="(max-width: 639px) calc(100vw - 4rem), 380px"
            onError={() => setImageFailed(true)}
            className="object-cover"
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center text-sm text-gray-500">
            {text.noPhoto}
          </div>
        )}
      </div>
      <div className="p-3.5">
        <h3 className="line-clamp-2 text-base font-semibold text-gray-900">{property.name}</h3>
        <p className="mt-1 flex items-center gap-1.5 text-sm text-gray-600">
          <MapPin size={15} aria-hidden="true" className="shrink-0" />
          <span>{[property.city, property.property_type_name].filter(Boolean).join(' · ')}</span>
        </p>
        <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-gray-600">
          {hasRating ? (
            <span className="inline-flex items-center gap-1">
              <Star size={15} aria-hidden="true" className="fill-amber-400 text-amber-500" />
              <span className="font-medium text-gray-800">{rating.toFixed(1)}</span>
              <span>· {property.total_reviews} {text.rating}</span>
            </span>
          ) : (
            <span>{text.noReviews}</span>
          )}
          {property.room_count > 0 && (
            <span>{property.room_count} {text.rooms}</span>
          )}
        </div>
        {property.amenities?.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1.5">
            {property.amenities.slice(0, 3).map((amenity) => (
              <span key={amenity.id} className="rounded-full bg-emerald-50 px-2 py-1 text-xs text-emerald-800">
                {amenity.name}
              </span>
            ))}
          </div>
        )}
        <div className="mt-3 flex items-end justify-between gap-2 border-t border-gray-100 pt-3">
          <div>
            <p className="text-xs text-gray-500">{hasPrice ? text.priceFrom : text.priceUnavailable}</p>
            {hasPrice && (
              <p className="font-semibold text-gray-900">
                LKR {price.toLocaleString()} <span className="text-xs font-normal text-gray-500">{text.perNight}</span>
              </p>
            )}
          </div>
          <Link
            href={propertyHref(property.id, context)}
            onClick={onNavigate}
            className="inline-flex shrink-0 items-center gap-1 rounded-lg bg-primary px-3 py-2 text-sm font-semibold text-white hover:bg-secondary focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
          >
            {text.view}
            <ArrowUpRight size={16} aria-hidden="true" />
          </Link>
        </div>
      </div>
    </article>
  )
}

export function FloatingBookingAssistant() {
  const pathname = usePathname()
  const [open, setOpen] = useState(false)
  const [language, setLanguage] = useState<Language>('en')
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [error, setError] = useState(false)
  const [status, setStatus] = useState<AssistantStatus>('ready')
  const endRef = useRef<HTMLDivElement>(null)
  const requestRef = useRef<PendingRequest | null>(null)
  const text = copy[language]

  useEffect(() => {
    endRef.current?.scrollIntoView({ block: 'end', behavior: 'smooth' })
  }, [messages, error, open, sending])

  if (pathname?.startsWith('/admin') || pathname?.startsWith('/owner')) return null

  async function submit(message: string, retry = false) {
    const trimmed = message.trim()
    if (!trimmed || sending) return
    const history = retry && requestRef.current
      ? requestRef.current.history
      : messages.map(({ role, content }) => ({ role, content })).slice(-8)
    if (!retry) {
      requestRef.current = { message: trimmed, history }
      setMessages((current) => [...current, { role: 'user', content: trimmed }])
    }
    setInput('')
    setSending(true)
    setError(false)
    setStatus('ready')
    try {
      const response = await api.sendAssistantMessage(trimmed, language, history)
      const properties = response.properties || []
      setStatus('online')
      setMessages((current) => [
        ...current,
        {
          role: 'assistant',
          content: response.reply,
          properties,
          bookingContext: response.booking_context || {},
          showRefinements: properties.length === 0 && isPropertySearch(trimmed),
        },
      ])
    } catch {
      setStatus('offline')
      setError(true)
    } finally {
      setSending(false)
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    void submit(input)
  }

  const statusLabel = status === 'online' ? text.online : status === 'offline' ? text.offline : text.ready

  return (
    <div className="fixed bottom-4 right-4 z-[60] sm:bottom-6 sm:right-6">
      {open && (
        <section
          id="booking-assistant-panel"
          aria-label={text.title}
          aria-labelledby="booking-assistant-title"
          aria-modal="false"
          role="dialog"
          className="mb-3 flex h-[min(74dvh,680px)] max-h-[calc(100dvh-2rem)] w-[calc(100vw-2rem)] max-w-[420px] flex-col overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-2xl sm:w-[410px]"
        >
          <header className="flex shrink-0 items-center justify-between gap-3 bg-primary px-4 py-3 text-white">
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <span aria-hidden="true" className="text-xl">🏡</span>
                <h2 id="booking-assistant-title" className="truncate font-semibold">{text.title}</h2>
              </div>
              <p className="mt-0.5 text-xs text-blue-100">{text.subtitle}</p>
              <p className="mt-1 inline-flex items-center gap-1.5 text-xs text-blue-100" aria-live="polite">
                <span
                  aria-hidden="true"
                  className={`h-2 w-2 rounded-full ${
                    status === 'offline' ? 'bg-amber-300' : status === 'online' ? 'bg-emerald-300' : 'bg-blue-200'
                  }`}
                />
                {statusLabel}
              </p>
            </div>
            <div className="flex shrink-0 items-center gap-1.5">
              <label className="sr-only" htmlFor="assistant-language">{text.language}</label>
              <select
                id="assistant-language"
                value={language}
                onChange={(event) => setLanguage(event.target.value === 'si' ? 'si' : 'en')}
                className="rounded-md border border-white/40 bg-white/10 px-2 py-1 text-sm text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white"
              >
                <option className="text-gray-900" value="en">EN</option>
                <option className="text-gray-900" value="si">සිං</option>
              </select>
              <button
                type="button"
                aria-label={text.close}
                onClick={() => setOpen(false)}
                className="rounded-full p-2 hover:bg-white/15 focus-visible:outline focus-visible:outline-2 focus-visible:outline-white"
              >
                <X size={19} aria-hidden="true" />
              </button>
            </div>
          </header>

          <div
            className="flex-1 space-y-4 overflow-y-auto bg-slate-50 p-3.5 sm:p-4"
            aria-live="polite"
            role="log"
            aria-relevant="additions"
          >
            {messages.length === 0 && (
              <div>
                <p className="max-w-[96%] whitespace-pre-line rounded-2xl rounded-tl-sm border border-gray-100 bg-white p-3.5 text-sm leading-6 text-gray-800 shadow-sm">
                  {text.welcome}
                </p>
                <div className="mt-4 grid grid-cols-2 gap-2">
                  {text.suggestions.map(({ label, prompt, icon: Icon }) => (
                    <button
                      key={label}
                      type="button"
                      disabled={sending}
                      onClick={() => void submit(prompt)}
                      className="flex min-h-11 items-center gap-2 rounded-xl border border-gray-200 bg-white px-2.5 py-2 text-left text-xs font-medium text-gray-700 shadow-sm hover:border-primary/40 hover:bg-blue-50 hover:text-primary focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-primary disabled:opacity-50"
                    >
                      <Icon size={16} aria-hidden="true" className="shrink-0 text-primary" />
                      <span>{label}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((message, index) => (
              <div
                key={`${message.role}-${index}`}
                className={message.role === 'user' ? 'flex justify-end' : 'flex items-start gap-2'}
              >
                {message.role === 'assistant' && (
                  <span aria-hidden="true" className="mt-1 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-blue-100 text-xs font-semibold text-primary">
                    B
                  </span>
                )}
                <div className={`min-w-0 ${message.role === 'user' ? 'max-w-[88%]' : 'max-w-[calc(100%-2.25rem)]'}`}>
                  <p
                    dir="auto"
                    className={`whitespace-pre-wrap break-words rounded-2xl p-3 text-sm leading-6 ${
                      message.role === 'user'
                        ? 'rounded-tr-sm bg-primary text-white'
                        : 'rounded-tl-sm border border-gray-100 bg-white text-gray-800 shadow-sm'
                    }`}
                  >
                    {message.content}
                  </p>
                  {message.properties && message.properties.length > 0 && (
                    <div className="mt-2.5 space-y-2.5">
                      {message.properties.slice(0, 5).map((property) => (
                        <PropertyResultCard
                          key={property.id}
                          property={property}
                          context={message.bookingContext || {}}
                          text={text}
                          onNavigate={() => setOpen(false)}
                        />
                      ))}
                      {message.properties.length > 5 && (
                        <div className="flex flex-wrap items-center justify-between gap-2 px-1">
                          <span className="text-xs text-gray-600">{text.bestMatches}</span>
                          <Link
                            href={searchHref(message.bookingContext || {})}
                            onClick={() => setOpen(false)}
                            className="inline-flex items-center gap-1 text-xs font-semibold text-primary hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
                          >
                            {text.viewAll}
                            <ArrowUpRight size={14} aria-hidden="true" />
                          </Link>
                        </div>
                      )}
                    </div>
                  )}
                  {message.showRefinements && (
                    <div className="mt-3 rounded-xl border border-blue-100 bg-blue-50/70 p-3">
                      <p className="mb-2 text-xs font-semibold text-gray-700">{text.refine}</p>
                      <div className="flex flex-wrap gap-2">
                        {text.refinements.map(({ label, prompt }) => (
                          <button
                            key={label}
                            type="button"
                            disabled={sending}
                            onClick={() => void submit(prompt)}
                            className="rounded-full border border-blue-200 bg-white px-2.5 py-1.5 text-left text-xs text-primary hover:bg-blue-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-primary disabled:opacity-50"
                          >
                            {label}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ))}

            {sending && (
              <div className="flex items-center gap-2" role="status" aria-label={language === 'si' ? 'පිළිතුරක් සකස් කරමින්' : 'Preparing a response'}>
                <span aria-hidden="true" className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-blue-100 text-xs font-semibold text-primary">B</span>
                <div className="flex items-center gap-1 rounded-2xl rounded-tl-sm border border-gray-100 bg-white px-3.5 py-3 shadow-sm">
                  <span className="sr-only">{language === 'si' ? 'සිතමින්…' : 'Thinking…'}</span>
                  <span aria-hidden="true" className="h-1.5 w-1.5 animate-pulse rounded-full bg-primary motion-reduce:animate-none" />
                  <span aria-hidden="true" className="h-1.5 w-1.5 animate-pulse rounded-full bg-primary [animation-delay:150ms] motion-reduce:animate-none" />
                  <span aria-hidden="true" className="h-1.5 w-1.5 animate-pulse rounded-full bg-primary [animation-delay:300ms] motion-reduce:animate-none" />
                </div>
              </div>
            )}
            <div ref={endRef} />
          </div>

          <p className="shrink-0 border-t border-gray-100 bg-white px-3 py-2 text-center text-xs leading-5 text-gray-500">
            {text.disclaimer}
          </p>
          {error && (
            <div role="alert" className="flex shrink-0 items-center justify-between gap-2 border-t border-amber-100 bg-amber-50 px-3 py-2 text-sm text-amber-900">
              <span>{status === 'offline' ? text.offlineMessage : text.error}</span>
              <button
                type="button"
                disabled={sending}
                onClick={() => requestRef.current && void submit(requestRef.current.message, true)}
                className="inline-flex shrink-0 items-center gap-1 rounded-md px-2 py-1 font-semibold text-primary hover:bg-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary disabled:opacity-50"
              >
                <RotateCw size={14} aria-hidden="true" />
                {text.retry}
              </button>
            </div>
          )}
          <form onSubmit={handleSubmit} className="flex shrink-0 items-end gap-2 border-t border-gray-200 bg-white p-3">
            <label className="sr-only" htmlFor="assistant-message">{text.placeholder}</label>
            <textarea
              id="assistant-message"
              dir="auto"
              rows={2}
              maxLength={1200}
              value={input}
              onChange={(event) => setInput(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === 'Enter' && !event.shiftKey) {
                  event.preventDefault()
                  event.currentTarget.form?.requestSubmit()
                }
              }}
              placeholder={text.placeholder}
              className="max-h-28 min-h-11 flex-1 resize-y rounded-xl border-gray-300 px-3 py-2 text-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary"
            />
            <button
              type="submit"
              aria-label={text.send}
              disabled={sending || !input.trim()}
              className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-primary text-white hover:bg-secondary focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary disabled:cursor-not-allowed disabled:opacity-50"
            >
              <Send size={18} aria-hidden="true" />
            </button>
          </form>
        </section>
      )}

      <button
        type="button"
        aria-label={open ? text.close : text.open}
        aria-expanded={open}
        aria-controls={open ? 'booking-assistant-panel' : undefined}
        onClick={() => setOpen((current) => !current)}
        className="ml-auto flex h-14 w-14 items-center justify-center rounded-full bg-primary text-white shadow-lg ring-2 ring-white hover:bg-secondary focus-visible:outline focus-visible:ring-4 focus-visible:ring-blue-300 sm:h-auto sm:w-auto sm:gap-2 sm:px-5 sm:py-3"
      >
        {open ? <X size={22} aria-hidden="true" /> : <MessageCircle size={22} aria-hidden="true" />}
        <span className="sr-only sm:not-sr-only">Ask Booking Sri Lanka AI</span>
      </button>
    </div>
  )
}
