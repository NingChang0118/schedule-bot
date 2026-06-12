from core.storage import (
    save_schedule,
    get_schedule,
    delete_schedule,
    load_all,
    dict_to_schedule,
    save_all,
)

from core.renderer import render_schedule


def schedule_key(car: str, date: str) -> str:
    return f"{car}_{date}"

def get_row_by_time(schedule, time: str):
    """
    從班表取得指定時段
    """

    for row in schedule.rows:
        if row.time == time:
            return row

    return None