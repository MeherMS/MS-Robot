'use client'

import { useEffect, useState } from 'react'
import { useChat } from '@/hooks/useChat'
import { warmupBackend } from '@/utils/api'

import MessageList from './MessageList'
import ChatInput from './ChatInput'
import ConsentModal from './ConsentModal'

export default function ChatContainer() {
  const { messages, loading, error, sendUserMessage, clearChat } = useChat()
  const [kbStats, setKbStats] = useState(null)
  const [tone, setTone] = useState('formal')
  const [backendReady, setBackendReady] = useState(false)
  const [backendConnecting, setBackendConnecting] = useState(true)

  // Warmup backend on app load
  useEffect(() => {
    const initializeBackend = async () => {
      setBackendConnecting(true)
      const isReady = await warmupBackend()
      setBackendReady(isReady)
      setBackendConnecting(false)
    }

    initializeBackend()
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
    <div className="flex flex-col flex-1 bg-white overflow-hidden">
      <ConsentModal />
      
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
              disabled={!backendReady || loading}
            >
              <option value="formal">Formal</option>
              <option value="casual">Casual</option>
            </select>

            <button
              onClick={clearChat}
              className="px-3 py-1 bg-blue-500 hover:bg-blue-400 rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              disabled={!backendReady || loading}
            >
              Clear
            </button>
          </div>
        </div>
      </div>

      {/* Backend Connection Status */}
      {backendConnecting && (
        <div className="bg-blue-50 border-l-4 border-blue-500 p-4 text-blue-700 text-sm flex items-center gap-2">
          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-700"></div>
          <span>
            <strong>Connecting to backend...</strong> This may take up to 30 seconds on first load.
          </span>
        </div>
      )}

      {!backendReady && !backendConnecting && (
        <div className="bg-orange-50 border-l-4 border-orange-500 p-4 text-orange-700 text-sm">
          <strong>Backend connection failed.</strong> Please refresh the page and try again.
        </div>
      )}

      {/* Error Display */}
      {error && (
        <div className="bg-red-50 border-l-4 border-red-500 p-4 text-red-700 text-sm">
          <strong>Error:</strong> {error}
        </div>
      )}

      {/* Chat Area */}
      <div className="flex-1 flex flex-col max-w-5xl mx-auto w-full overflow-y-auto">
        <MessageList
          messages={messages}
          onSelectFollowup={handleSelectFollowup}
          loading={loading}
        />

        {/* Input Area */}
        <ChatInput
          onSendMessage={handleSendMessage}
          disabled={loading || !backendReady}
          placeholder={
            backendConnecting
              ? 'Waiting for backend to connect...'
              : 'Ask me anything about Meher\'s experience, projects, and skills...'
          }
        />
      </div>
    </div>
  )
}