from fastapi import FastAPI, UploadFile, File, Form
from pydantic import BaseModel
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from services.transcript import read_transcript_with_quota_handling
from services.pinecone_storage import PineconeStorage
from api.chat_api import router as chat_router

class ChatMessage(BaseModel):
    video_id: str
    lesson_id: str
    message: str

app = FastAPI()

# Include chat router
app.include_router(chat_router)

@app.get("/")
async def root():
    return {"message": "Transcript Assistant API"}

@app.get("/pinecone/stats")
async def get_pinecone_stats():
    """Get Pinecone index statistics"""
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

@app.get("/pinecone/search")
async def search_pinecone(query: str, top_k: int = 5, video_id: str = None, lesson_id: str = None):
    """Search in Pinecone"""
    try:
        storage = PineconeStorage()
        results = storage.search_subtitles(query, top_k, video_id, lesson_id)
        return {
            "status": "success",
            "query": query,
            "results_count": len(results),
            "results": results
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
        
        # Wipe subtitles index
        subtitles_wiped = storage.wipe_index("subtitles")
        
        # Wipe summaries index  
        summaries_wiped = storage.wipe_index("summaries")
        
        # Get stats after wiping
        stats_after = storage.get_index_stats()
        
        return {
            "status": "success",
            "message": "Database wiped successfully",
            "subtitles_wiped": subtitles_wiped,
            "summaries_wiped": summaries_wiped,
            "stats_before": stats_before,
            "stats_after": stats_after
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

@app.post("/upload-file-async")
async def upload_file_async(
    video_id: str = Form(...),
    lesson_id: str = Form(None),
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
        # Use default lesson_id if not provided
        if lesson_id is None:
            lesson_id = f"lesson_{video_id}"
        
        # Process transcript with grammar correction
        chunks = read_transcript_with_quota_handling(file_path, video_id, lesson_id)
        
        # Create and store summary
        summary_created = False
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
            
        except Exception as summary_error:
            print(f"⚠️  Summary creation error: {summary_error}")
        
        return {
            "status": "success",
            "video_id": video_id,
            "lesson_id": lesson_id,
            "chunks_count": len(chunks),
            "summary_created": summary_created,
            "message": "File processed successfully"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }
