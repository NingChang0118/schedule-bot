from core.storage import get_schedule
from core.renderer import render_schedule


schedule = get_schedule("176", "一車", "6/11")

if schedule is None:
    print("找不到排班")
else:
    path = render_schedule(schedule)
    print(f"圖片已產生：{path}")