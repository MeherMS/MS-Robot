# backend/modules/session_manager.py
# backend/modules/session_manager.py

import json
import os
from datetime import datetime, timedelta
from typing import Optional, Dict
import google.generativeai as genai
from modules.key_manager import key_manager
from config import (
    GEMINI_API_KEYS,
    GEMINI_MODEL,
    MAX_RESPONSE_TOKENS,
)

class SessionManager:
    """
    Manages persistent Gemini chat sessions per user.
    Each session has:
    - A persistent Gemini chat object (maintains history automatically)
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
        self.sessions: Dict[str, Dict] = {}  # session_id → {chat, created_at, last_activity}
        self.session_timeout = timedelta(minutes=session_timeout_minutes)
        
        # Key management (do NOT configure genai yet - will do per-key)
        self.key_manager = key_manager

        # Model name for Gemini
        self.model_name = GEMINI_MODEL
        
        print(f"[SessionManager] ✅ Initialized. KB loaded: {self.kb_path}")
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
        Send message to persistent chat session. 
        Supports external API key rotation orchestration from main.py if api_key is provided.
        
        Args:
            session_id: Session identifier
            user_message: User's question/message
            tone: "formal" or "casual"
            api_key: Explicit Gemini API key passed from external router loop
        
        Returns:
            Dict with response, status, tokens, etc.
        """
        try:
            # Get or create session
            chat = self.get_or_create_session(session_id, tone)
            
            if chat is None:
                return {
                    "success": False,
                    "response": "",
                    "error": "Session not found and could not be created",
                    "error_type": "other",
                    "tokens_used": 0,
                    "session_id": session_id,
                }
            
            # Validate input
            if not user_message or not user_message.strip():
                return {
                    "success": False,
                    "response": "",
                    "error": "Message cannot be empty",
                    "error_type": "invalid_input",
                    "tokens_used": 0,
                    "session_id": session_id,
                }
            
            print(f"[SessionManager] 📤 Sending message to session {session_id}")
            print(f"[SessionManager] User: {user_message[:50]}...")
            
            # --- CASE 1: Explicit API key provided by main.py's rotation loop ---
            if api_key:
                genai.configure(api_key=api_key)
                try:
                    response = chat.send_message(user_message, stream=False)
                    assistant_response = response.text.strip()
                    
                    if not assistant_response:
                        return {
                            "success": False,
                            "response": "",
                            "error": "Empty response from Gemini",
                            "error_type": "other",
                            "tokens_used": 0,
                            "session_id": session_id,
                        }
                    
                    # Track activity and estimate tokens
                    tokens_used = self._estimate_tokens(user_message + assistant_response)
                    if session_id in self.sessions:
                        self.sessions[session_id]["last_activity"] = datetime.now()
                    
                    return {
                        "success": True,
                        "response": assistant_response,
                        "error": None,
                        "tokens_used": tokens_used,
                        "session_id": session_id,
                    }
                except Exception as e:
                    error_str = str(e)
                    error_str_lower = error_str.lower()
                    error_type = "other"
                    
                    # Categorize Gemini exceptions so main.py knows how to handle the key state
                    if "429" in error_str or "resource_exhausted" in error_str_lower or "quota" in error_str_lower:
                        if "daily" in error_str_lower or "limit exceeded" in error_str_lower:
                            error_type = "daily_quota"
                        else:
                            error_type = "rpm_limit"
                            
                    return {
                        "success": False,
                        "response": "",
                        "error": error_str,
                        "error_type": error_type,
                        "tokens_used": 0,
                        "session_id": session_id,
                    }
            
            # --- CASE 2: Fallback to internal session manager rotation loop ---
            return self._send_with_key_rotation(chat, user_message, session_id)
        
        except Exception as e:
            error_str = str(e)
            print(f"[SessionManager] ❌ Unexpected error: {error_str}")
            
            return {
                "success": False,
                "response": "",
                "error": f"Unexpected error: {error_str[:100]}",
                "error_type": "other",
                "tokens_used": 0,
                "session_id": session_id,
            }
    def _send_with_key_rotation(self, chat, user_message: str, session_id: str) -> dict:
        """
        Send message with automatic key rotation on quota exceeded
        
        Tries up to total_keys times (once per key)
        """
        attempts = 0
        max_attempts = self.key_manager.total_keys
        
        while attempts < max_attempts:
            attempts += 1
            
            # Configure genai with current key
            current_key = self.key_manager.get_current_key()
            genai.configure(api_key=current_key)
            
            try:
                # Send message to chat
                response = chat.send_message(
                    user_message,
                    stream=False,
                )
                
                assistant_response = response.text.strip()
                
                if not assistant_response:
                    return {
                        "success": False,
                        "response": "",
                        "error": "Empty response from Gemini",
                        "tokens_used": 0,
                        "session_id": session_id,
                    }
                
                # Success!
                tokens_used = self._estimate_tokens(user_message + assistant_response)
                
                # Update last activity
                if session_id in self.sessions:
                    self.sessions[session_id]["last_activity"] = datetime.now()
                
                print(f"[SessionManager] ✅ Response sent (~{tokens_used} tokens)")
                
                return {
                    "success": True,
                    "response": assistant_response,
                    "error": None,
                    "tokens_used": tokens_used,
                    "session_id": session_id,
                }
            
            except Exception as e:
                error_str = str(e)
                print(f"[SessionManager] ⚠️  Error with current key: {error_str[:80]}")
                
                # Check if it's a quota error
                if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str or "quota" in error_str.lower():
                    print(f"[SessionManager] 🚨 Quota exceeded! Attempting key rotation...")
                    
                    # Mark current key as exhausted
                    self.key_manager.mark_key_exhausted()
                    
                    # Try next key
                    next_key = self.key_manager.switch_to_next_key()
                    
                    if next_key is None:
                        # All keys exhausted
                        return {
                            "success": False,
                            "response": "",
                            "error": "🚨 All API keys quota exceeded. Please try again in a few hours.",
                            "tokens_used": 0,
                            "session_id": session_id,
                        }
                    
                    # Continue to next iteration with new key
                    continue
                
                # For other errors, handle as before
                elif "RATE_LIMIT" in error_str:
                    return {
                        "success": False,
                        "response": "",
                        "error": "Rate limit reached. Please wait a moment and try again.",
                        "tokens_used": 0,
                        "session_id": session_id,
                    }
                
                elif "INVALID_ARGUMENT" in error_str:
                    return {
                        "success": False,
                        "response": "",
                        "error": "Invalid request. Please try rephrasing your question.",
                        "tokens_used": 0,
                        "session_id": session_id,
                    }
                
                elif "UNAUTHENTICATED" in error_str:
                    return {
                        "success": False,
                        "response": "",
                        "error": "Gemini API authentication failed. Check your API keys.",
                        "tokens_used": 0,
                        "session_id": session_id,
                    }
                
                else:
                    # Non-quota error, return immediately
                    return {
                        "success": False,
                        "response": "",
                        "error": f"Gemini API error: {error_str[:100]}",
                        "tokens_used": 0,
                        "session_id": session_id,
                    }
        
        # Shouldn't reach here, but just in case
        return {
            "success": False,
            "response": "",
            "error": "Failed to get response after trying all keys",
            "tokens_used": 0,
            "session_id": session_id,
        }
    def get_or_create_session(self, session_id: str, tone: str = "formal") -> object:
        """
        Get existing session or create new one
        
        Args:
            session_id: Unique session identifier (from frontend)
            tone: "formal" or "casual"
        
        Returns:
            Gemini chat object (persistent across messages)
        """
        # Cleanup old sessions before processing
        self._cleanup_old_sessions()
        
        # Check if session exists
        if session_id in self.sessions:
            session = self.sessions[session_id]
            session["last_activity"] = datetime.now()
            print(f"[SessionManager] ♻️ Reusing session: {session_id}")
            return session["chat"]
        
        # Create new session
        print(f"[SessionManager] 🆕 Creating new session: {session_id} (tone: {tone})")
        
        try:
            # Build system prompt with KB
            system_prompt = self._build_system_prompt(tone)
            
            # Create model with system instruction
            model = genai.GenerativeModel(
                model_name=self.model_name,
                system_instruction=system_prompt,
            )
            
            # Create persistent chat session
            chat = model.start_chat(history=[])
            
            # Store session
            self.sessions[session_id] = {
                "chat": chat,
                "created_at": datetime.now(),
                "last_activity": datetime.now(),
                "tone": tone,
                "model": model,
                "system_prompt": system_prompt,
            }
            
            print(f"[SessionManager] ✅ Session created: {session_id}")
            return chat
        
        except Exception as e:
            print(f"[SessionManager] ❌ Error creating session: {e}")
            import traceback
            traceback.print_exc()
            raise
    def get_session(self, session_id: str) -> Optional[object]:
        """
        Get existing session (don't create if missing)
        
        Args:
            session_id: Session identifier
        
        Returns:
            Chat object or None if doesn't exist
        """
        if session_id in self.sessions:
            self.sessions[session_id]["last_activity"] = datetime.now()
            return self.sessions[session_id]["chat"]
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
        Uses Gemini's token counter or rough estimate
        
        Args:
            text: Text to estimate tokens for
        
        Returns:
            Estimated token count
        """
        try:
            # Try using Gemini's token counter
            model = genai.GenerativeModel(self.model_name)
            response = model.count_tokens(text)
            return response.total_tokens
        except Exception:
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
            
            age = now - created_at
            inactive = now - last_activity
            
            sessions_info[session_id] = {
                "tone": tone,
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
        Uses Gemini's token counter or rough estimate
        
        Args:
            text: Text to estimate tokens for
        
        Returns:
            Estimated token count
        """
        try:
            # Try using Gemini's token counter
            model = genai.GenerativeModel(self.model_name)
            response = model.count_tokens(text)
            return response.total_tokens
        except Exception:
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
            
            age = now - created_at
            inactive = now - last_activity
            
            sessions_info[session_id] = {
                "tone": tone,
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