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

    def dedupe_slots(slot_list):
        seen = set()
        result = []

        for slot in slot_list:
            if not isinstance(slot, dict):
                continue

            user_id = slot.get("user_id")
            role_type = slot.get("type")

            if user_id is None or role_type is None:
                continue

            key = (
                str(user_id),
                role_type
            )

            if key in seen:
                continue

            seen.add(key)
            result.append(slot)

        return result

    active_runners = [
        slot
        for slot in slots
        if is_runner_slot(slot)
    ]

    backup_runners = [
        slot
        for slot in row.backup
        if is_runner_slot(slot)
    ]

    runners = dedupe_slots(
        active_runners + backup_runners
    )

    s6_slots = []

    if (
        isinstance(row.s6, dict)
        and row.s6.get("type") == "s6"
    ):
        s6_slots.append(row.s6)

    active_pushers = [
        slot
        for slot in slots
        if is_pusher_slot(slot)
    ]

    backup_pushers = [
        slot
        for slot in row.backup
        if is_pusher_slot(slot)
    ]

    pushers = dedupe_slots(
        active_pushers + backup_pushers
    )

    pushers = [
        slot
        for slot in pushers
        if not (
            isinstance(row.s6, dict)
            and is_same_user(slot, row.s6)
        )
    ]

    pushers.sort(
        key=get_slot_rate,
        reverse=True
    )

    sorted_members = runners + s6_slots + pushers

    official_members = sorted_members[:5]
    backup_members = sorted_members[5:]

    row.slot_1 = official_members[0] if len(official_members) > 0 else ""
    row.slot_2 = official_members[1] if len(official_members) > 1 else ""
    row.slot_3 = official_members[2] if len(official_members) > 2 else ""
    row.slot_4 = official_members[3] if len(official_members) > 3 else ""
    row.slot_5 = official_members[4] if len(official_members) > 4 else ""

    row.backup = [
        slot
        for slot in backup_members
        if not (
            isinstance(slot, dict)
            and slot.get("type") == "s6"
        )
    ]


def remove_member_from_row(row, user_id, role_type: str):
    removed = []

    if (
        role_type == "s6"
        and isinstance(row.s6, dict)
        and is_same_user(row.s6, user_id)
        and row.s6.get("type") == "s6"
    ):
        removed.append(get_slot_display(row.s6))
        row.s6 = ""
    
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
