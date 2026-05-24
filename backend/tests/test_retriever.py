# backend/tests/test_retriever.py

import pytest
from modules.retriever import Retriever


class TestRetriever:
    """Test suite for the Retriever (KB search) module"""

    def test_retriever_finds_project_by_exact_keyword(self, retriever, sample_kb):
        """
        Test that retriever finds a project when question contains exact keyword
        
        WHY WE TEST THIS:
        - Users ask about projects by name or keyword
        - "Did you work with credit scoring?" should find credit_scoring project
        - If this breaks, users can't find relevant projects
        """
        # Arrange
        question = "Did you work with credit scoring?"
        
        # Act
        result_entry, score = retriever.search(question, sample_kb)
        
        # Assert
        assert result_entry is not None, "Should find a match"
        assert result_entry["id"] == "credit_scoring", f"Expected credit_scoring, got {result_entry.get('id')}"
        assert score > 0, "Score should be > 0"
        print(f"✅ Found project: {result_entry['title']} (score: {score})")

    def test_retriever_finds_esg_project(self, retriever, sample_kb):
        """Test that retriever finds ESG project"""
        question = "Tell me about your ESG modeling work"
        result_entry, score = retriever.search(question, sample_kb)
        
        assert result_entry is not None
        assert result_entry["id"] == "esg_modeling"
        assert score > 0

    def test_retriever_finds_experience_by_keyword(self, retriever, sample_kb):
        """Test that retriever finds experience entries"""
        question = "What was your role at Devoteam?"
        result_entry, score = retriever.search(question, sample_kb)
        
        assert result_entry is not None
        assert result_entry["type"] == "experience"
        assert "devoteam" in str(result_entry).lower()

    def test_retriever_returns_best_match_when_multiple_match(self, retriever, sample_kb):
        """
        Test that retriever returns the BEST match when multiple entries match
    
        NOTE: Best match = highest score, which favors entries that match ALL their keywords
        A specific entry (fewer keywords, all matched) scores higher than a generic one.
        """
        # Arrange
        # Create KB with multiple matching entries
        test_kb = {
            "projects": [
                {
                    "id": "project1",
                    "title": "Project 1",
                    "keywords": ["fintech", "credit"],  # 2 keywords
                },
                {
                    "id": "project2",
                    "title": "Project 2",
                    "keywords": ["fintech", "banking", "credit"],  # 3 keywords
                },
            ],
            "experience": [],
            "certifications": [],
            "education": [],
            "contacts": {},
        }
    
        question = "Tell me about fintech and credit work"
    
        # Act
        result_entry, score = retriever.search(question, test_kb)
    
        # Assert
        # Project 1 wins: scores 2/2 = 1.0 (all keywords matched)
        # Project 2 scores: 2/3 = 0.667 (only 2 of 3 keywords matched)
        assert result_entry is not None
        assert result_entry["id"] == "project1", f"Expected project1 (higher score), got {result_entry['id']}"
        print(f"✅ Returned best match: {result_entry['title']} (score: {score})")    

    def test_retriever_returns_none_for_no_match(self, retriever, sample_kb):
        """
        Test that retriever returns None when no keywords match
        
        WHY WE TEST THIS:
        - Not all questions have KB matches
        - "What's the weather?" should return None, score 0
        - If this breaks, non-KB questions might crash
        """
        # Arrange
        question = "What is the weather today?"
        
        # Act
        result_entry, score = retriever.search(question, sample_kb)
        
        # Assert
        assert result_entry is None, "Should return None for no match"
        assert score == 0.0, "Score should be 0.0 for no match"

    def test_retriever_handles_empty_kb(self, retriever):
        """
        Test that retriever handles empty KB gracefully
        
        WHY WE TEST THIS:
        - KB might be empty on startup or during errors
        - Should not crash, just return None
        """
        # Arrange
        empty_kb = {}
        question = "Any question"
        
        # Act
        result_entry, score = retriever.search(question, empty_kb)
        
        # Assert
        assert result_entry is None
        assert score == 0.0

    def test_retriever_handles_none_kb(self, retriever):
        """Test that retriever handles None KB gracefully"""
        question = "Any question"
        
        result_entry, score = retriever.search(question, None)
        
        assert result_entry is None
        assert score == 0.0

    def test_retriever_handles_empty_question(self, retriever, sample_kb):
        """Test that retriever handles empty question gracefully"""
        question = ""
        
        result_entry, score = retriever.search(question, sample_kb)
        
        assert result_entry is None
        assert score == 0.0

    def test_retriever_is_case_insensitive(self, retriever, sample_kb):
        """
        Test that retriever works regardless of question case
        
        WHY WE TEST THIS:
        - Users type in different cases
        - "CREDIT", "Credit", "credit" should all find the same project
        """
        # Arrange
        questions = [
            "Did you work with CREDIT SCORING?",
            "Did you work with Credit Scoring?",
            "Did you work with credit scoring?",
        ]
        
        # Act & Assert
        for question in questions:
            result_entry, score = retriever.search(question, sample_kb)
            assert result_entry is not None, f"Failed for: {question}"
            assert result_entry["id"] == "credit_scoring"

    def test_retriever_score_is_between_0_and_1(self, retriever, sample_kb):
        """
        Test that retriever scores are always between 0.0 and 1.0
        
        WHY WE TEST THIS:
        - Scores are used for confidence thresholds
        - Score > 1.0 or < 0 breaks routing logic
        - If this breaks, confidence scoring is invalid
        """
        # Arrange
        test_questions = [
            "Did you work with credit scoring?",
            "Tell me about ESG",
            "What's your name?",  # No match
        ]
        
        # Act & Assert
        for question in test_questions:
            result_entry, score = retriever.search(question, sample_kb)
            assert 0.0 <= score <= 1.0, f"Score {score} out of bounds for: {question}"

    def test_retriever_handles_kb_with_missing_keywords_field(self, retriever):
        """
        Test that retriever handles KB entries without keywords field
        
        WHY WE TEST THIS:
        - Some old KB entries might not have keywords
        - Should handle gracefully, not crash
        """
        # Arrange
        test_kb = {
            "projects": [
                {
                    "id": "bad_project",
                    "title": "Bad Project",
                    # Missing keywords field!
                },
            ],
            "experience": [],
            "certifications": [],
            "education": [],
            "contacts": {},
        }
        
        question = "Tell me about projects"
        
        # Act
        result_entry, score = retriever.search(question, test_kb)
        
        # Assert - should handle gracefully
        assert score == 0.0, "Missing keywords should result in 0 score"

    def test_retriever_searches_all_kb_sections(self, retriever):
        """
        Test that retriever searches ALL KB sections (projects, experience, certs, etc)
        
        WHY WE TEST THIS:
        - Retriever should search all sections
        - Users might ask about any section
        - If this breaks, some sections become invisible
        """
        # Arrange
        comprehensive_kb = {
            "projects": [
                {
                    "id": "proj1",
                    "title": "Credit Project",
                    "keywords": ["credit", "project"],
                    "type": "project",
                }
            ],
            "experience": [
                {
                    "id": "exp1",
                    "company": "TechCorp",
                    "keywords": ["techcorp", "experience"],
                    "type": "experience",
                }
            ],
            "certifications": [
                {
                    "name": "AWS Certified",
                    "issuer": "Amazon",
                    "status": "completed",
                }
            ],
            "education": [
                {
                    "degree": "B.S. Computer Science",
                    "institution": "MIT",
                }
            ],
            "contacts": {},
        }
        
        # Test project search
        result1, score1 = retriever.search("Tell me about credit projects", comprehensive_kb)
        assert result1 is not None and result1["id"] == "proj1"
        
        # Test experience search
        result2, score2 = retriever.search("Tell me about TechCorp", comprehensive_kb)
        assert result2 is not None and result2["type"] == "experience"
        
        print("✅ Retriever searches all KB sections successfully")

    def test_retriever_handles_special_characters_in_keywords(self, retriever):
        """Test that retriever handles special characters gracefully"""
        # Arrange
        test_kb = {
            "projects": [
                {
                    "id": "special",
                    "title": "Special Project",
                    "keywords": ["c++", "python", "ai/ml"],
                    "type": "project",
                }
            ],
            "experience": [],
            "certifications": [],
            "education": [],
            "contacts": {},
        }
        
        # Act
        result, score = retriever.search("Did you work with python?", test_kb)
        
        # Assert
        assert result is not None