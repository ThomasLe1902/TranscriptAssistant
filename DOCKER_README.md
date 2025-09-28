# Docker Setup cho Transcript Assistant

## Cách chạy ứng dụng với Docker

### 1. Build và chạy với Docker Compose (Khuyến nghị)

```bash
# Build và chạy ứng dụng
docker-compose up --build

# Chạy ở background
docker-compose up -d --build

# Dừng ứng dụng
docker-compose down
```

### 2. Build và chạy với Docker thông thường

```bash
# Build image
docker build -t transcript-assistant .

# Chạy container
docker run -p 8000:8000 -v $(pwd):/app transcript-assistant

# Chạy ở background
docker run -d -p 8000:8000 -v $(pwd):/app --name transcript-app transcript-assistant
```

### 3. Truy cập ứng dụng

Sau khi chạy thành công, bạn có thể truy cập:

- **API Documentation**: http://localhost:8000/docs
- **Root Endpoint**: http://localhost:8000/

### 4. Cấu hình Environment Variables

1. Copy file `env.example` thành `.env`:
```bash
cp env.example .env
```

2. Chỉnh sửa file `.env` với các giá trị thực tế của bạn:
```bash
# Google AI API Key (bắt buộc)
GOOGLE_API_KEY=your_actual_google_api_key

# Pinecone Configuration (nếu sử dụng)
PINECONE_API_KEY=your_actual_pinecone_api_key
```

### 5. Các lệnh Docker hữu ích

```bash
# Xem logs
docker-compose logs -f

# Vào container để debug
docker-compose exec transcript-assistant bash

# Rebuild image
docker-compose build --no-cache

# Xóa tất cả containers và images
docker-compose down --rmi all --volumes --remove-orphans
```

### 6. Troubleshooting

**Lỗi "version is obsolete":**
```bash
# Đã sửa trong docker-compose.yml - không cần version nữa
# Chỉ cần chạy lại:
docker-compose up --build
```

**Lỗi "unable to get image":**
```bash
# Xóa image cũ và build lại
docker-compose down
docker system prune -f
docker-compose up --build
```

**Lỗi port đã được sử dụng:**
```bash
# Kiểm tra port 8000 có đang được sử dụng không
netstat -tulpn | grep :8000

# Hoặc thay đổi port trong docker-compose.yml
ports:
  - "8001:8000"  # Sử dụng port 8001 thay vì 8000
```

**Lỗi permission:**
```bash
# Trên Linux/Mac, có thể cần thay đổi quyền
sudo chown -R $USER:$USER .
```

**Lỗi memory:**
```bash
# Tăng memory limit cho Docker
docker-compose up --build --memory=2g
```

**Lỗi Docker Desktop không chạy:**
```bash
# Khởi động Docker Desktop trước khi chạy
# Trên Windows: Mở Docker Desktop application
# Sau đó chạy:
docker-compose up --build
```

**Lỗi "python-multipart" missing:**
```bash
# Package này đã được thêm vào requirements.txt
# Nếu vẫn lỗi, cài đặt thủ công:
pip install python-multipart

# Hoặc rebuild Docker image:
docker-compose down
docker-compose up --build
```

**Lỗi FastAPI import:**
```bash
# Đã sửa cấu trúc import trong app.py
# Nếu vẫn lỗi, kiểm tra:
python -c "import app"
python -m uvicorn app:app --host 0.0.0.0 --port 8000
```

### 7. Cấu trúc thư mục trong container

```
/app/
├── app.py                 # Main application
├── services/              # Service modules
├── uploads/               # Uploaded files
├── requirements.txt       # Python dependencies
└── *.sbv                  # Subtitle files
```

### 8. API Endpoints

- `GET /` - Thông tin API
- `GET /health` - Health check
- `POST /chat` - Chat với AI
- `POST /process-file` - Xử lý file SBV
- `GET /database-stats` - Thống kê database
- `DELETE /wipe-database` - Xóa database
