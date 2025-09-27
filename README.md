# Transcript Assistant

Một ứng dụng FastAPI để xử lý, sửa chính tả và tìm kiếm subtitles từ các file subtitle (.sbv, .srt, .vtt).

## 🚀 Tính năng

- **Parse file subtitle**: Đọc và phân tích file subtitle (.sbv, .srt, .vtt)
- **Sửa chính tả**: Sử dụng AI để sửa lỗi ngữ pháp và chính tả
- **Vector hóa**: Lưu trữ và tìm kiếm semantic subtitles
- **Chat AI**: Tương tác với AI về nội dung subtitles với JSON structured response
- **Context Management**: Quản lý lịch sử cuộc trò chuyện theo session
- **Timestamp Tracking**: Theo dõi thời gian tạo và trả lời tin nhắn
- **API RESTful**: Giao diện API đầy đủ với FastAPI

## 📋 Yêu cầu hệ thống

- Python 3.10+
- Docker (tùy chọn)
- Google AI API Key
- Pinecone API Key (cho vector storage)

## 🛠️ Cài đặt

### Cách 1: Sử dụng Docker (Khuyến nghị)

```bash
# Clone repository
git clone <repository-url>
cd TranscriptAssistant

# Copy file environment
cp env.example .env

# Chỉnh sửa .env với API keys của bạn
# GOOGLE_API_KEY=your_google_api_key
# PINECONE_API_KEY=your_pinecone_api_key

# Chạy với Docker
docker-compose up --build
```

### Cách 2: Cài đặt local

```bash
# Clone repository
git clone <repository-url>
cd TranscriptAssistant

# Tạo virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# hoặc
venv\Scripts\activate     # Windows

# Cài đặt dependencies
pip install -r requirements.txt

# Copy file environment
cp env.example .env

# Chỉnh sửa .env với API keys của bạn

# Chạy ứng dụng
python -m uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

## 🔧 Cấu hình

Tạo file `.env` từ `env.example` và điền các thông tin:

```env
# Google AI API Key (bắt buộc)
GOOGLE_API_KEY=your_google_api_key

# Pinecone Configuration (cho vector storage)
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_ENVIRONMENT=your_pinecone_environment
PINECONE_INDEX_NAME=transcript-assistant

# Application Settings
APP_NAME=Transcript Assistant
APP_VERSION=1.0.0
DEBUG=False

# Server Configuration
HOST=0.0.0.0
PORT=8000
```

## 📚 API Documentation

Sau khi chạy ứng dụng, truy cập:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

### Các endpoint chính:

- `POST /process-file` - Xử lý file subtitle (.sbv/.srt/.vtt) (parse, sửa chính tả, vector hóa)
- `POST /chat` - Chat với AI về nội dung subtitles (trả về JSON structured với 5 parameters)
- `GET /context/sessions` - Xem tất cả chat sessions
- `GET /context/session/{id}` - Xem context của session
- `DELETE /context/session/{id}` - Xóa context của session
- `GET /database-stats` - Thống kê database
- `DELETE /wipe-database` - Xóa tất cả dữ liệu

## 🏗️ Cấu trúc dự án

```
TranscriptAssistant/
├── app.py                 # Main FastAPI application
├── requirements.txt       # Python dependencies
├── Dockerfile            # Docker configuration
├── docker-compose.yml    # Docker Compose setup
├── .gitignore           # Git ignore rules
├── README.md            # Project documentation
├── DOCKER_README.md     # Docker setup guide
├── env.example          # Environment variables template
├── services/            # Service modules
│   ├── model.py         # AI model integration
│   ├── transcript.py    # Subtitle processing (.sbv/.srt/.vtt)
│   ├── data.py          # Vector storage
│   ├── context.py       # Chat context management
│   └── response_parser.py # JSON response parser
├── prompts/             # AI prompts
│   └── prompts.py       # Chat and grammar correction prompts
│   └── chunking.py      # Text chunking utilities
├── prompts.py           # AI prompts configuration
└── *.sbv, *.srt, *.vtt  # Sample subtitle files
```

## 🔍 Sử dụng

### 1. Upload và xử lý file subtitle

```bash
# Upload file .sbv
curl -X POST "http://localhost:8000/process-file" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@your_subtitle.sbv" \
  -F "video_id=video_001"

# Upload file .srt
curl -X POST "http://localhost:8000/process-file" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@your_subtitle.srt" \
  -F "video_id=video_001"

# Upload file .vtt
curl -X POST "http://localhost:8000/process-file" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@your_subtitle.vtt" \
  -F "video_id=video_001"
```

### 2. Chat với AI

```bash
# Chat với context (session_id)
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Tóm tắt nội dung cuộc họp",
    "video_id": "video_001",
    "session_id": "user_123"
  }'

# Chat không có context
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Xin chào",
    "session_id": "user_123"
  }'
```

### 3. Quản lý Context Chat

```bash
# Xem tất cả sessions
curl -X GET "http://localhost:8000/context/sessions"

# Xem context của session cụ thể
curl -X GET "http://localhost:8000/context/session/user_123"

# Xem context của session với video_id
curl -X GET "http://localhost:8000/context/session/user_123?video_id=video_001"

# Xóa context của session
curl -X DELETE "http://localhost:8000/context/session/user_123"

# Cleanup context hết hạn
curl -X POST "http://localhost:8000/context/cleanup"
```

### 4. Xem thống kê database

```bash
curl -X GET "http://localhost:8000/database-stats"
```

## 🐳 Docker

Xem [DOCKER_README.md](DOCKER_README.md) để biết hướng dẫn chi tiết về Docker.

## 🤝 Đóng góp

1. Fork repository
2. Tạo feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Mở Pull Request

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.

## 📞 Liên hệ

- Project Link: [https://github.com/yourusername/TranscriptAssistant](https://github.com/yourusername/TranscriptAssistant)

## 🙏 Acknowledgments

- [FastAPI](https://fastapi.tiangolo.com/) - Web framework
- [LangChain](https://langchain.com/) - AI framework
- [Google AI](https://ai.google.dev/) - AI models
- [Pinecone](https://www.pinecone.io/) - Vector database

