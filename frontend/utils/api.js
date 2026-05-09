import axios from 'axios'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

const apiClient = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 180000, // 30 second timeout
})

export const sendMessage = async (message, tone = 'formal', conversationHistory = []) => {
  try {
    const response = await apiClient.post('/chat', {
      message,
      tone,
      conversation_history: conversationHistory,
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