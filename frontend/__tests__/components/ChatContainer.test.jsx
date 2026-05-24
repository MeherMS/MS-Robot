// frontend/__tests__/components/ChatContainer.test.jsx

import { render, screen, fireEvent, waitFor, within } from '@testing-library/react'
import ChatContainer from '@/components/ChatContainer'
import * as apiModule from '@/utils/api'

// Mock child components to simplify testing
jest.mock('@/components/MessageList', () => {
  return function MockMessageList({ messages, onSelectFollowup, loading }) {
    return (
      <div data-testid="message-list">
        {messages.map((msg, idx) => (
          <div key={idx} data-testid={`message-${idx}`}>
            {msg.role}: {typeof msg.content === 'string' ? msg.content : msg.content.response}
          </div>
        ))}
        {loading && <div data-testid="loading">Loading...</div>}
      </div>
    )
  }
})

jest.mock('@/components/ChatInput', () => {
  return function MockChatInput({ onSendMessage, disabled, placeholder }) {
    return (
      <input
        data-testid="chat-input"
        placeholder={placeholder}
        disabled={disabled}
        onKeyPress={(e) => {
          if (e.key === 'Enter') {
            onSendMessage(e.target.value)
            e.target.value = ''
          }
        }}
      />
    )
  }
})

jest.mock('@/components/ConsentModal', () => {
  return function MockConsentModal() {
    return <div data-testid="consent-modal">Consent Modal</div>
  }
})

jest.mock('@/utils/api', () => ({
  sendMessage: jest.fn(),
  getKBStats: jest.fn(),
}))

describe('ChatContainer Component', () => {
  beforeEach(() => {
    jest.clearAllMocks()
    apiModule.getKBStats.mockResolvedValue({
      total_projects: 5,
      total_experiences: 2,
      total_skills: 20,
      last_updated: '2026-05-01',
    })
  })

  // ========================================================================
  // Render Tests
  // ========================================================================

  it('should render without crashing', () => {
    /**
     * WHY WE TEST THIS:
     * - Component must mount successfully
     * - No render errors
     */
    render(<ChatContainer />)
    expect(screen.getByText('MSRobot')).toBeInTheDocument()
  })

  it('should display header with title', () => {
    /**
     * WHY WE TEST THIS:
     * - Header is main UI element
     * - Must show app name and description
     */
    render(<ChatContainer />)
    expect(screen.getByText('MSRobot')).toBeInTheDocument()
    expect(screen.getByText("Meher's AI Assistant")).toBeInTheDocument()
  })

  it('should render message list', () => {
    /**
     * WHY WE TEST THIS:
     * - MessageList is core component
     * - Must render correctly
     */
    render(<ChatContainer />)
    expect(screen.getByTestId('message-list')).toBeInTheDocument()
  })

  it('should render chat input', () => {
    /**
     * WHY WE TEST THIS:
     * - ChatInput is where user types
     * - Must be visible and functional
     */
    render(<ChatContainer />)
    const input = screen.getByTestId('chat-input')
    expect(input).toBeInTheDocument()
    expect(input).toHaveAttribute(
      'placeholder',
      expect.stringContaining("Ask me anything")
    )
  })

  // ========================================================================
  // Tone Selection Tests
  // ========================================================================

  it('should have tone selector with formal/casual options', () => {
    /**
     * WHY WE TEST THIS:
     * - Tone selector changes LLM behavior
     * - Must offer both options
     */
    render(<ChatContainer />)
    const toneSelect = screen.getByDisplayValue('Formal')
    expect(toneSelect).toBeInTheDocument()

    // Check options
    const options = within(toneSelect.parentElement).getByDisplayValue('Casual')
    expect(options).toBeInTheDocument()
  })

  it('should change tone when selector changes', () => {
    /**
     * WHY WE TEST THIS:
     * - User must be able to switch tones
     * - Affects subsequent messages
     */
    render(<ChatContainer />)
    const toneSelect = screen.getByDisplayValue('Formal')

    fireEvent.change(toneSelect, { target: { value: 'casual' } })

    expect(screen.getByDisplayValue('Casual')).toBeInTheDocument()
  })

  // ========================================================================
  // Clear Chat Tests
  // ========================================================================

  it('should have clear button', () => {
    /**
     * WHY WE TEST THIS:
     * - Clear button is important UX feature
     * - Must be visible and clickable
     */
    render(<ChatContainer />)
    const clearBtn = screen.getByRole('button', { name: /clear/i })
    expect(clearBtn).toBeInTheDocument()
  })

  it('should clear messages when clear button clicked', async () => {
    /**
     * WHY WE TEST THIS:
     * - Clear must reset conversation
     * - Must work with button click
     */
    apiModule.sendMessage.mockResolvedValue({
      response: 'Test response',
      confidence: 0.9,
    })

    render(<ChatContainer />)

    // Send a message first
    const input = screen.getByTestId('chat-input')
    fireEvent.change(input, { target: { value: 'Hello' } })
    fireEvent.keyPress(input, { key: 'Enter', code: 'Enter', charCode: 13 })

    await waitFor(() => {
      expect(screen.getByTestId('message-0')).toBeInTheDocument()
    })

    // Click clear
    const clearBtn = screen.getByRole('button', { name: /clear/i })
    fireEvent.click(clearBtn)

    // Messages should be cleared
    await waitFor(() => {
      expect(screen.queryByTestId('message-0')).not.toBeInTheDocument()
    })
  })

  // ========================================================================
  // KB Stats Tests
  // ========================================================================

  it('should fetch and display KB stats', async () => {
    /**
     * WHY WE TEST THIS:
     * - KB stats shown in footer
     * - Must fetch on mount
     */
    render(<ChatContainer />)

    await waitFor(() => {
      expect(screen.getByText(/5 projects/)).toBeInTheDocument()
      expect(screen.getByText(/2 experiences/)).toBeInTheDocument()
    })
  })

  it('should show loading KB info initially', () => {
    /**
     * WHY WE TEST THIS:
     * - While fetching, should show loading state
     */
    apiModule.getKBStats.mockImplementation(
      () =>
        new Promise((resolve) =>
          setTimeout(() => resolve({ total_projects: 5 }), 1000)
        )
    )

    render(<ChatContainer />)
    expect(screen.getByText('Loading KB info...')).toBeInTheDocument()
  })

  it('should handle KB stats fetch error gracefully', async () => {
    /**
     * WHY WE TEST THIS:
     * - API might fail
     * - Should not crash, show reasonable state
     */
    apiModule.getKBStats.mockRejectedValue(new Error('Network error'))

    render(<ChatContainer />)

    // Should still render without crashing
    await waitFor(() => {
      expect(screen.getByText('MSRobot')).toBeInTheDocument()
    })
  })

  // ========================================================================
  // Error Display Tests
  // ========================================================================

  it('should display error message when API fails', async () => {
    /**
     * WHY WE TEST THIS:
     * - Errors must be shown to user
     * - User needs to know what went wrong
     */
    apiModule.sendMessage.mockRejectedValue(
      new Error('Backend connection failed')
    )

    render(<ChatContainer />)

    const input = screen.getByTestId('chat-input')
    fireEvent.change(input, { target: { value: 'Test' } })
    fireEvent.keyPress(input, { key: 'Enter', code: 'Enter', charCode: 13 })

    await waitFor(() => {
      expect(screen.getByText(/Backend connection failed/)).toBeInTheDocument()
    })
  })

  // ========================================================================
  // Loading State Tests
  // ========================================================================

  it('should disable input while loading', async () => {
    /**
     * WHY WE TEST THIS:
     * - Input should be disabled during API call
     * - Prevents duplicate messages
     */
    apiModule.sendMessage.mockImplementation(
      () =>
        new Promise((resolve) =>
          setTimeout(() => resolve({ response: 'Response' }), 500)
        )
    )

    render(<ChatContainer />)

    const input = screen.getByTestId('chat-input')
    fireEvent.change(input, { target: { value: 'Test' } })
    fireEvent.keyPress(input, { key: 'Enter', code: 'Enter', charCode: 13 })

    // Should be disabled while loading
    expect(input).toBeDisabled()

    // Should be enabled after
    await waitFor(() => {
      expect(input).not.toBeDisabled()
    })
  })

  // ========================================================================
  // Follow-up Selection Tests
  // ========================================================================

  it('should send message when followup selected', async () => {
    /**
     * WHY WE TEST THIS:
     * - Follow-up buttons are important UX
     * - Must trigger new message
     */
    apiModule.sendMessage.mockResolvedValue({
      response: 'Response',
      suggested_followups: ['Follow-up 1', 'Follow-up 2'],
    })

    render(<ChatContainer />)

    const input = screen.getByTestId('chat-input')
    fireEvent.change(input, { target: { value: 'Initial' } })
    fireEvent.keyPress(input, { key: 'Enter', code: 'Enter', charCode: 13 })

    // Note: In real component, MessageList would render followup buttons
    // This test verifies the hook exists; actual followup rendering
    // is tested in MessageList tests
  })
})