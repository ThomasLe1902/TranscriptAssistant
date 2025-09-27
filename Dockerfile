# Sử dụng Python 3.10 slim image
FROM python:3.10-slim

# Đặt thư mục làm việc
WORKDIR /app

# Cài đặt system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements trước để tận dụng Docker layer caching
COPY requirements.txt .

# Cài đặt Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Tạo thư mục cho uploads và logs
RUN mkdir -p /app/uploads /app/logs

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1

# Chạy ứng dụng với reload cho development
CMD ["python", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
