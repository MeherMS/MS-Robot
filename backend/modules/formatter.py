# backend/modules/formatter.py

from datetime import datetime
import json

class ResponseFormatter:
    """
    Formats responses with sources, confidence, and suggested followups
    """

    def get_timestamp(self) -> str:
        """Get current ISO timestamp"""
        return datetime.utcnow().isoformat() + "Z"

    def format_kb_entry(self, kb_entry: dict) -> str:
        """
        Format a KB entry (project or experience) into readable text
        
        Args:
            kb_entry: Dictionary with 'type', 'title', 'description', 'outcome', etc.
        
        Returns:
            Formatted string
        """
        entry_type = kb_entry.get("type", "project")
        title = kb_entry.get("title", "Unknown")
        description = kb_entry.get("description", "")
        outcome = kb_entry.get("outcome", "")
        technologies = kb_entry.get("technologies", [])
        
        text = f"**{title}**\n\n"
        
        if description:
            text += f"{description}\n\n"
        
        if technologies:
            tech_str = ", ".join(technologies)
            text += f"**Technologies:** {tech_str}\n\n"
        
        if outcome:
            text += f"**Outcome:** {outcome}\n"
        
        return text.strip()

    def format_source(self, kb_entry: dict) -> dict:
        """
        Format KB entry as a source citation
        
        Returns:
            {"type": "project|experience", "id": "...", "title": "...", "link": "..."}
        """
        entry_type = kb_entry.get("type", "project")
        return {
            "type": entry_type,
            "id": kb_entry.get("id", "unknown"),
            "title": kb_entry.get("title", "Unknown"),
            "link": kb_entry.get("link", ""),
        }

    def generate_followups(self, original_question: str, kb_match: dict = None) -> list:
        """
        Generate 2-3 suggested follow-up questions
        
        Args:
            original_question: The user's original question
            kb_match: The KB entry that was matched (if any)
        
        Returns:
            List of 2-3 suggested follow-up questions
        """
        followups = []
        
        if kb_match:
            title = kb_match.get("title", "")
            
            # Suggest follow-ups based on KB match
            followups.append(f"Tell me more about the technologies you used in {title}")
            followups.append(f"What were the key outcomes of {title}?")
            
            # Add a generic follow-up
            if "how" in original_question.lower():
                followups.append("What challenges did you face?")
            elif "why" in original_question.lower():
                followups.append("What was the impact of this work?")
            else:
                followups.append("How does this relate to your current work?")
        else:
            # Generic follow-ups if no KB match
            followups = [
                "Can you expand on that?",
                "What's an example of this in your work?",
                "How would you approach this problem?",
            ]
        
        return followups[:3]  # Return max 3 followups

    def format_response(
        self,
        response_text: str,
        confidence: float,
        kb_used: bool,
        sources: list,
        suggested_followups: list,
    ) -> dict:
        """
        Format complete response (legacy method, kept for compatibility)
        
        Returns full response dict
        """
        return {
            "response": response_text,
            "confidence": confidence,
            "kb_used": kb_used,
            "sources": sources,
            "suggested_followups": suggested_followups,
            "timestamp": self.get_timestamp(),
        }