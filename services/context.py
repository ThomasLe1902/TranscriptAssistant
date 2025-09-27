from typing import List, Dict, Any, Optional
import json
import time
from datetime import datetime, timedelta

class ContextManager:
    """
    Quản lý context cho chat conversation
    """
    
    def __init__(self, max_context_length: int = 10, context_timeout: int = 3600):
        """
        Args:
            max_context_length: Số lượng tin nhắn tối đa trong context
            context_timeout: Thời gian timeout của context (giây)
        """
        self.max_context_length = max_context_length
        self.context_timeout = context_timeout
        self.contexts: Dict[str, List[Dict[str, Any]]] = {}
    
    def add_message(self, session_id: str, message: str, response: str, video_id: Optional[str] = None) -> None:
        """
        Thêm tin nhắn vào context
        
        Args:
            session_id: ID của session chat
            message: Tin nhắn của user
            response: Phản hồi của AI
            video_id: ID của video (nếu có)
        """
        if session_id not in self.contexts:
            self.contexts[session_id] = []
        
        context_entry = {
            "timestamp": datetime.now().isoformat(),
            "user_message": message,
            "ai_response": response,
            "video_id": video_id
        }
        
        self.contexts[session_id].append(context_entry)
        
        # Giới hạn độ dài context
        if len(self.contexts[session_id]) > self.max_context_length:
            self.contexts[session_id] = self.contexts[session_id][-self.max_context_length:]
    
    def get_context(self, session_id: str, video_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Lấy context cho session
        
        Args:
            session_id: ID của session
            video_id: Filter theo video_id (nếu có)
        
        Returns:
            List các tin nhắn trong context
        """
        if session_id not in self.contexts:
            return []
        
        # Lọc theo video_id nếu có
        if video_id:
            filtered_context = [
                entry for entry in self.contexts[session_id]
                if entry.get("video_id") == video_id
            ]
            return filtered_context
        
        return self.contexts[session_id]
    
    def clear_context(self, session_id: str) -> None:
        """
        Xóa context của session
        """
        if session_id in self.contexts:
            del self.contexts[session_id]
    
    def clear_expired_contexts(self) -> None:
        """
        Xóa các context đã hết hạn
        """
        current_time = datetime.now()
        expired_sessions = []
        
        for session_id, context in self.contexts.items():
            if context:
                last_message_time = datetime.fromisoformat(context[-1]["timestamp"])
                if current_time - last_message_time > timedelta(seconds=self.context_timeout):
                    expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            del self.contexts[session_id]
    
    def get_context_summary(self, session_id: str, video_id: Optional[str] = None) -> str:
        """
        Tạo summary của context để đưa vào prompt
        
        Args:
            session_id: ID của session
            video_id: Filter theo video_id
        
        Returns:
            String summary của context
        """
        context = self.get_context(session_id, video_id)
        
        if not context:
            return ""
        
        summary_parts = []
        for entry in context[-5:]:  # Chỉ lấy 5 tin nhắn gần nhất
            timestamp = entry["timestamp"][:19]  # Chỉ lấy phần date time
            user_msg = entry["user_message"]
            ai_resp = entry["ai_response"]
            
            summary_parts.append(f"[{timestamp}] User: {user_msg}")
            summary_parts.append(f"[{timestamp}] AI: {ai_resp}")
        
        return "\n".join(summary_parts)
    
    def get_session_stats(self) -> Dict[str, Any]:
        """
        Lấy thống kê về các session
        """
        return {
            "total_sessions": len(self.contexts),
            "sessions": {
                session_id: {
                    "message_count": len(context),
                    "last_activity": context[-1]["timestamp"] if context else None,
                    "video_ids": list(set(entry.get("video_id") for entry in context if entry.get("video_id")))
                }
                for session_id, context in self.contexts.items()
            }
        }

# Global context manager instance
context_manager = ContextManager()

def get_context_manager() -> ContextManager:
    """
    Lấy instance của context manager
    """
    return context_manager
