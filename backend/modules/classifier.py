# backend/modules/classifier.py

from config import PERSONAL_KEYWORDS, DOMAIN_KEYWORDS

class Classifier:
    """
    Classifies user intent (personal/domain/ambiguous)
    Uses keyword-based Tier 1 detection
    """

    def classify(self, question: str) -> str:
        """
        Classify user question intent
        
        Args:
            question: User's question
        
        Returns:
            "personal" | "domain" | "ambiguous"
        """
        
        question_lower = question.lower()
        
        # ====================================================================
        # Check for personal keywords
        # ====================================================================
        for keyword in PERSONAL_KEYWORDS:
            if keyword.lower() in question_lower:
                return "personal"
        
        # ====================================================================
        # Check for domain keywords
        # ====================================================================
        for keyword in DOMAIN_KEYWORDS:
            if keyword.lower() in question_lower:
                return "domain"
        
        # ====================================================================
        # Default to ambiguous if no matches
        # ====================================================================
        return "ambiguous"