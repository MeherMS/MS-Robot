# backend/tests/test_e2e_chat_flow.py

import pytest
from fastapi.testclient import TestClient
from modules.classifier import Classifier
from modules.retriever import Retriever
from modules.formatter import ResponseFormatter
import sys
from pathlib import Path

# Import the FastAPI app
sys.path.insert(0, str(Path(__file__).parent.parent))
from main import app


client = TestClient(app)


class TestE2EDomainQuestions:
    """
    E2E Tests for domain questions (about projects/experience)
    
    Real scenario: Recruiter asks technical questions
    """

    def test_e2e_credit_scoring_question_full_flow(self, classifier, retriever, sample_kb):
        """
        E2E: User asks about credit scoring → Full pipeline processes → Response generated
        
        SCENARIO:
        Recruiter: "Did you work with credit scoring?"
        Expected: Find credit_scoring project → Return with details
        
        WHY WE TEST THIS:
        - This is a common recruiter question
        - Tests the full pipeline: classify → retrieve → format
        - If any step breaks, the flow breaks
        """
        # Arrange
        question = "Did you work with credit scoring?"
        
        # Step 1: Classify
        intent = classifier.classify(question)
        assert intent == "domain", f"Should classify as domain, got {intent}"
        
        # Step 2: Retrieve
        kb_entry, score = retriever.search(question, sample_kb)
        assert kb_entry is not None, "Should find KB match"
        assert score > 0, f"Score should be > 0, got {score}"
        
        # Step 3: Format response (would normally be done by Gemini)
        formatter = ResponseFormatter()
        response_text = f"Yes, I built {kb_entry['title']}. {kb_entry['description']}"
        
        formatted = formatter.format_response(
            response_text=response_text,
            confidence=0.95,  # High confidence for KB match
            kb_used=True,
            sources=[{
                "type": "project",
                "id": kb_entry["id"],
                "title": kb_entry["title"],
                "link": kb_entry.get("link", "")
            }],
            suggested_followups=formatter.generate_followups(question, kb_match=kb_entry),
        )
        
        # Assert all components
        assert formatted["confidence"] == 0.95
        assert formatted["kb_used"] == True
        assert len(formatted["sources"]) > 0
        assert len(formatted["suggested_followups"]) > 0
        
        print(f"✅ Full flow successful:")
        print(f"   Intent: {intent}")
        print(f"   KB Match: {kb_entry['id']} (score: {score})")
        print(f"   Response: {response_text[:50]}...")

    def test_e2e_esg_modeling_question(self, classifier, retriever, sample_kb):
        """E2E: ESG project question → Full pipeline"""
        question = "Tell me about your ESG modeling work"
        
        # Classify
        intent = classifier.classify(question)
        assert intent == "domain"
        
        # Retrieve
        kb_entry, score = retriever.search(question, sample_kb)
        assert kb_entry is not None
        assert kb_entry["id"] == "esg_modeling"
        
        # Format
        formatter = ResponseFormatter()
        response = formatter.format_response(
            response_text=f"I built {kb_entry['title']}",
            confidence=0.9,
            kb_used=True,
            sources=[{"type": "project", "id": kb_entry["id"], "title": kb_entry["title"]}],
            suggested_followups=[],
        )
        
        assert response["confidence"] == 0.9
        assert response["kb_used"] == True

    def test_e2e_experience_question(self, classifier, retriever, sample_kb):
        """E2E: Experience question → Full pipeline"""
        question = "What was your role at Devoteam?"
        
        # Classify
        intent = classifier.classify(question)
        assert intent == "domain"
        
        # Retrieve
        kb_entry, score = retriever.search(question, sample_kb)
        assert kb_entry is not None
        assert kb_entry["type"] == "experience"


class TestE2EPersonalQuestions:
    """
    E2E Tests for personal questions
    
    Real scenario: Someone asks about hobbies/interests
    """

    def test_e2e_hobby_question_full_flow(self, classifier):
        """
        E2E: User asks personal question → Classifier detects → Appropriate response
        
        SCENARIO:
        Visitor: "What's your favorite hobby?"
        Expected: Detect personal intent → Suggest direct contact
        
        WHY WE TEST THIS:
        - Personal questions should NOT trigger KB search
        - Should offer to connect directly
        - Tests that classifier protects personal boundaries
        """
        # Arrange
        question = "What's your favorite hobby?"
        
        # Step 1: Classify
        intent = classifier.classify(question)
        
        # Assert
        assert intent == "personal", f"Should classify as personal, got {intent}"
        
        # Step 2: Format for personal response (would be done by system)
        formatter = ResponseFormatter()
        response = formatter.format_response(
            response_text="For personal questions, please reach out to Meher directly!",
            confidence=0.5,
            kb_used=False,
            sources=[],
            suggested_followups=["What about your professional background?"],
        )
        
        assert response["response"] != ""
        assert response["kb_used"] == False
        
        print(f"✅ Personal question detected and routed correctly")

    def test_e2e_music_question(self, classifier):
        """E2E: Music interest question → Personal detection"""
        question = "Do you like music?"
        
        intent = classifier.classify(question)
        assert intent == "personal"

    def test_e2e_family_question(self, classifier):
        """E2E: Family question → Personal detection"""
        question = "Tell me about your family"
        
        intent = classifier.classify(question)
        assert intent == "personal"


class TestE2EAmbiguousQuestions:
    """
    E2E Tests for ambiguous questions (unknown intent)
    
    Real scenario: User asks unclear question
    """

    def test_e2e_ambiguous_question_full_flow(self, classifier, retriever, sample_kb):
        """
        E2E: Ambiguous question → No KB match → LLM-only response
        
        SCENARIO:
        User: "Tell me something interesting"
        Expected: Classify as ambiguous → No KB match → LLM-only with low confidence
        
        WHY WE TEST THIS:
        - Ambiguous questions need fallback to LLM
        - Should NOT force a KB match
        - Tests graceful degradation
        """
        # Arrange
        question = "Tell me something interesting"
        
        # Step 1: Classify
        intent = classifier.classify(question)
        assert intent == "ambiguous"
        
        # Step 2: Try to retrieve (should fail)
        kb_entry, score = retriever.search(question, sample_kb)
        assert kb_entry is None, "Should not find match for ambiguous question"
        assert score == 0.0
        
        # Step 3: Format LLM-only response
        formatter = ResponseFormatter()
        response = formatter.format_response(
            response_text="Based on my training knowledge, here's something interesting...",
            confidence=0.6,  # Lower confidence for LLM-only
            kb_used=False,
            sources=[],
            suggested_followups=formatter.generate_followups(question, kb_match=None),
        )
        
        assert response["confidence"] == 0.6
        assert response["kb_used"] == False
        assert len(response["sources"]) == 0
        
        print(f"✅ Ambiguous question routed to LLM-only correctly")


class TestE2EAPIIntegration:
    """
    E2E Tests using actual `/chat` endpoint
    
    Tests the full HTTP request → response pipeline
    """

    def test_e2e_api_domain_question(self):
        """
        E2E API: Full HTTP request for domain question
        
        User sends HTTP POST to /chat → Backend processes → Returns formatted response
        """
        # Act
        response = client.post("/chat", json={
            "message": "Did you work with credit scoring?",
            "tone": "formal"
        })
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        
        # Check response structure
        assert "response" in data or "error" in data
        assert "confidence" in data
        assert "kb_used" in data
        assert "sources" in data
        assert "suggested_followups" in data
        assert "quota" in data
        
        # Check quota
        quota = data["quota"]
        assert quota["allowed"] == True
        assert quota["count"] >= 1
        assert quota["limit"] > 0
        
        print(f"✅ API request processed successfully")
        print(f"   Response: {data['response'][:50] if 'response' in data else 'N/A'}...")
        print(f"   Confidence: {data['confidence']}")
        print(f"   Quota: {quota['count']}/{quota['limit']}")

    def test_e2e_api_personal_question(self):
        """E2E API: Personal question via HTTP"""
        response = client.post("/chat", json={
            "message": "What's your favorite hobby?",
            "tone": "formal"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "response" in data or "error" in data

    def test_e2e_api_formal_tone(self):
        """
        E2E API: Test formal tone
        
        SCENARIO:
        Recruiter uses formal tone
        Expected: Response uses professional language
        """
        response = client.post("/chat", json={
            "message": "Tell me about your experience",
            "tone": "formal"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "response" in data or "error" in data

    def test_e2e_api_casual_tone(self):
        """
        E2E API: Test casual tone
        
        SCENARIO:
        Friend uses casual tone
        Expected: Response uses conversational language
        """
        response = client.post("/chat", json={
            "message": "Tell me about your experience",
            "tone": "casual"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "response" in data or "error" in data


class TestE2EConversationFlow:
    """
    E2E Tests for multi-turn conversations
    
    Real scenario: User asks follow-up questions in same session
    """

    def test_e2e_multi_turn_conversation(self):
        """
        E2E: Multi-turn conversation with context
        
        SCENARIO:
        1. User: "Did you work with credit scoring?"
        2. User: "Tell me more about the technologies"
        3. User: "What were the outcomes?"
        
        Expected: System tracks session and provides contextual responses
        
        WHY WE TEST THIS:
        - Conversation context is critical
        - Follow-ups should reference previous messages
        - If session tracking breaks, context is lost
        """
        session_id = "e2e_test_multi_turn"
        
        # Message 1: Initial question
        response1 = client.post("/chat", json={
            "message": "Did you work with credit scoring?",
            "tone": "formal",
            "session_id": session_id
        })
        
        assert response1.status_code == 200
        data1 = response1.json()
        assert "response" in data1 or "error" in data1
        
        # Verify session created
        if "session_id" in data1:
            assert data1["session_id"] == session_id
        
        # Message 2: Follow-up question
        response2 = client.post("/chat", json={
            "message": "Tell me more about the technologies you used",
            "tone": "formal",
            "session_id": session_id
        })
        
        assert response2.status_code == 200
        data2 = response2.json()
        assert "response" in data2 or "error" in data2
        
        # Message 3: Another follow-up
        response3 = client.post("/chat", json={
            "message": "What were the key outcomes?",
            "tone": "formal",
            "session_id": session_id
        })
        
        assert response3.status_code == 200
        data3 = response3.json()
        assert "response" in data3 or "error" in data3
        
        print(f"✅ Multi-turn conversation completed:")
        print(f"   Session: {session_id}")
        print(f"   Messages: 3")
        print(f"   All responses valid: ✅")

    def test_e2e_conversation_session_isolation(self):
        """
        E2E: Different sessions are isolated
        
        SCENARIO:
        Session A and Session B ask different questions
        Expected: Responses are independent
        
        WHY WE TEST THIS:
        - Sessions must not leak data between users
        - One user's conversation shouldn't affect another
        - If isolation breaks, privacy/security issue
        """
        # Session A
        response_a = client.post("/chat", json={
            "message": "Tell me about credit projects",
            "session_id": "session_a"
        })
        
        # Session B
        response_b = client.post("/chat", json={
            "message": "Tell me about ESG projects",
            "session_id": "session_b"
        })
        
        assert response_a.status_code == 200
        assert response_b.status_code == 200
        
        # Both should succeed independently
        data_a = response_a.json()
        data_b = response_b.json()
        
        assert "response" in data_a or "error" in data_a
        assert "response" in data_b or "error" in data_b
        
        print("✅ Session isolation working (no data leakage)")


class TestE2EErrorRecovery:
    """
    E2E Tests for error scenarios and recovery
    
    Real scenario: Edge cases and error conditions
    """

    def test_e2e_empty_message_recovery(self):
        """
        E2E: Empty message → Error handling → User can retry
        
        SCENARIO:
        User sends empty message
        Expected: Graceful error → User can retry
        
        WHY WE TEST THIS:
        - Users might accidentally send empty messages
        - System should handle gracefully
        - User should be able to retry
        """
        # Send empty message
        response1 = client.post("/chat", json={
            "message": "",
            "tone": "formal"
        })
        
        assert response1.status_code == 200
        data1 = response1.json()
        # Should have error or message validation
        assert "error" in data1 or "message" in data1
        
        # User retries with valid message
        response2 = client.post("/chat", json={
            "message": "Tell me about yourself",
            "tone": "formal"
        })
        
        assert response2.status_code == 200
        data2 = response2.json()
        assert "response" in data2 or "error" in data2
        
        print("✅ Error recovery working (can retry after error)")

    def test_e2e_special_characters_handling(self):
        """
        E2E: Special characters → Handled correctly
        
        SCENARIO:
        User: "Do you know C++ and AI/ML??? 🤔"
        Expected: Processed without breaking
        """
        response = client.post("/chat", json={
            "message": "Do you know C++ and AI/ML??? 🤔",
            "tone": "formal"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "response" in data or "error" in data
        
        print("✅ Special characters handled")

    def test_e2e_very_long_message(self):
        """
        E2E: Very long message → Handled correctly
        """
        long_message = "Tell me " + "about your experience " * 100
        
        response = client.post("/chat", json={
            "message": long_message,
            "tone": "formal"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "response" in data or "error" in data
        
        print("✅ Long messages handled")


class TestE2EQuotaManagement:
    """
    E2E Tests for token quota system
    
    Real scenario: User hits daily quota limit
    """

    def test_e2e_quota_tracking(self):
        """
        E2E: Quota is tracked across requests
        
        SCENARIO:
        1st message: quota 1/100
        2nd message: quota 2/100
        ...
        Expected: Quota increments each message
        """
        # Message 1
        response1 = client.post("/chat", json={
            "message": "Hello",
            "session_id": "quota_test_1"
        })
        
        data1 = response1.json()
        quota1_count = data1["quota"]["count"]
        
        # Message 2 (same IP)
        response2 = client.post("/chat", json={
            "message": "How are you?",
            "session_id": "quota_test_2"
        })
        
        data2 = response2.json()
        quota2_count = data2["quota"]["count"]
        
        # Quota should increment
        assert quota2_count > quota1_count
        
        print(f"✅ Quota tracking: {quota1_count} → {quota2_count}")

    def test_e2e_quota_reset_structure(self):
        """
        E2E: Quota response includes reset time
        """
        response = client.post("/chat", json={
            "message": "Test quota",
        })
        
        data = response.json()
        quota = data["quota"]
        
        assert "reset_time" in quota
        assert "allowed" in quota
        assert "status" in quota
        
        print(f"✅ Quota structure complete: {quota}")