import React from 'react'
import { DocumentTextIcon } from '@heroicons/react/24/outline'
import { SourceCitation as SourceCitationType } from '@/types'

interface SourceCitationProps {
  source: SourceCitationType
}

export function SourceCitation({ source }: SourceCitationProps) {
  const handleClick = () => {
    // In a real app, this might open the document or scroll to the specific location
    console.log('Source clicked:', source)
  }

  return (
    <button
      onClick={handleClick}
      className="inline-flex items-center px-2 py-1 rounded text-xs bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 hover:bg-blue-200 dark:hover:bg-blue-800 transition-colors cursor-pointer"
      title={`Source: ${source.filename}${source.page_number ? ` (Page ${source.page_number})` : ''}`}
    >
      <DocumentTextIcon className="h-3 w-3 mr-1 flex-shrink-0" />
      <span className="truncate max-w-32">
        {source.filename}
        {source.page_number && ` (p${source.page_number})`}
      </span>
      <span className="ml-1 text-blue-600 dark:text-blue-300">
        ({(source.relevance_score * 100).toFixed(0)}%)
      </span>
    </button>
  )
}