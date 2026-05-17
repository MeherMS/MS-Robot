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
        Format a KB entry (project, experience, certification, etc.) into readable text
        
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
        
        # ===== CERTIFICATIONS =====
        if entry_type == "certification":
            text = f"**{title}**\n\n"
            if description:
                text += f"{description}\n"
            issued = kb_entry.get("issued", "")
            if issued:
                text += f"\n**Issued:** {issued}"
            expires = kb_entry.get("expires", "")
            if expires:
                text += f" | **Expires:** {expires}"
            return text.strip()
        
        # ===== EDUCATION =====
        if entry_type == "education":
            text = f"**{title}**\n\n"
            if description:
                text += f"{description}\n"
            return text.strip()

        # ===== PROJECTS & EXPERIENCES =====
        if entry_type == "contact":
            text = f"**{title}**\n\n"
            if description:
                text += f"{description}\n"
            return text.strip()
        # ===== PROJECTS & EXPERIENCES =====
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

    def format_all_certifications(self, certifications: list) -> str:
        """
        Format all certifications as a formatted list
        
        Args:
            certifications: List of certification dicts from KB
        
        Returns:
            Formatted string with all certifications
        """
        if not certifications:
            return "I don't have any certifications listed in my records."
        
        text = "Here are my certifications:\n\n"
        
        for cert in certifications:
            name = cert.get("name", "")
            issuer = cert.get("issuer", "")
            issued = cert.get("issued", "")
            expires = cert.get("expires", "")
            
            text += f"**{name}**\n"
            if issuer:
                text += f"Issued by: {issuer}\n"
            if issued:
                text += f"Issued: {issued}\n"
            if expires:
                text += f"Expires: {expires}\n"
            text += "\n"
        
        return text.strip()
    
    def format_all_projects(self, projects: list) -> str:
        """
        Format all projects as a brief list, then offer to go into detail
        
        Args:
            projects: List of project dicts from KB
        
        Returns:
            Formatted string with project overview
        """
        if not projects:
            return "I don't have any projects listed in my records."
        
        text = "I've worked on several projects. Here's a quick overview:\n\n"
        
        for i, project in enumerate(projects, 1):
            title = project.get("title", "")
            duration = project.get("duration", "")
            outcome = project.get("outcome", "")
            
            text += f"**{i}. {title}**"
            if duration:
                text += f" ({duration})"
            text += "\n"
            if outcome:
                text += f"   {outcome}\n"
            text += "\n"
        
        text += "\nWould you like to know more details about any specific project? I can tell you about the technologies used, the challenges faced, or the impact it had."
        
        return text.strip()

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
            entry_type = kb_match.get("type", "project")
            
            # Customize based on entry type
            if entry_type == "certification":
                followups.append(f"Which aspect of {title} interests you?")
                followups.append("Tell me about your other certifications")
                followups.append("How did you prepare for this certification?")
            
            elif entry_type == "experience":
                followups.append(f"What were your key achievements in {title}?")
                followups.append("Tell me about the technologies you used")
                followups.append("What challenges did you face there?")
            
            else:  # project or other
                followups.append(f"Tell me more about the technologies you used in {title}")
                followups.append(f"What were the key outcomes of {title}?")
                
                if "how" in original_question.lower():
                    followups.append("What challenges did you face?")
                elif "why" in original_question.lower():
                    followups.append("What was the impact of this work?")
                else:
                    followups.append("How does this relate to your current work?")
        else:
            # Generic follow-ups if no KB match
            followups = [
                "Tell me about your projects",
                "What are your key skills?",
                "What's your background?",
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
        Format complete response
        
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