'use client'

import { useEffect, useState } from 'react'
import { useChat } from '@/hooks/useChat'
import { getKBStats } from '@/utils/api'
import MessageList from './MessageList'
import ChatInput from './ChatInput'

export default function ChatContainer() {
  const { messages, loading, error, sendUserMessage, clearChat } = useChat()
  const [kbStats, setKbStats] = useState(null)
  const [tone, setTone] = useState('formal')

  // Fetch KB stats on mount
  useEffect(() => {
    const fetchStats = async () => {
      try {
        const stats = await getKBStats()
        setKbStats(stats)
      } catch (err) {
        console.error('Failed to fetch KB stats:', err)
      }
    }

    fetchStats()
  }, [])

  const handleSendMessage = async (message) => {
    try {
      await sendUserMessage(message, tone)
    } catch (err) {
      console.error('Error sending message:', err)
    }
  }

  const handleSelectFollowup = (followup) => {
    handleSendMessage(followup)
  }

  return (
    <div className="h-screen flex flex-col bg-white">
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-600 to-blue-700 text-white p-4 shadow-sm">
        <div className="max-w-5xl mx-auto flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold">MSRobot</h1>
            <p className="text-blue-100 text-sm">Meher's AI Assistant</p>
          </div>

          {/* Controls */}
          <div className="flex gap-4 items-center text-sm">
            <select
              value={tone}
              onChange={(e) => setTone(e.target.value)}
              className="bg-blue-500 text-white px-3 py-1 rounded border border-blue-400 cursor-pointer"
            >
              <option value="formal">Formal</option>
              <option value="casual">Casual</option>
            </select>

            <button
              onClick={clearChat}
              className="px-3 py-1 bg-blue-500 hover:bg-blue-400 rounded transition-colors"
            >
              Clear
            </button>
          </div>
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="bg-red-50 border-l-4 border-red-500 p-4 text-red-700 text-sm">
          <strong>Error:</strong> {error}
        </div>
      )}

      {/* Chat Area */}
      <div className="flex-1 flex flex-col max-w-5xl mx-auto w-full">
        <MessageList
          messages={messages}
          onSelectFollowup={handleSelectFollowup}
          loading={loading}
        />

        {/* Input Area */}
        <ChatInput
          onSendMessage={handleSendMessage}
          disabled={loading}
          placeholder="Ask me anything about Meher's experience, projects, and skills..."
        />
      </div>

      {/* Footer with KB Stats */}
      <div className="bg-gray-50 border-t border-gray-200 p-3 text-xs text-gray-600 text-center">
        {kbStats ? (
          <span>
            📚 KB: {kbStats.total_projects} projects • {kbStats.total_experiences} experiences • Last updated: {kbStats.last_updated}
          </span>
        ) : (
          <span>Loading KB info...</span>
        )}
      </div>
    </div>
  )
}