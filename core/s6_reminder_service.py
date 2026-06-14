from core.slot_utils import get_all_slots
from core.s6_pusher_storage import get_s6_pusher
from core.schedule_utils import (
    normalize_car,
    normalize_date
)
from datetime import datetime, timedelta


def get_highest_runner_power(row):
    highest_power = 0

    for slot in get_all_slots(row):
        if not slot:
            continue

        if slot.get("type") != "runner":
            continue

        try:
            power = float(slot.get("power", 0))

        except Exception:
            power = 0

        highest_power = max(
            highest_power,
            power
        )

    return highest_power


def get_s6_candidates(row):
    if row.s6:
        return []

    highest_runner_power = get_highest_runner_power(row)

    if highest_runner_power <= 0:
        return []

    candidates = []

    for slot in get_all_slots(row):
        if not slot:
            continue

        if slot.get("type") != "pusher":
            continue

        user_id = slot.get("user_id")

        if user_id is None:
            continue

        s6_data = get_s6_pusher(user_id)

        if s6_data is None:
            continue

        try:
            s6_power = float(
                s6_data.get("power", 0)
            )

        except Exception:
            s6_power = 0

        if s6_power > highest_runner_power:
            candidates.append(
                {
                    "user_id": user_id,
                    "name": slot.get("name"),
                    "rate": s6_data.get("rate"),
                    "power": s6_power
                }
            )

    return candidates


def get_s6_reminder_user_ids(row):
    candidates = get_s6_candidates(row)

    return [
        candidate["user_id"]
        for candidate in candidates
    ]


def is_user_valid_s6_candidate(
    row,
    user_id
):
    user_id = str(user_id)

    if row.s6:
        return False

    for candidate in get_s6_candidates(row):
        if str(candidate["user_id"]) == user_id:
            return True

    return False


def get_s6_reminder_key(
    schedule,
    row
):
    return (
        f"{schedule.period}:"
        f"{schedule.car}:"
        f"{normalize_date(schedule.date)}:"
        f"{row.time}"
    )


def has_s6_reminder_been_sent(
    sent_keys: set,
    schedule,
    row
):
    key = get_s6_reminder_key(
        schedule,
        row
    )

    return key in sent_keys


def mark_s6_reminder_sent(
    sent_keys: set,
    schedule,
    row
):
    key = get_s6_reminder_key(
        schedule,
        row
    )

    sent_keys.add(key)


def parse_slot_start_datetime(
    schedule,
    row
):
    now = datetime.now()

    date_text = normalize_date(
        schedule.date
    )

    time_text = row.time

    candidates = []

    for year in [
        now.year - 1,
        now.year,
        now.year + 1
    ]:
        try:
            slot_start = datetime.strptime(
                f"{year}/{date_text} {time_text[:4]}",
                "%Y/%m/%d %H%M"
            )

            candidates.append(slot_start)

        except Exception:
            continue

    if not candidates:
        return None

    return min(
        candidates,
        key=lambda dt: abs(dt - now)
    )


def is_30_minutes_before_s6_slot(
    schedule,
    row
):
    slot_start = parse_slot_start_datetime(
        schedule,
        row
    )

    if slot_start is None:
        return False

    now = datetime.now()

    return (
        slot_start - timedelta(minutes=30)
        <= now
        < slot_start
    )


def build_s6_reminder_message(
    schedule,
    row,
    user_ids
):
    mentions = [
        f"<@{user_id}>"
        for user_id in user_ids
    ]

    mention_text = " ".join(
        mentions
    )

    return (
        f"{mention_text}\n"
        f"S6提醒\n"
        f"車輛：{schedule.car}\n"
        f"日期：{schedule.date}\n"
        f"時間：{row.time}"
    )