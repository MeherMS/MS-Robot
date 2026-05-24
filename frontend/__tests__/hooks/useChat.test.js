// frontend/__tests__/hooks/useChat.test.js

import { renderHook, act, waitFor } from '@testing-library/react'
import { useChat } from '@/hooks/useChat'
import * as apiModule from '@/utils/api'

// Mock the API module
jest.mock('@/utils/api', () => ({
  sendMessage: jest.fn(),
}))

describe('useChat Hook', () => {
  beforeEach(() => {
    jest.clearAllMocks()
    sessionStorage.clear()
  })

  // ========================================================================
  // Initial State Tests
  // ========================================================================

  it('should initialize with empty state', () => {
    /**
     * WHY WE TEST THIS:
     * - Hook must start fresh
     * - Initial state affects first render
     */
    const { result } = renderHook(() => useChat())

    expect(result.current.messages).toEqual([])
    expect(result.current.loading).toBe(false)
    expect(result.current.error).toBe(null)
  })

  // ========================================================================
  // addMessage Tests
  // ========================================================================

  it('should add a message to the messages array', () => {
    /**
     * WHY WE TEST THIS:
     * - addMessage is core state update
     * - Must add messages correctly
     */
    const { result } = renderHook(() => useChat())

    act(() => {
      result.current.addMessage('user', 'Hello')
    })

    expect(result.current.messages).toHaveLength(1)
    expect(result.current.messages[0]).toEqual({
      role: 'user',
      content: 'Hello',
    })
  })

  it('should add multiple messages in order', () => {
    /**
     * WHY WE TEST THIS:
     * - Conversation requires message history
     * - Order matters for context
     */
    const { result } = renderHook(() => useChat())

    act(() => {
      result.current.addMessage('user', 'First')
      result.current.addMessage('assistant', 'Response')
      result.current.addMessage('user', 'Second')
    })

    expect(result.current.messages).toHaveLength(3)
    expect(result.current.messages[0].content).toBe('First')
    expect(result.current.messages[1].content).toBe('Response')
    expect(result.current.messages[2].content).toBe('Second')
  })

  // ========================================================================
  // sendUserMessage Tests
  // ========================================================================

  it('should send message and add to history', async () => {
    /**
     * WHY WE TEST THIS:
     * - Core chat functionality
     * - Must send message and handle response
     */
    const mockResponse = {
      response: 'Hello back!',
      confidence: 0.95,
    }
    apiModule.sendMessage.mockResolvedValue(mockResponse)

    const { result } = renderHook(() => useChat())

    await act(async () => {
      await result.current.sendUserMessage('Hello')
    })

    // Should have user message + assistant response
    expect(result.current.messages).toHaveLength(2)
    expect(result.current.messages[0].role).toBe('user')
    expect(result.current.messages[1].role).toBe('assistant')
  })

  it('should set loading state during API call', async () => {
    /**
     * WHY WE TEST THIS:
     * - Loading state shows spinner to user
     * - Must be true during request, false after
     */
    let resolveResponse
    const responsePromise = new Promise((resolve) => {
      resolveResponse = resolve
    })

    apiModule.sendMessage.mockReturnValue(responsePromise)

    const { result } = renderHook(() => useChat())

    // Start the async operation (don't await yet)
    act(() => {
      result.current.sendUserMessage('Test')
    })

    // Give it a moment to set loading to true
    await waitFor(() => {
      expect(result.current.loading).toBe(true)
    })

    // Resolve the API call
    act(() => {
      resolveResponse({ response: 'Answer' })
    })

    // Wait for loading to become false
    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })
  })

  it('should clear error after successful message', async () => {
    /**
     * WHY WE TEST THIS:
     * - Error state must be cleared on success
     * - Prevents stale errors from previous requests
     */
    apiModule.sendMessage.mockResolvedValue({ response: 'Success' })

    const { result } = renderHook(() => useChat())

    // Send message (should succeed)
    await act(async () => {
      await result.current.sendUserMessage('New message')
    })

    // Error should be cleared
    expect(result.current.error).toBeNull()
  })

  it('should handle API errors', async () => {
    /**
     * WHY WE TEST THIS:
     * - API calls can fail
     * - Must show error to user
     */
    const error = new Error('Network error')
    apiModule.sendMessage.mockRejectedValue(error)

    const { result } = renderHook(() => useChat())

    // Act & Assert
    await act(async () => {
      try {
        await result.current.sendUserMessage('Test')
      } catch (e) {
        // Expected to throw
      }
    })

    expect(result.current.error).toBe('Network error')
  })

  it('should pass tone to API', async () => {
    /**
     * WHY WE TEST THIS:
     * - Tone changes LLM behavior
     * - Must be passed correctly
     */
    apiModule.sendMessage.mockResolvedValue({ response: 'Response' })

    const { result } = renderHook(() => useChat())

    await act(async () => {
      await result.current.sendUserMessage('Test', 'casual')
    })

    expect(apiModule.sendMessage).toHaveBeenCalledWith(
      'Test',
      'casual',
      expect.any(Array),
      expect.any(Boolean)
    )
  })

  it('should format conversation history correctly', async () => {
    /**
     * WHY WE TEST THIS:
     * - Backend expects specific format
     * - Must extract response from assistant objects
     */
    apiModule.sendMessage.mockResolvedValue({
      response: 'New response',
    })

    const { result } = renderHook(() => useChat())

    // Add messages
    act(() => {
      result.current.addMessage('user', 'First')
      result.current.addMessage('assistant', { response: 'First answer' })
    })

    // Send follow-up
    await act(async () => {
      await result.current.sendUserMessage('Follow-up')
    })

    // Check history passed to API
    const callArgs = apiModule.sendMessage.mock.calls[0]
    const historyArg = callArgs[2]

    expect(historyArg).toEqual([
      { role: 'user', content: 'First' },
      { role: 'assistant', content: 'First answer' },
    ])
  })

  // ========================================================================
  // clearChat Tests
  // ========================================================================

  it('should clear all messages', async () => {
    /**
     * WHY WE TEST THIS:
     * - Clear button is important UX feature
     * - Must reset conversation
     */
    const { result } = renderHook(() => useChat())

    // Add messages
    act(() => {
      result.current.addMessage('user', 'Message 1')
      result.current.addMessage('assistant', 'Response 1')
    })

    expect(result.current.messages).toHaveLength(2)

    // Clear
    act(() => {
      result.current.clearChat()
    })

    expect(result.current.messages).toHaveLength(0)
  })

  it('should clear error on chat clear', async () => {
    /**
     * WHY WE TEST THIS:
     * - Error should disappear when user clears
     * - Fresh start should have no error
     */
    apiModule.sendMessage.mockRejectedValue(new Error('Some error'))

    const { result } = renderHook(() => useChat())

    // Trigger an error
    await act(async () => {
      try {
        await result.current.sendUserMessage('Test')
      } catch (e) {
        // Expected to throw
      }
    })

    expect(result.current.error).toBe('Some error')

    // Clear chat
    act(() => {
      result.current.clearChat()
    })

    expect(result.current.error).toBeNull()
  })

  it('should add user message immediately on send', async () => {
    /**
     * WHY WE TEST THIS:
     * - User message should appear instantly
     * - Don't wait for API response
     */
    apiModule.sendMessage.mockImplementation(
      () =>
        new Promise((resolve) =>
          setTimeout(() => resolve({ response: 'Delayed response' }), 1000)
        )
    )

    const { result } = renderHook(() => useChat())

    // Send message
    act(() => {
      result.current.sendUserMessage('Hello')
    })

    // User message should be there immediately
    expect(result.current.messages).toHaveLength(1)
    expect(result.current.messages[0].role).toBe('user')
    expect(result.current.messages[0].content).toBe('Hello')
  })
})