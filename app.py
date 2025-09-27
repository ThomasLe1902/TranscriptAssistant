import os
import tempfile
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, UploadFile, File, Form
from pydantic import BaseModel

from services.model import get_response
from services.transcript import get_transcript, grammar_correction, prepare_subtitle_vectors
from services.data import insert_data, wipe_database, get_stats

def process_subtitle_file(file_path: str, video_id: str = None) -> Dict[str, Any]:
    """
    Xử lý file subtitle hoàn chỉnh: parse → correct → vectorize
    """
    try:
        # 1. Parse SBV file
        subtitles = get_transcript(file_path)
        if not subtitles:
            raise ValueError("Không thể parse file hoặc file trống")
        
        # 2. Sửa chính tả
        corrected_subtitles = grammar_correction(subtitles)
        
        # 3. Thêm video_id vào subtitles nếu có
        if video_id:
            for subtitle in corrected_subtitles:
                subtitle['video_id'] = video_id
        
        # 4. Chuẩn bị dữ liệu vector hóa
        texts, metadatas = prepare_subtitle_vectors(corrected_subtitles)
        
        # 5. Vector hóa
        vectorstore = insert_data(texts, metadatas)
        
        return {
            "success": True,
            "original_count": len(subtitles),
            "corrected_count": len(corrected_subtitles),
            "vector_count": len(texts),
            "video_id": video_id,
            "subtitles": corrected_subtitles
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "original_count": 0,
            "corrected_count": 0,
            "vector_count": 0,
            "video_id": video_id,
            "subtitles": []
        }

app = FastAPI(
    title="Transcript Assistant API",
    description="API để xử lý, sửa chính tả và tìm kiếm subtitles",
    version="1.0.0"
)

# Request Models
class ChatRequest(BaseModel):
    message: str
    video_id: Optional[str] = None

# Response Models
class APIResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Any] = None
    error: Optional[str] = None

@app.get("/")
def read_root():
    return {
        "message": "Transcript Assistant API",
        "version": "1.0.0",
        "endpoints": {
            "chat": "/chat - params: message, video_id",
            "process_file": "/process-file (parse, correct, vectorize) - params: file, video_id",
            "test_upload": "/test-file-upload - test file explorer",
            "health": "/health"
        }
    }

@app.get("/health")
def health_check():
    return {"status": "healthy", "message": "API is running"}

@app.post("/test-file-upload")
async def test_file_upload(file: UploadFile = File(...)):
    """
    Test endpoint để kiểm tra file explorer
    """
    return {
        "success": True,
        "message": f"File đã upload thành công: {file.filename}",
        "filename": file.filename,
        "content_type": file.content_type,
        "size": file.size
    }

@app.post("/chat", response_model=APIResponse)
def send_chat(request: ChatRequest):
    """
    Chat với AI về transcript
    
    Args:
        message: Câu hỏi hoặc yêu cầu của người dùng
        video_id: ID của video để tìm kiếm context (optional)
    """
    try:
        response = get_response(request.message, request.video_id)
        return APIResponse(
            success=True,
            message="Chat response generated successfully",
            data={
                "response": response,
                "video_id": request.video_id
            }
        )
    except Exception as e:
        return APIResponse(
            success=False,
            message="Error generating chat response",
            error=str(e)
        )

@app.post("/process-file", response_model=APIResponse)
async def process_file(
    file: UploadFile = File(...),
    video_id: Optional[str] = Form(None)
):
    """
    Xử lý file SBV: parse, sửa chính tả và vector hóa
    Hỗ trợ upload file qua file explorer
    
    Args:
        file: File SBV upload (required) - Click "Choose File" để mở file explorer
        video_id: ID của video để lưu metadata (optional)
    """
    try:
        # Kiểm tra file upload
        if file is None:
            return APIResponse(
                success=False,
                message="Vui lòng chọn file SBV để upload",
                error="File upload is required"
            )
        
        # Kiểm tra định dạng file
        if not file.filename or not file.filename.lower().endswith('.sbv'):
            return APIResponse(
                success=False,
                message="Chỉ hỗ trợ file .sbv",
                error="Invalid file format. Only .sbv files are supported"
            )
        
        # Lưu file tạm thời
        with tempfile.NamedTemporaryFile(delete=False, suffix='.sbv') as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        try:
            # Xử lý file hoàn chỉnh
            result = process_subtitle_file(temp_file_path, video_id)
            
            if not result["success"]:
                return APIResponse(
                    success=False,
                    message="Lỗi xử lý file",
                    error=result["error"]
                )
            
            # Thêm thông tin file
            if file is not None:
                result["file_name"] = file.filename
            else:
                result["file_path"] = file_path
            
            result["vectorized"] = True
            
            return APIResponse(
                success=True,
                message=f"Xử lý file thành công: {result['original_count']} → {result['corrected_count']} subtitles",
                data=result
            )
            
        finally:
            # Xóa file tạm nếu là upload file
            if file is not None and temp_file_path and os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
            
    except Exception as e:
        return APIResponse(
            success=False,
            message="Lỗi xử lý file",
            error=str(e)
        )

@app.delete("/wipe-database", response_model=APIResponse)
async def wipe_database_endpoint():
    """
    Xóa tất cả records trong Pinecone index
    """
    try:
        result = wipe_database()
        
        if result.get("success"):
            return APIResponse(
                success=True,
                message=result.get("message", "Database wiped successfully"),
                data=result
            )
        else:
            return APIResponse(
                success=False,
                message=result.get("message", "Failed to wipe database"),
                error=result.get("error", "Unknown error")
            )
            
    except Exception as e:
        return APIResponse(
            success=False,
            message="Lỗi xóa database",
            error=str(e)
        )

@app.post("/process-file-local", response_model=APIResponse)
async def process_file_local(
    file_path: str = Form(...),
    video_id: Optional[str] = Form(None)
):
    """
    Xử lý file SBV local: parse, sửa chính tả và vector hóa
    Hỗ trợ file local trên server
    
    Args:
        file_path: Đường dẫn file SBV local (required)
        video_id: ID của video để lưu metadata (optional)
    """
    try:
        # Kiểm tra file tồn tại
        if not os.path.exists(file_path):
            return APIResponse(
                success=False,
                message="File không tồn tại",
                error=f"File not found: {file_path}"
            )
        
        # Kiểm tra định dạng file
        if not file_path.lower().endswith('.sbv'):
            return APIResponse(
                success=False,
                message="Chỉ hỗ trợ file .sbv",
                error="Invalid file format. Only .sbv files are supported"
            )
        
        # Xử lý file hoàn chỉnh
        result = process_subtitle_file(file_path, video_id)
        
        return APIResponse(
            success=True,
            message=f"Xử lý file thành công: {result['original_count']} → {result['corrected_count']} subtitles",
            data=result
        )
        
    except Exception as e:
        return APIResponse(
            success=False,
            message="Lỗi xử lý file local",
            error=str(e)
        )

@app.get("/database-stats", response_model=APIResponse)
async def get_database_stats():
    """
    Lấy thống kê về database
    """
    try:
        stats = get_stats()
        
        if stats:
            return APIResponse(
                success=True,
                message="Database stats retrieved successfully",
                data=stats
            )
        else:
            return APIResponse(
                success=False,
                message="Failed to retrieve database stats",
                error="No stats available"
            )
            
    except Exception as e:
        return APIResponse(
            success=False,
            message="Lỗi lấy thống kê database",
            error=str(e)
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)