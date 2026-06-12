from config import BOARDING_REMINDER_CHANNEL_IDS
from datetime import datetime, timedelta

def get_boarding_reminder_user_ids(row) -> list[int]:
    user_ids = []

    slots = [
        row.slot_1,
        row.slot_2,
        row.slot_3,
        row.slot_4,
        row.slot_5
    ]

    for slot in slots:
        if not isinstance(slot, dict):
            continue

        user_id = slot.get("user_id")

        if user_id is None:
            continue

        if user_id not in user_ids:
            user_ids.append(user_id)

    if row.backup:
        first_backup = row.backup[0]

        if isinstance(first_backup, dict):
            user_id = first_backup.get("user_id")

            if user_id is not None and user_id not in user_ids:
                user_ids.append(user_id)

    return user_ids

def get_boarding_reminder_key(schedule, row) -> str:
    return (
        f"{schedule.car}_"
        f"{schedule.date}_"
        f"{row.time}"
    )

def get_boarding_reminder_channel_id(schedule) -> int | None:
    return BOARDING_REMINDER_CHANNEL_IDS.get(
        schedule.car
    )

def build_boarding_reminder_message(
    schedule,
    row,
    user_ids
) -> str:

    mentions = " ".join(
        f"<@{user_id}>"
        for user_id in user_ids
    )

    return (
        f"{mentions}\n\n"
        f"🚗 發車提醒\n\n"
        f"車輛：{schedule.car}\n"
        f"日期：{schedule.date}\n"
        f"時段：{row.time}\n\n"
        f"請準備上車。"
    )

def has_boarding_reminder_been_sent(
    sent_keys: set,
    schedule,
    row
) -> bool:

    key = get_boarding_reminder_key(
        schedule,
        row
    )

    return key in sent_keys

def mark_boarding_reminder_sent(
    sent_keys: set,
    schedule,
    row
):
    key = get_boarding_reminder_key(
        schedule,
        row
    )

    sent_keys.add(key)

def is_5_minutes_before_slot(schedule, row) -> bool:
    try:
        now = datetime.now()

        month, day = map(int, schedule.date.split("/"))

        start_time = row.time.split("-")[0]
        hour = int(start_time[:2])
        minute = int(start_time[2:])

        slot_start = datetime(
            year=now.year,
            month=month,
            day=day,
            hour=hour,
            minute=minute
        )

        if slot_start < now - timedelta(days=180):
            slot_start = slot_start.replace(
                year=now.year + 1
            )

        target_time = slot_start - timedelta(minutes=5)

        return (
            now.year == target_time.year
            and now.month == target_time.month
            and now.day == target_time.day
            and now.hour == target_time.hour
            and now.minute == target_time.minute
        )

    except Exception as e:
        print("[上車提醒] 時間判斷失敗：", e)
        return False
    
