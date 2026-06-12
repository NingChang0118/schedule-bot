from core.schedule_utils import expand_time_range
from core.schedule_service import get_row_by_time

def get_backup_slots(row):
    backups = [
        slot
        for slot in row.backup
        if isinstance(slot, dict)
    ]

    return backups


def build_backup_list_text(
    car: str,
    date: str,
    time: str,
    backups: list
):
    text = f"📋 **候補順位**\n\n"
    text += f"`{car} {date} {time}`\n\n"

    for index, slot in enumerate(backups, start=1):
        text += f"{index}. {slot.get('display')}\n"

    text += f"\n目前候補人數：{len(backups)}"

    return text

def get_backup_list(schedule, time: str):
    target_time = expand_time_range(time)[0]

    target_row = get_row_by_time(
        schedule,
        target_time
    )

    if target_row is None:
        return {
            "ok": False,
            "error": "time_not_found",
            "target_time": target_time,
            "backups": []
        }

    backups = get_backup_slots(target_row)

    return {
        "ok": True,
        "error": None,
        "target_time": target_time,
        "backups": backups
    }