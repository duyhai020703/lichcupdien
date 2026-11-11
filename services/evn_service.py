import asyncio
import re
import time
from datetime import datetime, date, timedelta
from typing import List, Optional, Tuple, Dict
import httpx
from bs4 import BeautifulSoup
from models import OutageItem, DaySummary, WeeklyReport, TayNinhOutagesResponse

WEEKDAY_MAP = {
    0: ("T2", "Thứ Hai"),
    1: ("T3", "Thứ Ba"),
    2: ("T4", "Thứ Tư"),
    3: ("T5", "Thứ Năm"),
    4: ("T6", "Thứ Sáu"),
    5: ("T7", "Thứ Bảy"),
    6: ("CN", "Chủ Nhật"),
}

TAY_NINH_UNITS = {
    "PB0501": "Điện lực Tân Ninh (TP. Tây Ninh)",
    "PB0502": "Điện lực Gò Dầu",
    "PB0503": "Điện lực Trảng Bàng",
    "PB0504": "Điện lực Tân Châu",
    "PB0505": "Điện lực Thái Bình (Châu Thành)",
    "PB0506": "Điện lực Dương Minh Châu",
    "PB0507": "Điện lực Tân Biên",
    "PB0508": "Điện lực Hòa Thành",
    "PB0509": "Điện lực Bến Cầu",
}

# Bộ nhớ tạm (cache) để tránh gọi EVN liên tục, TTL = 10 phút (600 giây)
_CACHE: Dict[str, Tuple[float, List[OutageItem]]] = {}
CACHE_TTL = 600

def is_khu_pho_match(location_text: str, target_kp: str = "2") -> bool:
    """
    Kiểm tra xem địa chỉ có chứa khu phố mục tiêu (mặc định là 2).
    Xử lý thông minh các trường hợp:
      - 'Khu phố 2', 'KP 2', 'KP.2', 'KP2'
      - Dạng liệt kê: 'Khu phố 1, 2, 3, 5, 6, 7, 14...'
      - Dạng khoảng: 'Khu phố 1 - 3'
    """
    text = location_text.lower()
    target_num = int(target_kp) if target_kp.isdigit() else None

    # Khớp chính xác cụm 'khu phố 2' hoặc 'kp 2'
    if re.search(rf"\b(khu\s*ph[ốo]|kp)\.?\s*{target_kp}\b", text):
        return True

    # Khớp dạng danh sách các số đi sau 'khu phố' hoặc 'kp'
    matches = re.finditer(r"\b(?:khu\s*ph[ốo]|kp)\s*([0-9\s,–-]+)", text)
    for m in matches:
        sub_str = m.group(1)
        numbers = [int(n) for n in re.findall(r"\d+", sub_str)]
        if target_num is not None and target_num in numbers:
            return True

        ranges = re.findall(r"(\d+)\s*[-–]\s*(\d+)", sub_str)
        for s_str, e_str in ranges:
            s_num, e_num = int(s_str), int(e_str)
            if target_num is not None and s_num <= target_num <= e_num:
                return True

    return False

def extract_ward_or_commune(location_text: str) -> List[str]:
    """
    Trích xuất tên các phường, xã, thị trấn từ chuỗi mô tả địa chỉ của EVN.
    Ví dụ: 'Khu phố Nội Ô phường Gò Dầu; khu phố Phước Đức A phường Gia Lộc'
    -> ['Phường Gò Dầu', 'Phường Gia Lộc']
    """
    pattern = r"\b((?:phường|xã|thị trấn)\s+[0-9a-zA-Zà-ỹÀ-Ỹ\s]+?)(?=[,;.\n]|\s+(?:phường|xã|thị trấn|ấp|khu phố|huyện|thị xã|tp\b|thành phố)|$)"
    found = re.findall(pattern, location_text, re.IGNORECASE)
    cleaned = []
    for item in found:
        c = " ".join(item.strip().split()).title()
        if c and c not in cleaned:
            cleaned.append(c)
    if not cleaned:
        cleaned.append("Địa bàn chung")
    return cleaned

def calculate_duration(start_time: str, end_time: str) -> str:
    """Tính khoảng thời gian cúp điện (ví dụ: '9 giờ 30 phút' hoặc '25 phút')"""
    try:
        t1 = datetime.strptime(start_time, "%H:%M")
        t2 = datetime.strptime(end_time, "%H:%M")
        diff = t2 - t1
        mins = int(diff.total_seconds() // 60)
        if mins < 0:
            return ""
        hours = mins // 60
        rem_mins = mins % 60
        if hours > 0 and rem_mins > 0:
            return f"{hours} giờ {rem_mins} phút"
        elif hours > 0:
            return f"{hours} giờ"
        else:
            return f"{rem_mins} phút"
    except Exception:
        return ""

def parse_time_string(raw_time: str) -> Tuple[str, str, str, str]:
    """
    Trích xuất: start_date (YYYY-MM-DD), start_time (HH:MM), end_date (YYYY-MM-DD), end_time (HH:MM)
    từ chuỗi: 'Từ 09:00:00 ngày 11/11/2026 đến 09:25:00 ngày 11/11/2026'
    """
    clean_time = " ".join(raw_time.split())
    pattern = r"Từ\s+([0-9:]+)\s+ngày\s+([0-9/]+)\s+đến\s+([0-9:]+)\s+ngày\s+([0-9/]+)"
    match = re.search(pattern, clean_time, re.IGNORECASE)

    if match:
        st_raw, sd_raw, et_raw, ed_raw = match.groups()
        st = ":".join(st_raw.split(":")[:2])
        et = ":".join(et_raw.split(":")[:2])

        try:
            sd_obj = datetime.strptime(sd_raw, "%d/%m/%Y").date()
            sd = sd_obj.strftime("%Y-%m-%d")
        except Exception:
            sd = sd_raw

        try:
            ed_obj = datetime.strptime(ed_raw, "%d/%m/%Y").date()
            ed = ed_obj.strftime("%Y-%m-%d")
        except Exception:
            ed = ed_raw

        return sd, st, ed, et

    return "", "", "", ""

async def fetch_evn_raw_outages(ma_dvi: str, tu_ngay_str: str, den_ngay_str: str) -> List[OutageItem]:
    """
    Gọi API CSKH EVN SPC để lấy thông báo lịch cúp điện theo đơn vị.
    """
    cache_key = f"{ma_dvi}_{tu_ngay_str}_{den_ngay_str}"
    now_ts = time.time()
    if cache_key in _CACHE:
        cache_time, cached_items = _CACHE[cache_key]
        if now_ts - cache_time < CACHE_TTL:
            return cached_items

    url = "https://cskh.evnspc.vn/TraCuu/GetThongTinLichNgungGiamCungCapDien"
    params = {
        "madvi": ma_dvi,
        "tuNgay": tu_ngay_str,
        "denNgay": den_ngay_str,
        "ChucNang": "MaDonVi",
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    }

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(url, params=params, headers=headers)
            if resp.status_code != 200:
                print(f"[EVN API Error] Mã {ma_dvi} - Status: {resp.status_code}")
                return []
    except Exception as e:
        print(f"[EVN API Exception] Mã {ma_dvi}: {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    entries = soup.select(".entry")
    items: List[OutageItem] = []
    unit_label = TAY_NINH_UNITS.get(ma_dvi, "Điện lực Tây Ninh")

    for entry in entries:
        where_el = entry.select_one(".where")
        time_el = entry.select_one(".time")
        cause_el = entry.select_one(".cause")

        location = where_el.text.replace("KHU VỰC:", "").strip() if where_el else ""
        raw_time = time_el.text.replace("THỜI GIAN:", "").strip() if time_el else ""
        cause = cause_el.text.replace("LÝ DO NGỪNG CUNG CẤP ĐIỆN:", "").strip() if cause_el else ""
        raw_time = " ".join(raw_time.split())

        sd, st, ed, et = parse_time_string(raw_time)
        wards = extract_ward_or_commune(location)
        duration = calculate_duration(st, et)

        items.append(OutageItem(
            start_date=sd,
            start_time=st,
            end_date=ed,
            end_time=et,
            location=location,
            cause=cause,
            raw_time=raw_time,
            unit_code=ma_dvi,
            unit_name=unit_label,
            wards=wards,
            duration=duration,
        ))

    _CACHE[cache_key] = (now_ts, items)
    return items

def get_current_week_dates(base_date: Optional[date] = None) -> List[date]:
    """Lấy danh sách 7 ngày từ Thứ Hai đến Chủ Nhật của tuần chứa base_date."""
    if base_date is None:
        base_date = datetime.now().date()
    monday = base_date - timedelta(days=base_date.weekday())
    return [monday + timedelta(days=i) for i in range(7)]

async def get_weekly_outages_report(
    ma_dvi: str,
    target_ward: str,
    target_kp: str,
    base_date: Optional[date] = None
) -> WeeklyReport:
    """Quét lịch cúp điện cả tuần và nhóm theo T2 -> CN."""
    week_days = get_current_week_dates(base_date)
    start_date = week_days[0]
    end_date = week_days[-1]

    tu_ngay_str = start_date.strftime("%d-%m-%Y")
    den_ngay_str = end_date.strftime("%d-%m-%Y")

    all_outages = await fetch_evn_raw_outages(ma_dvi, tu_ngay_str, den_ngay_str)

    matched_outages = []
    for outg in all_outages:
        loc_lower = outg.location.lower()
        if target_ward in loc_lower and is_khu_pho_match(outg.location, target_kp):
            matched_outages.append(outg)

    days_summary: List[DaySummary] = []
    formatted_lines: List[str] = []

    for d in week_days:
        d_str = d.strftime("%Y-%m-%d")
        w_code, w_full = WEEKDAY_MAP[d.weekday()]
        day_outages = [o for o in matched_outages if o.start_date == d_str]

        if day_outages:
            times_text = ", ".join([f"từ {o.start_time} - {o.end_time}" for o in day_outages])
            status_text = f"Cúp điện ({times_text})"
            days_summary.append(DaySummary(
                date=d_str,
                weekday_code=w_code,
                weekday_full=w_full,
                is_outage=True,
                status_text=status_text,
                outages=day_outages
            ))
            formatted_lines.append(f"🔴 <b>{w_code} ({d.strftime('%d/%m')})</b>: {status_text}")
            for o in day_outages:
                formatted_lines.append(f"   • <i>Lý do:</i> {o.cause}")
        else:
            status_text = "Không cúp"
            days_summary.append(DaySummary(
                date=d_str,
                weekday_code=w_code,
                weekday_full=w_full,
                is_outage=False,
                status_text=status_text,
                outages=[]
            ))
            formatted_lines.append(f"🟢 <b>{w_code} ({d.strftime('%d/%m')})</b>: {status_text}")

    full_formatted = (
        f"⚡ <b>LỊCH CÚP ĐIỆN CẢ TUẦN ({start_date.strftime('%d/%m')} - {end_date.strftime('%d/%m/%Y')})</b>\n"
        f"📍 <b>Khu vực:</b> Khu phố {target_kp}, {target_ward.title()}\n"
        f"{'-'*36}\n"
        + "\n".join(formatted_lines) + "\n"
        f"{'-'*36}\n"
        f"💡 <i>Nguồn: Tổng công ty Điện lực Miền Nam (EVN SPC)</i>"
    )

    return WeeklyReport(
        ward=target_ward,
        area=f"Khu phố {target_kp}",
        unit_code=ma_dvi,
        start_week=start_date.strftime("%Y-%m-%d"),
        end_week=end_date.strftime("%Y-%m-%d"),
        days=days_summary,
        formatted_text=full_formatted
    )

async def check_tomorrow_outage(
    ma_dvi: str,
    target_ward: str,
    target_kp: str,
    base_date: Optional[date] = None
) -> List[OutageItem]:
    """Kiểm tra riêng lịch cúp điện của NGÀY MAI."""
    if base_date is None:
        base_date = datetime.now().date()
    tomorrow = base_date + timedelta(days=1)
    tomorrow_str = tomorrow.strftime("%d-%m-%Y")
    tomorrow_iso = tomorrow.strftime("%Y-%m-%d")

    all_outages = await fetch_evn_raw_outages(ma_dvi, tomorrow_str, tomorrow_str)

    matched = []
    for outg in all_outages:
        loc_lower = outg.location.lower()
        if target_ward in loc_lower and is_khu_pho_match(outg.location, target_kp):
            if outg.start_date == tomorrow_iso or not outg.start_date:
                matched.append(outg)

    return matched

async def fetch_tay_ninh_all_outages_by_date(
    target_date: date,
    unit_code: Optional[str] = None
) -> TayNinhOutagesResponse:
    """
    Lấy toàn bộ lịch cúp điện trong ngày của tỉnh Tây Ninh (hoặc lọc theo mã đơn vị).
    Chạy song song 9 đơn vị điện lực huyện/thị bằng asyncio.gather.
    """
    date_str = target_date.strftime("%d-%m-%Y")
    date_iso = target_date.strftime("%Y-%m-%d")

    if unit_code and unit_code != "ALL" and unit_code in TAY_NINH_UNITS:
        units_to_fetch = [unit_code]
    else:
        units_to_fetch = list(TAY_NINH_UNITS.keys())

    tasks = [fetch_evn_raw_outages(u, date_str, date_str) for u in units_to_fetch]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    all_items: List[OutageItem] = []
    wards_summary: Dict[str, int] = {}

    for res in results:
        if isinstance(res, list):
            for item in res:
                # Lọc đúng ngày
                if item.start_date == date_iso or not item.start_date:
                    all_items.append(item)
                    for w in item.wards:
                        wards_summary[w] = wards_summary.get(w, 0) + 1

    # Sắp xếp theo giờ bắt đầu
    all_items.sort(key=lambda x: x.start_time or "00:00")

    # Format ngày hiển thị tiếng Việt
    w_code, w_full = WEEKDAY_MAP[target_date.weekday()]
    display_date = f"{w_full}, {target_date.strftime('%d/%m/%Y')}"

    return TayNinhOutagesResponse(
        date=date_iso,
        display_date=display_date,
        total_count=len(all_items),
        wards_summary=wards_summary,
        items=all_items,
    )
