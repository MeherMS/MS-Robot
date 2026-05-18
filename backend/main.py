# backend/main.py - UPDATED FOR SESSION MANAGER

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from modules.session_manager import session_manager
from modules.formatter import ResponseFormatter
from modules.token_limiter import token_limiter
from config import CONF_LLM_ONLY
from datetime import datetime
from pathlib import Path
import asyncio
from concurrent.futures import ThreadPoolExecutor
import json
from pymongo import MongoClient
import os


app = FastAPI(title="MSRobot Backend")


# Thread pool for non-blocking file writes
file_executor = ThreadPoolExecutor(max_workers=2)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins (restrict in production)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB connection
MONGODB_URI = os.getenv("MONGODB_URI")

if not MONGODB_URI:
    print("[MONGODB] ⚠️ MONGODB_URI not set in environment variables")
    db = None
    conversations_collection = None
else:
    try:
        mongo_client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
        # Test connection
        mongo_client.server_info()
        db = mongo_client.get_database()
        conversations_collection = db["conversations"]
        print("[MONGODB] ✅ Connected successfully")
    except Exception as e:
        print(f"[MONGODB] ⚠️ Connection failed: {str(e)}")
        db = None
        conversations_collection = None

def get_client_ip(request: Request) -> str:
    """Extract client IP from request"""
    # Check X-Forwarded-For first (for proxies)
    if "x-forwarded-for" in request.headers:
        return request.headers["x-forwarded-for"].split(",")[0].strip()
    # Fall back to direct connection
    return request.client.host if request.client else "unknown"

def save_conversation_to_mongodb(session_id: str, message: str, response_text: str, confidence: float, kb_used: bool, tone: str):
    """Save conversation to MongoDB (non-blocking, silent fail)"""
    try:
        if conversations_collection is None:
            return  # Skip if DB not connected
        
        data = {
            "timestamp": datetime.utcnow(),
            "session_id": session_id,
            "tone": tone,
            "user_message": message,
            "assistant_response": response_text,
            "confidence": confidence,
            "kb_used": kb_used,
        }
        conversations_collection.insert_one(data)
        print(f"[MONGODB] ✅ Conversation saved")
    except Exception as e:
        # Silently fail - don't break the chat
        print(f"[MONGODB] ⚠️ Save failed (ignored): {str(e)}")


@app.get("/health")
async def health_check(request: Request):
    """Health check endpoint"""
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "active_sessions": len(session_manager.sessions),
    }


@app.get("/kb/stats")
async def kb_stats():
    """Get KB statistics"""
    kb = session_manager.kb_data
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
    Simplified chat endpoint using SessionManager
    
    Flow:
    1. Check token limit (by IP)
    2. Validate input
    3. Get or create session
    4. Send message to Gemini (with KB context)
    5. Format and return response
    """
    
    # Get client IP and check token limit
    client_ip = get_client_ip(request)
    limit_status = token_limiter.check_and_increment(client_ip)
    
    # Extract request data
    message = payload.get("message", "").strip()
    tone = payload.get("tone", "formal")
    session_id = payload.get("session_id", client_ip)
    
    # Validate input
    if not message:
        return {
            "error": "Message cannot be empty",
            "quota": limit_status,
        }
    
    try:
        # Check if token limit reached BEFORE processing
        if not limit_status["allowed"]:
            return {
                "response": f"⚠️ {limit_status['message']}",
                "confidence": 0,
                "kb_used": False,
                "sources": [],
                "suggested_followups": [],
                "quota": limit_status,
            }
        
        print(f"[CHAT] Session: {session_id}, Tone: {tone}, IP: {client_ip}")
        print(f"[CHAT] Message: {message[:50]}...")
        
        # Send message to SessionManager
        # SessionManager handles:
        # - Persistent Gemini chat session
        # - KB context in system instruction
        # - Conversation history (auto-managed by Gemini)
        llm_result = session_manager.send_message(
            session_id=session_id,
            user_message=message,
            tone=tone,
        )
        
        # Check if LLM call succeeded
        if not llm_result["success"]:
            return {
                "response": f"❌ {llm_result['error']}",
                "confidence": 0,
                "kb_used": False,
                "sources": [],
                "suggested_followups": [],
                "quota": limit_status,
                "error": llm_result["error"],
            }
        
        # Format response
        formatter = ResponseFormatter()
        formatted_response = formatter.format_response(
            response_text=llm_result["response"],
            confidence=CONF_LLM_ONLY,  # SessionManager handles KB internally
            kb_used=True,  # SessionManager has KB context
            sources=[],  # Gemini will cite KB in response text
            suggested_followups=formatter.generate_followups(message, kb_match=None),
        )
        
        # Add quota and session info
        formatted_response["quota"] = limit_status
        formatted_response["session_id"] = session_id
        
        print(f"[CHAT] ✅ Response sent. Tokens: ~{llm_result['tokens_used']}. Quota: {limit_status['count']}/{limit_status['limit']}")
        file_executor.submit(save_conversation_to_mongodb, session_id, message, llm_result["response"], CONF_LLM_ONLY, True, tone)

        return formatted_response
    
    except Exception as e:
        print(f"[ERROR] {str(e)}")
        import traceback
        traceback.print_exc()
        
        return {
            "error": f"Server error: {str(e)}",
            "response": None,
            "quota": limit_status,
        }


@app.get("/test-llm")
async def test_llm():
    """Test LLM and session connectivity"""
    test_session_id = "test_session"
    
    try:
        result = session_manager.send_message(
            session_id=test_session_id,
            user_message="What is 2+2?",
            tone="formal",
        )
        
        # Clean up test session
        session_manager.clear_session(test_session_id)
        
        return {
            "status": "ok" if result["success"] else "error",
            "response": result["response"],
            "error": result["error"],
            "model": "gemini-2.5-flash",
        }
    
    except Exception as e:
        return {
            "status": "error",
            "response": "",
            "error": str(e),
        }


@app.get("/sessions")
async def get_sessions():
    """Debug endpoint: Get info about all active sessions"""
    return session_manager.get_all_sessions()


@app.delete("/sessions/{session_id}")
async def clear_session(session_id: str):
    """Debug endpoint: Clear a specific session"""
    deleted = session_manager.clear_session(session_id)
    return {
        "session_id": session_id,
        "deleted": deleted,
        "message": "Session cleared" if deleted else "Session not found",
    }

@app.get("/debug/conversations")
async def debug_conversations(limit: int = 10):
    """Debug endpoint: View recent conversations"""
    try:
        if conversations_collection is None:
            return {"error": "MongoDB not connected"}
        
        # Get recent conversations
        convos = list(conversations_collection.find().sort("timestamp", -1).limit(limit))
        
        # Convert MongoDB ObjectId to string for JSON
        for conv in convos:
            conv["_id"] = str(conv["_id"])
            conv["timestamp"] = str(conv["timestamp"])
        
        return {
            "total_saved": conversations_collection.count_documents({}),
            "recent": convos,
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/debug/export-csv")
async def export_conversations():
    """Export all conversations as CSV"""
    try:
        if conversations_collection is None:
            return {"error": "MongoDB not connected"}
        
        import csv
        from io import StringIO
        
        convos = list(conversations_collection.find().sort("timestamp", -1))
        
        # Create CSV in memory
        output = StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            "timestamp",
            "tone",
            "user_message",
            "assistant_response",
            "confidence",
            "kb_used"
        ])
        
        # Write data
        for conv in convos:
            writer.writerow([
                str(conv.get("timestamp", "")),
                conv.get("tone", ""),
                conv.get("user_message", ""),
                conv.get("assistant_response", ""),
                conv.get("confidence", ""),
                conv.get("kb_used", ""),
            ])
        
        return {
            "message": "Export data manually from debug/conversations endpoint",
            "total_records": len(convos),
        }
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)