# backend/modules/session_manager.py

import json
import os
from datetime import datetime, timedelta
from typing import Optional, Dict
from groq import Groq
from modules.key_manager import key_manager
from config import (
    GROQ_API_KEYS,
    GROQ_MODEL,
    MAX_RESPONSE_TOKENS,
)

class SessionManager:
    """
    Manages persistent Groq chat sessions per user.
    Each session has:
    - A persistent Groq chat object (maintains history automatically)
    - Knowledge Base loaded in system instruction (one-time cost)
    - Timeout tracking (30 minutes inactivity)
    """

    def __init__(self, kb_path: str = "kb/meher_kb.json", session_timeout_minutes: int = 30):
        """
        Initialize SessionManager
        
        Args:
            kb_path: Path to Knowledge Base JSON file
            session_timeout_minutes: Minutes before inactive session is deleted (default 30)
        """
        # Load KB once at startup
        self.kb_path = kb_path
        self.kb_data = self._load_kb()
        
        # Session storage
        self.sessions: Dict[str, Dict] = {}  # session_id → {chat_history, created_at, last_activity}
        self.session_timeout = timedelta(minutes=session_timeout_minutes)
        
        # Key management
        self.key_manager = key_manager

        # Model name for Groq
        self.model_name = GROQ_MODEL
        
        print(f"[SessionManager] ✅ Initialized. KB loaded: {self.kb_path}")
        print(f"[SessionManager] Using Groq model: {self.model_name}")
        print(f"[SessionManager] Session timeout: {session_timeout_minutes} minutes")
    
    def _load_kb(self) -> dict:
        """
        Load Knowledge Base from JSON file
        
        Returns:
            KB dictionary
        """
        try:
            if not os.path.exists(self.kb_path):
                raise FileNotFoundError(f"KB file not found: {self.kb_path}")
            
            with open(self.kb_path, "r", encoding="utf-8") as f:
                kb = json.load(f)
            
            print(f"[SessionManager] KB loaded: {len(kb.get('projects', []))} projects, {len(kb.get('experience', []))} experiences")
            return kb
        
        except Exception as e:
            print(f"[SessionManager] ❌ Error loading KB: {e}")
            raise

    def _build_system_prompt(self, tone: str = "formal") -> str:
        """
        Build system instruction with KB embedded
        
        Args:
            tone: "formal" or "casual"
        
        Returns:
            Complete system instruction string (includes KB data)
        """
        # Base personality and instructions
        prompt = """You are MSRobot, an AI assistant representing Meher Selmi, a Senior Data Scientist.

PERSONALITY:
- Direct, casual
- Transparent about KB vs. training knowledge
- Technical depth when appropriate
- Prefers clear, simple language over jargon
- Professional but approachable

INSTRUCTIONS:
1. If answering about Meher's projects, experience, or skills, cite them clearly: "I created/worked on [project name]..."
2. If answering from your general knowledge, prefix with: "Based on my training knowledge, I can..."
3. Keep responses concise (1-2 paragraphs max unless asked for details)
4. Never make up projects or achievements
5. Be transparent about your limitations
6. Use first person (I, me, my) when speaking about yourself
7. Use male pronouns (he, him, his) if referring to yourself in third person

TONE ADAPTATION:
"""
        
        # Add tone-specific instructions
        if tone == "casual":
            prompt += """Adopt a casual, conversational tone suitable for peers and colleagues.
- Use natural, everyday language
- Be relaxed and friendly
- Use contractions and informal phrasing
- Can use light humor if appropriate
"""
        else:  # default formal
            prompt += """Adopt a formal, professional tone suitable for recruiters and business contexts.
- Use proper grammar and professional vocabulary
- Structure responses clearly with bullet points if needed
- Focus on measurable outcomes and technical details
- Be concise and direct
"""
        
        # Embed KB as reference data
        kb_json = json.dumps(self.kb_data, indent=2)
        prompt += f"""
KNOWLEDGE BASE (YOUR ACTUAL EXPERIENCE):
Below is your verified knowledge base. Use this as your source of truth.

{kb_json}

RESPONSE RULES:
- When users ask about your projects, experience, or skills, search the KB above first
- Answer directly from KB: "Yes, I worked on [project]..."
- If question is not in KB, use your training knowledge with the "Based on my training knowledge..." prefix
- Always maintain the distinction between KB (verified) and training knowledge (general)
"""
        
        return prompt



    def send_message(self, session_id: str, user_message: str, tone: str = "formal", api_key: Optional[str] = None) -> dict:
        """
        Send message to persistent chat session using Groq.
        Supports external API key rotation orchestration from main.py.
        
        Args:
            session_id: Session identifier
            user_message: User's question/message
            tone: "formal" or "casual"
            api_key: Explicit Groq API key passed from main.py rotation loop
        
        Returns:
            Dict with response, status, tokens, error_type, etc.
        """
        try:
            # Validate input first
            if not user_message or not user_message.strip():
                return {
                    "success": False,
                    "response": "",
                    "error": "Message cannot be empty",
                    "error_type": "invalid_input",
                    "tokens_used": 0,
                    "session_id": session_id,
                }
            
            # ===== Use provided API key or default to first key =====
            api_key_to_use = api_key if api_key else GROQ_API_KEYS[0]
            print(f"[SessionManager] 🔑 Using Groq API key")
            
            # When switching keys, clear the old session
            if api_key and session_id in self.sessions:
                print(f"[SessionManager] 🔄 Clearing old session (switching keys)")
                del self.sessions[session_id]
            
            # ===== Get or create session =====
            session_data = self.get_or_create_session(session_id, tone)
            
            if session_data is None:
                return {
                    "success": False,
                    "response": "",
                    "error": "Session not found and could not be created",
                    "error_type": "other",
                    "tokens_used": 0,
                    "session_id": session_id,
                }
            
            print(f"[SessionManager] 📤 Sending message to session {session_id}")
            print(f"[SessionManager] User: {user_message[:50]}...")
            
            # Build system prompt
            system_prompt = self._build_system_prompt(tone)
            
            # Get conversation history
            messages = session_data["messages"]
            
            # Initialize Groq client with current API key
            client = Groq(api_key=api_key_to_use)
            
            # Send message to Groq
            response = client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    *messages,
                    {"role": "user", "content": user_message}
                ],
                max_tokens=MAX_RESPONSE_TOKENS,
                temperature=0.7,
            )
            
            assistant_response = response.choices[0].message.content.strip()
            
            if not assistant_response:
                return {
                    "success": False,
                    "response": "",
                    "error": "Empty response from Groq",
                    "error_type": "other",
                    "tokens_used": 0,
                    "session_id": session_id,
                }
            
            # Update conversation history
            messages.append({"role": "user", "content": user_message})
            messages.append({"role": "assistant", "content": assistant_response})
            
            # Keep only last 20 messages to prevent token explosion
            if len(messages) > 20:
                messages = messages[-20:]
            
            # Track activity and estimate tokens
            tokens_used = self._estimate_tokens(user_message + assistant_response)
            if session_id in self.sessions:
                self.sessions[session_id]["last_activity"] = datetime.now()
            
            print(f"[SessionManager] ✅ Response sent. Tokens: ~{tokens_used}")
            
            return {
                "success": True,
                "response": assistant_response,
                "error": None,
                "error_type": None,
                "tokens_used": tokens_used,
                "session_id": session_id,
            }
        
        except Exception as e:
            error_str = str(e)
            error_type = self._detect_error_type(error_str)
            
            print(f"[SessionManager] ⚠️  Error: {error_str}")
            print(f"[SessionManager] Error type detected: {error_type}")
            
            return {
                "success": False,
                "response": "",
                "error": error_str[:100],
                "error_type": error_type,
                "tokens_used": 0,
                "session_id": session_id,
            }
    
    def _detect_error_type(self, error_str: str) -> str:
        """
        Detect error type from Groq exception message
        
        Args:
            error_str: Exception error message
        
        Returns:
            "rpm_limit", "daily_quota", "other"
        """
        error_lower = error_str.lower()
        
        # Check for quota/rate limit errors
        if "429" in error_str or "rate_limit" in error_lower or "too many requests" in error_lower:
            return "rpm_limit"
        
        if "quota" in error_lower or "limit exceeded" in error_lower:
            return "daily_quota"
        
        # Everything else
        return "other"

    def get_or_create_session(self, session_id: str, tone: str = "formal") -> Optional[dict]:
        """
        Get existing session or create new one
        
        Args:
            session_id: Unique session identifier
            tone: "formal" or "casual"
        
        Returns:
            Session data dict with message history, or None if error
        """
        # Cleanup old sessions before processing
        self._cleanup_old_sessions()
        
        # Check if session exists
        if session_id in self.sessions:
            session = self.sessions[session_id]
            session["last_activity"] = datetime.now()
            print(f"[SessionManager] ♻️ Reusing session: {session_id}")
            return session
        
        # Create new session
        print(f"[SessionManager] 🆕 Creating new session: {session_id} (tone: {tone})")
        
        try:
            # Create session data
            session_data = {
                "messages": [],  # Will store conversation history
                "created_at": datetime.now(),
                "last_activity": datetime.now(),
                "tone": tone,
            }
            
            # Store session
            self.sessions[session_id] = session_data
            
            print(f"[SessionManager] ✅ Session created: {session_id}")
            return session_data
        
        except Exception as e:
            print(f"[SessionManager] ❌ Error creating session: {e}")
            import traceback
            traceback.print_exc()
            return None

    def get_session(self, session_id: str) -> Optional[dict]:
        """
        Get existing session (don't create if missing)
        
        Args:
            session_id: Session identifier
        
        Returns:
            Session data if exists, None otherwise
        """
        if session_id in self.sessions:
            return self.sessions[session_id]
        return None

    def _cleanup_old_sessions(self) -> int:
        """
        Remove sessions inactive for 30+ minutes
        Prevents memory leaks from accumulating old sessions
        
        Returns:
            Number of sessions deleted
        """
        now = datetime.now()
        sessions_to_delete = []
        
        for session_id, session_data in self.sessions.items():
            last_activity = session_data["last_activity"]
            time_since_activity = now - last_activity
            
            if time_since_activity > self.session_timeout:
                sessions_to_delete.append(session_id)
        
        # Delete old sessions
        for session_id in sessions_to_delete:
            del self.sessions[session_id]
            print(f"[SessionManager] 🗑️  Deleted inactive session: {session_id}")
        
        if sessions_to_delete:
            print(f"[SessionManager] Cleanup: Deleted {len(sessions_to_delete)} old sessions. Active: {len(self.sessions)}")
        
        return len(sessions_to_delete)
        

    def _estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for text
        Rough estimate: 1 token ≈ 4 characters
        
        Args:
            text: Text to estimate tokens for
        
        Returns:
            Estimated token count
        """
        # Fallback: rough estimate (1 token ≈ 4 characters)
        return max(1, len(text) // 4)

    def get_all_sessions(self) -> dict:
        """
        Get info about all active sessions (useful for debugging)
        
        Returns:
            Dict with session stats
        """
        now = datetime.now()
        sessions_info = {}
        
        for session_id, session_data in self.sessions.items():
            created_at = session_data["created_at"]
            last_activity = session_data["last_activity"]
            tone = session_data.get("tone", "unknown")
            msg_count = len(session_data.get("messages", []))
            
            age = now - created_at
            inactive = now - last_activity
            
            sessions_info[session_id] = {
                "tone": tone,
                "message_count": msg_count,
                "age_minutes": int(age.total_seconds() / 60),
                "inactive_minutes": int(inactive.total_seconds() / 60),
                "created_at": created_at.isoformat(),
                "last_activity": last_activity.isoformat(),
            }
        
        return {
            "active_sessions": len(self.sessions),
            "timeout_minutes": self.session_timeout.total_seconds() / 60,
            "sessions": sessions_info,
        }

    def clear_session(self, session_id: str) -> bool:
        """
        Manually delete a specific session
        
        Args:
            session_id: Session to delete
        
        Returns:
            True if deleted, False if not found
        """
        if session_id in self.sessions:
            del self.sessions[session_id]
            print(f"[SessionManager] 🗑️  Manually cleared session: {session_id}")
            return True
        return False

    def clear_all_sessions(self):
        """
        Clear all sessions (use with caution!)
        """
        count = len(self.sessions)
        self.sessions.clear()
        print(f"[SessionManager] ⚠️  Cleared all {count} sessions")


# Singleton instance - initialize once at backend startup
session_manager = SessionManager()