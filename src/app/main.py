from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from services.transcript import read_transcript_with_quota_handling
from services.pinecone_storage import PineconeStorage
from services.chat_service import SimpleChatService


app = FastAPI()

# Pydantic models for chat
class ChatMessage(BaseModel):
    message: str
    video_id: str
    lesson_title: str
    session_id: str = "default"

class ChatResponse(BaseModel):
    response: str
    success: bool
    error: Optional[str] = None
    available_queries: Optional[dict] = None
    query_examples: Optional[list] = None

# API Response model để đồng bộ với ai-service
class APIResponse(BaseModel):
    success: bool
    message: str
    data: Optional[dict] = None
    error: Optional[str] = None

# Global chat service instance
_chat_service: Optional[SimpleChatService] = None

def get_chat_service() -> SimpleChatService:
    """Get chat service instance"""
    global _chat_service
    if _chat_service is None:
        _chat_service = SimpleChatService()
    return _chat_service

def get_available_queries() -> dict:
    """Get available query types and examples"""
    return {
        "timestamp_queries": {
            "description": "Truy vấn theo thời gian cụ thể",
            "examples": [
                "phút 19",
                "minute 5", 
                "tại phút 10",
                "timestamp_id 15"
            ]
        },
        "search_queries": {
            "description": "Tìm kiếm nội dung",
            "examples": [
                "tìm kiếm API",
                "authentication là gì",
                "cách sử dụng token"
            ]
        },
        "summary_queries": {
            "description": "Lấy tóm tắt và tổng quan",
            "examples": [
                "tóm tắt bài học",
                "summary video",
                "tổng quan nội dung"
            ]
        },
        "video_queries": {
            "description": "Quản lý video và lesson",
            "examples": [
                "danh sách video",
                "video nào có sẵn",
                "lesson_title abc123"
            ]
        }
    }

def get_query_examples() -> list:
    """Get simple query examples"""
    return [
        "phút 19 - Xem nội dung tại phút 19-20",
        "tìm kiếm API - Tìm kiếm nội dung về API",
        "tóm tắt - Lấy tóm tắt bài học",
        "danh sách video - Xem tất cả video có sẵn",
        "timestamp_id 5 - Xem nội dung timestamp ID 5",
        "minute 10 - Xem nội dung tại phút 10-11"
    ]




@app.get("/chat/queries")
async def get_chat_queries():
    """Lấy danh sách các truy vấn có thể sử dụng"""
    return {
        "available_queries": get_available_queries(),
        "query_examples": get_query_examples(),
        "success": True
    }


@app.post("/ai/chat", response_model=APIResponse)
async def ai_chat(message: ChatMessage):
    """
    Chat với AI - API chính thức
    
    Args:
        message: ChatMessage với message (required), video_id (required), lesson_title (required), session_id (optional, default: "default")
    """
    try:
        if not message.message.strip():
            return APIResponse(
                success=False,
                message="Tin nhắn không được để trống",
                error="Message cannot be empty"
            )
        
        # Tạo chat service mới với tất cả tham số (required)
        chat_service = SimpleChatService(
            video_id=message.video_id,
            lesson_title=message.lesson_title,
            session_id=message.session_id
        )
        
        response = chat_service.chat(message.message)
        
        return APIResponse(
            success=True,
            message="Chat response generated successfully",
            data={
                "structured_response": {
                    "answer": response,
                    "video_id": message.video_id,
                    "lesson_title": message.lesson_title,
                    "session_id": message.session_id,
                    "has_context": bool(message.video_id),
                    "timestamp_references": [],
                    "citations": [],
                    "citation_count": 0
                },
                "video_id": message.video_id,
                "session_id": message.session_id,
                "format": "json"
            }
        )
        
    except Exception as e:
        return APIResponse(
            success=False,
            message="Error generating chat response",
            error=str(e)
        )

@app.get("/pinecone/stats")
async def get_pinecone_stats():
    """Lấy thống kê Pinecone index"""
    try:
        storage = PineconeStorage()
        stats = storage.get_index_stats()
        return {
            "status": "success",
            "stats": stats
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


@app.delete("/pinecone/wipe")
async def wipe_pinecone_database():
    """Wipe all data from both Pinecone indexes"""
    try:
        storage = PineconeStorage()
        
        # Get current stats before wiping
        stats_before = storage.get_index_stats()
        
        # Calculate total vectors before wiping
        total_vectors_before = 0
        if stats_before.get('subtitles', {}).get('total_vectors'):
            total_vectors_before += stats_before['subtitles']['total_vectors']
        if stats_before.get('summaries', {}).get('total_vectors'):
            total_vectors_before += stats_before['summaries']['total_vectors']
        
        # Wipe subtitles namespace
        subtitles_wiped = storage.wipe_index(storage.subtitles_namespace)
        
        # Wipe summaries namespace  
        summaries_wiped = storage.wipe_index(storage.summaries_namespace)
        
        # Get stats after wiping
        stats_after = storage.get_index_stats()
        
        # Calculate total vectors after wiping
        total_vectors_after = 0
        if stats_after.get('subtitles', {}).get('total_vectors'):
            total_vectors_after += stats_after['subtitles']['total_vectors']
        if stats_after.get('summaries', {}).get('total_vectors'):
            total_vectors_after += stats_after['summaries']['total_vectors']
        
        # Calculate wiped vectors
        vectors_wiped = total_vectors_before - total_vectors_after
        
        return {
            "status": "success",
            "message": "Database wiped successfully",
            "operation_summary": {
                "subtitles_wiped": subtitles_wiped,
                "summaries_wiped": summaries_wiped,
                "total_vectors_wiped": vectors_wiped,
                "vectors_before": total_vectors_before,
                "vectors_after": total_vectors_after
            },
            "detailed_stats": {
                "before": stats_before,
                "after": stats_after
            },
            "indexes_affected": [storage.index_name],
            "namespaces_affected": [storage.subtitles_namespace, storage.summaries_namespace],
            "timestamp": __import__('datetime').datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "timestamp": __import__('datetime').datetime.now().isoformat()
        }

@app.post("/upload-file-async")
async def upload_file_async(
    video_id: str = Form(...),
    lesson_title: str = Form(None),
    file: UploadFile = File(...)
):
    try:
        # Save uploaded file temporarily
        file_path = f"uploads/{file.filename}"
        os.makedirs("uploads", exist_ok=True)
        
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Process transcript
        # Use default lesson_title if not provided
        if lesson_title is None:
            lesson_title = f"lesson_{video_id}"
        
        # Process transcript with grammar correction
        chunks = read_transcript_with_quota_handling(file_path, video_id, lesson_title)
        
        # Thống kê chunks
        chunks_stats = {
            "total_chunks": len(chunks),
            "subtitle_chunks": len([c for c in chunks if c.get('type') == 'subtitle']),
            "summary_chunks": len([c for c in chunks if c.get('type') == 'summary']),
            "total_text_length": sum(len(c.get('text', '')) for c in chunks if c.get('type') == 'subtitle'),
            "average_chunk_length": sum(len(c.get('text', '')) for c in chunks if c.get('type') == 'subtitle') / max(len([c for c in chunks if c.get('type') == 'subtitle']), 1)
        }
        
        # Lấy thông tin file
        file_info = {
            "filename": file.filename,
            "file_size": len(content),
            "file_type": file.content_type,
            "upload_path": file_path
        }
        
        # Create and store summary
        summary_created = False
        summary_info = {}
        try:
            from services.summarize import summarize_chunks
            import asyncio
            
            print(f"📝 Creating summary from {len(chunks)} chunks...")
            
            # Kiểm tra xem có đang chạy trong event loop không
            try:
                # Thử lấy event loop hiện tại
                current_loop = asyncio.get_running_loop()
                # Nếu có event loop đang chạy, dùng ThreadPoolExecutor
                import concurrent.futures
                
                def run_summary():
                    # Tạo event loop mới trong thread riêng
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        return new_loop.run_until_complete(summarize_chunks(chunks, max_chunks_per_batch=10))
                    finally:
                        new_loop.close()
                
                # Chạy trong thread riêng để tránh conflict với event loop hiện tại
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(run_summary)
                    summary_result = future.result()
                    
            except RuntimeError:
                # Không có event loop đang chạy, dùng asyncio.run bình thường
                summary_result = asyncio.run(summarize_chunks(chunks, max_chunks_per_batch=10))
            
            # Store summary in Pinecone
            storage = PineconeStorage()
            summary_stored = storage.store_summary(summary_result)
            print(f"📦 Summary stored in Pinecone: {summary_stored}")
            
            summary_created = True
            summary_info = {
                "summary_length": len(summary_result.get('text', '')),
                "small_summaries_count": len(summary_result.get('small_summaries', [])),
                "stored_in_pinecone": summary_stored,
                "summary_preview": summary_result.get('text', '')[:200] + "..." if len(summary_result.get('text', '')) > 200 else summary_result.get('text', '')
            }
            
        except Exception as summary_error:
            print(f"⚠️  Summary creation error: {summary_error}")
            summary_info = {
                "error": str(summary_error),
                "stored_in_pinecone": False
            }
        
        # Lấy thống kê Pinecone
        pinecone_stats = {}
        try:
            storage = PineconeStorage()
            pinecone_stats = storage.get_index_stats()
        except Exception as e:
            pinecone_stats = {"error": str(e)}
        
        return {
            "status": "success",
            "video_id": video_id,
            "lesson_title": lesson_title,
            "file_info": file_info,
            "chunks_stats": chunks_stats,
            "summary_created": summary_created,
            "summary_info": summary_info,
            "pinecone_stats": pinecone_stats,
            "message": "File processed successfully"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }
