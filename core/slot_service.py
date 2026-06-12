def get_slot_rate(slot) -> float:
    if not slot:
        return 0.0

    if isinstance(slot, str):
        if "(" not in slot or ")" not in slot:
            return 0.0

        try:
            rate_text = slot.split("(")[-1].split(")")[0]
            return float(rate_text)
        except ValueError:
            return 0.0

    try:
        return float(slot.get("rate") or 0.0)
    except ValueError:
        return 0.0


def is_runner_slot(slot) -> bool:
    if not slot:
        return False

    if isinstance(slot, str):
        return "(" not in slot or ")" not in slot

    return slot.get("type") == "runner"


def is_pusher_slot(slot) -> bool:
    if not slot:
        return False

    if isinstance(slot, str):
        return "(" in slot and ")" in slot

    return slot.get("type") == "pusher"