'use client'

import { useEffect, useRef } from 'react'
import ResponseCard from './ResponseCard'

export default function MessageList({ messages, onSelectFollowup, loading }) {
  const endRef = useRef(null)

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  if (messages.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center p-4">
        <div className="text-center">
          <h2 className="text-2xl font-bold text-gray-900 mb-2">MSRobot 🤖</h2>
          <p className="text-gray-600">
            Hi! I'm an AI assistant representing Meher. <br />
            Ask me anything about her experience, projects, and skills.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex-1 overflow-y-auto chat-container p-4 space-y-4">
      {messages.map((msg, idx) => (
        <div
          key={idx}
          className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
        >
          {msg.role === 'user' ? (
            // User message (simple, right-aligned)
            <div className="max-w-xs bg-blue-600 text-white rounded-lg p-3 text-sm break-words message-fade">
              {msg.content.text || msg.content}
            </div>
          ) : (
            // Assistant message (rich, left-aligned, with metadata)
            <div className="max-w-2xl w-full message-fade">
              <ResponseCard
                response={msg.content.response || msg.content}
                confidence={msg.content.confidence || 0.7}
                kbUsed={msg.content.kb_used !== false}
                sources={msg.content.sources || []}
                suggestedFollowups={msg.content.suggested_followups || []}
                onSelectFollowup={onSelectFollowup}
              />
            </div>
          )}
        </div>
      ))}

      {/* Loading indicator */}
      {loading && (
        <div className="flex justify-start">
          <div className="bg-gray-100 rounded-lg p-3 text-sm text-gray-600 message-fade">
            <div className="flex gap-2 items-center">
              <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
              <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-100"></div>
              <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-200"></div>
            </div>
          </div>
        </div>
      )}

      {/* Scroll anchor */}
      <div ref={endRef} />
    </div>
  )
}