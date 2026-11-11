from typing import List, Dict, Optional
from pydantic import BaseModel

class OutageItem(BaseModel):
    start_date: str
    start_time: str
    end_date: str
    end_time: str
    location: str
    cause: str
    raw_time: str
    unit_code: Optional[str] = "PB0501"
    unit_name: Optional[str] = "Điện lực Tân Ninh"
    wards: List[str] = []
    duration: Optional[str] = ""

class DaySummary(BaseModel):
    date: str
    weekday_code: str  # T2, T3, T4, T5, T6, T7, CN
    weekday_full: str  # Thứ Hai, Thứ Ba...
    is_outage: bool
    status_text: str   # "Không cúp" hoặc "Cúp điện (từ 07:00 - 17:00)"
    outages: List[OutageItem] = []

class WeeklyReport(BaseModel):
    ward: str
    area: str
    unit_code: str
    start_week: str
    end_week: str
    days: List[DaySummary]
    formatted_text: str

class TayNinhOutagesResponse(BaseModel):
    date: str
    display_date: str
    total_count: int
    wards_summary: Dict[str, int]
    items: List[OutageItem]
