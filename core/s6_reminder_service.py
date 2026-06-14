from core.slot_utils import get_all_slots
from core.s6_pusher_storage import get_s6_pusher
from datetime import datetime, timedelta


def get_highest_runner_power(row):

    highest_power = 0

    for slot in get_all_slots(row):

        if not slot:
            continue

        if slot.get("type") != "runner":
            continue

        try:
            power = int(slot.get("power", 0))

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

    highest_runner_power = (
        get_highest_runner_power(row)
    )

    if highest_runner_power <= 0:
        return []

    candidates = []

    for slot in get_all_slots(row):

        if not slot:
            continue

        if slot.get("type") != "pusher":
            continue

        user_id = slot.get("user_id")

        s6_data = get_s6_pusher(
            user_id
        )

        if s6_data is None:
            continue

        try:
            s6_power = int(
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

    candidates = get_s6_candidates(
        row
    )

    return [
        candidate["user_id"]
        for candidate in candidates
    ]


def get_s6_reminder_key(
    schedule,
    row
):
    return (
        f"{schedule.period}:"
        f"{schedule.car}:"
        f"{schedule.date}:"
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


def is_30_minutes_before_s6_slot(
    schedule,
    row
):
    try:
        now = datetime.now()

        slot_start = datetime.strptime(
            f"{now.year}/{schedule.date} {row.time[:4]}",
            "%Y/%m/%d %H%M"
        )

    except Exception:
        return False

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

