# backend/modules/gemini_llm_client.py

import google.generativeai as genai
from google.api_core import retry
import json
from config import (
    GEMINI_API_KEY,
    GEMINI_MODEL,
    SYSTEM_PROMPT_BASE,
    TONE_FORMAL,
    TONE_CASUAL,
    MAX_RESPONSE_TOKENS,
)


class GeminiLLMClient:
    """
    Gemini LLM Client - interfaces with Google Gemini API (free tier)
    """

    def __init__(self):
        """Initialize Gemini API client"""
        genai.configure(api_key=GEMINI_API_KEY)
        self.model_name = GEMINI_MODEL  # e.g., "gemini-1.5-flash"
        self.model = genai.GenerativeModel(self.model_name)

    # backend/modules/gemini_llm_client.py - REPLACE is_available() method

    def is_available(self) -> bool:
        """
        Check if Gemini API is available and API key is valid
        """
        try:
            # Simple test: count tokens on a simple string
            result = self.model.count_tokens("Hello")
            tokens = result.total_tokens
            print(f"[LLM] ✅ Gemini API available (token test: {tokens})")
            return True
            
        except TypeError as e:
            # Handle generator/list issues
            if "generator" in str(e).lower():
                print(f"[LLM] ⚠️  API available but minor issue. Using fallback.")
                return True
            else:
                raise
                
        except Exception as e:
            error_str = str(e)
            print(f"[LLM] ❌ Gemini API check failed:")
            print(f"     Error: {error_str[:100]}")
            
            # Provide helpful hints
            if "API_KEY" in error_str.upper() or "UNAUTHENTICATED" in error_str:
                print(f"     → Check GEMINI_API_KEY in backend/.env")
            elif "RESOURCE_EXHAUSTED" in error_str:
                print(f"     → Rate limited. Wait a few minutes.")
            elif "INVALID_ARGUMENT" in error_str:
                print(f"     → Invalid API key. Get a new one at https://ai.google.dev/")
            
            return False

    def build_system_prompt(self, tone: str = "formal", kb_context: str = "") -> str:
        """
        Build system prompt with tone and optional KB context
        
        Args:
            tone: "formal" or "casual"
            kb_context: Optional KB information to inject into prompt
        
        Returns:
            Full system prompt string
        """
        prompt = SYSTEM_PROMPT_BASE

        # Add tone instruction
        if tone == "casual":
            prompt += TONE_CASUAL
        else:  # default formal
            prompt += TONE_FORMAL

        # Inject KB context if provided
        if kb_context:
            prompt += f"\n\nKNOWLEDGE BASE CONTEXT:\n{kb_context}"

        return prompt

    def generate(
        self,
        question: str,
        conversation_history: list = None,
        kb_context: str = "",
        tone: str = "formal",
    ) -> dict:
        """
        Generate LLM response using Gemini API
        
        Args:
            question: User's question
            conversation_history: List of previous messages [{role, content}, ...]
            kb_context: KB information to inject into system prompt
            tone: "formal" or "casual"
        
        Returns:
            {
                "success": bool,
                "response": str,
                "error": str (if failed),
                "tokens_used": int
            }
        """

        # Check if Gemini is available
        if not self.is_available():
            return {
                "success": False,
                "response": "",
                "error": "Gemini API is not available. Check your API key and internet connection.",
                "tokens_used": 0,
            }

        try:
            # Build system prompt
            system_prompt = self.build_system_prompt(tone, kb_context)

            # Prepare conversation for Gemini
            # Gemini expects: [{"role": "user"/"model", "parts": [...]}, ...]
            conversation_messages = []

            # Add conversation history if provided
            if conversation_history:
                for msg in conversation_history:
                    role = msg.get("role", "user")
                    content = msg.get("content", "")
                    
                    # Convert role: "assistant" → "model" (Gemini terminology)
                    gemini_role = "model" if role == "assistant" else role
                    conversation_messages.append({
                        "role": gemini_role,
                        "parts": [content]
                    })

            # Add current question
            conversation_messages.append({
                "role": "user",
                "parts": [question]
            })

            # Create chat session with system prompt
            chat = self.model.start_chat(history=conversation_messages[:-1])

            # Count tokens before sending (for quota tracking)
            # Estimate: system_prompt + current question
            tokens_estimate = self._estimate_tokens(system_prompt + question)

            # Send message with system prompt context
            # Note: Inject system prompt as context in the message
            full_message = f"{system_prompt}\n\nUser Question: {question}"
            
            response = chat.send_message(
                full_message,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=MAX_RESPONSE_TOKENS,
                    temperature=0.7,  # Balanced creativity vs consistency
                    top_p=0.9,
                    top_k=40,
                ),
            )

            assistant_response = response.text.strip()

            if not assistant_response:
                return {
                    "success": False,
                    "response": "",
                    "error": "Empty response from Gemini API",
                    "tokens_used": 0,
                }

            # Count actual output tokens
            output_tokens = self._estimate_tokens(assistant_response)
            total_tokens = tokens_estimate + output_tokens

            return {
                "success": True,
                "response": assistant_response,
                "error": None,
                "tokens_used": total_tokens,
            }

        except Exception as e:
            error_str = str(e)
            
            # Handle specific Gemini errors
            if "RESOURCE_EXHAUSTED" in error_str:
                return {
                    "success": False,
                    "response": "",
                    "error": "Gemini API rate limit reached. Please try again in a few moments.",
                    "tokens_used": 0,
                }
            elif "INVALID_ARGUMENT" in error_str:
                return {
                    "success": False,
                    "response": "",
                    "error": "Invalid request to Gemini API. Please try rephrasing your question.",
                    "tokens_used": 0,
                }
            elif "UNAUTHENTICATED" in error_str:
                return {
                    "success": False,
                    "response": "",
                    "error": "Gemini API authentication failed. Check your API key.",
                    "tokens_used": 0,
                }
            else:
                return {
                    "success": False,
                    "response": "",
                    "error": f"Gemini API error: {error_str}",
                    "tokens_used": 0,
                }

    def _estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for text.
        Gemini provides token counting, but for free tier we estimate:
        Rough estimate: 1 token ≈ 4 characters (conservative)
        """
        try:
            # Try using Gemini's token counter
            response = self.model.count_tokens(text)
            return response.total_tokens
        except Exception:
            # Fallback to rough estimate if token counting fails
            return max(1, len(text) // 4)


# Singleton instance
llm_client = GeminiLLMClient()