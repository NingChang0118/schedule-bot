from core.models import create_empty_schedule
from core.storage import save_schedule, get_schedule


schedule = create_empty_schedule(
    period="176",
    car="一車",
    date="6/11"
)

save_schedule(schedule)

loaded = get_schedule(
    period="176",
    car="一車",
    date="6/11"
)

print(loaded)