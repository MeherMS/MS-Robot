# backend/modules/retriever.py

from config import DOMAIN_KEYWORDS

class Retriever:
    """
    KB Retrieval using keyword matching
    Returns best match from KB based on keyword overlap
    """

    def search(self, question: str, kb: dict) -> tuple:
        """
        Search KB for best match using keyword overlap
        
        Args:
            question: User's question
            kb: Knowledge base dictionary
        
        Returns:
            (kb_entry, score) where:
            - kb_entry: Best matching entry (dict) or None
            - score: Confidence score (0.0 - 1.0)
        """
        
        if not kb:
            return None, 0.0
        
        # Extract keywords from question
        q_keywords = self._extract_keywords(question)
        
        if not q_keywords:
            return None, 0.0
        
        all_matches = []
        
        # ====================================================================
        # Search projects
        # ====================================================================
        projects = kb.get("projects", [])
        for project in projects:
            score = self._calculate_score(q_keywords, project)
            if score > 0:
                # Add type to entry for formatter
                project_with_type = dict(project)
                project_with_type["type"] = "project"
                all_matches.append((project_with_type, score))
        
        # ====================================================================
        # Search experiences
        # ====================================================================
        experiences = kb.get("experience", [])
        for exp in experiences:
            score = self._calculate_score(q_keywords, exp)
            if score > 0:
                # Add type to entry for formatter
                exp_with_type = dict(exp)
                exp_with_type["type"] = "experience"
                all_matches.append((exp_with_type, score))
        
        # ====================================================================
        # Search skills
        # ====================================================================
        skills = kb.get("skills", [])
        for skill_category in skills:
            items = skill_category.get("items", [])
            for skill in items:
                score = self._calculate_score(q_keywords, skill)
                if score > 0:
                    # Format skill as entry
                    skill_with_type = {
                        "type": "skill",
                        "title": skill.get("name", ""),
                        "description": f"Proficiency: {skill.get('proficiency', 'unknown')}",
                        "keywords": [skill.get("name", "").lower()],
                    }
                    all_matches.append((skill_with_type, score))
        
        # Return best match or None
        if all_matches:
            best_match = max(all_matches, key=lambda x: x[1])
            return best_match[0], best_match[1]
        
        return None, 0.0

    def _extract_keywords(self, text: str) -> list:
        """
        Extract lowercase keywords from text
        
        Returns list of words (split by spaces, stripped of punctuation)
        """
        import re
        # Remove punctuation and split into words
        words = re.findall(r'\b\w+\b', text.lower())
        return words

    def _calculate_score(self, q_keywords: list, kb_entry: dict) -> float:
        """
        Calculate keyword overlap score between question and KB entry
        
        Score = (matching keywords) / (total keywords in entry)
        
        Args:
            q_keywords: Keywords extracted from question
            kb_entry: KB entry (project, experience, skill, etc.)
        
        Returns:
            Score between 0.0 and 1.0
        """
        
        # Get all keywords from entry
        entry_keywords = kb_entry.get("keywords", [])
        
        if not entry_keywords:
            return 0.0
        
        # Convert to lowercase for comparison
        entry_keywords_lower = [k.lower() for k in entry_keywords]
        
        # Count matches
        matches = sum(1 for keyword in q_keywords if keyword in entry_keywords_lower)
        
        # Score = matches / total entry keywords
        score = matches / len(entry_keywords_lower) if entry_keywords_lower else 0.0
        
        return min(score, 1.0)  # Cap at 1.0