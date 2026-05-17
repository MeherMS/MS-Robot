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
        # Search certifications
        # ====================================================================
        certifications = kb.get("certifications", [])
        for cert in certifications:
            score = self._calculate_score(q_keywords, cert)
            if score > 0:
                # Format certification as entry
                cert_with_type = {
                    "type": "certification",
                    "title": cert.get("name", ""),
                    "description": f"Issued by: {cert.get('issuer', 'Unknown')}. Status: {cert.get('status', 'completed')}",
                    "keywords": [cert.get("name", "").lower(), cert.get("issuer", "").lower()],
                }
                all_matches.append((cert_with_type, score))
        # ====================================================================
        # Search contacts
        # ====================================================================
        contacts = kb.get("contacts", {})
        if contacts:
            # Create a searchable contacts entry
            contacts_entry = {
                "type": "contact",
                "title": "Contact Information",
                "description": self._format_contacts(contacts),
                "keywords": ["contact", "email", "phone", "linkedin", "github", "portfolio", "reach", "connect", "get in touch"],
                #"contact_data": contacts,
            }
    
            # Check if question is asking for contacts
            score = self._calculate_score(q_keywords, contacts_entry)
            if score > 0:
                all_matches.append((contacts_entry, score))
                
        # ====================================================================
        # Search education
        # ====================================================================
        education = kb.get("education", [])
        for edu in education:
            score = self._calculate_score(q_keywords, edu)
            if score > 0:
                # Format education as entry
                edu_with_type = {
                    "type": "education",
                    "title": edu.get("degree", ""),
                    "description": f"From: {edu.get('institution', 'Unknown')}",
                    "keywords": [edu.get("degree", "").lower(), edu.get("institution", "").lower()],
                }
                all_matches.append((edu_with_type, score))
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
        entry_keywords = kb_entry.get("keywords", [])
        if not entry_keywords:
            return 0.0
        
        entry_keywords_lower = [k.lower() for k in entry_keywords]
        matches = sum(1 for keyword in q_keywords if keyword in entry_keywords_lower)
        
        # FIX: Base the score on the minimum of entry keywords or query keywords 
        # so short, highly specific queries get a high confidence score.
        denominator = min(len(entry_keywords_lower), len(q_keywords))
        score = matches / denominator if denominator > 0 else 0.0
        
        return min(score, 1.0)

    def _format_contacts(self, contacts: dict) -> str:
        """Format contacts dictionary into readable text"""
        text = "You can reach me at:\n\n"
        for key, value in contacts.items():
            clean_key = key.rstrip(":").replace("_", " ").title()
            text += f"📧 **{clean_key}:** {value}\n"
        return text.strip()