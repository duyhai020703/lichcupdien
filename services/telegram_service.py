import hashlib
import json
import os
from typing import Set
import httpx
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from models import OutageItem, WeeklyReport

CACHE_FILE = "sent_notifications.json"

def load_sent_cache() -> Set[str]:
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except Exception:
            return set()
    return set()

def save_sent_cache(cache: Set[str]):
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(list(cache), f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[Cache Error] {e}")

def get_outage_hash(outage: OutageItem) -> str:
    key = f"{outage.start_date}|{outage.start_time}|{outage.end_time}|{outage.location}|{outage.cause}"
    return hashlib.md5(key.encode("utf-8")).hexdigest()

async def send_telegram_raw(message_html: str) -> bool:
    """
    Gửi tin nhắn định dạng HTML qua Telegram Bot API.
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[Telegram Warning] Chưa cấu hình TELEGRAM_BOT_TOKEN hoặc TELEGRAM_CHAT_ID trong file .env!")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message_html,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code == 200:
                return True
            else:
                print(f"[Telegram API Error {resp.status_code}]: {resp.text}")
                return False
    except Exception as e:
        print(f"[Telegram Request Exception]: {e}")
        return False

async def send_tomorrow_alert(outage: OutageItem) -> bool:
    """
    Gửi tin nhắn cảnh báo khẩn cấp: Ngày mai có lịch cúp điện!
    """
    msg = (
        "⚠️ <b>CẢNH BÁO: NGÀY MAI CÓ LỊCH CÚP ĐIỆN!</b> ⚠️\n\n"
        f"📅 <b>Ngày:</b> {outage.start_date}\n"
        f"⏰ <b>Thời gian:</b> Từ {outage.start_time} đến {outage.end_time}\n"
        f"📍 <b>Khu vực:</b>\n{outage.location}\n\n"
        f"🛠 <b>Lý do:</b> {outage.cause}\n\n"
        "<i>Vui lòng chủ động sắp xếp công việc và sạc đầy các thiết bị!</i>"
    )
    return await send_telegram_raw(msg)

async def send_weekly_report(report: WeeklyReport) -> bool:
    """
    Gửi bản tin tổng hợp cả tuần.
    """
    return await send_telegram_raw(report.formatted_text)

