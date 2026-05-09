# backend/modules/llm_client.py

import requests
import json
from config import (
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
    OLLAMA_TIMEOUT,
    SYSTEM_PROMPT_BASE,
    TONE_FORMAL,
    TONE_CASUAL,
    MAX_RESPONSE_TOKENS,
)

class OllamaLLMClient:
    """
    Ollama LLM Client - interfaces with local Ollama/Mistral 7B
    """

    def __init__(self):
        self.base_url = OLLAMA_BASE_URL
        self.model = OLLAMA_MODEL
        self.timeout = OLLAMA_TIMEOUT
        self.chat_endpoint = f"{self.base_url}/api/chat"

    def is_available(self) -> bool:
        """
        Check if Ollama is running and model is available
        """
        try:
            response = requests.get(
                f"{self.base_url}/api/tags",
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                models = data.get("models", [])
                model_names = [m.get("name", "") for m in models]
                return any(self.model in name for name in model_names)
            return False
        except Exception as e:
            print(f"[LLM] Ollama availability check failed: {e}")
            return False

    def build_system_prompt(self, tone: str = "formal", kb_context: str = "") -> str:
        """
        Build system prompt with tone and optional KB context
        
        Args:
            tone: "formal" or "casual"
            kb_context: Optional KB information to inject into prompt
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
        Generate LLM response using Ollama
        
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

        # Check if Ollama is available
        if not self.is_available():
            return {
                "success": False,
                "response": "",
                "error": "Ollama is not running or Mistral model not found. Start Ollama: 'ollama serve'",
                "tokens_used": 0,
            }

        try:
            # Build system prompt
            system_prompt = self.build_system_prompt(tone, kb_context)

            # Prepare messages
            messages = [
                {"role": "system", "content": system_prompt}
            ]

            # Add conversation history if provided
            if conversation_history:
                messages.extend(conversation_history)

            # Add current question
            messages.append({"role": "user", "content": question})

            # Call Ollama API
            response = requests.post(
                self.chat_endpoint,
                json={
                    "model": self.model,
                    "messages": messages,
                    "stream": False,  # Don't stream for simplicity
                    "options": {
                        "temperature": 0.7,  # Balanced creativity vs consistency
                        "top_p": 0.9,
                        "top_k": 40,
                    },
                },
                timeout=self.timeout,
            )

            if response.status_code != 200:
                return {
                    "success": False,
                    "response": "",
                    "error": f"Ollama API error: {response.status_code}",
                    "tokens_used": 0,
                }

            data = response.json()
            message = data.get("message", {})
            assistant_response = message.get("content", "").strip()

            # Extract token counts (Ollama provides these)
            tokens_used = data.get("eval_count", 0)

            if not assistant_response:
                return {
                    "success": False,
                    "response": "",
                    "error": "Empty response from Ollama",
                    "tokens_used": 0,
                }

            return {
                "success": True,
                "response": assistant_response,
                "error": None,
                "tokens_used": tokens_used,
            }

        except requests.exceptions.Timeout:
            return {
                "success": False,
                "response": "",
                "error": "Ollama request timed out. Is it still running?",
                "tokens_used": 0,
            }
        except requests.exceptions.ConnectionError:
            return {
                "success": False,
                "response": "",
                "error": "Cannot connect to Ollama. Start it with: 'ollama serve'",
                "tokens_used": 0,
            }
        except Exception as e:
            return {
                "success": False,
                "response": "",
                "error": f"Unexpected error: {str(e)}",
                "tokens_used": 0,
            }


# Singleton instance
llm_client = OllamaLLMClient()