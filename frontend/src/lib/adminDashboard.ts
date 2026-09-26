/**
 * Super Admin dashboard statistics: API response -> display values.
 *
 * A failed or malformed GET /api/admin/stats/dashboard/ must NEVER be shown
 * as a valid platform with zero users/properties/bookings - it becomes an
 * error the page displays instead. (Production once showed all zeros because
 * the endpoint returned HTTP 500 and the page silently fell back to 0.)
 *
 * No path aliases / TS-only syntax so `node --test` can run the unit tests
 * (tests/adminDashboard.test.mjs).
 */

export interface MostViewedProperty {
  id: string
  name: string
  city: string
  view_count: number
}

export interface DashboardStats {
  totalUsers: number
  totalOwners: number
  totalProperties: number
  pendingProperties: number
  approvedProperties: number
  totalBookings: number
  activeBookings: number
  /** null when the backend could not calculate revenue */
  platformRevenue: number | null
  averageRating: number
  totalPropertyViews: number
  propertyViewsToday: number
  propertyViewsThisMonth: number
  mostViewedProperties: MostViewedProperty[]
}

export type DashboardLoadResult =
  | { stats: DashboardStats; error: null }
  | { stats: null; error: string }

// Counters every valid stats response contains (AdminDashboardStatsSerializer)
const REQUIRED_COUNTERS = [
  'total_users', 'total_owners', 'total_properties', 'pending_properties',
  'approved_properties', 'total_bookings', 'confirmed_bookings',
]

function count(value: unknown): number | null {
  const number = typeof value === 'string' ? Number(value) : value
  return typeof number === 'number' && Number.isFinite(number) && number >= 0 ? number : null
}

/** Validate and map the API payload; throws when it is not a real stats response. */
export function toDashboardStats(data: unknown): DashboardStats {
  if (!data || typeof data !== 'object') throw new Error('The statistics response was empty.')
  const raw = data as Record<string, unknown>
  const missing = REQUIRED_COUNTERS.filter((key) => count(raw[key]) === null)
  if (missing.length > 0) throw new Error(`The statistics response is missing: ${missing.join(', ')}.`)

  const optional = (key: string) => count(raw[key]) ?? 0 // view stats: absent on older backends
  const revenue = raw.platform_revenue === null || raw.platform_revenue === undefined ? null : count(raw.platform_revenue)
  const mostViewed = Array.isArray(raw.most_viewed_properties) ? raw.most_viewed_properties : []

  return {
    totalUsers: count(raw.total_users)!,
    totalOwners: count(raw.total_owners)!,
    totalProperties: count(raw.total_properties)!,
    pendingProperties: count(raw.pending_properties)!,
    approvedProperties: count(raw.approved_properties)!,
    totalBookings: count(raw.total_bookings)!,
    activeBookings: count(raw.confirmed_bookings)!,
    platformRevenue: revenue,
    averageRating: count(raw.average_rating) ?? 0,
    totalPropertyViews: optional('total_property_views'),
    propertyViewsToday: optional('property_views_today'),
    propertyViewsThisMonth: optional('property_views_this_month'),
    mostViewedProperties: mostViewed.filter(
      (row): row is MostViewedProperty => !!row && typeof row === 'object' && typeof (row as MostViewedProperty).id === 'string'
    ),
  }
}

/** Human-readable reason a stats request failed (no tokens or payload details). */
export function dashboardErrorMessage(error: unknown): string {
  const err = error as { response?: { status?: number }; message?: string } | null
  const status = err?.response?.status
  if (status === 401) return 'Your session has expired. Please log in again.'
  if (status === 403) return 'Your account does not have permission to view platform statistics.'
  if (status && status >= 500) return `The server could not load the dashboard statistics (HTTP ${status}). Please try again shortly.`
  if (status) return `The dashboard statistics could not be loaded (HTTP ${status}).`
  if (err?.message && /response/i.test(err.message)) return err.message
  return 'The dashboard statistics could not be loaded. Check your connection and try again.'
}

/** Load statistics: real numbers on success, an error (never zeros) on failure. */
export async function loadDashboardStats(fetchStats: () => Promise<unknown>): Promise<DashboardLoadResult> {
  try {
    return { stats: toDashboardStats(await fetchStats()), error: null }
  } catch (error) {
    return { stats: null, error: dashboardErrorMessage(error) }
  }
}
