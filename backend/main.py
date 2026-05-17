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
    Improved chat endpoint with:
    - First person (Meher speaking, not MSRobot)
    - Special handling for certifications
    - Special handling for "all projects" queries
    - Better KB retrieval
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
                "response": f"⚠️ {limit_status['message']}", # Send string, not None
        		"confidence": 0,
        		"kb_used": False,
        		"sources": [],
        		"suggested_followups": [],
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
                "Feel free to reach out to me directly for a deeper conversation:\n\n"
                "📧 **Email:** selmi.ms1995@gmail.com\n"
                "🐙 **GitHub:** https://github.com/meherms\n"
                "🌐 **Portfolio:** https://meherms.github.io\n"
                "💼 **LinkedIn:** https://linkedin.com/in/meherms"
            )
            
            kb_used = False
            confidence = CONF_LLM_ONLY
            sources = []
            suggested_followups = ["Tell me about your projects", "What certifications do you have?", "What's your background?"]

        else:
            # ===== SPECIAL HANDLERS (Before KB search) =====
            
            # Handler 1: All Certifications Query
            if any(word in message.lower() for word in ["certification", "credentials", "all certifications"]):
                certifications = kb.get("certifications", [])
                response_text = formatter.format_all_certifications(certifications)
                kb_used = True
                confidence = 0.95
                sources = []
                suggested_followups = [
                    "Which certification interests you most?",
                    "Tell me about your projects",
                    "What skills do you have?"
                ]
            
            # Handler 2: All Projects Query
            elif any(word in message.lower() for word in ["all projects", "projects you done", "projects you've done", "tell me about projects", "projects"]):
                projects = kb.get("projects", [])
                response_text = formatter.format_all_projects(projects)
                kb_used = True
                confidence = 0.95
                sources = []
                suggested_followups = [
                    "Tell me more about the first project",
                    "What technologies did you use?",
                    "What were your key achievements?"
                ]
            
            # Handler 3: All Experience/Background Query
            elif any(word in message.lower() for word in ["background", "experience", "work history", "where did you work"]):
                experience = kb.get("experience", [])
                response_text = "Here's my work background:\n\n"
                for exp in experience:
                    company = exp.get("company", "Unknown")
                    role = exp.get("role", "Unknown")
                    location = exp.get("location", "")
                    duration = exp.get("duration", "")
                    response_text += f"**{role}** at **{company}**"
                    if location:
                        response_text += f" (📍 {location})"
                    if duration:
                        response_text += f" — {duration}"
                    response_text += "\n"
                    
                    achievements = exp.get("key_achievements", [])
                    if achievements:
                        response_text += "Key achievements:\n"
                        for achievement in achievements:
                            response_text += f"• {achievement}\n"
                    response_text += "\n"
                
                kb_used = True
                confidence = 0.95
                sources = []
                suggested_followups = [
                    "Tell me about your current role",
                    "What were your key achievements?",
                    "Tell me about your projects"
                ]
            # ==========================================
            # ADDED HANDLER 4: Explicit Contact Query
            # ==========================================
            elif any(word in message.lower() for word in ["contact", "email", "phone", "reach you", "get in touch", "connect with you"]):
                contacts = kb.get("contacts", {})
                if contacts:
                    response_text = retriever._format_contacts(contacts)
                else:
                    # Fallback to the hardcoded links if the KB block is missing
                    response_text = (
                        "You can reach out to me directly through any of these channels:\n\n"
                        "📧 **Email:** selmi.ms1995@gmail.com\n"
                        "💼 **LinkedIn:** https://linkedin.com/in/meherms\n"
                        "🐙 **GitHub:** https://github.com/meherms\n"
                        "🌐 **Portfolio:** https://meherms.github.io"
                    )
                kb_used = True
                confidence = 0.95
                sources = []
                suggested_followups = [
                    "Tell me about your projects",
                    "What certifications do you have?",
                    "What's your data science background?"
                ]
            # Default: KB Retrieval with 3-tier routing
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
        				"response": "I'm sorry, I'm having trouble connecting to my brain right now. Please try again in a moment!",
        				"confidence": 0,
        				"kb_used": False,
        				"sources": [],
        				"suggested_followups": [],
        				"quota": limit_status,
    					}

                    # Combine KB + LLM
                    response_text = f"{kb_text}\n\n**Additional thoughts:**\n{llm_result['response']}"
                    
                    kb_used = True
                    confidence = CONF_KB_MEDIUM
                    sources = [formatter.format_source(kb_entry)]
                    suggested_followups = formatter.generate_followups(message, kb_match=kb_entry)

                else:
                    # ===== ROUTE 3: LLM-only Response (Low confidence) =====
                    print(f"[ROUTE] LOW/NO KB MATCH (score {kb_score:.2f}) - LLM-only")
                    full_kb_context = f"Full Knowledge Base:\n{json.dumps(kb, indent=2)}"
                    llm_result = llm_client.generate(
                        question=message,
                        conversation_history=conversation_history,
                        kb_context=full_kb_context,
                        tone=tone,
                    )

                    if not llm_result["success"]:
                        error_msg="I'm currently over-capacity. Please try again later"
                        return {
        					"response": error_msg, # Now a string, react-markdown won't crash
        					"confidence": 0,
        					"kb_used": False,
        					"sources": [],
        					"suggested_followups": [],
        					"quota": limit_status,
        					"error": llm_result["error"] # Keep this for debugging
    					}

                    response_text = (
                        f"{llm_result['response']}\n\n"
                        "*That said, if you want to know what I've actually worked on, ask me about my projects or certifications!*"
                    )
                    
                    kb_used = True
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