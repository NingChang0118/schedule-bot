from datetime import datetime, timedelta

from config import EMERGENCY_RECRUIT_ROLE_ID


def is_15_minutes_before_slot(schedule, row) -> bool:
    """
    判斷目前時間是否剛好是該時段發車前 15 分鐘
    """
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

        target_time = slot_start - timedelta(minutes=15)

        return (
            now.year == target_time.year
            and now.month == target_time.month
            and now.day == target_time.day
            and now.hour == target_time.hour
            and now.minute == target_time.minute
        )

    except Exception as e:
        print("[緊急招募] 時間判斷失敗：", e)
        return False


def needs_emergency_recruit(row) -> bool:
    """
    判斷該時段是否需要緊急招募

    條件：
    - 有跑者
    - 總人數未滿 5 人
    """
    slots = [
        row.slot_1,
        row.slot_2,
        row.slot_3,
        row.slot_4,
        row.slot_5
    ]

    has_runner = False
    filled_count = 0

    for slot in slots:
        if not slot:
            continue

        filled_count += 1

        if isinstance(slot, dict) and slot.get("type") == "runner":
            has_runner = True

    return has_runner and filled_count < 5


def get_emergency_key(schedule, row) -> str:
    """
    產生緊急招募唯一 Key
    """
    return (
        f"{schedule.car}_"
        f"{schedule.date}_"
        f"{row.time}"
    )


def has_emergency_recruit_been_sent(
    emergency_recruited: set,
    schedule,
    row
) -> bool:
    """
    是否已經發送過緊急招募
    """
    key = get_emergency_key(schedule, row)

    return key in emergency_recruited


def mark_emergency_recruit_sent(
    emergency_recruited: set,
    schedule,
    row
):
    """
    標記已發送
    """
    key = get_emergency_key(schedule, row)

    emergency_recruited.add(key)


def get_missing_count(row) -> int:
    """
    計算該時段缺幾人
    滿班為 5 人
    """
    slots = [
        row.slot_1,
        row.slot_2,
        row.slot_3,
        row.slot_4,
        row.slot_5
    ]

    filled_count = 0

    for slot in slots:
        if slot:
            filled_count += 1

    return 5 - filled_count


def build_emergency_recruit_message(
    schedule,
    row
) -> str:
    missing_count = get_missing_count(row)

    display_time = row.time

    if len(display_time) == 9:
        display_time = (
            f"{display_time[0:2]}-"
            f"{display_time[5:7]}"
        )

    return (
        f"<@&{EMERGENCY_RECRUIT_ROLE_ID}>\n"
        f"{schedule.car} {display_time} @{missing_count}"
    )