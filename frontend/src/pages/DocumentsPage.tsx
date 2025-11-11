import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  DocumentTextIcon,
  CloudArrowUpIcon,
  TrashIcon,
  EyeIcon,
  ArrowPathIcon,
} from '@heroicons/react/24/outline'
import apiClient from '@/services/api'
import { Document, IngestionJob } from '@/types'
import toast from 'react-hot-toast'

export default function DocumentsPage() {
  const queryClient = useQueryClient()
  const [selectedFiles, setSelectedFiles] = useState<File[]>([])
  const [uploadModalOpen, setUploadModalOpen] = useState(false)

  // Queries
  const { data: documents, isLoading } = useQuery({
    queryKey: ['documents'],
    queryFn: () => apiClient.getDocuments(),
  })

  const { data: stats } = useQuery({
    queryKey: ['ingestion-stats'],
    queryFn: () => apiClient.getIngestionStats(),
  })

  // Mutations
  const uploadMutation = useMutation({
    mutationFn: ({ file, metadata }: { file: File; metadata: any }) =>
      apiClient.uploadDocument(file, metadata),
    onSuccess: (response) => {
      toast.success('Document uploaded successfully')
      setSelectedFiles([])
      setUploadModalOpen(false)
      queryClient.invalidateQueries({ queryKey: ['documents'] })

      // Poll for completion
      const jobId = response.ingestion_job_id
      const pollInterval = setInterval(async () => {
        try {
          const job: IngestionJob = await apiClient.getIngestionStatus(jobId)
          if (job.status === 'completed') {
            toast.success('Document processing completed')
            clearInterval(pollInterval)
            queryClient.invalidateQueries({ queryKey: ['documents'] })
            queryClient.invalidateQueries({ queryKey: ['ingestion-stats'] })
          } else if (job.status === 'failed') {
            toast.error(`Document processing failed: ${job.error_message}`)
            clearInterval(pollInterval)
            queryClient.invalidateQueries({ queryKey: ['documents'] })
          }
        } catch (error) {
          clearInterval(pollInterval)
        }
      }, 2000)
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.error?.message || 'Upload failed')
    },
  })

  const deleteMutation = useMutation({
    mutationFn: apiClient.deleteDocument,
    onSuccess: () => {
      toast.success('Document deleted successfully')
      queryClient.invalidateQueries({ queryKey: ['documents'] })
      queryClient.invalidateQueries({ queryKey: ['ingestion-stats'] })
    },
    onError: (error: any) => {
      toast.error('Failed to delete document')
    },
  })

  const reprocessMutation = useMutation({
    mutationFn: apiClient.reprocessDocument,
    onSuccess: (response) => {
      toast.success('Document reprocessing started')
      queryClient.invalidateQueries({ queryKey: ['documents'] })
    },
    onError: (error: any) => {
      toast.error('Failed to reprocess document')
    },
  })

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files || [])
    setSelectedFiles(files)
  }

  const handleUpload = () => {
    if (selectedFiles.length === 0) return

    selectedFiles.forEach((file) => {
      uploadMutation.mutate({
        file,
        metadata: {
          title: file.name,
          access_level: 'private',
          tags: '',
        },
      })
    })
  }

  const handleDelete = (documentId: string) => {
    if (window.confirm('Are you sure you want to delete this document?')) {
      deleteMutation.mutate(documentId)
    }
  }

  const handleReprocess = (documentId: string) => {
    reprocessMutation.mutate(documentId)
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'text-green-600 dark:text-green-400'
      case 'processing':
        return 'text-yellow-600 dark:text-yellow-400'
      case 'failed':
        return 'text-red-600 dark:text-red-400'
      default:
        return 'text-gray-600 dark:text-gray-400'
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'processing':
        return <div className="loading-spinner h-4 w-4"></div>
      case 'completed':
        return <EyeIcon className="h-4 w-4" />
      case 'failed':
        return <TrashIcon className="h-4 w-4" />
      default:
        return <DocumentTextIcon className="h-4 w-4" />
    }
  }

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  return (
    <div>
      {/* Header */}
      <div className="mb-8 sm:flex sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Documents</h1>
          <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
            Manage your document library and ingestion status
          </p>
        </div>
        <div className="mt-4 sm:mt-0">
          <button
            onClick={() => setUploadModalOpen(true)}
            className="btn-primary"
          >
            <CloudArrowUpIcon className="h-4 w-4 mr-2" />
            Upload Document
          </button>
        </div>
      </div>

      {/* Stats */}
      {stats && (
        <div className="mb-8 grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
          <div className="card">
            <div className="p-6">
              <div className="flex items-center">
                <div className="flex-shrink-0 bg-blue-100 dark:bg-blue-900 rounded-md p-3">
                  <DocumentTextIcon className="h-6 w-6 text-blue-600 dark:text-blue-300" />
                </div>
                <div className="ml-5 w-0 flex-1">
                  <dl>
                    <dt className="text-sm font-medium text-gray-500 dark:text-gray-400 truncate">
                      Total Documents
                    </dt>
                    <dd className="text-lg font-semibold text-gray-900 dark:text-white">
                      {stats.total_documents}
                    </dd>
                  </dl>
                </div>
              </div>
            </div>
          </div>

          <div className="card">
            <div className="p-6">
              <div className="flex items-center">
                <div className="flex-shrink-0 bg-green-100 dark:bg-green-900 rounded-md p-3">
                  <EyeIcon className="h-6 w-6 text-green-600 dark:text-green-300" />
                </div>
                <div className="ml-5 w-0 flex-1">
                  <dl>
                    <dt className="text-sm font-medium text-gray-500 dark:text-gray-400 truncate">
                      Completed
                    </dt>
                    <dd className="text-lg font-semibold text-gray-900 dark:text-white">
                      {stats.completed_documents}
                    </dd>
                  </dl>
                </div>
              </div>
            </div>
          </div>

          <div className="card">
            <div className="p-6">
              <div className="flex items-center">
                <div className="flex-shrink-0 bg-yellow-100 dark:bg-yellow-900 rounded-md p-3">
                  <div className="loading-spinner h-6 w-6" />
                </div>
                <div className="ml-5 w-0 flex-1">
                  <dl>
                    <dt className="text-sm font-medium text-gray-500 dark:text-gray-400 truncate">
                      Processing
                    </dt>
                    <dd className="text-lg font-semibold text-gray-900 dark:text-white">
                      {stats.processing_documents}
                    </dd>
                  </dl>
                </div>
              </div>
            </div>
          </div>

          <div className="card">
            <div className="p-6">
              <div className="flex items-center">
                <div className="flex-shrink-0 bg-purple-100 dark:bg-purple-900 rounded-md p-3">
                  <DocumentTextIcon className="h-6 w-6 text-purple-600 dark:text-purple-300" />
                </div>
                <div className="ml-5 w-0 flex-1">
                  <dl>
                    <dt className="text-sm font-medium text-gray-500 dark:text-gray-400 truncate">
                      Total Size
                    </dt>
                    <dd className="text-lg font-semibold text-gray-900 dark:text-white">
                      {stats.total_size_mb.toFixed(1)} MB
                    </dd>
                  </dl>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Documents list */}
      <div className="card">
        <div className="card-header">
          <h3 className="text-lg font-medium text-gray-900 dark:text-white">Document Library</h3>
        </div>
        <div className="card-body">
          {isLoading ? (
            <div className="text-center py-8">
              <div className="loading-spinner h-8 w-8 mx-auto"></div>
              <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">Loading documents...</p>
            </div>
          ) : !documents?.data || documents.data.length === 0 ? (
            <div className="text-center py-8">
              <DocumentTextIcon className="mx-auto h-12 w-12 text-gray-400" />
              <h3 className="mt-2 text-sm font-medium text-gray-900 dark:text-white">No documents</h3>
              <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                Get started by uploading your first document.
              </p>
              <div className="mt-6">
                <button
                  onClick={() => setUploadModalOpen(true)}
                  className="btn-primary"
                >
                  <CloudArrowUpIcon className="h-4 w-4 mr-2" />
                  Upload Document
                </button>
              </div>
            </div>
          ) : (
            <div className="overflow-hidden shadow ring-1 ring-black ring-opacity-5 md:rounded-lg">
              <table className="min-w-full divide-y divide-gray-300 dark:divide-gray-700">
                <thead className="bg-gray-50 dark:bg-gray-800">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                      Name
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                      Type
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                      Status
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                      Size
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                      Chunks
                    </th>
                    <th className="relative px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                      <span className="sr-only">Actions</span>
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white dark:bg-gray-900 divide-y divide-gray-200 dark:divide-gray-700">
                  {documents.data.map((doc: Document) => (
                    <tr key={doc.id}>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center">
                          <DocumentTextIcon className="h-5 w-5 text-gray-400 dark:text-gray-500" />
                          <div className="ml-4">
                            <div className="text-sm font-medium text-gray-900 dark:text-white">
                              {doc.title || doc.original_filename}
                            </div>
                            <div className="text-sm text-gray-500 dark:text-gray-400">
                              {doc.original_filename}
                            </div>
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className="text-sm text-gray-900 dark:text-white uppercase">
                          {doc.file_type}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center">
                          {getStatusIcon(doc.ingestion_status)}
                          <span className={`ml-2 text-sm ${getStatusColor(doc.ingestion_status)}`}>
                            {doc.ingestion_status}
                          </span>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                        {formatFileSize(doc.file_size)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                        {doc.chunk_count}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                        <button
                          onClick={() => handleReprocess(doc.id)}
                          className="text-gray-400 hover:text-gray-600 dark:text-gray-300 dark:hover:text-gray-100 mr-3"
                          title="Reprocess"
                        >
                          <ArrowPathIcon className="h-4 w-4" />
                        </button>
                        <button
                          onClick={() => handleDelete(doc.id)}
                          className="text-red-400 hover:text-red-600 dark:text-red-300 dark:hover:text-red-100"
                          title="Delete"
                        >
                          <TrashIcon className="h-4 w-4" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* Upload Modal */}
      {uploadModalOpen && (
        <div className="fixed inset-0 z-50 overflow-y-auto">
          <div className="flex min-h-screen items-end justify-center px-4 pt-4 pb-20 text-center sm:block sm:p-0">
            <div className="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity"></div>

            <div className="inline-block align-bottom bg-white dark:bg-gray-800 rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full">
              <div className="bg-white dark:bg-gray-800 px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
                <div className="sm:flex sm:items-start">
                  <div className="w-full">
                    <h3 className="text-lg leading-6 font-medium text-gray-900 dark:text-white">
                      Upload Documents
                    </h3>
                    <div className="mt-2">
                      <p className="text-sm text-gray-500 dark:text-gray-400">
                        Upload PDF, DOCX, HTML, or TXT files to add them to your knowledge base.
                      </p>
                    </div>
                  </div>
                </div>
              </div>

              <div className="bg-white dark:bg-gray-800 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse">
                <div className="w-full">
                  {/* File input area */}
                  <div className="border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-lg p-6 text-center">
                    <CloudArrowUpIcon className="mx-auto h-12 w-12 text-gray-400" />
                    <div className="mt-4">
                      <label htmlFor="file-upload" className="cursor-pointer">
                        <span className="mt-2 block text-sm font-medium text-primary-600 dark:text-primary-400">
                          Click to upload or drag and drop
                        </span>
                        <span className="mt-1 block text-xs text-gray-500 dark:text-gray-400">
                          PDF, DOCX, HTML, TXT up to 50MB
                        </span>
                        <input
                          id="file-upload"
                          name="file-upload"
                          type="file"
                          multiple
                          accept=".pdf,.docx,.html,.txt"
                          className="sr-only"
                          onChange={handleFileSelect}
                        />
                      </label>
                    </div>
                  </div>

                  {/* Selected files */}
                  {selectedFiles.length > 0 && (
                    <div className="mt-4 space-y-2">
                      <p className="text-sm font-medium text-gray-900 dark:text-white">
                        Selected files:
                      </p>
                      {selectedFiles.map((file, index) => (
                        <div key={index} className="flex items-center justify-between p-2 bg-gray-50 dark:bg-gray-700 rounded">
                          <span className="text-sm text-gray-900 dark:text-white truncate">
                            {file.name}
                          </span>
                          <span className="text-xs text-gray-500 dark:text-gray-400">
                            {(file.size / 1024 / 1024).toFixed(2)} MB
                          </span>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Action buttons */}
                  <div className="mt-6 flex space-x-3">
                    <button
                      type="button"
                      onClick={handleUpload}
                      disabled={selectedFiles.length === 0 || uploadMutation.isPending}
                      className="btn-primary flex-1 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {uploadMutation.isPending ? (
                        <>
                          <div className="loading-spinner h-4 w-4 mr-2"></div>
                          Uploading...
                        </>
                      ) : (
                        'Upload'
                      )}
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        setUploadModalOpen(false)
                        setSelectedFiles([])
                      }}
                      className="btn-outline flex-1"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}