from core.storage import load_all, dict_to_schedule
from core.slot_utils import is_same_user

def get_user_schedule_records(
    user_id,
    current_period
):
    user_id = str(user_id)

    all_data = load_all()

    records = []

    for schedule_data in all_data.values():
        schedule = dict_to_schedule(schedule_data)

        if schedule.period != current_period:
            continue

        for row in schedule.rows:
            slots = [
                row.slot_1,
                row.slot_2,
                row.slot_3,
                row.slot_4,
                row.slot_5,
            ]

            slots.extend(row.backup)

            found = False

            for slot in slots:
                if is_same_user(slot, user_id):
                    found = True
                    break

            if found:
                records.append({
                    "date": schedule.date,
                    "car": schedule.car,
                    "time": row.time
                })

    records.sort(
        key=lambda item: (
            item["date"],
            item["car"],
            item["time"]
        )
    )

    return records

def build_my_schedule_text(records):
    if not records:
        return "你目前沒有任何報班紀錄。"

    text = "📋 **我的班表**\n\n"

    current_group = None

    for record in records:
        group = f"{record['date']} {record['car']}"

        if group != current_group:
            if current_group is not None:
                text += "\n"

            text += f"**{group}**\n"
            current_group = group

        text += f"- {record['time']}\n"

    return text