/**
 * Simple layout for static information pages (/about, /contact, /privacy, /terms),
 * using the site's existing container and typography.
 */

export function InfoPage({
  title,
  intro,
  draftNotice,
  children,
}: {
  title: string
  intro?: string
  /** Shown on legal pages whose wording still needs review */
  draftNotice?: string
  children: React.ReactNode
}) {
  return (
    <div className="container py-12">
      <article className="mx-auto max-w-3xl">
        <h1 className="text-4xl font-bold text-gray-900">{title}</h1>
        {intro && <p className="mt-4 text-lg text-gray-600">{intro}</p>}
        {draftNotice && (
          <p className="mt-6 rounded-lg border border-yellow-200 bg-yellow-50 p-4 text-sm text-yellow-900">{draftNotice}</p>
        )}
        <div className="mt-8 space-y-8 text-gray-700 leading-relaxed [&_h2]:text-2xl [&_h2]:font-semibold [&_h2]:text-gray-900 [&_h2]:mb-3 [&_ul]:list-disc [&_ul]:pl-6 [&_ul]:space-y-1 [&_a]:text-primary [&_a]:underline">
          {children}
        </div>
      </article>
    </div>
  )
}
