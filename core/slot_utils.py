def make_slot(user_id, name, role_type, rate=None, power=None, is_double=False):
    if role_type in ["pusher", "s6"]:
        display = f"{name}({rate})"
    else:
        display = name

    return {
        "user_id": str(user_id),
        "name": name,
        "rate": rate,
        "power": power,
        "type": role_type,
        "is_double": is_double,
        "display": display
    }

def get_slot_display(slot):
    if not slot:
        return ""

    if isinstance(slot, str):
        return slot

    return slot.get("display", "")


def is_same_user(slot, user_id):
    if not slot:
        return False

    if isinstance(slot, str):
        return False

    return slot.get("user_id") == str(user_id)


def is_same_identity(slot, user_id, role_type):
    if not slot:
        return False

    if isinstance(slot, str):
        return False

    return (
        slot.get("user_id") == str(user_id)
        and slot.get("type") == role_type
    )


def get_all_slots(row):
    return [
        row.slot_1,
        row.slot_2,
        row.slot_3,
        row.slot_4,
        row.slot_5
    ]


def count_filled_slots(row):
    return sum(
        1
        for slot in get_all_slots(row)
        if slot
    )


def is_row_full(row):
    return count_filled_slots(row) >= 5


def add_to_backup(row, slot_data):
    if not isinstance(row.backup, list):
        row.backup = []
    row.backup.append(slot_data)


def pop_backup(row):
    if not row.backup:
        return None

    return row.backup.pop(0)