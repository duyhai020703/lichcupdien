# Hệ Thống Lịch Cúp Điện Tây Ninh (FastAPI + Mobile PWA + Telegram)

Ứng dụng web tra cứu lịch cúp điện toàn tỉnh **Tây Ninh** (các phường, xã, thị trấn, khu phố), được thiết kế tối ưu hóa giao diện **Mobile / iOS PWA** để cài đặt làm icon ứng dụng trên màn hình chính của **iPhone**, kết hợp hệ thống tự động cảnh báo qua **Telegram**.

---

## 📱 Điểm Nổi Bật Của Giao Diện Mobile (Giống Web Lịch Cúp Điện)

1. **Chuẩn Progressive Web App (PWA) cho iPhone:**
   - Hỗ trợ `apple-touch-icon`, `standalone display mode` (khi mở từ màn hình chính sẽ biến mất thanh địa chỉ trình duyệt Safari, hiển thị tràn viền toàn màn hình như một ứng dụng Native trên iOS).
   - Tối ưu vùng an toàn (Safe Area insets) cho màn hình tai thỏ (Notch) và Dynamic Island.
2. **Thanh chọn ngày trượt ngang mượt mà:**
   - Chuyển đổi nhanh giữa: *Hôm nay, Ngày mai, T5, T6, T7, CN...*
3. **Nút ghim nhanh cho người dùng:**
   - Nút ⭐ **Khu phố 2, Phường Tân Ninh**: Chỉ cần 1 chạm là lọc ra ngay lịch của khu phố bạn.
4. **Bộ lọc đa năng:**
   - Lọc theo từng huyện/thị xã: *Tân Ninh (TP. Tây Ninh), Gò Dầu, Trảng Bàng, Tân Châu, Hòa Thành, Châu Thành, Bến Cầu, Tân Biên, Dương Minh Châu*.
   - Thanh điều hướng danh sách các phường/xã có cúp điện kèm số điểm đếm tự động.
   - Ô tìm kiếm tức thì theo tên đường, tên khu phố, tên xã/phường.
5. **Thẻ thông tin chi tiết:**
   - Khung giờ cúp điện to, rõ ràng kèm thời lượng cúp điện (ví dụ: *09:00 – 09:25 | 25 phút*).
   - Địa điểm chi tiết, lý do ngừng cấp điện và đơn vị điện lực phụ trách.
   - Tự động viền vàng nổi bật đối với các điểm thuộc **Khu phố 2, P. Tân Ninh**.
6. **Thanh gửi Telegram 1 chạm:**
   - Nút bấm dưới đáy màn hình cho phép gửi ngay bản tin tổng hợp cả tuần về Telegram.

---

## 📁 Cấu Trúc Thư Mục Dự Án

```text
D:\lichcupdien\
│── .env                     # File cấu hình Bot Token & Chat ID Telegram
│── requirements.txt         # Thư viện Python cần thiết
│── models.py                # Pydantic models (Tuần, Ngày, Tây Ninh All Outages)
│── config.py                # Cấu hình môi trường
│── scheduler.py             # Lập lịch quét tự động định kỳ
│── main.py                  # Server FastAPI phục vụ API & giao diện Web
│── run.bat                  # Script click đúp chạy nhanh trên Windows
│── README.md                # Tài liệu hướng dẫn
│── services/
│   │── evn_service.py       # Thuật toán cào song song 9 đơn vị & bóc tách KP2
│   └── telegram_service.py  # Gửi tin nhắn HTML qua Telegram Bot
└── static/
    │── index.html           # Giao diện Web App iOS
    │── app.css              # Giao diện Dark theme hiện đại phong cách Apple
    │── app.js               # Logic fetch, lọc phường/xã, chuyển ngày
    │── manifest.json        # Cấu hình PWA Web App Manifest
    │── apple-touch-icon.png # Icon ứng dụng sắc nét cho màn hình iPhone (180x180)
    │── icon-192.png         # Icon PWA 192px
    └── icon-512.png         # Icon PWA 512px
```

---

## 📲 Hướng Dẫn Cài Icon Ứng Dụng Lên Màn Hình iPhone

1. **Khởi động server trên máy tính:**
   - Click đúp vào file [`run.bat`](file:///D:/lichcupdien/run.bat).
   - Server sẽ chạy trên cổng `8000` (cho phép các thiết bị cùng mạng Wi-Fi truy cập).
2. **Mở trên iPhone:**
   - Đảm bảo iPhone kết nối cùng mạng Wi-Fi với máy tính.
   - Mở trình duyệt **Safari** trên iPhone, nhập địa chỉ:
     ```text
     http://192.168.1.128:8000/
     ```
     *(Trong đó `192.168.1.128` là IP mạng LAN máy tính của bạn)*.
3. **Thêm vào màn hình chính (Add to Home Screen):**
   - Nhấn vào biểu tượng **Chia sẻ (Share)** ở thanh công cụ dưới đáy Safari (hình vuông có mũi tên chỉ lên ⬆️).
   - Cuộn xuống chọn dòng **"Thêm vào MH chính" (Add to Home Screen)** ➕.
   - Đặt tên hiển thị (mặc định là **Lịch Cúp Điện**) và bấm **Thêm (Add)** ở góc trên bên phải.
   - **Xong!** Ngay lập tức một icon ứng dụng sấm sét viền xanh sang trọng sẽ xuất hiện trên màn hình iPhone của bạn. Khi bấm mở, nó sẽ hoạt động ở chế độ toàn màn hình như app tải từ App Store.

---

## 🚀 Khởi Chạy Bằng Lệnh Thủ Công

```bash
cd D:\lichcupdien
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Sau đó truy cập:
- Máy tính: `http://127.0.0.1:8000/`
- iPhone: `http://192.168.1.128:8000/`
- Swagger API Docs: `http://127.0.0.1:8000/docs`
