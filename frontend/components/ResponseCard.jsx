'use client'

import ReactMarkdown from 'react-markdown'
import SuggestedFollowups from './SuggestedFollowups'

export default function ResponseCard({
  response,
  confidence,
  kbUsed,
  sources,
  suggestedFollowups,
  onSelectFollowup,
}) {
  // Convert confidence to percentage
  const confidencePercent = Math.round(confidence * 100)

  // Determine confidence badge color
  const getConfidenceColor = () => {
    if (confidence >= 0.8) return 'bg-green-100 text-green-800'
    if (confidence >= 0.65) return 'bg-yellow-100 text-yellow-800'
    return 'bg-orange-100 text-orange-800'
  }

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4 message-fade">
      {/* Main Response Text */}
      <div className="mb-4 text-gray-800 prose prose-sm max-w-none">
        <ReactMarkdown
          components={{
            p: ({ node, ...props }) => <p className="mb-2" {...props} />,
            code: ({ node, inline, ...props }) =>
              inline ? (
                <code className="bg-gray-100 px-2 py-1 rounded text-sm font-mono" {...props} />
              ) : (
                <code className="block bg-gray-900 text-gray-100 p-3 rounded-lg my-2 font-mono text-sm overflow-x-auto" {...props} />
              ),
            strong: ({ node, ...props }) => <strong className="font-semibold" {...props} />,
            em: ({ node, ...props }) => <em className="italic" {...props} />,
            a: ({ node, ...props }) => (
              <a className="text-blue-600 hover:underline" target="_blank" rel="noopener noreferrer" {...props} />
            ),
          }}
        >
          {response}
        </ReactMarkdown>
      </div>

     {/* Metadata: Confidence + Sources */}
      <div className="flex flex-wrap items-center gap-3 text-xs mb-4 pb-4 border-b border-gray-200">
        {/* Confidence Badge */}
        <span className={`px-2 py-1 rounded ${getConfidenceColor()} font-medium`}>
          {confidencePercent}% confident
        </span>

        {/* KB vs LLM indicator */}
        <span className="text-gray-600">
          {kbUsed ? '📚 KB-based' : '🤖 LLM-based'}
        </span>

        {/* Sources */}
        {sources && sources.length > 0 && (
          <div className="flex gap-2">
            {sources.map((source, idx) => (
              <a
                key={idx}
                href={source.link || '#'}
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-600 hover:underline"
              >
                📎 {source.title}
              </a>
            ))}
          </div>
        )}
      </div>

      {/* Suggested Follow-ups */}
      <SuggestedFollowups
        followups={suggestedFollowups}
        onSelectFollowup={onSelectFollowup}
      />
    </div>
  )
}