from core.schedule_utils import expand_time_range
from core.schedule_service import get_row_by_time
from core.slot_utils import is_same_user
from core.row_service import (
    fill_first_empty_slot,
    already_in_row
)
from core.rebalance_service import (
    rebalance_row,
    remove_member_from_row,
    has_runner_in_row
)


def fill_pusher_schedule(schedule, user_id, slot_data, time: str, double_slot_data=None):
    times = expand_time_range(time)
    target_rows = []

    for target_time in times:
        target_row = get_row_by_time(schedule, target_time)

        if target_row is None:
            return {
                "ok": False,
                "error": "time_not_found",
                "target_time": target_time,
                "joined_times": [],
                "backup_times": []
            }

        target_rows.append((target_time, target_row))

    for target_time, target_row in target_rows:
        if already_in_row(target_row, user_id, "pusher") and double_slot_data is None:
            return {
                "ok": False,
                "error": "already_joined",
                "target_time": target_time,
                "joined_times": [],
                "backup_times": []
            }

    joined_times = []
    backup_times = []

    for target_time, target_row in target_rows:
        if not already_in_row(target_row, user_id, "pusher"):
            target_row.backup.append(slot_data)

        if double_slot_data is not None:
            target_row.backup.append(double_slot_data)

        rebalance_row(target_row)

        user_is_active = any(
            is_same_user(slot, user_id)
            and isinstance(slot, dict)
            and slot.get("type") == "pusher"
            for slot in [
                target_row.slot_1,
                target_row.slot_2,
                target_row.slot_3,
                target_row.slot_4,
                target_row.slot_5
            ]
        )

        if user_is_active:
            joined_times.append(target_time)
        else:
            backup_times.append(target_time)

    return {
        "ok": True,
        "error": None,
        "joined_times": joined_times,
        "backup_times": backup_times
    }


def fill_runner_schedule(schedule, user_id, slot_data, time: str, car_type: str | None = None):
    times = expand_time_range(time)
    target_rows = []

    for target_time in times:
        target_row = get_row_by_time(schedule, target_time)

        if target_row is None:
            return {
                "ok": False,
                "error": "time_not_found",
                "target_time": target_time,
                "joined_times": []
            }

        target_rows.append((target_time, target_row))

    for target_time, target_row in target_rows:
        if already_in_row(target_row, user_id, "runner"):
            return {
                "ok": False,
                "error": "already_joined",
                "target_time": target_time,
                "joined_times": []
            }
        
        if car_type:
            if target_row.car_type and target_row.car_type != car_type:
                return {
                    "ok": False,
                    "error": "car_type_locked",
                    "target_time": target_time,
                    "locked_car_type": target_row.car_type,
                    "joined_times": []
                }

    joined_times = []

    for target_time, target_row in target_rows:
        target_row.backup.append(slot_data)

        if car_type and not target_row.car_type:
            target_row.car_type = car_type

        rebalance_row(target_row)

        joined_times.append(target_time)

    return {
        "ok": True,
        "error": None,
        "joined_times": joined_times
    }


def cancel_user_schedule(
    schedule,
    user_id,
    role_type: str,
    time: str = "",
    all_day: bool = False
):
    if all_day:
        target_rows = [
            (row.time, row)
            for row in schedule.rows
        ]
    else:
        if not time:
            return {
                "ok": False,
                "error": "missing_time",
                "removed_records": [],
                "promoted_slots": [],
                "cleared_slots": [],
                "cancelled_rows": [],
                "runner_removed_rows": []
            }

        times = expand_time_range(time)
        target_rows = []

        for target_time in times:
            target_row = get_row_by_time(schedule, target_time)

            if target_row is None:
                return {
                    "ok": False,
                    "error": "time_not_found",
                    "target_time": target_time,
                    "removed_records": [],
                    "promoted_slots": [],
                    "cleared_slots": [],
                    "cancelled_rows": [],
                    "runner_removed_rows": []
                }

            target_rows.append((target_time, target_row))

    removed_records = []
    all_promoted_slots = []
    cleared_slots = []
    cancelled_rows = []
    runner_removed_rows = []

    for target_time, target_row in target_rows:
        slots_before_clear = [
            target_row.slot_1,
            target_row.slot_2,
            target_row.slot_3,
            target_row.slot_4,
            target_row.slot_5,
            target_row.s6
        ]

        slots_before_clear.extend(target_row.backup)

        removed_names, promoted_slots = remove_member_from_row(
            target_row,
            user_id,
            role_type
        )

        all_promoted_slots.extend(promoted_slots)

        for removed_name in removed_names:
            removed_records.append(
                f"{target_time}：{removed_name}"
            )

        if role_type == "runner" and removed_names:
            if has_runner_in_row(target_row):
                runner_removed_rows.append({
                    "time": target_time
                })

                continue

            for slot in slots_before_clear:
                if not isinstance(slot, dict):
                    continue

                if slot.get("type") not in ["pusher", "s6"]:
                    continue

                slot_user_id = slot.get("user_id")

                if slot_user_id is None:
                    continue

                cleared_slots.append({
                    "time": target_time,
                    "user_id": slot_user_id,
                    "display": slot.get("display", ""),
                    "type": slot.get("type", "")
                })

            target_row.slot_1 = ""
            target_row.slot_2 = ""
            target_row.slot_3 = ""
            target_row.slot_4 = ""
            target_row.slot_5 = ""
            target_row.backup = []
            target_row.s6 = ""
            target_row.car_type = ""

            cancelled_rows.append({
                "time": target_time
            })

    return {
        "ok": True,
        "error": None,
        "removed_records": removed_records,
        "promoted_slots": all_promoted_slots,
        "cleared_slots": cleared_slots,
        "cancelled_rows": cancelled_rows,
        "runner_removed_rows": runner_removed_rows
    }


def fill_s6_schedule(schedule, user_id, slot_data, time: str):
    times = expand_time_range(time)
    target_rows = []

    for target_time in times:
        target_row = get_row_by_time(schedule, target_time)

        if target_row is None:
            return {
                "ok": False,
                "error": "time_not_found",
                "target_time": target_time,
                "joined_times": []
            }

        target_rows.append((target_time, target_row))

    for target_time, target_row in target_rows:
        if target_row.s6:
            return {
                "ok": False,
                "error": "s6_already_exists",
                "target_time": target_time,
                "joined_times": []
            }

        if not already_in_row(target_row, user_id, "pusher"):
            return {
                "ok": False,
                "error": "not_pusher",
                "target_time": target_time,
                "joined_times": []
            }

    joined_times = []

    for target_time, target_row in target_rows:
        remove_member_from_row(
            target_row,
            user_id,
            "pusher"
        )

        target_row.s6 = slot_data

        rebalance_row(target_row)

        joined_times.append(target_time)

    return {
        "ok": True,
        "error": None,
        "joined_times": joined_times
    }