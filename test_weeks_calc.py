import datetime
import re
from typing import Any, Dict, List

def calculate_recent_weeks(ref_date: datetime.date, count: int = 4) -> List[Dict[str, Any]]:
    """Calculates metadata for the last N weeks ending with the reference date."""
    weeks = []
    # Start of current week (Monday)
    curr_monday = ref_date - datetime.timedelta(days=ref_date.weekday())
    
    for i in range(count - 1, -1, -1):
        monday = curr_monday - datetime.timedelta(weeks=i)
        sunday = monday + datetime.timedelta(days=6)
        m = monday.month
        w_of_m = (monday.day - 1) // 7 + 1
        label = f"{m}월 {w_of_m}주차 ({monday.strftime('%m.%d')}~{sunday.strftime('%m.%d')})"
        short_label = f"{m}월 {w_of_m}주차"
        weeks.append({
            "index": count - 1 - i,
            "monday": monday,
            "sunday": sunday,
            "label": label,
            "short_label": short_label,
            "month": m,
            "week_of_month": w_of_m,
        })
    return weeks

print(calculate_recent_weeks(datetime.date(2026, 9, 26), count=4))
