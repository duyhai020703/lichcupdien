from apscheduler.schedulers.asyncio import AsyncIOScheduler
from config import (
    EVN_MA_DON_VI,
    TARGET_WARD,
    TARGET_AREA,
    DAILY_SCAN_HOUR,
    DAILY_SCAN_MINUTE,
    WEEKLY_SCAN_DAY,
    WEEKLY_SCAN_HOUR,
    WEEKLY_SCAN_MINUTE,
)
from services.evn_service import check_tomorrow_outage, get_weekly_outages_report
from services.telegram_service import (
    load_sent_cache,
    save_sent_cache,
    get_outage_hash,
    send_tomorrow_alert,
    send_weekly_report,
)

scheduler = AsyncIOScheduler()

async def job_daily_tomorrow_check():
    """
    Quét tự động hàng ngày:
    Kiểm tra nếu ngày mai có lịch cúp điện ở Khu phố 2, Phường Tân Ninh thì hôm nay sẽ báo ngay.
    """
    print("[Scheduler] Bắt đầu kiểm tra lịch cúp điện ngày mai...")
    outages = await check_tomorrow_outage(
        ma_dvi=EVN_MA_DON_VI,
        target_ward=TARGET_WARD,
        target_kp=TARGET_AREA,
    )

    if not outages:
        print("[Scheduler] Ngày mai an toàn, không có lịch cúp điện.")
        return

    sent_cache = load_sent_cache()
    alerts_count = 0

    for outg in outages:
        outg_id = get_outage_hash(outg)
        if outg_id not in sent_cache:
            success = await send_tomorrow_alert(outg)
            if success:
                sent_cache.add(outg_id)
                alerts_count += 1

    if alerts_count > 0:
        save_sent_cache(sent_cache)
        print(f"[Scheduler] Đã gửi {alerts_count} cảnh báo cúp điện ngày mai tới Telegram.")

async def job_weekly_summary_broadcast():
    """
    Quét tự động cả tuần (Thứ Hai -> Chủ Nhật):
    Format theo dạng: T2: Không cúp, T3: Cúp điện (từ 7:00 - 17:00)... và gửi Telegram.
    """
    print("[Scheduler] Bắt đầu tổng hợp lịch cúp điện cả tuần...")
    report = await get_weekly_outages_report(
        ma_dvi=EVN_MA_DON_VI,
        target_ward=TARGET_WARD,
        target_kp=TARGET_AREA,
    )

    success = await send_weekly_report(report)
    if success:
        print("[Scheduler] Đã gửi bản tin tổng hợp tuần thành công!")

def start_scheduler():
    """
    Kích hoạt các tác vụ lập lịch ngầm.
    """
    # 1. Cảnh báo ngày mai: Chạy cố định mỗi sáng lúc DAILY_SCAN_HOUR:DAILY_SCAN_MINUTE
    scheduler.add_job(
        job_daily_tomorrow_check,
        "cron",
        hour=DAILY_SCAN_HOUR,
        minute=DAILY_SCAN_MINUTE,
        id="daily_tomorrow_check",
        replace_existing=True,
    )

    # 2. Quét kiểm tra định kỳ mỗi 3 tiếng 1 lần để phát hiện ngay khi EVN vừa đăng lịch mới
    scheduler.add_job(
        job_daily_tomorrow_check,
        "interval",
        hours=3,
        id="interval_check",
        replace_existing=True,
    )

    # 3. Gửi bản tin cả tuần: Chạy vào sáng Thứ Hai hàng tuần
    scheduler.add_job(
        job_weekly_summary_broadcast,
        "cron",
        day_of_week=WEEKLY_SCAN_DAY,
        hour=WEEKLY_SCAN_HOUR,
        minute=WEEKLY_SCAN_MINUTE,
        id="weekly_summary_broadcast",
        replace_existing=True,
    )

    scheduler.start()
    print("[Scheduler] Hệ thống lập lịch tự động đã khởi động.")

