from core.slot_utils import is_same_user


def fill_first_empty_slot(row, slot_data) -> bool:
    if not row.slot_1:
        row.slot_1 = slot_data
        return True

    if not row.slot_2:
        row.slot_2 = slot_data
        return True

    if not row.slot_3:
        row.slot_3 = slot_data
        return True

    if not row.slot_4:
        row.slot_4 = slot_data
        return True

    if not row.slot_5:
        row.slot_5 = slot_data
        return True

    return False


def is_row_full(row) -> bool:
    return (
        row.slot_1
        and row.slot_2
        and row.slot_3
        and row.slot_4
        and row.slot_5
    )


def already_in_row(row, user_id, role_type: str) -> bool:
    slots = [
        row.slot_1,
        row.slot_2,
        row.slot_3,
        row.slot_4,
        row.slot_5,
    ]

    for slot in slots:
        if not is_same_user(slot, user_id):
            continue

        if isinstance(slot, dict) and slot.get("type") == role_type:
            return True

    for slot in row.backup:
        if not is_same_user(slot, user_id):
            continue

        if isinstance(slot, dict) and slot.get("type") == role_type:
            return True

    return False