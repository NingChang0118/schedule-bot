from config import (
    RECRUIT_ROLE_ID,
    RECRUIT_CARS
)

from core.settings_storage import (
    get_current_period
)

from core.storage import get_schedule
from core.recruit_service import (
    get_recruit_rows,
    build_daily_recruit_message
)

from core.daily_recruit_state import (
    load_recruit_state,
    save_recruit_state
)


def has_sent_daily_recruit(date: str) -> bool:
    state = load_recruit_state()

    return (
        state.get("last_daily_recruit_date")
        == date
    )


def mark_daily_recruit_sent(date: str):
    state = load_recruit_state()

    state["last_daily_recruit_date"] = date

    save_recruit_state(state)


def build_today_daily_recruit_message(
    date: str
) -> str | None:

    car_sections = []

    for car in RECRUIT_CARS:
        current_period = get_current_period()

        schedule = get_schedule(
            current_period,
            car,
            date
        )

        if schedule is None:
            continue

        recruit_rows = get_recruit_rows(
            schedule
        )

        if not recruit_rows:
            continue

        car_sections.append(
            (
                car,
                recruit_rows
            )
        )

    if not car_sections:
        return None

    return build_daily_recruit_message(
        role_id=RECRUIT_ROLE_ID,
        date=date,
        car_sections=car_sections
    )