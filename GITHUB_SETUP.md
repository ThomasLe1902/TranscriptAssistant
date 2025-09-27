# Hướng dẫn đẩy code lên GitHub

## 📋 Bước 1: Cài đặt Git

### Trên Windows:
1. Tải Git từ: https://git-scm.com/download/win
2. Cài đặt với các tùy chọn mặc định
3. Mở Command Prompt hoặc PowerShell mới

### Trên macOS:
```bash
# Sử dụng Homebrew
brew install git

# Hoặc tải từ: https://git-scm.com/download/mac
```

### Trên Linux:
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install git

# CentOS/RHEL
sudo yum install git
```

## 🔧 Bước 2: Cấu hình Git

```bash
# Cấu hình tên và email
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"

# Kiểm tra cấu hình
git config --list
```

## 🚀 Bước 3: Khởi tạo Git Repository

```bash
# Di chuyển vào thư mục dự án
cd D:\Documents\TranscriptAssistant

# Khởi tạo git repository
git init

# Thêm tất cả files
git add .

# Commit lần đầu
git commit -m "Initial commit: Transcript Assistant API"
```

## 📝 Bước 4: Tạo Repository trên GitHub

1. Đăng nhập vào GitHub: https://github.com
2. Click "New repository" (nút + ở góc trên bên phải)
3. Điền thông tin:
   - **Repository name**: `TranscriptAssistant`
   - **Description**: `FastAPI application for processing and correcting subtitles`
   - **Visibility**: Public hoặc Private
   - **Không check** "Initialize with README" (vì đã có sẵn)
4. Click "Create repository"

## 🔗 Bước 5: Kết nối với GitHub

```bash
# Thêm remote origin (thay YOUR_USERNAME bằng username GitHub của bạn)
git remote add origin https://github.com/YOUR_USERNAME/TranscriptAssistant.git

# Kiểm tra remote
git remote -v
```

## 📤 Bước 6: Đẩy code lên GitHub

```bash
# Đẩy code lên GitHub
git push -u origin main

# Nếu lỗi về branch name, thử:
git branch -M main
git push -u origin main
```

## 🔄 Bước 7: Cập nhật code sau này

```bash
# Thêm files mới hoặc thay đổi
git add .

# Commit với message mô tả
git commit -m "Add new feature: description"

# Đẩy lên GitHub
git push origin main
```

## 🛠️ Troubleshooting

### Lỗi authentication:
```bash
# Sử dụng Personal Access Token thay vì password
# Tạo token tại: https://github.com/settings/tokens
# Sử dụng token khi được hỏi password
```

### Lỗi branch name:
```bash
# Đổi tên branch thành main
git branch -M main
```

### Lỗi remote already exists:
```bash
# Xóa remote cũ
git remote remove origin

# Thêm lại
git remote add origin https://github.com/YOUR_USERNAME/TranscriptAssistant.git
```

### Lỗi permission denied:
```bash
# Kiểm tra SSH key hoặc sử dụng HTTPS với token
git remote set-url origin https://github.com/YOUR_USERNAME/TranscriptAssistant.git
```

## 📋 Checklist hoàn thành

- [ ] Cài đặt Git
- [ ] Cấu hình Git (tên, email)
- [ ] Khởi tạo git repository local
- [ ] Tạo repository trên GitHub
- [ ] Kết nối local với GitHub
- [ ] Đẩy code lên GitHub
- [ ] Kiểm tra repository trên GitHub

## 🎉 Kết quả

Sau khi hoàn thành, bạn sẽ có:
- Repository GitHub: `https://github.com/YOUR_USERNAME/TranscriptAssistant`
- Code được backup trên cloud
- Có thể chia sẻ với người khác
- Có thể clone về máy khác

## 💡 Tips

1. **Commit thường xuyên**: Commit mỗi khi hoàn thành một tính năng
2. **Message rõ ràng**: Viết commit message mô tả rõ thay đổi
3. **Branch cho features**: Tạo branch riêng cho mỗi tính năng mới
4. **README cập nhật**: Luôn cập nhật README khi thêm tính năng mới

