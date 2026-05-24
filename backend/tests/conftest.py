# backend/tests/conftest.py

import pytest
import sys
from pathlib import Path

# Add backend root to path so we can import modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import PERSONAL_KEYWORDS, DOMAIN_KEYWORDS
from modules.classifier import Classifier
from modules.retriever import Retriever


# ============================================================================
# FIXTURES (Reusable test setup)
# ============================================================================

@pytest.fixture
def classifier():
    """Provide a Classifier instance for tests"""
    return Classifier()


@pytest.fixture
def retriever():
    """Provide a Retriever instance for tests"""
    return Retriever()


@pytest.fixture
def sample_kb():
    """Provide sample KB data for testing retriever"""
    return {
        "projects": [
            {
                "id": "credit_scoring",
                "title": "Credit Scoring Model",
                "description": "Built a credit scoring system",
                "keywords": ["credit", "scoring", "model", "fintech"],
                "type": "project",
            },
            {
                "id": "esg_modeling",
                "title": "ESG Modeling System",
                "description": "Built ESG compliance tool",
                "keywords": ["esg", "modeling", "compliance", "sustainability"],
                "type": "project",
            },
        ],
        "experience": [
            {
                "id": "devoteam",
                "company": "Devoteam",
                "role": "Senior Data Scientist",
                "keywords": ["devoteam", "senior", "data scientist"],
                "type": "experience",
            },
        ],
        "certifications": [],
        "education": [],
        "contacts": {},
    }


@pytest.fixture
def sample_questions():
    """Provide sample questions for testing"""
    return {
        "personal": "What's your favorite hobby?",
        "domain": "Did you work with credit scoring?",
        "ambiguous": "Tell me something interesting",
    }


# ============================================================================
# MARKS (For organizing tests)
# ============================================================================

def pytest_configure(config):
    """Register custom markers"""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )