from core.storage import (
    get_schedule,
    save_schedule
)

from core.schedule_utils import (
    normalize_car,
    normalize_date,
    normalize_time
)


def get_slot_attr(slot_number: int) -> str | None:
    if slot_number < 1 or slot_number > 5:
        return None

    return f"slot_{slot_number}"


def find_row_by_time(schedule, time: str):
    time = normalize_time(time)

    for row in schedule.rows:
        if row.time == time:
            return row

    return None


def move_formal_member(
    period: str,
    from_car: str,
    date: str,
    from_time: str,
    from_slot: int,
    to_car: str,
    to_time: str,
    to_slot: int
) -> tuple[bool, str]:

    from_car = normalize_car(from_car)
    to_car = normalize_car(to_car)
    date = normalize_date(date)
    from_time = normalize_time(from_time)
    to_time = normalize_time(to_time)

    from_slot_attr = get_slot_attr(from_slot)
    to_slot_attr = get_slot_attr(to_slot)

    if from_slot_attr is None:
        return False, "❌ 來源格位只能是 1 到 5。"

    if to_slot_attr is None:
        return False, "❌ 目標格位只能是 1 到 5。"

    from_schedule = get_schedule(
        period,
        from_car,
        date
    )

    if from_schedule is None:
        return False, f"❌ 找不到來源班表：`{from_car} {date}`。"

    to_schedule = get_schedule(
        period,
        to_car,
        date
    )

    if to_schedule is None:
        return False, f"❌ 找不到目標班表：`{to_car} {date}`。"

    from_row = find_row_by_time(
        from_schedule,
        from_time
    )

    if from_row is None:
        return False, f"❌ 找不到來源時段：`{from_time}`。"

    to_row = find_row_by_time(
        to_schedule,
        to_time
    )

    if to_row is None:
        return False, f"❌ 找不到目標時段：`{to_time}`。"

    member = getattr(from_row, from_slot_attr)

    if not member:
        return False, f"❌ 來源格位 `{from_slot}` 沒有成員。"

    target_member = getattr(to_row, to_slot_attr)

    if target_member:
        return False, f"❌ 目標格位 `{to_slot}` 已有人，不能覆蓋。"

    setattr(from_row, from_slot_attr, "")
    setattr(to_row, to_slot_attr, member)

    save_schedule(from_schedule)

    if from_car != to_car:
        save_schedule(to_schedule)
    else:
        save_schedule(from_schedule)

    return (
        True,
        f"✅ 已將 `{member}` 從 `{from_car} {date} {from_time} slot_{from_slot}` "
        f"移動到 `{to_car} {date} {to_time} slot_{to_slot}`。"
    )