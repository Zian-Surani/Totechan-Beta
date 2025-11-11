import React from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { UserCircleIcon, SparklesIcon } from '@heroicons/react/24/outline'
import { Message } from '@/types'
import { SourceCitation } from './SourceCitation'
import clsx from 'clsx'

interface ChatMessageProps {
  message: Message
}

export function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === 'user'

  return (
    <div className={clsx('flex', isUser ? 'justify-end' : 'justify-start')}>
      <div className={clsx('flex items-start space-x-3 max-w-3xl', isUser && 'flex-row-reverse space-x-reverse')}>
        {/* Avatar */}
        <div className={clsx(
          'flex-shrink-0 h-8 w-8 rounded-full flex items-center justify-center',
          isUser ? 'bg-primary-600' : 'bg-gray-200 dark:bg-gray-700'
        )}>
          {isUser ? (
            <UserCircleIcon className="h-5 w-5 text-white" />
          ) : (
            <SparklesIcon className="h-5 w-5 text-gray-600 dark:text-gray-300" />
          )}
        </div>

        {/* Message content */}
        <div className={clsx(
          'rounded-lg px-4 py-3',
          isUser
            ? 'bg-primary-600 text-white'
            : 'bg-white dark:bg-gray-800 text-gray-900 dark:text-white border border-gray-200 dark:border-gray-700'
        )}>
          {/* Message text */}
          <div className="text-sm">
            {isUser ? (
              <p className="whitespace-pre-wrap">{message.content}</p>
            ) : (
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                className={clsx(
                  'prose prose-sm max-w-none',
                  'prose-p:my-1',
                  'prose-ul:my-1',
                  'prose-ol:my-1',
                  'prose-li:my-0.5',
                  isUser
                    ? 'prose-invert prose-p:text-white prose-ul:text-white prose-ol:text-white prose-li:text-white'
                    : 'prose-gray dark:prose-invert'
                )}
                components={{
                  code: ({ node, inline, className, children, ...props }) => {
                      const match = /language-(\w+)/.exec(className || '')
                      return !inline && match ? (
                        <pre className="bg-gray-100 dark:bg-gray-900 rounded p-2 overflow-x-auto">
                          <code className={className} {...props}>
                            {children}
                          </code>
                        </pre>
                      ) : (
                        <code className={clsx(
                          'px-1 py-0.5 rounded text-xs font-mono',
                          isUser
                            ? 'bg-primary-700 text-white'
                            : 'bg-gray-100 dark:bg-gray-900 text-gray-800 dark:text-gray-200'
                        )} {...props}>
                          {children}
                        </code>
                      )
                    },
                  a: ({ href, children }) => (
                    <a
                      href={href}
                      target="_blank"
                      rel="noopener noreferrer"
                      className={clsx(
                        'underline',
                        isUser ? 'text-primary-200 hover:text-white' : 'text-primary-600 hover:text-primary-800 dark:text-primary-400 dark:hover:text-primary-300'
                      )}
                    >
                      {children}
                    </a>
                  ),
                }}
              >
                {message.content}
              </ReactMarkdown>
            )}
          </div>

          {/* Sources */}
          {message.sources && message.sources.length > 0 && (
            <div className="mt-3 space-y-2">
              <p className={clsx(
                'text-xs font-medium',
                isUser ? 'text-primary-200' : 'text-gray-500 dark:text-gray-400'
              )}>
                Sources:
              </p>
              <div className="flex flex-wrap gap-1">
                {message.sources.slice(0, 3).map((source, index) => (
                  <SourceCitation key={index} source={source} />
                ))}
                {message.sources.length > 3 && (
                  <span className={clsx(
                    'text-xs px-2 py-1 rounded',
                    isUser
                      ? 'bg-primary-700 text-primary-200'
                      : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300'
                  )}>
                    +{message.sources.length - 3} more
                  </span>
                )}
              </div>
            </div>
          )}

          {/* Metadata */}
          <div className={clsx(
            'mt-2 flex items-center space-x-2 text-xs',
            isUser ? 'text-primary-200' : 'text-gray-500 dark:text-gray-400'
          )}>
            {message.model_used && (
              <span>Model: {message.model_used}</span>
            )}
            {message.token_count && (
              <span>• {message.token_count} tokens</span>
            )}
            {message.cost_estimate && (
              <span>• {message.cost_estimate}</span>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}