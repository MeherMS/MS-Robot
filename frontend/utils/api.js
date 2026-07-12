import axios from 'axios'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

const apiClient = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 180000, // 30 second timeout
})

/**
 * Warmup backend by pinging /health with exponential backoff
 * Wakes up Render's sleeping container on first load
 * @returns {Promise<boolean>} true if backend is ready, false if timeout
 */
export const warmupBackend = async (maxRetries = 12, initialDelay = 500) => {
  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
  
  let delay = initialDelay
  let attempt = 0

  while (attempt < maxRetries) {
    try {
      const response = await fetch(`${API_URL}/health`, {
        method: 'GET',
        timeout: 5000,
      })

      if (response.ok) {
        console.log(`[Warmup] ✅ Backend ready after ${attempt} attempts`)
        return true
      }
    } catch (error) {
      // Backend not ready yet, will retry
      console.log(`[Warmup] Attempt ${attempt + 1}/${maxRetries} - Backend not ready, retrying in ${delay}ms`)
    }

    // Wait before next attempt (exponential backoff: 500ms → 1s → 2s → 4s...)
    await new Promise((resolve) => setTimeout(resolve, delay))
    delay = Math.min(delay * 2, 5000) // Cap at 5 seconds
    attempt++
  }

  console.warn(`[Warmup] ❌ Backend did not respond after ${maxRetries} attempts`)
  return false
}

export const sendMessage = async (message, tone = 'formal', conversationHistory = [], consentGiven = false) => {
  try {
    const response = await apiClient.post('/chat', {
      message,
      tone,
      conversation_history: conversationHistory,
      consent_given: consentGiven,
    })
    // Validate response structure
    if (!response.data || typeof response.data !== 'object') {
      throw new Error('Invalid response structure from server')
    }
    return response.data
  } catch (error) {
    console.error('API Error:', error)
    // Provide user-friendly error messages
    if (error.code === 'ECONNABORTED') {
      throw new Error('Request timeout - backend took too long to respond')
    }
    if (error.response?.status === 404) {
      throw new Error('Backend not found - is it running at ' + API_URL + '?')
    }
    if (error.response?.status === 500) {
      throw new Error('Server error - ' + (error.response.data?.detail || 'unknown error'))
    }
    if (!error.response) {
      throw new Error('Cannot connect to backend at ' + API_URL)
    }
    throw new Error(error.response?.data?.detail || error.message || 'Unknown error')
  }
}
export const getKBStats = async () => {
  try {
    const response = await apiClient.get('/kb/stats')
    return response.data
  } catch (error) {
    console.error('API Error fetching KB stats:', error)
    return {
      total_projects: 0,
      total_experiences: 0,
      total_skills: 0,
      last_updated: 'unknown',
    }
  }
}

export default apiClient