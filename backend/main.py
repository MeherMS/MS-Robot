# backend/main.py - KEY CHANGES

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from modules.gemini_llm_client import llm_client  # CHANGED: from llm_client import
from modules.classifier import Classifier
from modules.retriever import Retriever
from modules.formatter import ResponseFormatter
from modules.context_manager import ContextManager
from modules.token_limiter import token_limiter  # NEW: import token limiter
from config import (
    KB_HIGH_THRESHOLD,
    KB_MEDIUM_THRESHOLD,
    CONF_KB_HIGH,
    CONF_KB_MEDIUM,
    CONF_LLM_ONLY,
)
import json
from datetime import datetime

app = FastAPI(title="MSRobot Backend")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins (restrict in production)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Context managers (per session)
context_managers = {}


def get_client_ip(request: Request) -> str:
    """Extract client IP from request"""
    # Check X-Forwarded-For first (for proxies)
    if "x-forwarded-for" in request.headers:
        return request.headers["x-forwarded-for"].split(",")[0].strip()
    # Fall back to direct connection
    return request.client.host if request.client else "unknown"


@app.get("/health")
async def health_check(request: Request):
    """Health check endpoint"""
    return {
        "status": "ok",
        "llm_available": llm_client.is_available(),
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/kb/stats")
async def kb_stats():
    """Get KB statistics"""
    with open("kb/meher_kb.json", "r") as f:
        kb = json.load(f)
    
    metadata = kb.get("metadata", {})
    return {
        "total_projects": len(kb.get("projects", [])),
        "total_experiences": len(kb.get("experience", [])),
        "total_skills": len(kb.get("skills", [])),
        "last_updated": metadata.get("last_updated", "unknown"),
        "kb_version": metadata.get("version", "1.0"),
    }

@app.post("/chat")
async def chat(request: Request, payload: dict):
    """
    Main chat endpoint with token limiting
    Uses Gemini LLM + KB retrieval with 3-tier routing
    """
    
    # Get client IP and check token limit
    client_ip = get_client_ip(request)
    limit_status = token_limiter.check_and_increment(client_ip)
    
    # Extract request data
    message = payload.get("message", "").strip()
    tone = payload.get("tone", "formal")
    session_id = payload.get("session_id", client_ip)
    conversation_history = payload.get("conversation_history", [])

    # Validate input
    if not message:
        return {
            "error": "Message cannot be empty",
            "quota": limit_status,
        }

    try:
        # Check if limit reached BEFORE processing
        if not limit_status["allowed"]:
            return {
                "error": limit_status["message"],
                "response": None,
                "quota": limit_status,
            }

        # ===== INSTANTIATE CLASSES =====
        classifier = Classifier()
        retriever = Retriever()
        formatter = ResponseFormatter()

        # Load KB
        with open("kb/meher_kb.json", "r") as f:
            kb = json.load(f)

        # ===== CLASSIFICATION (Tier 1) =====
        intent = classifier.classify(message)
        print(f"[CHAT] Intent detected: {intent}")

        # If personal question, offer contact
        if intent == "personal":
            response_text = (
                "That sounds like a personal question! 😊\n\n"
                "For a deeper conversation about Meher's interests and personality, "
                "I'd recommend reaching out directly:\n\n"
                "📧 **Email:** selmi.ms1995@gmail.com\n"
                "🐙 **GitHub:** https://github.com/meherms\n"
                "🌐 **Portfolio:** https://meherms.github.io\n\n"
                "That said, based on my general training knowledge, I can share some insights..."
            )
            
            kb_used = False
            confidence = CONF_LLM_ONLY
            sources = []
            suggested_followups = formatter.generate_followups(message, kb_match=None)

        else:
            # ===== KB RETRIEVAL (Tier 2) =====
            kb_entry, kb_score = retriever.search(message, kb)
            
            print(f"[KB] Score: {kb_score:.2f}, Entry: {kb_entry.get('title') if kb_entry else 'None'}")

            # ===== ROUTING (Tier 3) =====
            if kb_score > KB_HIGH_THRESHOLD:
                # ===== ROUTE 1: Direct KB Response (High confidence) =====
                print(f"[ROUTE] HIGH KB MATCH (score {kb_score:.2f})")
                
                # Format KB entry as readable text
                kb_text = formatter.format_kb_entry(kb_entry)
                response_text = kb_text
                
                kb_used = True
                confidence = CONF_KB_HIGH
                sources = [formatter.format_source(kb_entry)]
                suggested_followups = formatter.generate_followups(message, kb_match=kb_entry)

            elif kb_score > KB_MEDIUM_THRESHOLD:
                # ===== ROUTE 2: Blended KB + LLM Response (Medium confidence) =====
                print(f"[ROUTE] MEDIUM KB MATCH (score {kb_score:.2f}) - Blending with LLM")
                
                # Format KB entry
                kb_text = formatter.format_kb_entry(kb_entry)
                
                # Get LLM reasoning
                kb_context = f"KB Entry:\n{kb_text}"
                llm_result = llm_client.generate(
                    question=message,
                    conversation_history=conversation_history,
                    kb_context=kb_context,
                    tone=tone,
                )

                if not llm_result["success"]:
                    return {
                        "error": llm_result["error"],
                        "response": None,
                        "quota": limit_status,
                    }

                # Combine KB + LLM
                response_text = f"{kb_text}\n\n**Additional context (from my training knowledge):**\n{llm_result['response']}"
                
                kb_used = True
                confidence = CONF_KB_MEDIUM
                sources = [formatter.format_source(kb_entry)]
                suggested_followups = formatter.generate_followups(message, kb_match=kb_entry)

            else:
                # ===== ROUTE 3: LLM-only Response (Low confidence) =====
                print(f"[ROUTE] LOW/NO KB MATCH (score {kb_score:.2f}) - LLM-only")
                
                llm_result = llm_client.generate(
                    question=message,
                    conversation_history=conversation_history,
                    kb_context="",
                    tone=tone,
                )

                if not llm_result["success"]:
                    return {
                        "error": llm_result["error"],
                        "response": None,
                        "quota": limit_status,
                    }

                response_text = (
                    #"Based on my training knowledge (my second artificial brain), I can help with this:\n\n"
                    f"{llm_result['response']}\n\n"
                    "*Note: This might be a general knowledge, not only based on Meher's specific experience. "
                    "Ask me about specific projects or skills for more accurate information!*"
                )
                
                kb_used = False
                confidence = CONF_LLM_ONLY
                sources = []
                suggested_followups = formatter.generate_followups(message, kb_match=None)

        # ===== FORMAT FINAL RESPONSE =====
        formatted_response = formatter.format_response(
            response_text=response_text,
            confidence=confidence,
            kb_used=kb_used,
            sources=sources,
            suggested_followups=suggested_followups,
        )

        # Add quota info to response
        formatted_response["quota"] = limit_status

        # Log
        print(f"[CHAT] Response sent. Route: {'KB' if kb_used else 'LLM'}. Confidence: {confidence:.2f}. Quota: {limit_status['count']}/{limit_status['limit']}")

        return formatted_response

    except Exception as e:
        print(f"[ERROR] {str(e)}")
        import traceback
        traceback.print_exc()  # Print full error for debugging
        
        return {
            "error": f"Server error: {str(e)}",
            "response": None,
            "quota": limit_status,
        }

@app.get("/test-llm")
async def test_llm():
    """Test LLM connectivity"""
    available = llm_client.is_available()
    
    if not available:
        return {
            "status": "error",
            "message": "Gemini API is not available",
        }

    # Try a simple generation
    result = llm_client.generate(
        question="What is 2+2?",
        conversation_history=[],
        kb_context="",
        tone="formal",
    )

    return {
        "status": "ok" if result["success"] else "error",
        "response": result["response"],
        "error": result["error"],
        "model": "gemini-1.5-flash",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)