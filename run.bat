@echo off
chcp 65001 > nul
echo ====================================================
echo   KHỞI ĐỘNG HỆ THỐNG CẢNH BÁO LỊCH CÚP ĐIỆN FASTAPI
echo ====================================================
cd /d %~dp0

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [LỖI] Máy tính chưa cài đặt Python hoặc chưa tick "Add Python to PATH"!
    echo Vui lòng tải và cài đặt Python từ: https://www.python.org/downloads/
    pause
    exit /b
)

if not exist ".venv" (
    echo [INFO] Đang khởi tạo môi trường ảo Python (.venv)...
    python -m venv .venv
)

echo [INFO] Kích hoạt môi trường ảo...
call .venv\Scripts\activate.bat

echo [INFO] Cài đặt / cập nhật các thư viện phụ thuộc...
pip install -r requirements.txt

echo.
echo ====================================================
echo [SẴN SÀNG] Server FastAPI đang chạy!
echo.
echo 📱 Mở trên máy tính:  http://127.0.0.1:8000/
echo 📲 Mở trên iPhone:    http://192.168.1.128:8000/
echo.
echo 💡 Hướng dẫn tạo App trên iPhone:
echo    1. Mở Safari trên iPhone, vào: http://192.168.1.128:8000/
echo    2. Nhấn nút Chia sẻ (Share - mũi tên hướng lên) ở dưới màn hình
echo    3. Chọn "Thêm vào MH chính" (Add to Home Screen)
echo ====================================================
echo.
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
pause
