import React from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { Cog6ToothIcon, UserCircleIcon } from '@heroicons/react/24/outline'

export default function SettingsPage() {
  const { user } = useAuth()

  return (
    <div>
      {/* Page header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Settings</h1>
        <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
          Manage your account and application preferences
        </p>
      </div>

      {/* Settings sections */}
      <div className="space-y-6">
        {/* Profile Settings */}
        <div className="card">
          <div className="card-header">
            <div className="flex items-center">
              <UserCircleIcon className="h-5 w-5 text-gray-400" />
              <h3 className="ml-2 text-lg font-medium text-gray-900 dark:text-white">
                Profile Information
              </h3>
            </div>
          </div>
          <div className="card-body">
            <dl className="grid grid-cols-1 gap-x-4 gap-y-6 sm:grid-cols-2">
              <div>
                <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">Name</dt>
                <dd className="mt-1 text-sm text-gray-900 dark:text-white">
                  {user?.first_name && user?.last_name
                    ? `${user.first_name} ${user.last_name}`
                    : 'Not set'}
                </dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">Email address</dt>
                <dd className="mt-1 text-sm text-gray-900 dark:text-white">
                  {user?.email}
                </dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">Role</dt>
                <dd className="mt-1 text-sm text-gray-900 dark:text-white">
                  {user?.role}
                </dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">Account Status</dt>
                <dd className="mt-1">
                  <span className="inline-flex px-2 py-1 text-xs font-semibold rounded-full bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200">
                    {user?.is_active ? 'Active' : 'Inactive'}
                  </span>
                </dd>
              </div>
            </dl>
          </div>
        </div>

        {/* Chat Settings */}
        <div className="card">
          <div className="card-header">
            <div className="flex items-center">
              <Cog6ToothIcon className="h-5 w-5 text-gray-400" />
              <h3 className="ml-2 text-lg font-medium text-gray-900 dark:text-white">
                Chat Preferences
              </h3>
            </div>
          </div>
          <div className="card-body">
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="text-sm font-medium text-gray-900 dark:text-white">Default Retrieval Count</h4>
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    Number of document chunks to retrieve for each query
                  </p>
                </div>
                <select className="input-field max-w-xs">
                  <option value="5">5</option>
                  <option value="8">8</option>
                  <option value="10">10</option>
                  <option value="15">15</option>
                </select>
              </div>

              <div className="flex items-center justify-between">
                <div>
                  <h4 className="text-sm font-medium text-gray-900 dark:text-white">Enable Reranking</h4>
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    Use advanced reranking to improve result relevance
                  </p>
                </div>
                <button className="relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent bg-primary-600 transition-colors focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2">
                  <span className="translate-x-5 inline-block h-5 w-5 transform rounded-full bg-white transition-transform"></span>
                </button>
              </div>

              <div className="flex items-center justify-between">
                <div>
                  <h4 className="text-sm font-medium text-gray-900 dark:text-white">Show Sources</h4>
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    Display source citations in chat responses
                  </p>
                </div>
                <button className="relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent bg-primary-600 transition-colors focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2">
                  <span className="translate-x-5 inline-block h-5 w-5 transform rounded-full bg-white transition-transform"></span>
                </button>
              </div>

              <div className="flex items-center justify-between">
                <div>
                  <h4 className="text-sm font-medium text-gray-900 dark:text-white">Auto-save Sessions</h4>
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    Automatically save chat sessions
                  </p>
                </div>
                <button className="relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent bg-primary-600 transition-colors focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2">
                  <span className="translate-x-5 inline-block h-5 w-5 transform rounded-full bg-white transition-transform"></span>
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* System Information */}
        <div className="card">
          <div className="card-header">
            <h3 className="text-lg font-medium text-gray-900 dark:text-white">System Information</h3>
          </div>
          <div className="card-body">
            <dl className="grid grid-cols-1 gap-x-4 gap-y-6 sm:grid-cols-2">
              <div>
                <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">Version</dt>
                <dd className="mt-1 text-sm text-gray-900 dark:text-white">1.0.0</dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">Environment</dt>
                <dd className="mt-1 text-sm text-gray-900 dark:text-white">
                  {import.meta.env.MODE === 'development' ? 'Development' : 'Production'}
                </dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">Member Since</dt>
                <dd className="mt-1 text-sm text-gray-900 dark:text-white">
                  {user?.created_at ? new Date(user.created_at).toLocaleDateString() : 'Unknown'}
                </dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">Last Login</dt>
                <dd className="mt-1 text-sm text-gray-900 dark:text-white">
                  {user?.last_login ? new Date(user.last_login).toLocaleDateString() : 'Never'}
                </dd>
              </div>
            </dl>
          </div>
        </div>

        {/* Danger Zone */}
        <div className="card border-red-200 dark:border-red-800">
          <div className="card-header">
            <h3 className="text-lg font-medium text-red-600 dark:text-red-400">Danger Zone</h3>
          </div>
          <div className="card-body">
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
              Irreversible actions that affect your account
            </p>
            <div className="space-y-3">
              <button className="btn-outline text-red-600 border-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 dark:text-red-400 dark:border-red-400">
                Clear Chat History
              </button>
              <button className="btn-outline text-red-600 border-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 dark:text-red-400 dark:border-red-400">
                Export My Data
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}