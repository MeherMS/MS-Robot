'use client'

import { useState, useCallback } from 'react'
import { sendMessage } from '@/utils/api'

export const useChat = () => {
  const [messages, setMessages] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const addMessage = useCallback((role, content) => {
    setMessages((prev) => [...prev, { role, content }])
  }, [])

  const sendUserMessage = useCallback(
    async (userMessage, tone = 'formal') => {
      // Add user message to history
      addMessage('user', userMessage)
      setLoading(true)
      setError(null)

      try {
        // Prepare conversation history for API
        // Backend expects: [{ role: "user|assistant", content: "text" }]
        const conversationHistory = messages.map((msg) => {
          let content = msg.content

          // If it's an assistant message (object), extract just the response text
          if (msg.role === 'assistant' && typeof msg.content === 'object') {
            content = msg.content.response || ''
          }

          return {
            role: msg.role,
            content: content,
          }
        })

        // Call API
        const response = await sendMessage(userMessage, tone, conversationHistory)

        // Add assistant response (full object with metadata)
        addMessage('assistant', response)

        return response
      } catch (err) {
        setError(err.message || 'Failed to get response')
        console.error('Error:', err)
        throw err
      } finally {
        setLoading(false)
      }
    },
    [messages, addMessage]
  )

  const clearChat = useCallback(() => {
    setMessages([])
    setError(null)
  }, [])

  return {
    messages,
    loading,
    error,
    sendUserMessage,
    addMessage,
    clearChat,
  }
}