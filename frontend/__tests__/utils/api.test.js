// frontend/__tests__/utils/api.test.js

describe('API Utilities', () => {
  let sendMessage
  let getKBStats
  let mockPost
  let mockGet
  let mockAxiosInstance

  beforeEach(() => {
    // Clear all mocks and modules before each test
    jest.clearAllMocks()
    jest.resetModules()

    // Now mock axios
    jest.mock('axios')
    const axios = require('axios').default

    // Create mock methods
    mockPost = jest.fn()
    mockGet = jest.fn()

    // Create mock axios instance
    mockAxiosInstance = {
      post: mockPost,
      get: mockGet,
    }

    // Mock axios.create
    axios.create = jest.fn().mockReturnValue(mockAxiosInstance)

    // NOW import the api module (after mocking axios)
    const apiModule = require('@/utils/api')
    sendMessage = apiModule.sendMessage
    getKBStats = apiModule.getKBStats
  })

  // ========================================================================
  // sendMessage Tests
  // ========================================================================

  describe('sendMessage', () => {
    it('should send a message and return response data', async () => {
      /**
       * WHY WE TEST THIS:
       * - sendMessage is the core API function
       * - Must correctly format request and parse response
       * - If broken, entire chat breaks
       */
      // Arrange
      const mockResponse = {
        response: 'Hello there!',
        confidence: 0.95,
        kb_used: true,
        sources: [],
        suggested_followups: ['Question 1', 'Question 2'],
        quota: {
          allowed: true,
          count: 1,
          limit: 100,
          remaining: 99,
          status: 'ok',
        },
      }

      mockPost.mockResolvedValue({ data: mockResponse })

      // Act
      const result = await sendMessage('Hello', 'formal')

      // Assert
      expect(result).toEqual(mockResponse)
      expect(result.response).toBe('Hello there!')
      expect(result.confidence).toBe(0.95)
    })

    it('should include conversation history in request', async () => {
      /**
       * WHY WE TEST THIS:
       * - Context requires conversation history
       * - Must pass full history to backend
       * - If broken, follow-ups lose context
       */
      // Arrange
      mockPost.mockResolvedValue({
        data: { response: 'Response' },
      })

      const conversationHistory = [
        { role: 'user', content: 'First message' },
        { role: 'assistant', content: 'First response' },
      ]

      // Act
      await sendMessage('Follow-up', 'formal', conversationHistory)

      // Assert
      expect(mockPost).toHaveBeenCalledWith(
        '/chat',
        expect.objectContaining({
          message: 'Follow-up',
          conversation_history: conversationHistory,
        })
      )
    })

    it('should include tone in request', async () => {
      /**
       * WHY WE TEST THIS:
       * - Tone affects LLM behavior
       * - Must pass tone correctly
       */
      mockPost.mockResolvedValue({
        data: { response: 'Response' },
      })

      // Act
      await sendMessage('Test', 'casual')

      // Assert
      expect(mockPost).toHaveBeenCalledWith(
        '/chat',
        expect.objectContaining({ tone: 'casual' })
      )
    })

    it('should handle timeout errors gracefully', async () => {
      /**
       * WHY WE TEST THIS:
       * - Long-running requests might timeout
       * - Should show user-friendly message
       * - If broken, users see cryptic errors
       */
      // Arrange
      const error = new Error('Request timeout')
      error.code = 'ECONNABORTED'
      mockPost.mockRejectedValue(error)

      // Act & Assert
      await expect(sendMessage('Test', 'formal')).rejects.toThrow(
        'Request timeout - backend took too long to respond'
      )
    })

    it('should handle backend not found error', async () => {
      /**
       * WHY WE TEST THIS:
       * - Backend might be offline
       * - Should tell user where to check
       */
      const error = new Error('Not found')
      error.response = { status: 404 }
      mockPost.mockRejectedValue(error)

      await expect(sendMessage('Test', 'formal')).rejects.toThrow(
        'Backend not found'
      )
    })

    it('should handle server error (500)', async () => {
      /**
       * WHY WE TEST THIS:
       * - Backend might have internal errors
       * - Should show error details to user
       */
      const error = new Error('Server error')
      error.response = {
        status: 500,
        data: { detail: 'Database connection failed' },
      }
      mockPost.mockRejectedValue(error)

      await expect(sendMessage('Test', 'formal')).rejects.toThrow(
        'Server error'
      )
    })

    it('should handle connection errors', async () => {
      /**
       * WHY WE TEST THIS:
       * - Network might be down
       * - Should show clear error message
       */
      const error = new Error('Network error')
      error.response = undefined // No response means network error
      mockPost.mockRejectedValue(error)

      await expect(sendMessage('Test', 'formal')).rejects.toThrow(
        'Cannot connect to backend'
      )
    })

    it('should handle invalid response structure', async () => {
      /**
       * WHY WE TEST THIS:
       * - Backend might return malformed data
       * - Should validate response
       */
      mockPost.mockResolvedValue({ data: null })

      await expect(sendMessage('Test', 'formal')).rejects.toThrow(
        'Invalid response structure'
      )
    })

    it('should include consent in request', async () => {
      /**
       * WHY WE TEST THIS:
       * - Privacy requires tracking consent
       * - Must pass consent status to backend
       */
      mockPost.mockResolvedValue({
        data: { response: 'Response' },
      })

      await sendMessage('Test', 'formal', [], true)

      expect(mockPost).toHaveBeenCalledWith(
        '/chat',
        expect.objectContaining({ consent_given: true })
      )
    })

    it('should validate response is an object', async () => {
      /**
       * WHY WE TEST THIS:
       * - Response must be valid JSON object
       * - Not a string, array, or other type
       */
      mockPost.mockResolvedValue({ data: 'string instead of object' })

      await expect(sendMessage('Test', 'formal')).rejects.toThrow(
        'Invalid response structure'
      )
    })
  })

  // ========================================================================
  // getKBStats Tests
  // ========================================================================

  describe('getKBStats', () => {
    it('should fetch KB stats successfully', async () => {
      /**
       * WHY WE TEST THIS:
       * - KB stats shown in footer
       * - Must fetch and display correctly
       */
      const mockStats = {
        total_projects: 5,
        total_experiences: 2,
        total_skills: 20,
        last_updated: '2026-05-01',
      }

      mockGet.mockResolvedValue({ data: mockStats })

      const result = await getKBStats()

      expect(result).toEqual(mockStats)
      expect(result.total_projects).toBe(5)
    })

    it('should return default values on error', async () => {
      /**
       * WHY WE TEST THIS:
       * - API might fail
       * - Should show reasonable defaults, not crash
       */
      mockGet.mockRejectedValue(new Error('Network error'))

      const result = await getKBStats()

      expect(result.total_projects).toBe(0)
      expect(result.total_experiences).toBe(0)
      expect(result.total_skills).toBe(0)
      expect(result.last_updated).toBe('unknown')
    })

    it('should call /kb/stats endpoint', async () => {
      /**
       * WHY WE TEST THIS:
       * - Must call correct endpoint
       */
      mockGet.mockResolvedValue({
        data: { total_projects: 5 },
      })

      await getKBStats()

      expect(mockGet).toHaveBeenCalledWith('/kb/stats')
    })

    it('should handle network errors gracefully', async () => {
      /**
       * WHY WE TEST THIS:
       * - Network can fail
       * - Should not crash app
       */
      mockGet.mockRejectedValue(new Error('Network timeout'))

      const result = await getKBStats()

      expect(result).toBeDefined()
      expect(result.last_updated).toBe('unknown')
    })
  })

  // ========================================================================
  // Integration Tests (sendMessage + getKBStats together)
  // ========================================================================

  describe('API Integration', () => {
    it('should handle multiple concurrent requests', async () => {
      /**
       * WHY WE TEST THIS:
       * - User might send message while KB stats loading
       * - Must not interfere with each other
       */
      mockPost.mockResolvedValue({
        data: { response: 'Response' },
      })
      mockGet.mockResolvedValue({
        data: { total_projects: 5 },
      })

      // Send both requests concurrently
      const [chatResult, statsResult] = await Promise.all([
        sendMessage('Test'),
        getKBStats(),
      ])

      expect(chatResult.response).toBe('Response')
      expect(statsResult.total_projects).toBe(5)
    })

    it('should maintain separate request/response handling', async () => {
      /**
       * WHY WE TEST THIS:
       * - Each request is independent
       * - Error in one shouldn't affect other
       */
      mockPost.mockResolvedValue({
        data: { response: 'Chat response' },
      })
      mockGet.mockRejectedValue(new Error('Stats API down'))

      // Chat should succeed even if stats fails
      const chatResult = await sendMessage('Test')
      expect(chatResult.response).toBe('Chat response')

      // Stats should return defaults gracefully
      const statsResult = await getKBStats()
      expect(statsResult.last_updated).toBe('unknown')
    })
  })
})