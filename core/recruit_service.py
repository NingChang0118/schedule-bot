from core.rebalance_service import has_runner_in_row

def analyze_recruit_slots(row):
    formal_slots = [
        row.slot_1,
        row.slot_2,
        row.slot_3,
        row.slot_4,
        row.slot_5,
    ]

    occupied_slots = [
        slot
        for slot in formal_slots
        if slot
    ]

    total_count = len(occupied_slots)
    missing_count = max(0, 5 - total_count)

    return {
        "total_count": total_count,
        "missing_count": missing_count,
    }

def get_recruit_rows(schedule):
    recruit_rows = []

    for row in schedule.rows:
        if not has_runner_in_row(row):
            continue

        stats = analyze_recruit_slots(row)

        if stats["missing_count"] <= 0:
            continue

        recruit_rows.append(
            (
                row.time,
                stats["missing_count"]
            )
        )

    return recruit_rows

def build_recruit_message(
    role_id: int,
    car: str,
    date: str,
    recruit_rows: list
):
    role_mention = f"<@&{role_id}>"

    text = (
        f"{role_mention}\n\n"
        f"🚨 **缺額招募** 🚨\n\n"
        f"車輛：{car}\n"
        f"日期：{date}\n\n"
    )

    for time_text, missing_count in recruit_rows:
        text += (
            f"• {time_text}"
            f"（缺 {missing_count} 人）\n"
        )

    text += "\n請使用 `/報班` 補班。"

    return text