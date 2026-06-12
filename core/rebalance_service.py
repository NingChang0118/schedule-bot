# core/rebalance_service.py

from core.slot_service import (
    get_slot_rate,
    is_runner_slot,
    is_pusher_slot
)

from core.slot_utils import (
    get_slot_display,
    is_same_user
)


def get_official_keys(row):
    keys = set()

    for slot in [
        row.slot_1,
        row.slot_2,
        row.slot_3,
        row.slot_4,
        row.slot_5
    ]:
        if not isinstance(slot, dict):
            continue

        keys.add(
            (
                str(slot["user_id"]),
                slot["type"]
            )
        )

    return keys


def count_runners(row) -> int:
    slots = [
        row.slot_1,
        row.slot_2,
        row.slot_3,
        row.slot_4,
        row.slot_5
    ]

    return sum(
        1
        for slot in slots
        if is_runner_slot(slot)
    )


def has_runner_in_row(row) -> bool:
    slots = [
        row.slot_1,
        row.slot_2,
        row.slot_3,
        row.slot_4,
        row.slot_5
    ]

    return any(
        is_runner_slot(slot)
        for slot in slots
    )


def count_pushers(row) -> int:
    slots = [
        row.slot_1,
        row.slot_2,
        row.slot_3,
        row.slot_4,
        row.slot_5
    ]

    return sum(
        1
        for slot in slots
        if is_pusher_slot(slot)
    )


def rebalance_row(row):
    slots = [
        row.slot_1,
        row.slot_2,
        row.slot_3,
        row.slot_4,
        row.slot_5
    ]

    runners = [
        slot
        for slot in slots
        if is_runner_slot(slot)
    ]

    pushers = [
        slot
        for slot in slots
        if is_pusher_slot(slot)
    ]

    backup_pushers = [
        slot
        for slot in row.backup
        if isinstance(slot, dict) and slot.get("type") == "pusher"
    ]

    all_pushers = pushers + backup_pushers

    all_pushers.sort(
        key=get_slot_rate,
        reverse=True
    )

    max_pusher_count = 5 - len(runners)

    if max_pusher_count < 0:
        max_pusher_count = 0

    active_pushers = all_pushers[:max_pusher_count]
    backup_pushers = all_pushers[max_pusher_count:]

    sorted_members = runners + active_pushers

    row.slot_1 = sorted_members[0] if len(sorted_members) > 0 else ""
    row.slot_2 = sorted_members[1] if len(sorted_members) > 1 else ""
    row.slot_3 = sorted_members[2] if len(sorted_members) > 2 else ""
    row.slot_4 = sorted_members[3] if len(sorted_members) > 3 else ""
    row.slot_5 = sorted_members[4] if len(sorted_members) > 4 else ""

    row.backup = backup_pushers


def remove_member_from_row(row, user_id, role_type: str):
    removed = []

    before_keys = get_official_keys(row)

    def should_remove(slot):
        return (
            isinstance(slot, dict)
            and is_same_user(slot, user_id)
            and slot.get("type") == role_type
        )

    if should_remove(row.slot_1):
        removed.append(get_slot_display(row.slot_1))
        row.slot_1 = ""

    if should_remove(row.slot_2):
        removed.append(get_slot_display(row.slot_2))
        row.slot_2 = ""

    if should_remove(row.slot_3):
        removed.append(get_slot_display(row.slot_3))
        row.slot_3 = ""

    if should_remove(row.slot_4):
        removed.append(get_slot_display(row.slot_4))
        row.slot_4 = ""

    if should_remove(row.slot_5):
        removed.append(get_slot_display(row.slot_5))
        row.slot_5 = ""

    for backup_slot in row.backup[:]:
        if should_remove(backup_slot):
            removed.append(
                get_slot_display(backup_slot)
            )

            row.backup.remove(backup_slot)

    rebalance_row(row)

    after_keys = get_official_keys(row)

    promoted_keys = after_keys - before_keys

    print("遞補轉正：", promoted_keys)

    promoted_slots = []

    for slot in [
        row.slot_1,
        row.slot_2,
        row.slot_3,
        row.slot_4,
        row.slot_5
    ]:
        if not isinstance(slot, dict):
            continue

        key = (
            str(slot["user_id"]),
            slot["type"]
        )

        if key in promoted_keys:
            promoted_slots.append(slot)

    print("遞補轉正資料：", promoted_slots)

    return removed, promoted_slots

