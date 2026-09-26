/**
 * Admin dashboard statistics (src/lib/adminDashboard.ts): a failed or
 * malformed stats response must become an ERROR, never zero statistics.
 *
 *   npm run test:unit
 */
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { dashboardErrorMessage, loadDashboardStats, toDashboardStats } from '../src/lib/adminDashboard.ts'

const API_DATA = {
  total_users: 12, total_owners: 3, total_guests: 8, total_properties: 5,
  pending_properties: 1, approved_properties: 4, rejected_properties: 0, suspended_properties: 0,
  total_bookings: 7, pending_bookings: 2, confirmed_bookings: 3, completed_bookings: 1, cancelled_bookings: 1,
  platform_revenue: '45000.00', average_rating: '4.50',
  total_property_views: 20, property_views_today: 2, property_views_this_month: 11,
  most_viewed_properties: [{ id: 'a1', name: 'Villa', city: 'Kandy', view_count: 9 }],
}

const httpError = (status) => Object.assign(new Error(`Request failed with status code ${status}`), { response: { status } })

test('a successful response gives the real statistics', async () => {
  const result = await loadDashboardStats(async () => API_DATA)
  assert.equal(result.error, null)
  assert.deepEqual(result.stats, {
    totalUsers: 12, totalOwners: 3, totalProperties: 5, pendingProperties: 1, approvedProperties: 4,
    totalBookings: 7, activeBookings: 3, platformRevenue: 45000, averageRating: 4.5,
    totalPropertyViews: 20, propertyViewsToday: 2, propertyViewsThisMonth: 11,
    mostViewedProperties: [{ id: 'a1', name: 'Villa', city: 'Kandy', view_count: 9 }],
  })
})

test('an HTTP 500 (the production outage) is an error, not zero statistics', async () => {
  const result = await loadDashboardStats(async () => { throw httpError(500) })
  assert.equal(result.stats, null)
  assert.match(result.error, /HTTP 500/)
})

test('403, 401 and network failures are errors too', async () => {
  for (const [error, pattern] of [[httpError(403), /permission/], [httpError(401), /session/], [new Error('Network Error'), /could not be loaded/]]) {
    const result = await loadDashboardStats(async () => { throw error })
    assert.equal(result.stats, null)
    assert.match(result.error, pattern)
  }
})

test('an empty or malformed body is an error, not zeros', async () => {
  for (const body of [undefined, null, {}, { success: false }, { total_users: 'lots' }, { ...API_DATA, total_properties: undefined }]) {
    const result = await loadDashboardStats(async () => body)
    assert.equal(result.stats, null, JSON.stringify(body))
    assert.ok(result.error)
  }
})

test('genuine zeros from a valid response are kept as zeros', () => {
  const zeros = Object.fromEntries(Object.entries(API_DATA).map(([k, v]) => [k, typeof v === 'number' ? 0 : v]))
  const stats = toDashboardStats({ ...zeros, platform_revenue: '0.00', most_viewed_properties: [] })
  assert.equal(stats.totalUsers, 0)
  assert.equal(stats.platformRevenue, 0)
})

test('revenue the backend could not calculate is shown as unavailable, not 0', () => {
  assert.equal(toDashboardStats({ ...API_DATA, platform_revenue: null }).platformRevenue, null)
})

test('error messages never echo response bodies', () => {
  assert.equal(dashboardErrorMessage(httpError(502)).includes('502'), true)
  assert.equal(dashboardErrorMessage({ response: { status: 500, data: { token: 'eyJ...' } } }).includes('eyJ'), false)
})
