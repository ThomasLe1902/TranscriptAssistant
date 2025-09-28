import os
import tempfile
from typing import List, Dict, Any, Optional
import uvicorn

from fastapi import FastAPI, UploadFile, File, Form, APIRouter
from pydantic import BaseModel

from services.model import get_response
from services.transcript import get_transcript, grammar_correction, prepare_subtitle_vectors
from services.data import insert_data

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

# Tạo router với prefix /api/ai
api_router = APIRouter(prefix="/api/ai")

# Request Models
class ChatRequest(BaseModel):
    message: str
    video_id: Optional[str] = None
    session_id: Optional[str] = "default"

# Response Models
class APIResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Any] = None
    error: Optional[str] = None
    
    class Config:
        # Đảm bảo response được serialize đúng
        json_encoders = {
            # Custom encoders nếu cần
        }



@api_router.post("/chat", response_model=APIResponse)
def send_chat(request: ChatRequest):
    """
    Chat với AI về transcript - Luôn trả về JSON structured
    
    Args:
        message: Câu hỏi hoặc yêu cầu của người dùng
        video_id: ID của video để tìm kiếm context (optional)
        session_id: ID của session chat (optional, default: "default")
    """
    try:
        # Luôn trả về JSON
        response = get_response(
            request.message, 
            request.video_id, 
            request.session_id
        )
        
        try:
            import json
            parsed_response = json.loads(response)
            return APIResponse(
                success=True,
                message="Structured JSON response generated successfully",
                data={
                    "structured_response": parsed_response,
                    "video_id": request.video_id,
                    "session_id": request.session_id,
                    "format": "json"
                }
            )
        except json.JSONDecodeError:
            # Fallback nếu JSON parsing thất bại
            return APIResponse(
                success=True,
                message="Response generated (JSON parsing failed, returning raw)",
                data={
                    "response": response,
                    "video_id": request.video_id,
                    "session_id": request.session_id,
                    "format": "raw"
                }
            )
    except Exception as e:
        return APIResponse(
            success=False,
            message="Error generating chat response",
            error=str(e)
        )


@api_router.post("/process-file", response_model=APIResponse)
async def process_file(
    file: UploadFile = File(...),
    video_id: Optional[str] = Form(None)
):
    """
    Xử lý file subtitle: parse, sửa chính tả và vector hóa
    Hỗ trợ upload file qua file explorer
    
    Args:
        file: File subtitle upload (.sbv/.srt/.vtt) (required) - Click "Choose File" để mở file explorer
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
        if not file.filename or not any(file.filename.lower().endswith(ext) for ext in ['.sbv', '.srt', '.vtt']):
            return APIResponse(
                success=False,
                message="Chỉ hỗ trợ file .sbv, .srt, .vtt",
                error="Invalid file format. Only .sbv, .srt, .vtt files are supported"
            )
        
        # Lưu file tạm thời với đúng extension
        file_extension = os.path.splitext(file.filename)[1].lower()
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
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


# Thêm router vào app
app.include_router(api_router)

# Endpoints cơ bản không có prefix
@app.get("/")
async def root():
    """
    Root endpoint - API information
    """
    return {
        "message": "Transcript Assistant API",
        "version": "1.0.0",
        "docs": "/docs",
        "api_prefix": "/api/ai",
        "endpoints": {
            "chat": "POST /api/ai/chat",
            "process_file": "POST /api/ai/process-file"
        }
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)