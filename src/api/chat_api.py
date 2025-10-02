#!/usr/bin/env python3
"""
Chat API endpoints cho FastAPI
"""

import os
import sys
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from services.chat_service import SimpleChatService

# Create router
router = APIRouter(prefix="/chat", tags=["chat"])

# Global chat service instance
_chat_service: Optional[SimpleChatService] = None

def get_chat_service() -> SimpleChatService:
    """Get chat service instance"""
    global _chat_service
    if _chat_service is None:
        _chat_service = SimpleChatService()
    return _chat_service


# Pydantic models
class ChatMessage(BaseModel):
    message: str
    video_id: Optional[str] = None
    lesson_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    success: bool
    error: Optional[str] = None

class ChatHistoryResponse(BaseModel):
    history: List[Dict[str, str]]
    success: bool
    error: Optional[str] = None

class VideoListResponse(BaseModel):
    videos: List[Dict[str, Any]]
    success: bool
    error: Optional[str] = None

class ChatServiceResponse(BaseModel):
    video_id: Optional[str] = None
    lesson_id: Optional[str] = None
    success: bool
    error: Optional[str] = None


@router.post("/message", response_model=ChatResponse)
async def send_message(
    message: ChatMessage,
    chat_service: SimpleChatService = Depends(get_chat_service)
):
    """Gửi tin nhắn đến chat bot"""
    try:
        if not message.message.strip():
            raise HTTPException(status_code=400, detail="Tin nhắn không được để trống")
        
        # Tạo chat service mới với video_id và lesson_id nếu được cung cấp
        if message.video_id or message.lesson_id:
            chat_service = SimpleChatService(
                video_id=message.video_id,
                lesson_id=message.lesson_id
            )
        
        response = chat_service.chat(message.message)
        
        return ChatResponse(
            response=response,
            success=True
        )
        
    except Exception as e:
        return ChatResponse(
            response="",
            success=False,
            error=str(e)
        )


@router.get("/history", response_model=ChatHistoryResponse)
async def get_chat_history(
    chat_service: SimpleChatService = Depends(get_chat_service)
):
    """Lấy lịch sử chat"""
    try:
        history = chat_service.get_chat_history()
        
        return ChatHistoryResponse(
            history=history,
            success=True
        )
        
    except Exception as e:
        return ChatHistoryResponse(
            history=[],
            success=False,
            error=str(e)
        )


@router.delete("/history")
async def clear_chat_history(
    chat_service: SimpleChatService = Depends(get_chat_service)
):
    """Xóa lịch sử chat"""
    try:
        chat_service.clear_history()
        
        return {
            "message": "Lịch sử chat đã được xóa",
            "success": True
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi xóa lịch sử chat: {e}")


@router.get("/videos", response_model=VideoListResponse)
async def get_available_videos(
    chat_service: SimpleChatService = Depends(get_chat_service)
):
    """Lấy danh sách video có sẵn"""
    try:
        videos = chat_service.storage.get_all_videos()
        
        return VideoListResponse(
            videos=videos,
            success=True
        )
        
    except Exception as e:
        return VideoListResponse(
            videos=[],
            success=False,
            error=str(e)
        )


@router.get("/service", response_model=ChatServiceResponse)
async def get_chat_service_info(
    chat_service: SimpleChatService = Depends(get_chat_service)
):
    """Lấy thông tin chat service hiện tại"""
    try:
        return ChatServiceResponse(
            video_id=chat_service.video_id,
            lesson_id=chat_service.lesson_id,
            success=True
        )
    except Exception as e:
        return ChatServiceResponse(
            video_id=None,
            lesson_id=None,
            success=False,
            error=str(e)
        )

@router.post("/service", response_model=ChatServiceResponse)
async def set_chat_service_info(
    video_id: Optional[str] = None,
    lesson_id: Optional[str] = None
):
    """Thiết lập thông tin chat service"""
    try:
        global _chat_service
        _chat_service = SimpleChatService(video_id=video_id, lesson_id=lesson_id)
        
        return ChatServiceResponse(
            video_id=video_id,
            lesson_id=lesson_id,
            success=True
        )
    except Exception as e:
        return ChatServiceResponse(
            video_id=None,
            lesson_id=None,
            success=False,
            error=str(e)
        )

@router.get("/health")
async def health_check():
    """Kiểm tra trạng thái chat service"""
    try:
        chat_service = get_chat_service()
        return {
            "status": "healthy",
            "message": "Chat service đang hoạt động bình thường",
            "video_id": chat_service.video_id,
            "lesson_id": chat_service.lesson_id
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Lỗi: {e}"
        }
