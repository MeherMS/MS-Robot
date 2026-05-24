# backend/tests/test_classifier.py

import pytest
from modules.classifier import Classifier


class TestClassifier:
    """Test suite for the Classifier module"""

    def test_classifier_detects_personal_intent_with_hobby_keyword(self, classifier):
        """
        Test that classifier detects 'personal' intent when hobby keyword is present
        
        WHY WE TEST THIS:
        - The classifier must correctly identify personal questions
        - Personal questions should be routed to "ask Meher directly"
        - If this breaks, personal questions might get LLM-only responses
        """
        # Arrange (Setup)
        question = "What's your favorite hobby?"
        
        # Act (Execute)
        result = classifier.classify(question)
        
        # Assert (Verify)
        assert result == "personal", f"Expected 'personal', got '{result}'"
        print(f"✅ Test passed: '{question}' → '{result}'")

    def test_classifier_detects_personal_intent_with_music_keyword(self, classifier):
        """Test that 'music' keyword triggers personal intent"""
        question = "Do you like music?"
        result = classifier.classify(question)
        assert result == "personal"

    def test_classifier_detects_domain_intent_with_credit_keyword(self, classifier):
        """
        Test that classifier detects 'domain' intent when domain keyword is present
        
        WHY WE TEST THIS:
        - Domain questions should trigger KB search
        - Credit scoring is a key domain area for Meher
        - If this breaks, important project questions get LLM-only
        """
        # Arrange
        question = "Did you work with credit scoring?"
        
        # Act
        result = classifier.classify(question)
        
        # Assert
        assert result == "domain", f"Expected 'domain', got '{result}'"

    def test_classifier_detects_domain_intent_with_esg_keyword(self, classifier):
        """Test that 'esg' keyword triggers domain intent"""
        question = "Tell me about your ESG work"
        result = classifier.classify(question)
        assert result == "domain"

    def test_classifier_detects_domain_intent_with_build_keyword(self, classifier):
        """Test that 'build' keyword triggers domain intent"""
        question = "Can you build a machine learning model?"
        result = classifier.classify(question)
        assert result == "domain"

    def test_classifier_defaults_to_ambiguous_for_unclear_questions(self, classifier):
        """
        Test that classifier defaults to 'ambiguous' when no keywords match
        
        WHY WE TEST THIS:
        - Ambiguous questions should get LLM-only response
        - We need a fallback for unexpected questions
        - If this breaks, unexpected questions might crash
        """
        # Arrange
        question = "Tell me something interesting"
        
        # Act
        result = classifier.classify(question)
        
        # Assert
        assert result == "ambiguous"

    def test_classifier_is_case_insensitive(self, classifier):
        """
        Test that classifier works regardless of question case
        
        WHY WE TEST THIS:
        - Users type questions in different cases
        - "MUSIC", "Music", "music" should all work
        - If this breaks, uppercase questions break
        """
        # Arrange
        questions = [
            "What is your FAVORITE hobby?",  # All caps
            "What is your Favorite hobby?",  # Title case
            "what is your favorite hobby?",  # Lower case
        ]
        
        # Act & Assert
        for question in questions:
            result = classifier.classify(question)
            assert result == "personal", f"Failed for: {question}"

    def test_classifier_handles_empty_string(self, classifier):
        """Test that classifier handles empty string gracefully"""
        result = classifier.classify("")
        assert result == "ambiguous"

    def test_classifier_handles_whitespace_only(self, classifier):
        """Test that classifier handles whitespace-only string"""
        result = classifier.classify("   ")
        assert result == "ambiguous"

    def test_classifier_handles_special_characters(self, classifier):
        """Test that classifier works with special characters"""
        question = "Can you build something??? Maybe!!!"
        result = classifier.classify(question)
        assert result == "domain"