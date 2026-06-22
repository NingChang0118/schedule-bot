from core.storage import load_all, dict_to_schedule
from core.slot_utils import is_same_user
from config import RECRUIT_CARS

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

TAIPEI_TZ = ZoneInfo("Asia/Taipei")


def is_full_car(row):
    slots = [
        row.slot_1,
        row.slot_2,
        row.slot_3,
        row.slot_4,
        row.slot_5,
    ]

    return all(
        isinstance(slot, dict)
        for slot in slots
    )


def parse_time_to_hour_minute(time_text):
    if len(time_text) == 2:
        return int(time_text), 0

    return int(time_text[:2]), int(time_text[2:])


def is_finished_slot(schedule, row):
    now = datetime.now(TAIPEI_TZ)

    month, day = map(int, schedule.date.split("/"))

    end_time = row.time.split("-")[1]

    hour, minute = parse_time_to_hour_minute(end_time)

    day_offset = 0

    if hour == 24:
        hour = 0
        day_offset = 1

    slot_end = datetime(
        year=now.year,
        month=month,
        day=day,
        hour=hour,
        minute=minute,
        tzinfo=TAIPEI_TZ
    )

    if day_offset:
        slot_end += timedelta(days=1)

    return now >= slot_end


def get_user_hours(
    user_id,
    current_period=None
):
    user_id = str(user_id)

    all_data = load_all()

    pusher_hours = 0
    runner_hours = 0

    for schedule_data in all_data.values():
        schedule = dict_to_schedule(schedule_data)

        if schedule.car not in RECRUIT_CARS:
            continue

        if current_period is not None:
            if schedule.period != current_period:
                continue

        for row in schedule.rows:
            if not is_full_car(row):
                continue

            if not is_finished_slot(schedule, row):
                continue

            slots = [
                row.slot_1,
                row.slot_2,
                row.slot_3,
                row.slot_4,
                row.slot_5,
            ]

            for slot in slots:
                if not isinstance(slot, dict):
                    continue

                if not is_same_user(slot, user_id):
                    continue

                if slot.get("type") == "pusher":
                    pusher_hours += 1

                elif slot.get("type") == "runner":
                    runner_hours += 1

    return {
        "pusher_hours": pusher_hours,
        "runner_hours": runner_hours,
        "total_hours": pusher_hours - runner_hours
    }


def get_period_total_hours(current_period):
    all_data = load_all()

    runner_hours = {}
    pusher_hours = {}

    for schedule_data in all_data.values():
        schedule = dict_to_schedule(schedule_data)

        if schedule.car not in RECRUIT_CARS:
            continue

        if schedule.period != current_period:
            continue

        for row in schedule.rows:
            if not is_full_car(row):
                continue

            if not is_finished_slot(schedule, row):
                continue

            slots = [
                row.slot_1,
                row.slot_2,
                row.slot_3,
                row.slot_4,
                row.slot_5,
            ]

            for slot in slots:
                if not isinstance(slot, dict):
                    continue

                name = slot.get("name")
                role_type = slot.get("type")

                if not name:
                    continue

                if role_type == "runner":
                    runner_hours[name] = runner_hours.get(name, 0) + 1

                elif role_type == "pusher":
                    pusher_hours[name] = pusher_hours.get(name, 0) + 1

    return {
        "runner_hours": runner_hours,
        "pusher_hours": pusher_hours
    }


def build_current_hours_text(
    current_period,
    stats
):
    pusher_hours = stats["pusher_hours"]
    runner_hours = stats["runner_hours"]
    total_hours = stats["total_hours"]

    return (
        f"📊 **{current_period}期時數統計**\n\n"
        f"推車時數：{pusher_hours}\n"
        f"跑者時數：{runner_hours}\n"
        f"結算時數：{total_hours}"
    )


def build_history_hours_text(stats):
    pusher_hours = stats["pusher_hours"]
    runner_hours = stats["runner_hours"]
    total_hours = stats["total_hours"]

    return (
        f"📊 **歷史時數統計**\n\n"
        f"推車時數：{pusher_hours}\n"
        f"跑者時數：{runner_hours}\n"
        f"結算時數：{total_hours}"
    )


def build_period_total_hours_text(current_period):
    stats = get_period_total_hours(
        current_period
    )

    runner_hours = stats["runner_hours"]
    pusher_hours = stats["pusher_hours"]

    text = "📊 **當期累積時數統計**\n\n"

    text += "**時數結算 R**\n"

    if runner_hours:
        sorted_runners = sorted(
            runner_hours.items(),
            key=lambda item: item[1],
            reverse=True
        )

        for name, hours in sorted_runners:
            text += f"{name}    {hours}\n"
    else:
        text += "目前沒有跑者時數\n"

    text += "\n**時數結算 H**\n"

    if pusher_hours:
        sorted_pushers = sorted(
            pusher_hours.items(),
            key=lambda item: item[1],
            reverse=True
        )

        for name, hours in sorted_pushers:
            text += f"{name}    {hours}\n"
    else:
        text += "目前沒有推車時數\n"

    return text