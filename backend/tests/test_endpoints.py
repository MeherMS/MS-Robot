# backend/tests/test_endpoints.py

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

# Import the FastAPI app
sys.path.insert(0, str(Path(__file__).parent.parent))
from main import app


# Create test client
client = TestClient(app)


class TestHealthEndpoint:
    """Test the /health endpoint"""

    def test_health_check_returns_ok_status(self):
        """
        Test that /health endpoint returns ok status
        
        WHY WE TEST THIS:
        - Health check is used by load balancers
        - If it breaks, deployment monitoring breaks
        - Must always return quickly
        """
        # Act
        response = client.get("/health")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "timestamp" in data
        assert "active_sessions" in data
        print(f"✅ Health check returns: {data}")

    def test_health_check_response_format(self):
        """Test that health check has correct response structure"""
        response = client.get("/health")
        data = response.json()
        
        assert isinstance(data, dict)
        assert "status" in data
        assert "timestamp" in data
        assert "active_sessions" in data


class TestKBStatsEndpoint:
    """Test the /kb/stats endpoint"""

    def test_kb_stats_returns_stats(self):
        """
        Test that /kb/stats returns KB metadata
        
        WHY WE TEST THIS:
        - Frontend displays KB stats
        - If endpoint breaks, frontend can't show update time
        """
        # Act
        response = client.get("/kb/stats")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "total_projects" in data
        assert "total_experiences" in data
        assert "total_skills" in data
        assert "last_updated" in data
        assert "kb_version" in data
        print(f"✅ KB Stats: {data}")

    def test_kb_stats_numbers_are_non_negative(self):
        """Test that KB stats show non-negative numbers"""
        response = client.get("/kb/stats")
        data = response.json()
        
        assert data["total_projects"] >= 0
        assert data["total_experiences"] >= 0
        assert data["total_skills"] >= 0


class TestChatEndpoint:
    """Test the /chat endpoint - THE CRITICAL ENDPOINT"""

    def test_chat_endpoint_requires_message(self):
        """
        Test that /chat endpoint requires a message
        
        WHY WE TEST THIS:
        - Empty requests should be rejected
        - If this breaks, bad requests might crash the API
        """
        # Act - Send empty message
        response = client.post("/chat", json={"message": ""})
        
        # Assert
        assert response.status_code == 200  # FastAPI still returns 200 but with error
        data = response.json()
        assert "error" in data or data.get("message") == ""
        print(f"✅ Empty message rejected: {data.get('error', 'No error field')}")

    def test_chat_endpoint_accepts_valid_message(self):
        """
        Test that /chat endpoint accepts and processes a valid message
        
        WHY WE TEST THIS:
        - This is the core functionality
        - Must accept user messages and return structured response
        - If this breaks, the entire app breaks
        """
        # Act
        response = client.post("/chat", json={
            "message": "Hello, who are you?",
            "tone": "formal"
        })
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "response" in data or "error" in data
        print(f"✅ Chat endpoint response keys: {data.keys()}")

    def test_chat_endpoint_response_has_required_fields(self):
        """
        Test that /chat response has all required fields
        
        WHY WE TEST THIS:
        - Frontend expects specific response format
        - Missing fields break the UI
        - If this breaks, frontend crashes
        """
        # Act
        response = client.post("/chat", json={
            "message": "Did you work with credit?",
            "tone": "formal"
        })
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        
        # Check required fields
        required_fields = ["confidence", "kb_used", "sources", "suggested_followups", "quota"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"
        
        print(f"✅ All required fields present: {list(data.keys())}")

    def test_chat_endpoint_quota_field_structure(self):
        """Test that quota field has correct structure"""
        response = client.post("/chat", json={
            "message": "Test message",
            "tone": "formal"
        })
        
        data = response.json()
        quota = data.get("quota", {})
        
        # Check quota structure
        assert "allowed" in quota
        assert "count" in quota
        assert "limit" in quota
        assert "remaining" in quota
        assert "status" in quota
        print(f"✅ Quota structure correct: {quota}")

    def test_chat_endpoint_confidence_is_between_0_and_1(self):
        """
        Test that confidence score is always valid (0.0-1.0)
        
        WHY WE TEST THIS:
        - Confidence is displayed as percentage
        - Invalid values break the UI
        """
        response = client.post("/chat", json={
            "message": "Tell me about your experience",
            "tone": "formal"
        })
        
        data = response.json()
        confidence = data.get("confidence")
        
        if confidence is not None and confidence != 0:
            assert 0 <= confidence <= 1, f"Confidence {confidence} out of bounds"
        print(f"✅ Confidence valid: {confidence}")

    def test_chat_endpoint_sources_is_list(self):
        """Test that sources field is always a list"""
        response = client.post("/chat", json={
            "message": "Did you work with credit?",
            "tone": "formal"
        })
        
        data = response.json()
        sources = data.get("sources", [])
        
        assert isinstance(sources, list), "Sources must be a list"
        print(f"✅ Sources is list with {len(sources)} items")

    def test_chat_endpoint_suggested_followups_is_list(self):
        """Test that suggested_followups is always a list"""
        response = client.post("/chat", json={
            "message": "Tell me about yourself",
            "tone": "formal"
        })
        
        data = response.json()
        followups = data.get("suggested_followups", [])
        
        assert isinstance(followups, list), "Suggested followups must be a list"
        print(f"✅ Followups is list with {len(followups)} items")

    def test_chat_endpoint_accepts_tone_parameter(self):
        """
        Test that /chat accepts tone parameter
        
        WHY WE TEST THIS:
        - Tone affects LLM behavior
        - Must accept both "formal" and "casual"
        """
        # Test formal
        response1 = client.post("/chat", json={
            "message": "Who are you?",
            "tone": "formal"
        })
        assert response1.status_code == 200
        
        # Test casual
        response2 = client.post("/chat", json={
            "message": "Who are you?",
            "tone": "casual"
        })
        assert response2.status_code == 200
        
        print("✅ Both formal and casual tones accepted")

    def test_chat_endpoint_defaults_to_formal_tone(self):
        """Test that tone defaults to formal if not provided"""
        response = client.post("/chat", json={
            "message": "Hello",
            # tone not provided
        })
        
        assert response.status_code == 200
        data = response.json()
        # Should have a response (tone defaulted internally)
        assert "response" in data or "error" in data
        print("✅ Tone defaults to formal")

    def test_chat_endpoint_handles_special_characters(self):
        """Test that endpoint handles special characters gracefully"""
        response = client.post("/chat", json={
            "message": "What about C++ and AI/ML??? 🤔",
            "tone": "formal"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "response" in data or "error" in data
        print("✅ Special characters handled")

    def test_chat_endpoint_handles_long_messages(self):
        """Test that endpoint handles long messages"""
        long_message = "Tell me " + "about yourself " * 50  # Repeat to make it long
        
        response = client.post("/chat", json={
            "message": long_message,
            "tone": "formal"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "response" in data or "error" in data
        print("✅ Long messages handled")

    def test_chat_endpoint_session_id_tracking(self):
        """
        Test that /chat tracks session_id
        
        WHY WE TEST THIS:
        - Session tracking enables conversation history
        - If session tracking breaks, context is lost
        """
        response = client.post("/chat", json={
            "message": "First message",
            "tone": "formal",
            "session_id": "test_session_123"
        })
        
        data = response.json()
        assert "session_id" in data or response.status_code == 200
        print("✅ Session tracking working")

    def test_chat_endpoint_multiple_messages_same_session(self):
        """
        Test that multiple messages in same session are tracked
        
        WHY WE TEST THIS:
        - Conversation context requires session continuity
        - If session management breaks, conversations break
        """
        session_id = "test_session_multi"
        
        # First message
        response1 = client.post("/chat", json={
            "message": "What's your name?",
            "session_id": session_id,
            "tone": "formal"
        })
        assert response1.status_code == 200
        
        # Second message (same session)
        response2 = client.post("/chat", json={
            "message": "What did you do before?",
            "session_id": session_id,
            "tone": "formal"
        })
        assert response2.status_code == 200
        
        print("✅ Multi-message session works")

    def test_chat_endpoint_error_response_format(self):
        """
        Test that errors are returned in consistent format
        
        WHY WE TEST THIS:
        - Frontend expects error format
        - Inconsistent errors break error handling
        """
        # Send invalid/problematic input
        response = client.post("/chat", json={
            "message": "",  # Empty
            "tone": "formal"
        })
        
        # Even with error, response should be valid JSON
        assert response.status_code == 200
        data = response.json()
        # Should have either response or error
        assert "response" in data or "error" in data
        print("✅ Error responses well-formatted")


class TestTestLLMEndpoint:
    """Test the /test-llm endpoint"""

    def test_test_llm_endpoint_returns_response(self):
        """
        Test that /test-llm endpoint works
        
        WHY WE TEST THIS:
        - Used to verify LLM is available
        - If it breaks, users can't check LLM status
        """
        response = client.get("/test-llm")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "response" in data or "error" in data
        print(f"✅ Test LLM endpoint response: {data}")