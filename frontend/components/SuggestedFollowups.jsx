'use client'

export default function SuggestedFollowups({ followups, onSelectFollowup }) {
  if (!followups || followups.length === 0) {
    return null
  }

  return (
    <div className="mt-4 space-y-2">
      <p className="text-sm font-medium text-gray-600">Suggested follow-ups:</p>
      <div className="space-y-2">
        {followups.map((followup, idx) => (
          <button
            key={idx}
            onClick={() => onSelectFollowup(followup)}
            className="w-full text-left px-3 py-2 text-sm bg-gray-50 hover:bg-blue-50 border border-gray-200 rounded-lg transition-colors text-gray-700 hover:text-blue-700"
          >
            • {followup}
          </button>
        ))}
      </div>
    </div>
  )
}