# backend/main.py - UPDATED FOR SESSION MANAGER

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from modules.session_manager import session_manager
from modules.formatter import ResponseFormatter
from modules.token_limiter import token_limiter
from modules.token_limiter import token_limiter
from modules.key_manager import key_manager
from modules.logger import chat_logger
from config import CONF_LLM_ONLY
from datetime import datetime
from pathlib import Path
import asyncio
from concurrent.futures import ThreadPoolExecutor
import json
from pymongo import MongoClient
import os
import time
from modules.key_manager import key_manager


app = FastAPI(title="MSRobot Backend")


# Thread pool for non-blocking file writes
file_executor = ThreadPoolExecutor(max_workers=2)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://ms-robot.vercel.app",  # Production frontend
        "http://localhost:3000" ],       # Local development"],  # Allow all origins (restrict in production)
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

# Input validation function
def validate_input(message: str, max_length: int = 500) -> tuple[bool, str]:
    """
    Validate user input for chat.
    Returns: (is_valid, cleaned_message_or_error_message)
    """
    # Check if empty
    if not message or not message.strip():
        return False, "Message cannot be empty"
    
    # Clean whitespace
    cleaned = message.strip()
    
    # Check max length
    if len(cleaned) > max_length:
        return False, f"Message exceeds {max_length} character limit"
    
    # Check for null bytes (security)
    if '\x00' in cleaned:
        return False, "Invalid characters detected in message"
    
    return True, cleaned

# Security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """
    Add security headers to all responses.
    Protects against XSS, clickjacking, MIME sniffing, etc.
    """
    response = await call_next(request)
    
    # Prevent XSS attacks
    response.headers["X-XSS-Protection"] = "1; mode=block"
    
    # Prevent MIME type sniffing
    response.headers["X-Content-Type-Options"] = "nosniff"
    
    # Prevent framing attacks (clickjacking)
    response.headers["X-Frame-Options"] = "DENY"
    
    # Content Security Policy (basic, allow only self + API)
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; img-src 'self' https://cdn.jsdelivr.net data:"
    
    # Referrer policy (privacy)
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    
    # Permissions policy (prevent abuse of device features)
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    
    return response


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
    Chat endpoint with multi-key rotation and smart error handling.
    
    Flow:
    1. Check token limit (daily quota per IP)
    2. Check burst limit (10 msgs per 60 sec per IP)
    3. Validate input
    4. Try to send message with key rotation:
       - If RPM limit → cooldown key, try next key
       - If daily quota → mark exhausted, try next key
       - If other error → fail immediately
    5. Format and return response
    """
    
    # Get client IP and check token limit
    client_ip = get_client_ip(request)
    limit_status = token_limiter.check_and_increment(client_ip)
    
    # Check burst limit
    burst_allowed, burst_message = token_limiter.check_burst_limit(client_ip)
    if not burst_allowed:
        return {
            "error": burst_message,
            "quota": limit_status,
        }
    
    # Extract request data
    raw_message = payload.get("message", "")
    tone = payload.get("tone", "formal")
    session_id = payload.get("session_id", client_ip)
    consent_given = payload.get("consent_given", False)
    
    # Validate input
    is_valid, validation_result = validate_input(raw_message)
    if not is_valid:
        return {
            "error": validation_result,
            "quota": limit_status,
        }
    
    message = validation_result  # Use cleaned message
    
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
    
    print(f"\n[CHAT] Session: {session_id}, Tone: {tone}, IP: {client_ip}")
    print(f"[CHAT] Message: {message[:50]}...")
    
    # ============================================================
    # KEY ROTATION LOOP - Try each available API key
    # ============================================================
    max_retries = key_manager.total_keys
    attempt = 0
    
    while attempt < max_retries:
        attempt += 1
        
        # Get current available key
        key_info = key_manager.get_current_key()
        
        if key_info[0] is None:
            # All keys unavailable (in cooldown or exhausted)
            status = key_manager.get_status()
            print(f"[KEY_ROTATION] All keys unavailable. Status: {status}")
            
            # Determine which error to show user
            cooldown_keys = status["keys_in_cooldown"]
            exhausted_keys = status["keys_daily_exhausted"]
            
            if exhausted_keys == key_manager.total_keys:
                # All keys permanently exhausted
                return {
                    "response": "🚨 All API keys daily quota exceeded. Please try again after midnight UTC.",
                    "error": "All keys quota exhausted",
                    "confidence": 0,
                    "kb_used": False,
                    "sources": [],
                    "suggested_followups": [],
                    "quota": limit_status,
                }
            elif cooldown_keys > 0:
                # All keys in cooldown (RPM limit)
                return {
                    "response": "⏱️ Rate limit hit. Please try again in a few moments.",
                    "error": "All keys in cooldown",
                    "confidence": 0,
                    "kb_used": False,
                    "sources": [],
                    "suggested_followups": [],
                    "quota": limit_status,
                }
            else:
                # Generic unavailable
                return {
                    "response": "Please try again in a few moments.",
                    "error": "All keys unavailable",
                    "confidence": 0,
                    "kb_used": False,
                    "sources": [],
                    "suggested_followups": [],
                    "quota": limit_status,
                }
        
        # Log attempt
        print(f"[KEY_ROTATION] Attempt {attempt}/{max_retries} with key {key_info[1]}/{key_manager.total_keys}")
        
        # Send message to SessionManager with specific API key
        try:
            llm_result = session_manager.send_message(
                session_id=session_id,
                user_message=message,
                tone=tone,
                api_key=key_info[0],  # Pass the specific API key
            )
        except Exception as e:
            print(f"[CHAT] Exception during send_message: {str(e)}")
            llm_result = {
                "success": False,
                "error": str(e),
                "error_type": "other",
                "response": "",
                "tokens_used": 0,
            }
        
        # Check if successful
        if llm_result["success"]:
            # ✅ SUCCESS - Format and return response
            print(f"[CHAT] ✅ Response sent with key {key_info[1]}. Tokens: ~{llm_result.get('tokens_used', 0)}")
            
            formatter = ResponseFormatter()
            formatted_response = formatter.format_response(
                response_text=llm_result["response"],
                confidence=CONF_LLM_ONLY,
                kb_used=True,
                sources=[],
                suggested_followups=formatter.generate_followups(message, kb_match=None),
            )
            
            formatted_response["quota"] = limit_status
            formatted_response["session_id"] = session_id
            
            # Log to chat logger
            chat_logger.log_chat(
                user_message=message,
                assistant_response=llm_result["response"],
                confidence=CONF_LLM_ONLY,
                kb_used=True,
                session_id=session_id,
                tone=tone,
                consent_given=consent_given,
            )
            
            # Save to MongoDB (non-blocking)
            file_executor.submit(
                save_conversation_to_mongodb,
                session_id, message, llm_result["response"],
                CONF_LLM_ONLY, True, tone
            )
            
            print(f"[CHAT] Quota: {limit_status['count']}/{limit_status['limit']}")
            return formatted_response
        
        # ❌ FAILED - Check error type and decide whether to retry
        error_type = llm_result.get("error_type", "other")
        error_message = llm_result.get("error", "Unknown error")
        
        print(f"[KEY_ROTATION] Error type: {error_type} | Message: {error_message[:80]}")
        
        if error_type == "rpm_limit":
            # Temporary: RPM limit exceeded
            # Mark current key for cooldown and try next key
            key_manager.mark_key_with_error("rpm_limit")
            print(f"[KEY_ROTATION] RPM limit on key {key_info[1]}, rotating to next key...")
            continue  # Try next iteration with different key
            
        elif error_type == "daily_quota":
            # Permanent: Daily quota exhausted
            # Mark current key as exhausted and try next key
            key_manager.mark_key_with_error("daily_quota")
            print(f"[KEY_ROTATION] Daily quota on key {key_info[1]}, rotating to next key...")
            continue  # Try next iteration with different key
            
        else:
            # Other errors (auth, invalid arg, etc.)
            # Don't retry, return error immediately
            print(f"[KEY_ROTATION] Non-recoverable error on key {key_info[1]}, not retrying")
            return {
                "response": f"❌ {error_message}",
                "error": error_message,
                "confidence": 0,
                "kb_used": False,
                "sources": [],
                "suggested_followups": [],
                "quota": limit_status,
            }
    
    # All retries exhausted
    print(f"[KEY_ROTATION] All {max_retries} key attempts failed")
    return {
        "response": "Please try again in a few moments.",
        "error": "All API keys failed",
        "confidence": 0,
        "kb_used": False,
        "sources": [],
        "suggested_followups": [],
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



import os
from fastapi import FastAPI, HTTPException
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()



# Retrieve and split the keys into a list
# Falls back to an empty list if the env variable doesn't exist
GEMINI_API_KEYS = [key.strip() for key in os.getenv("GEMINI_API_KEYS", "").split(",") if key.strip()]
#from config import CONF_LLM_ONLY, GEMINI_API_KEYS

@app.get("/debug/test-key-switching")
async def debug_test_key_switching():
    """
    Test if chat objects respect API key switches.
    
    This endpoint helps determine:
    1. Does genai.configure() affect existing chat objects?
    2. Does rotation actually work?
    3. Are keys properly bound or are they global?
    
    Returns detailed logs to help diagnose key switching behavior.
    """
    
    print("\n" + "="*80)
    print("[DEBUG] KEY SWITCHING TEST STARTED")
    print("="*80 + "\n")
    
    results = {
        "test_name": "Key Switching Behavior Test",
        "timestamp": datetime.utcnow().isoformat(),
        "total_keys_available": key_manager._get_available_keys,
        "tests": [],
    }
    
    try:
        # ============================================================
        # TEST 1: Simple key switch with different sessions
        # ============================================================
        print("[TEST 1] Different Sessions with Different Keys")
        print("-" * 80)
        
        test1_result = {
            "name": "Different sessions, different keys",
            "session_1": None,
            "session_2": None,
            "analysis": None,
        }
        
        # Get first key
        key1 = GEMINI_API_KEYS[0]
        key1_num = 1
        print(f"[TEST 1] Using Key {key1_num}: {key1[:20]}...{key1[-10:]}")
        
        # Session 1 with Key 1
        result1 = session_manager.send_message(
            session_id="debug_session_1",
            user_message="What is 2+2?",
            tone="formal",
            api_key=key1,
        )
        
        test1_result["session_1"] = {
            "session_id": "debug_session_1",
            "key_used": f"Key {key1_num}",
            "success": result1["success"],
            "response_preview": result1["response"][:50] if result1["response"] else "N/A",
            "error": result1.get("error"),
            "tokens": result1.get("tokens_used"),
        }
        
        print(f"[TEST 1] Session 1 Result: {'✅ SUCCESS' if result1['success'] else '❌ FAILED'}")
        if not result1['success']:
            print(f"[TEST 1] Error: {result1.get('error')}")
        
        time.sleep(1)  # Pause between requests
        
        # Get second key (if available)
        if key_manager.total_keys > 1:
            key2 = GEMINI_API_KEYS[1]
            key2_num = 2
            print(f"\n[TEST 1] Using Key {key2_num}: {key2[:20]}...{key2[-10:]}")
            
            # Session 2 with Key 2
            result2 = session_manager.send_message(
                session_id="debug_session_2",
                user_message="What is 3+3?",
                tone="formal",
                api_key=key2,
            )
            
            test1_result["session_2"] = {
                "session_id": "debug_session_2",
                "key_used": f"Key {key2_num}",
                "success": result2["success"],
                "response_preview": result2["response"][:50] if result2["response"] else "N/A",
                "error": result2.get("error"),
                "tokens": result2.get("tokens_used"),
            }
            
            print(f"[TEST 1] Session 2 Result: {'✅ SUCCESS' if result2['success'] else '❌ FAILED'}")
            if not result2['success']:
                print(f"[TEST 1] Error: {result2.get('error')}")
            
            # Analysis
            if result1["success"] and result2["success"]:
                test1_result["analysis"] = "✅ Both keys work independently in different sessions"
            elif result1["success"] and not result2["success"]:
                test1_result["analysis"] = "⚠️ Key 1 works but Key 2 fails - possible key issue"
            elif not result1["success"] and result2["success"]:
                test1_result["analysis"] = "⚠️ Key 1 fails but Key 2 works - possible key issue"
            else:
                test1_result["analysis"] = "❌ Both keys failed - likely global rate limit hit"
        else:
            test1_result["analysis"] = "⚠️ Only 1 key available, skipping comparison"
        
        results["tests"].append(test1_result)
        
        # ============================================================
        # TEST 2: Same session, different keys (the critical test)
        # ============================================================
        print("\n[TEST 2] Same Session, Key Switch Mid-Conversation")
        print("-" * 80)
        
        test2_result = {
            "name": "Same session with key switch",
            "message_1": None,
            "message_2": None,
            "analysis": None,
        }
        
        # Create session with Key 1
        session_id = "debug_session_keyswitch"
        print(f"[TEST 2] Creating session with Key 1: {key1[:20]}...{key1[-10:]}")
        
        result2_msg1 = session_manager.send_message(
            session_id=session_id,
            user_message="Remember this: I like Python",
            tone="formal",
            api_key=key1,
        )
        
        test2_result["message_1"] = {
            "message": "Remember this: I like Python",
            "key_used": "Key 1",
            "success": result2_msg1["success"],
            "response_preview": result2_msg1["response"][:50] if result2_msg1["response"] else "N/A",
        }
        
        print(f"[TEST 2] Message 1 with Key 1: {'✅ SUCCESS' if result2_msg1['success'] else '❌ FAILED'}")
        
        time.sleep(1)
        
        # Now send another message with Key 2 (if available) - SAME SESSION
        if key_manager.total_keys > 1:
            print(f"[TEST 2] Same session, switching to Key 2: {key2[:20]}...{key2[-10:]}")
            
            result2_msg2 = session_manager.send_message(
                session_id=session_id,
                user_message="Do you remember what I said earlier?",
                tone="formal",
                api_key=key2,
            )
            
            test2_result["message_2"] = {
                "message": "Do you remember what I said earlier?",
                "key_used": "Key 2",
                "success": result2_msg2["success"],
                "response_preview": result2_msg2["response"][:50] if result2_msg2["response"] else "N/A",
            }
            
            print(f"[TEST 2] Message 2 with Key 2: {'✅ SUCCESS' if result2_msg2['success'] else '❌ FAILED'}")
            
            # Check if Key 2 maintained session context
            response_text = result2_msg2["response"].lower()
            
            if "python" in response_text or "remember" in response_text or "earlier" in response_text:
                test2_result["analysis"] = "✅ Key 2 can access chat history - session/context preserved"
            elif result2_msg2["success"] and "python" not in response_text:
                test2_result["analysis"] = "⚠️ Key 2 works but may have lost session context (new chat object?)"
            else:
                test2_result["analysis"] = "❌ Key 2 failed - cannot switch keys mid-session"
        else:
            test2_result["analysis"] = "⚠️ Only 1 key available, cannot test switch"
        
        results["tests"].append(test2_result)
        
        # ============================================================
        # TEST 3: Key Manager Status
        # ============================================================
        print("\n[TEST 3] Key Manager Status Check")
        print("-" * 80)
        
        status = key_manager.get_status()
        
        test3_result = {
            "name": "Key Manager Status",
            "total_keys": status.get("total_keys"),
            "available_keys": status.get("available_keys"),
            "in_cooldown": status.get("keys_in_cooldown"),
            "daily_exhausted": status.get("keys_daily_exhausted"),
            "breakdown": status.get("breakdown"),
        }
        
        print(f"[TEST 3] Total Keys: {status.get('total_keys')}")
        print(f"[TEST 3] Available: {status.get('available_keys')}")
        print(f"[TEST 3] In Cooldown: {status.get('keys_in_cooldown')}")
        print(f"[TEST 3] Daily Exhausted: {status.get('keys_daily_exhausted')}")
        
        for line in status.get("breakdown", []):
            print(f"[TEST 3]   {line}")
        
        results["tests"].append(test3_result)
        
        # ============================================================
        # CLEANUP
        # ============================================================
        print("\n[DEBUG] Cleaning up test sessions...")
        session_manager.clear_session("debug_session_1")
        session_manager.clear_session("debug_session_2")
        session_manager.clear_session(session_id)
        print("[DEBUG] Cleanup complete")
        
        # ============================================================
        # SUMMARY & RECOMMENDATIONS
        # ============================================================
        print("\n" + "="*80)
        print("[DEBUG] TEST SUMMARY")
        print("="*80)
        
        summary = {
            "all_tests_passed": all(test["analysis"] and "✅" in test["analysis"] for test in results["tests"]),
            "key_switching_works": "✅" in test2_result["analysis"],
            "recommendations": [],
        }
        
        # Generate recommendations
        if "✅" in test1_result["analysis"] and "✅" in test2_result["analysis"]:
            summary["recommendations"].append("✅ KEY SWITCHING IS WORKING! Your rotation logic should work fine.")
        elif "⚠️" in test2_result["analysis"] or "❌" in test2_result["analysis"]:
            summary["recommendations"].append("⚠️ Key switching has issues. You may need to:")
            summary["recommendations"].append("   1. Create new chat objects when switching keys (not reuse existing ones)")
            summary["recommendations"].append("   2. Clear and recreate sessions on key switch")
            summary["recommendations"].append("   3. Investigate if genai.configure() works as expected")
        
        if status.get("keys_in_cooldown", 0) > 0 or status.get("keys_daily_exhausted", 0) > 0:
            summary["recommendations"].append(f"⚠️ Some keys are in cooldown or exhausted - normal if you just tested errors")
        
        results["summary"] = summary
        
        print("\n[DEBUG] Final Status:")
        for line in summary["recommendations"]:
            print(f"[DEBUG] {line}")
        
        print("\n" + "="*80 + "\n")
        
        return results
    
    except Exception as e:
        print(f"\n[ERROR] Test failed with exception: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return {
            "status": "error",
            "error": str(e),
            "traceback": traceback.format_exc(),
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


# backend/main.py - Add new test endpoint


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