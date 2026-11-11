import os
from contextlib import asynccontextmanager
from datetime import datetime, date
from typing import Optional
from fastapi import FastAPI, BackgroundTasks, Request, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from config import EVN_MA_DON_VI, TARGET_WARD, TARGET_AREA
from models import WeeklyReport, TayNinhOutagesResponse
from scheduler import (
    start_scheduler,
    job_daily_tomorrow_check,
    job_weekly_summary_broadcast,
)
from services.evn_service import (
    get_weekly_outages_report,
    check_tomorrow_outage,
    fetch_tay_ninh_all_outages_by_date,
    TAY_NINH_UNITS,
)
from services.telegram_service import (
    send_weekly_report,
    send_tomorrow_alert,
    send_telegram_raw,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Khởi động lập lịch chạy nền (cho môi trường local/VPS)
    try:
        start_scheduler()
    except Exception as e:
        print(f"[Scheduler Warning]: {e}")
    print(f"🚀 Hệ thống đã sẵn sàng!")
    yield

app = FastAPI(
    title="Hệ thống Theo dõi & Cảnh báo Lịch Cúp Điện Tây Ninh",
    description="Tra cứu lịch cúp điện các phường xã, khu phố Tây Ninh & cảnh báo qua Telegram",
    version="2.1.0",
    lifespan=lifespan,
)

# Mount thư mục static phục vụ CSS, JS, Icon cho iOS PWA
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
async def serve_index():
    """Giao diện Web tối ưu mobile & PWA cho iPhone."""
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Lịch Cúp Điện Tây Ninh API"}

@app.get("/manifest.json")
async def serve_manifest():
    """Web App Manifest cho iOS/Android Add to Home Screen."""
    manifest_path = os.path.join(STATIC_DIR, "manifest.json")
    if os.path.exists(manifest_path):
        return FileResponse(manifest_path, media_type="application/manifest+json")
    return {"name": "Lịch Cúp Điện Tây Ninh"}

@app.get("/api/tay-ninh-outages", response_model=TayNinhOutagesResponse)
async def get_tay_ninh_outages(
    date: Optional[str] = Query(None, description="Ngày tra cứu (YYYY-MM-DD)"),
    unit: Optional[str] = Query("ALL", description="Mã điện lực (hoặc 'ALL' cho tất cả Tây Ninh)"),
):
    """
    API tra cứu toàn bộ lịch cúp điện của các phường, xã, khu phố tại tỉnh Tây Ninh.
    """
    if date:
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            target_date = datetime.now().date()
    else:
        target_date = datetime.now().date()

    return await fetch_tay_ninh_all_outages_by_date(target_date, unit)

@app.get("/api/units")
def get_units():
    """Lấy danh sách các đơn vị điện lực tại Tây Ninh."""
    return {"units": TAY_NINH_UNITS}

@app.get("/api/weekly", response_model=WeeklyReport)
async def get_weekly_schedule():
    """
    Xem lịch cúp điện cả tuần (Thứ 2 -> Chủ nhật) của KP2, P. Tân Ninh.
    """
    report = await get_weekly_outages_report(
        ma_dvi=EVN_MA_DON_VI,
        target_ward=TARGET_WARD,
        target_kp=TARGET_AREA,
    )
    return report

@app.post("/api/send-weekly")
async def send_weekly_to_telegram(background_tasks: BackgroundTasks):
    """
    Kích hoạt gửi ngay bản tin tổng hợp cả tuần về điện thoại qua Telegram.
    """
    background_tasks.add_task(job_weekly_summary_broadcast)
    return {
        "message": "Đang tổng hợp và gửi lịch cúp điện cả tuần tới Telegram của bạn..."
    }

@app.post("/api/check-tomorrow")
async def check_tomorrow(background_tasks: BackgroundTasks):
    """
    Kích hoạt quét kiểm tra lịch cúp điện ngày mai ngay lập tức.
    """
    background_tasks.add_task(job_daily_tomorrow_check)
    return {
        "message": "Đã kích hoạt quét lịch cúp điện ngày mai. Nếu có lịch, hệ thống sẽ gửi Telegram ngay!"
    }

# ========================================================
# ENDPOINTS DÀNH RIÊNG CHO VERCEL CRON JOBS
# ========================================================
@app.get("/api/cron-daily")
async def vercel_cron_daily():
    """Endpoint được Vercel Cron Jobs gọi mỗi ngày để kiểm tra lịch cúp điện ngày mai."""
    await job_daily_tomorrow_check()
    return {"ok": True, "message": "Vercel cron daily check finished."}

@app.get("/api/cron-weekly")
async def vercel_cron_weekly():
    """Endpoint được Vercel Cron Jobs gọi sáng Thứ Hai để gửi bản tin tuần."""
    await job_weekly_summary_broadcast()
    return {"ok": True, "message": "Vercel cron weekly broadcast finished."}

@app.post("/api/telegram-webhook")
async def telegram_webhook(request: Request):
    """
    Webhook tiếp nhận tin nhắn từ Telegram.
    """
    data = await request.json()
    message = data.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    text = (message.get("text") or "").strip().lower()

    if not chat_id:
        return {"ok": True}

    if text in ["/tuan", "tuan", "lịch", "lich", "lịch tuần", "/start"]:
        report = await get_weekly_outages_report(
            ma_dvi=EVN_MA_DON_VI,
            target_ward=TARGET_WARD,
            target_kp=TARGET_AREA,
        )
        await send_weekly_report(report)
    elif text in ["/mai", "mai", "ngày mai"]:
        outages = await check_tomorrow_outage(
            ma_dvi=EVN_MA_DON_VI,
            target_ward=TARGET_WARD,
            target_kp=TARGET_AREA,
        )
        if outages:
            for outg in outages:
                await send_tomorrow_alert(outg)
        else:
            await send_telegram_raw(
                f"🟢 <b>Thông báo:</b> Ngày mai Khu phố {TARGET_AREA}, {TARGET_WARD.title()} <b>KHÔNG</b> có lịch cúp điện!"
            )

    return {"ok": True}
