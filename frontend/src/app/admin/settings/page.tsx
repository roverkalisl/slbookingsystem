/**
 * Admin Settings - System configuration and platform settings
 */

'use client'

import { useState } from 'react'
import {
  Settings,
  Save,
  AlertCircle,
  DollarSign,
  Mail,
  Bell,
  Lock,
  Globe,
} from 'lucide-react'

export default function AdminSettings() {
  const [activeTab, setActiveTab] = useState<'general' | 'payments' | 'email' | 'notifications'>('general')
  const [saved, setSaved] = useState(false)

  const handleSave = () => {
    setSaved(true)
    setTimeout(() => setSaved(false), 3000)
  }

  return (
    <div>
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-4xl font-bold text-gray-900">System Settings</h1>
        <p className="text-gray-600 mt-2">Configure platform settings and integrations</p>
      </div>

      {/* Tabs */}
      <div className="bg-white rounded-lg shadow mb-6 border-b border-gray-200">
        <div className="flex flex-wrap">
          {(
            [
              { id: 'general', label: 'General', icon: Globe },
              { id: 'payments', label: 'Payments', icon: DollarSign },
              { id: 'email', label: 'Email', icon: Mail },
              { id: 'notifications', label: 'Notifications', icon: Bell },
            ] as const
          ).map((tab) => {
            const Icon = tab.icon
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-6 py-4 font-medium transition-colors border-b-2 ${
                  activeTab === tab.id
                    ? 'border-red-600 text-red-600'
                    : 'border-transparent text-gray-600 hover:text-gray-900'
                }`}
              >
                <Icon className="w-4 h-4" />
                {tab.label}
              </button>
            )
          })}
        </div>
      </div>

      {/* Content */}
      <div className="max-w-4xl">
        {/* Success Message */}
        {saved && (
          <div className="mb-6 p-4 bg-green-50 border border-green-200 rounded-lg text-green-800">
            Settings saved successfully!
          </div>
        )}

        {/* General Settings */}
        {activeTab === 'general' && (
          <div className="space-y-6">
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-xl font-bold mb-6 flex items-center gap-2">
                <Globe className="w-5 h-5 text-red-600" />
                General Platform Settings
              </h2>

              <div className="space-y-6">
                <div>
                  <label className="block text-sm font-medium text-gray-900 mb-2">
                    Platform Name
                  </label>
                  <input
                    type="text"
                    defaultValue="SL Booking"
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-900 mb-2">
                    Platform URL
                  </label>
                  <input
                    type="text"
                    defaultValue="https://slbooking.hotel.lk"
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-900 mb-2">
                    Platform Commission (%)
                  </label>
                  <input
                    type="number"
                    defaultValue="15"
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                  />
                  <p className="text-sm text-gray-600 mt-1">
                    Commission taken from each booking
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-900 mb-2">
                    Support Email
                  </label>
                  <input
                    type="email"
                    defaultValue="support@slbooking.hotel.lk"
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-900 mb-2">
                    Support Phone
                  </label>
                  <input
                    type="tel"
                    defaultValue="+94 11 123 4567"
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                  />
                </div>

                <div>
                  <label className="flex items-center gap-3 cursor-pointer">
                    <input type="checkbox" defaultChecked className="w-4 h-4 rounded" />
                    <span className="text-sm font-medium text-gray-900">
                      Maintenance Mode
                    </span>
                  </label>
                  <p className="text-sm text-gray-600 mt-1">
                    When enabled, only admins can access the platform
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Payment Settings */}
        {activeTab === 'payments' && (
          <div className="space-y-6">
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-xl font-bold mb-6 flex items-center gap-2">
                <DollarSign className="w-5 h-5 text-red-600" />
                Payment Gateway Configuration
              </h2>

              <div className="space-y-6">
                <div className="border border-blue-200 rounded-lg p-4 bg-blue-50">
                  <h3 className="font-semibold text-blue-900 mb-4">Stripe</h3>
                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-900 mb-2">
                        Publishable Key
                      </label>
                      <input
                        type="password"
                        placeholder="pk_live_..."
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-900 mb-2">
                        Secret Key
                      </label>
                      <input
                        type="password"
                        placeholder="sk_live_..."
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                      />
                    </div>
                  </div>
                </div>

                <div className="border border-gray-200 rounded-lg p-4 bg-gray-50">
                  <div className="flex items-start gap-3">
                    <AlertCircle className="w-5 h-5 text-orange-600 flex-shrink-0 mt-1" />
                    <div>
                      <p className="font-semibold text-gray-900">Bank Transfer</p>
                      <p className="text-sm text-gray-600 mt-1">
                        Manual payment method - requires verification
                      </p>
                    </div>
                  </div>
                  <div className="mt-4">
                    <label className="flex items-center gap-3 cursor-pointer">
                      <input type="checkbox" defaultChecked className="w-4 h-4 rounded" />
                      <span className="text-sm font-medium text-gray-900">
                        Enable Bank Transfers
                      </span>
                    </label>
                  </div>
                </div>

                <div className="border border-gray-200 rounded-lg p-4 bg-gray-50">
                  <div className="flex items-start gap-3">
                    <AlertCircle className="w-5 h-5 text-orange-600 flex-shrink-0 mt-1" />
                    <div>
                      <p className="font-semibold text-gray-900">Pay at Property</p>
                      <p className="text-sm text-gray-600 mt-1">
                        Allow guests to pay on arrival
                      </p>
                    </div>
                  </div>
                  <div className="mt-4">
                    <label className="flex items-center gap-3 cursor-pointer">
                      <input type="checkbox" defaultChecked className="w-4 h-4 rounded" />
                      <span className="text-sm font-medium text-gray-900">
                        Enable Pay at Property
                      </span>
                    </label>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Email Settings */}
        {activeTab === 'email' && (
          <div className="space-y-6">
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-xl font-bold mb-6 flex items-center gap-2">
                <Mail className="w-5 h-5 text-red-600" />
                Email Configuration
              </h2>

              <div className="space-y-6">
                <div>
                  <label className="block text-sm font-medium text-gray-900 mb-2">
                    Email Provider
                  </label>
                  <select className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent">
                    <option>SendGrid</option>
                    <option>Gmail SMTP</option>
                    <option>Custom SMTP</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-900 mb-2">
                    SendGrid API Key
                  </label>
                  <input
                    type="password"
                    placeholder="SG.xxxxxxxxxxxxx"
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-900 mb-2">
                    From Email Address
                  </label>
                  <input
                    type="email"
                    defaultValue="noreply@slbooking.hotel.lk"
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                  />
                </div>

                <div>
                  <label className="flex items-center gap-3 cursor-pointer">
                    <input type="checkbox" defaultChecked className="w-4 h-4 rounded" />
                    <span className="text-sm font-medium text-gray-900">
                      Enable Transactional Emails
                    </span>
                  </label>
                </div>

                <div>
                  <label className="flex items-center gap-3 cursor-pointer">
                    <input type="checkbox" defaultChecked className="w-4 h-4 rounded" />
                    <span className="text-sm font-medium text-gray-900">
                      Enable Marketing Emails
                    </span>
                  </label>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Notification Settings */}
        {activeTab === 'notifications' && (
          <div className="space-y-6">
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-xl font-bold mb-6 flex items-center gap-2">
                <Bell className="w-5 h-5 text-red-600" />
                Notification Settings
              </h2>

              <div className="space-y-4">
                <div className="flex items-center justify-between p-4 border border-gray-200 rounded-lg">
                  <div>
                    <p className="font-medium text-gray-900">Property Approval Notifications</p>
                    <p className="text-sm text-gray-600">Notify owners when property is approved</p>
                  </div>
                  <label className="flex items-center cursor-pointer">
                    <input type="checkbox" defaultChecked className="w-4 h-4 rounded" />
                  </label>
                </div>

                <div className="flex items-center justify-between p-4 border border-gray-200 rounded-lg">
                  <div>
                    <p className="font-medium text-gray-900">Booking Confirmations</p>
                    <p className="text-sm text-gray-600">Send confirmation emails to guests</p>
                  </div>
                  <label className="flex items-center cursor-pointer">
                    <input type="checkbox" defaultChecked className="w-4 h-4 rounded" />
                  </label>
                </div>

                <div className="flex items-center justify-between p-4 border border-gray-200 rounded-lg">
                  <div>
                    <p className="font-medium text-gray-900">Payment Notifications</p>
                    <p className="text-sm text-gray-600">Notify about payment received/failed</p>
                  </div>
                  <label className="flex items-center cursor-pointer">
                    <input type="checkbox" defaultChecked className="w-4 h-4 rounded" />
                  </label>
                </div>

                <div className="flex items-center justify-between p-4 border border-gray-200 rounded-lg">
                  <div>
                    <p className="font-medium text-gray-900">Review Notifications</p>
                    <p className="text-sm text-gray-600">Notify owners about new reviews</p>
                  </div>
                  <label className="flex items-center cursor-pointer">
                    <input type="checkbox" defaultChecked className="w-4 h-4 rounded" />
                  </label>
                </div>

                <div className="flex items-center justify-between p-4 border border-gray-200 rounded-lg">
                  <div>
                    <p className="font-medium text-gray-900">WhatsApp Notifications</p>
                    <p className="text-sm text-gray-600">Enable WhatsApp notifications</p>
                  </div>
                  <label className="flex items-center cursor-pointer">
                    <input type="checkbox" className="w-4 h-4 rounded" />
                  </label>
                </div>
              </div>

              <div className="mt-6 p-4 border border-blue-200 rounded-lg bg-blue-50">
                <p className="text-sm text-blue-900">
                  <strong>Note:</strong> WhatsApp notifications require a Twilio account and API configuration
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Save Button */}
        <div className="mt-8 flex gap-4">
          <button
            onClick={handleSave}
            className="flex items-center gap-2 px-6 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg font-medium transition-colors"
          >
            <Save className="w-4 h-4" />
            Save Changes
          </button>
          <button className="px-6 py-2 bg-gray-200 hover:bg-gray-300 text-gray-900 rounded-lg font-medium transition-colors">
            Reset
          </button>
        </div>
      </div>
    </div>
  )
}
