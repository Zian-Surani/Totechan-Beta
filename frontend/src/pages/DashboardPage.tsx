import React from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  ChatBubbleLeftRightIcon,
  DocumentTextIcon,
  ChartBarIcon,
  ArrowTrendingUpIcon,
} from '@heroicons/react/24/outline'
import apiClient from '@/services/api'
import { UsageStats, DocumentStats } from '@/types'

export default function DashboardPage() {
  const { data: usageStats, isLoading: usageLoading } = useQuery<UsageStats>({
    queryKey: ['chat-stats'],
    queryFn: () => apiClient.getChatStats(),
  })

  const { data: documentStats, isLoading: docsLoading } = useQuery<DocumentStats>({
    queryKey: ['ingestion-stats'],
    queryFn: () => apiClient.getIngestionStats(),
  })

  const stats = [
    {
      name: 'Total Sessions',
      value: usageStats?.total_sessions || 0,
      icon: ChatBubbleLeftRightIcon,
      color: 'bg-blue-500',
      loading: usageLoading,
    },
    {
      name: 'Total Messages',
      value: usageStats?.total_messages || 0,
      icon: ChatBubbleLeftRightIcon,
      color: 'bg-green-500',
      loading: usageLoading,
    },
    {
      name: 'Documents Uploaded',
      value: documentStats?.total_documents || 0,
      icon: DocumentTextIcon,
      color: 'bg-purple-500',
      loading: docsLoading,
    },
    {
      name: 'Total Tokens Used',
      value: usageStats?.total_tokens_used || 0,
      icon: ChartBarIcon,
      color: 'bg-orange-500',
      loading: usageLoading,
      format: (value: number) => value.toLocaleString(),
    },
  ]

  const recentActivity = [
    // This would come from an API endpoint in a real app
    { type: 'chat', message: 'Asked about refund policy', time: '2 minutes ago' },
    { type: 'upload', message: 'Uploaded policy_document.pdf', time: '1 hour ago' },
    { type: 'chat', message: 'Asked about shipping costs', time: '3 hours ago' },
    { type: 'upload', message: 'Uploaded FAQ.html', time: '1 day ago' },
  ]

  return (
    <div>
      {/* Page header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Dashboard</h1>
        <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
          Welcome to your RAG chatbot dashboard. Here's an overview of your activity.
        </p>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat) => (
          <div key={stat.name} className="card">
            <div className="p-6">
              <div className="flex items-center">
                <div className={`flex-shrink-0 rounded-md p-3 ${stat.color}`}>
                  <stat.icon className="h-6 w-6 text-white" aria-hidden="true" />
                </div>
                <div className="ml-5 w-0 flex-1">
                  <dl>
                    <dt className="text-sm font-medium text-gray-500 dark:text-gray-400 truncate">
                      {stat.name}
                    </dt>
                    <dd className="flex items-baseline">
                      <div className="text-2xl font-semibold text-gray-900 dark:text-white">
                        {stat.loading ? (
                          <div className="loading-spinner h-6 w-6"></div>
                        ) : (
                          stat.format ? stat.format(stat.value) : stat.value.toLocaleString()
                        )}
                      </div>
                    </dd>
                  </dl>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Quick actions */}
      <div className="mt-8">
        <div className="card">
          <div className="card-header">
            <h3 className="text-lg font-medium text-gray-900 dark:text-white">Quick Actions</h3>
            <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
              Get started with these common tasks
            </p>
          </div>
          <div className="card-body">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
              <Link
                to="/chat"
                className="flex items-center p-3 bg-gray-50 dark:bg-gray-800 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
              >
                <ChatBubbleLeftRightIcon className="h-6 w-6 text-primary-600 dark:text-primary-400" />
                <span className="ml-3 text-sm font-medium text-gray-900 dark:text-white">
                  Start New Chat
                </span>
              </Link>
              <Link
                to="/documents"
                className="flex items-center p-3 bg-gray-50 dark:bg-gray-800 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
              >
                <DocumentTextIcon className="h-6 w-6 text-primary-600 dark:text-primary-400" />
                <span className="ml-3 text-sm font-medium text-gray-900 dark:text-white">
                  Upload Documents
                </span>
              </Link>
              <button className="flex items-center p-3 bg-gray-50 dark:bg-gray-800 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors">
                <ChartBarIcon className="h-6 w-6 text-primary-600 dark:text-primary-400" />
                <span className="ml-3 text-sm font-medium text-gray-900 dark:text-white">
                  View Analytics
                </span>
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Recent activity and stats */}
      <div className="mt-8 grid grid-cols-1 gap-8 lg:grid-cols-2">
        {/* Recent activity */}
        <div className="card">
          <div className="card-header">
            <h3 className="text-lg font-medium text-gray-900 dark:text-white">Recent Activity</h3>
          </div>
          <div className="card-body">
            <div className="space-y-4">
              {recentActivity.map((activity, index) => (
                <div key={index} className="flex items-center space-x-3">
                  <div className="flex-shrink-0">
                    {activity.type === 'chat' ? (
                      <div className="h-8 w-8 rounded-full bg-blue-100 dark:bg-blue-900 flex items-center justify-center">
                        <ChatBubbleLeftRightIcon className="h-4 w-4 text-blue-600 dark:text-blue-300" />
                      </div>
                    ) : (
                      <div className="h-8 w-8 rounded-full bg-green-100 dark:bg-green-900 flex items-center justify-center">
                        <DocumentTextIcon className="h-4 w-4 text-green-600 dark:text-green-300" />
                      </div>
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-gray-900 dark:text-white truncate">
                      {activity.message}
                    </p>
                    <p className="text-xs text-gray-500 dark:text-gray-400">
                      {activity.time}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Document status */}
        <div className="card">
          <div className="card-header">
            <h3 className="text-lg font-medium text-gray-900 dark:text-white">Document Status</h3>
          </div>
          <div className="card-body">
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600 dark:text-gray-400">Completed</span>
                <span className="text-sm font-medium text-green-600 dark:text-green-400">
                  {documentStats?.completed_documents || 0}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600 dark:text-gray-400">Processing</span>
                <span className="text-sm font-medium text-yellow-600 dark:text-yellow-400">
                  {documentStats?.processing_documents || 0}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600 dark:text-gray-400">Failed</span>
                <span className="text-sm font-medium text-red-600 dark:text-red-400">
                  {documentStats?.failed_documents || 0}
                </span>
              </div>
              <div className="pt-4 border-t border-gray-200 dark:border-gray-700">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600 dark:text-gray-400">Total Size</span>
                  <span className="text-sm font-medium text-gray-900 dark:text-white">
                    {documentStats?.total_size_mb || 0} MB
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}