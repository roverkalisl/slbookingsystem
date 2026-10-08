'use client'

import Link from 'next/link'
import Image from 'next/image'
import { usePathname } from 'next/navigation'
import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { MessageCircle, RotateCw, Send, X } from 'lucide-react'
import { api } from '@/lib/api'
import type { AssistantBookingContext, AssistantPropertyCard } from '@/types'

type Language = 'en' | 'si'
type ChatMessage = {
  role: 'user' | 'assistant'
  content: string
  properties?: AssistantPropertyCard[]
  bookingContext?: AssistantBookingContext
}
type PendingRequest = {
  message: string
  history: Array<{ role: 'user' | 'assistant'; content: string }>
}

const copy = {
  en: {
    title: 'Booking assistant',
    subtitle: 'Find your stay in Sri Lanka',
    welcome: 'Hi! I can help you find a place to stay, compare rooms, and check dates. What are you looking for?',
    placeholder: 'Ask about places to stay…',
    send: 'Send message',
    close: 'Close assistant',
    open: 'Open booking assistant',
    retry: 'Try again',
    error: 'The assistant could not respond just now. Please try again.',
    disclaimer: 'Availability and prices are confirmed on the property page before booking.',
    view: 'View and book',
    perNight: 'from / night',
    priceUnavailable: 'Price unavailable',
    rating: 'reviews',
    suggestions: ['Find a stay in Galle', 'Show beach stays in Mirissa'],
    language: 'Language',
  },
  si: {
    title: 'වෙන්කිරීමේ සහායක',
    subtitle: 'ශ්‍රී ලංකාවේ නවාතැනක් සොයන්න',
    welcome: 'ආයුබෝවන්! නවාතැනක් සොයා ගැනීමට, කාමර සසඳා බැලීමට සහ දින පරීක්ෂා කිරීමට මට උදව් කළ හැකියි. ඔබ සොයන්නේ කුමක්ද?',
    placeholder: 'නවාතැන් ගැන විමසන්න…',
    send: 'පණිවිඩය යවන්න',
    close: 'සහායක වසන්න',
    open: 'වෙන්කිරීමේ සහායක විවෘත කරන්න',
    retry: 'නැවත උත්සාහ කරන්න',
    error: 'සහායකගෙන් මේ මොහොතේ පිළිතුරක් ලබාගත නොහැකි විය. නැවත උත්සාහ කරන්න.',
    disclaimer: 'වෙන්කර ගැනීමට පෙර දේපළ පිටුවේ ලබාගත හැකි බව සහ මිල තහවුරු කරන්න.',
    view: 'බලා වෙන්කරන්න',
    perNight: 'සිට / රාත්‍රියකට',
    priceUnavailable: 'මිල ලබාගත නොහැක',
    rating: 'සමාලෝචන',
    suggestions: ['ගාල්ලේ නවාතැනක් සොයන්න', 'මිරිස්සේ වෙරළබඩ නවාතැන් පෙන්වන්න'],
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

export function FloatingBookingAssistant() {
  const pathname = usePathname()
  const [open, setOpen] = useState(false)
  const [language, setLanguage] = useState<Language>('en')
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [error, setError] = useState(false)
  const [bookingContext, setBookingContext] = useState<AssistantBookingContext>({})
  const endRef = useRef<HTMLDivElement>(null)
  const requestRef = useRef<PendingRequest | null>(null)
  const text = copy[language]

  useEffect(() => {
    endRef.current?.scrollIntoView({ block: 'end', behavior: 'smooth' })
  }, [messages, error, open])

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
    try {
      const response = await api.sendAssistantMessage(trimmed, language, history)
      setBookingContext(response.booking_context || {})
      setMessages((current) => [
        ...current,
        {
          role: 'assistant',
          content: response.reply,
          properties: response.properties || [],
          bookingContext: response.booking_context || {},
        },
      ])
    } catch {
      setError(true)
    } finally {
      setSending(false)
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    void submit(input)
  }

  return (
    <div className="fixed bottom-4 right-4 z-[60] sm:bottom-6 sm:right-6">
      {open && (
        <section
          aria-label={text.title}
          aria-modal="false"
          role="dialog"
          className="mb-3 flex h-[min(74dvh,680px)] w-[calc(100vw-2rem)] flex-col overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-2xl sm:w-[410px]"
        >
          <header className="flex items-center justify-between bg-primary px-4 py-3 text-white">
            <div>
              <h2 className="font-semibold">{text.title}</h2>
              <p className="text-xs text-blue-100">{text.subtitle}</p>
            </div>
            <div className="flex items-center gap-2">
              <label className="sr-only" htmlFor="assistant-language">{text.language}</label>
              <select
                id="assistant-language"
                value={language}
                onChange={(event) => setLanguage(event.target.value === 'si' ? 'si' : 'en')}
                className="rounded-md border border-white/40 bg-white/10 px-2 py-1 text-sm text-white focus:ring-white"
              >
                <option className="text-gray-900" value="en">EN</option>
                <option className="text-gray-900" value="si">සිංහල</option>
              </select>
              <button
                type="button"
                aria-label={text.close}
                onClick={() => setOpen(false)}
                className="rounded-full p-2 hover:bg-white/15"
              >
                <X size={19} aria-hidden="true" />
              </button>
            </div>
          </header>

          <div className="flex-1 space-y-3 overflow-y-auto bg-gray-50 p-3" aria-live="polite" role="log">
            {messages.length === 0 && (
              <div>
                <p className="max-w-[90%] rounded-2xl rounded-tl-sm bg-white p-3 text-sm leading-6 text-gray-800 shadow-sm">
                  {text.welcome}
                </p>
                <div className="mt-3 flex flex-wrap gap-2">
                  {text.suggestions.map((suggestion) => (
                    <button
                      key={suggestion}
                      type="button"
                      disabled={sending}
                      onClick={() => void submit(suggestion)}
                      className="rounded-full border border-primary/30 bg-white px-3 py-2 text-left text-xs text-primary hover:bg-blue-50 disabled:opacity-50"
                    >
                      {suggestion}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((message, index) => (
              <div
                key={`${message.role}-${index}`}
                className={message.role === 'user' ? 'flex justify-end' : ''}
              >
                <p
                  dir="auto"
                  className={`max-w-[90%] whitespace-pre-wrap rounded-2xl p-3 text-sm leading-6 ${
                    message.role === 'user'
                      ? 'rounded-tr-sm bg-primary text-white'
                      : 'rounded-tl-sm bg-white text-gray-800 shadow-sm'
                  }`}
                >
                  {message.content}
                </p>
                {message.properties && message.properties.length > 0 && (
                  <div className="mt-2 space-y-2">
                    {message.properties.map((property) => (
                      <article key={property.id} className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
                        {property.cover_photo_url && (
                          <div className="relative h-32 w-full bg-gray-100">
                            <Image
                              src={property.cover_photo_url}
                              alt=""
                              fill
                              unoptimized
                              sizes="410px"
                              className="object-cover"
                            />
                          </div>
                        )}
                        <div className="p-3">
                          <h3 className="font-semibold text-gray-900">{property.name}</h3>
                          <p className="text-sm text-gray-600">
                            {[property.property_type_name, property.city].filter(Boolean).join(' · ')}
                          </p>
                          <div className="mt-2 flex items-center justify-between gap-2 text-sm">
                            <span className="text-gray-700">
                              {property.min_price
                                ? `LKR ${Number(property.min_price).toLocaleString()} ${text.perNight}`
                                : text.priceUnavailable}
                            </span>
                            {Number(property.average_rating) > 0 && (
                              <span className="shrink-0 text-gray-600">
                                ★ {Number(property.average_rating).toFixed(1)} ({property.total_reviews} {text.rating})
                              </span>
                            )}
                          </div>
                          <Link
                            href={propertyHref(property.id, message.bookingContext || bookingContext)}
                            onClick={() => setOpen(false)}
                            className="mt-3 inline-flex w-full justify-center rounded-lg bg-primary px-3 py-2 text-sm font-medium text-white hover:bg-secondary"
                          >
                            {text.view}
                          </Link>
                        </div>
                      </article>
                    ))}
                  </div>
                )}
              </div>
            ))}

            {sending && (
              <p className="w-fit rounded-2xl bg-white px-3 py-2 text-sm text-gray-500 shadow-sm">
                {language === 'si' ? 'සිතමින්…' : 'Thinking…'}
              </p>
            )}
            <div ref={endRef} />
          </div>

          <p className="border-t border-gray-100 px-3 py-2 text-center text-xs text-gray-500">
            {text.disclaimer}
          </p>
          {error && (
            <div role="alert" className="flex items-center justify-between gap-2 px-3 pb-2 text-sm text-red-700">
              <span>{text.error}</span>
              <button
                type="button"
                disabled={sending}
                onClick={() => requestRef.current && void submit(requestRef.current.message, true)}
                className="inline-flex shrink-0 items-center gap-1 rounded-md px-2 py-1 font-medium hover:bg-red-50 disabled:opacity-50"
              >
                <RotateCw size={14} aria-hidden="true" />
                {text.retry}
              </button>
            </div>
          )}
          <form onSubmit={handleSubmit} className="flex items-end gap-2 border-t border-gray-200 bg-white p-3">
            <label className="sr-only" htmlFor="assistant-message">{text.placeholder}</label>
            <textarea
              id="assistant-message"
              dir="auto"
              rows={1}
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
              className="max-h-28 min-h-11 flex-1 resize-y rounded-xl border-gray-300 px-3 py-2 text-sm focus:ring-primary"
            />
            <button
              type="submit"
              aria-label={text.send}
              disabled={sending || !input.trim()}
              className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-primary text-white hover:bg-secondary disabled:cursor-not-allowed disabled:opacity-50"
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
        onClick={() => setOpen((current) => !current)}
        className="ml-auto flex h-14 w-14 items-center justify-center rounded-full bg-primary text-white shadow-lg ring-2 ring-white hover:bg-secondary focus:outline-none focus:ring-4 focus:ring-blue-300"
      >
        {open ? <X size={23} aria-hidden="true" /> : <MessageCircle size={24} aria-hidden="true" />}
      </button>
    </div>
  )
}
