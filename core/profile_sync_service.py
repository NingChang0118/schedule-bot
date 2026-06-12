from config import CURRENT_PERIOD
from core.slot_utils import get_all_slots
from core.storage import (
    load_all,
    dict_to_schedule,
    save_schedule
)
from core.discord_message_service import update_schedule_message


def update_profile_slot(
    slot,
    user_id: int,
    role_type: str,
    name: str,
    rate: str | None = None
) -> bool:
    if not isinstance(slot, dict):
        return False

    if slot.get("user_id") != str(user_id):
        return False

    if slot.get("type") != role_type:
        return False

    slot["name"] = name
    slot["rate"] = rate

    if role_type == "pusher":
        slot["display"] = f"{name}({rate})"
    else:
        slot["display"] = f"{name}R"

    return True


def sync_profile_to_schedule(
    schedule,
    user_id: int,
    role_type: str,
    name: str,
    rate: str | None = None
) -> int:
    updated_count = 0

    for row in schedule.rows:
        for slot in get_all_slots(row):
            if update_profile_slot(
                slot,
                user_id,
                role_type,
                name,
                rate
            ):
                updated_count += 1

        for slot in row.backup:
            if update_profile_slot(
                slot,
                user_id,
                role_type,
                name,
                rate
            ):
                updated_count += 1

    return updated_count


async def sync_profile_to_all_current_schedules(
    bot,
    user_id: int,
    role_type: str,
    name: str,
    rate: str | None = None
) -> tuple[int, int]:
    all_data = load_all()

    updated_schedule_count = 0
    updated_slot_count = 0

    for schedule_key, schedule_data in all_data.items():
        schedule = dict_to_schedule(
            schedule_data
        )

        if schedule.period != CURRENT_PERIOD:
            continue

        updated_count = sync_profile_to_schedule(
            schedule,
            user_id,
            role_type,
            name,
            rate
        )

        if updated_count == 0:
            continue

        save_schedule(
            schedule
        )

        await update_schedule_message(
            bot,
            schedule
        )

        updated_schedule_count += 1
        updated_slot_count += updated_count

    return updated_schedule_count, updated_slot_count