from pymongo import MongoClient
from pymongo.errors import PyMongoError
from datetime import datetime
import os
import json

class ChatLogger:
    def __init__(self):
        """Initialize MongoDB connection"""
        self.uri = os.getenv("MONGODB_URI")
        self.client = None
        self.db = None
        self.collection = None
        self.connected = False
        
        if not self.uri:
            print("[LOGGER] ⚠️ WARNING: MONGODB_URI not set in .env")
            return
        
        try:
            self.client = MongoClient(self.uri, serverSelectionTimeoutMS=5000)
            # Test connection
            self.client.admin.command('ping')
            
            # Access database and collection
            self.db = self.client['msrobot']
            self.collection = self.db['chat_logs']
            self.connected = True
            
            print("[LOGGER] ✅ MongoDB connected successfully")
        except PyMongoError as e:
            print(f"[LOGGER] ❌ MongoDB connection failed: {str(e)}")
            self.connected = False
    
    def log_chat(self, user_message: str, assistant_response: str, confidence: float, 
                 kb_used: bool, session_id: str, tone: str = "formal", consent_given: bool = False):
        """
        Log chat interaction to MongoDB
        
        Args:
            user_message: User's question
            assistant_response: MSRobot's response
            confidence: Confidence score (0-1)
            kb_used: Whether KB was used
            session_id: Session identifier (anonymous)
            tone: Tone of response (formal/casual)
            consent_given: Whether user consented to data collection (tracked but not used for blocking)
        
        Returns:
            True if logged successfully, False otherwise
        """
        
        # If MongoDB not connected, skip logging
        if not self.connected:
            print("[LOGGER] ⚠️ MongoDB not connected - skipping log")
            return False
        
        try:
            # Create log entry
            log_entry = {
                "session_id": session_id,
                "user_message": user_message,
                "assistant_response": assistant_response,
                "confidence": confidence,
                "kb_used": kb_used,
                "tone": tone,
                "timestamp": datetime.utcnow(),
                "consent_given": consent_given,
                "consent_version": "1.0",
            }
            
            # Insert into MongoDB
            result = self.collection.insert_one(log_entry)
            
            consent_status = "✅ consented" if consent_given else "❌ declined"
            print(f"[LOGGER] ✅ Chat logged successfully ({consent_status}) (ID: {result.inserted_id})")
            return True
        
        except PyMongoError as e:
            print(f"[LOGGER] ❌ Error logging to MongoDB: {str(e)}")
            return False
        except Exception as e:
            print(f"[LOGGER] ❌ Unexpected error logging chat: {str(e)}")
            return False
            
    def get_logs_by_session(self, session_id: str, limit: int = 10):
        """Get all logs for a specific session (for future user dashboard)"""
        if not self.connected:
            return []
        
        try:
            logs = list(self.collection.find(
                {"session_id": session_id},
                {"_id": 1, "user_message": 1, "assistant_response": 1, "timestamp": 1}
            ).limit(limit).sort("timestamp", -1))
            
            # Convert ObjectId to string for JSON serialization
            for log in logs:
                log["_id"] = str(log["_id"])
            
            return logs
        except PyMongoError as e:
            print(f"[LOGGER] ❌ Error retrieving logs: {str(e)}")
            return []
    
    def delete_session_logs(self, session_id: str):
        """Delete all logs for a session (for GDPR right to be forgotten)"""
        if not self.connected:
            return False
        
        try:
            result = self.collection.delete_many({"session_id": session_id})
            print(f"[LOGGER] ✅ Deleted {result.deleted_count} logs for session {session_id}")
            return result.deleted_count > 0
        except PyMongoError as e:
            print(f"[LOGGER] ❌ Error deleting logs: {str(e)}")
            return False
    
    def close(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            print("[LOGGER] ✅ MongoDB connection closed")

# Create global logger instance
chat_logger = ChatLogger()