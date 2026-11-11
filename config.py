import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()

# Thông tin địa bàn
EVN_MA_DON_VI = os.getenv("EVN_MA_DON_VI", "PB0501").strip()  # Điện lực Tân Ninh
TARGET_WARD = os.getenv("TARGET_WARD", "phường tân ninh").strip().lower()
TARGET_AREA = os.getenv("TARGET_AREA", "2").strip()

# Cấu hình giờ chạy Scheduler
DAILY_SCAN_HOUR = int(os.getenv("DAILY_SCAN_HOUR", "7"))
DAILY_SCAN_MINUTE = int(os.getenv("DAILY_SCAN_MINUTE", "0"))

WEEKLY_SCAN_DAY = os.getenv("WEEKLY_SCAN_DAY", "mon").strip().lower()
WEEKLY_SCAN_HOUR = int(os.getenv("WEEKLY_SCAN_HOUR", "7"))
WEEKLY_SCAN_MINUTE = int(os.getenv("WEEKLY_SCAN_MINUTE", "5"))

