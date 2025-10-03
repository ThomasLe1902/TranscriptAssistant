# API Documentation

## Tổng quan

API `/ai/chat` sử dụng format input JSON chuẩn với các field bắt buộc.

## Input JSON Format

### Format chính thức (required)
```json
{
  "message": "string",
  "video_id": "string", 
  "lesson_title": "string",
  "session_id": "string"
}
```

### Field Descriptions

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `message` | `string` | ✅ | - | Câu hỏi hoặc yêu cầu của người dùng |
| `video_id` | `string` | ✅ | - | ID của video để tìm kiếm context |
| `lesson_title` | `string` | ✅ | - | Tiêu đề bài học để cung cấp context bổ sung |
| `session_id` | `string` | ❌ | `"default"` | ID của session chat để quản lý lịch sử hội thoại |

## Response Format

Response trả về theo format chuẩn:
```json
{
  "success": true,
  "message": "Chat response generated successfully",
  "data": {
    "structured_response": {
      "answer": "string",
      "video_id": "string",
      "lesson_title": "string", 
      "session_id": "string",
      "has_context": boolean,
      "timestamp_references": [],
      "citations": [],
      "citation_count": 0
    },
    "video_id": "string",
    "session_id": "string",
    "format": "json"
  }
}
```

## Usage Examples

### Basic Usage
```python
import requests

response = requests.post("http://localhost:8000/ai/chat", json={
    "message": "Giải thích về dependency injection trong Java",
    "video_id": "java_basics_01",
    "lesson_title": "Java Cơ Bản - Bài 1",
    "session_id": "user123_session"
})

data = response.json()
print(data["data"]["structured_response"]["answer"])
```

### With Default Session ID
```python
response = requests.post("http://localhost:8000/ai/chat", json={
    "message": "Xin chào",
    "video_id": "welcome_video",
    "lesson_title": "Chào mừng đến với khóa học"
})
```

## Error Handling

### Validation Errors (422)
Khi thiếu required fields:
```json
{
  "detail": [
    {
      "loc": ["body", "video_id"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

### Server Errors (500)
Khi có lỗi xử lý:
```json
{
  "success": false,
  "message": "Error generating chat response",
  "error": "Error details here"
}
```

## Testing

Chạy test:
```bash
python test_api_compatibility.py
```

Test sẽ kiểm tra:
- Input format đầy đủ
- Input với session_id mặc định
- Validation errors cho missing fields
- Error handling
