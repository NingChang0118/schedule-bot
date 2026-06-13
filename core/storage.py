import json
from pathlib import Path
from dataclasses import asdict

from core.models import Schedule, TimeSlot


DATA_DIR = Path("data")
DATA_FILE = DATA_DIR / "schedules.json"


def ensure_data_file():
    DATA_DIR.mkdir(exist_ok=True)

    if not DATA_FILE.exists():
        DATA_FILE.write_text("{}", encoding="utf-8")


def load_all() -> dict:
    ensure_data_file()

    try:
        with DATA_FILE.open("r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {}


def save_all(data: dict):
    ensure_data_file()

    temp_file = DATA_FILE.with_suffix(".tmp")

    with temp_file.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    temp_file.replace(DATA_FILE)


def schedule_to_dict(schedule: Schedule) -> dict:
    return asdict(schedule)


def normalize_row(row: dict) -> dict:
    row = row.copy()

    row.setdefault("slot_1", "")
    row.setdefault("slot_2", "")
    row.setdefault("slot_3", "")
    row.setdefault("slot_4", "")
    row.setdefault("slot_5", "")
    row.setdefault("s6", "")
    row.setdefault("car_type", "")

    backup = row.get("backup", [])

    if backup == "" or backup is None:
        backup = []

    if not isinstance(backup, list):
        backup = []

    row["backup"] = backup

    return row


def dict_to_schedule(data: dict) -> Schedule:
    rows = [
        TimeSlot(**normalize_row(row))
        for row in data.get("rows", [])
    ]

    return Schedule(
        period=data["period"],
        car=data["car"],
        date=data["date"],
        channel_id=data.get("channel_id"),
        message_id=data.get("message_id"),
        rows=rows
    )


def make_schedule_id(period: str, car: str, date: str) -> str:
    return f"{period}-{car}-{date}"


def save_schedule(schedule: Schedule):
    data = load_all()
    schedule_id = make_schedule_id(
        schedule.period,
        schedule.car,
        schedule.date
    )

    data[schedule_id] = schedule_to_dict(schedule)
    save_all(data)


def get_schedule(period: str, car: str, date: str) -> Schedule | None:
    data = load_all()
    schedule_id = make_schedule_id(period, car, date)

    if schedule_id not in data:
        return None

    return dict_to_schedule(data[schedule_id])


def delete_schedule(period: str, car: str, date: str) -> bool:
    data = load_all()

    schedule_id = make_schedule_id(period, car, date)

    if schedule_id in data:
        del data[schedule_id]
        save_all(data)
        return True

    target_date = date

    try:
        if "/" in target_date:
            month, day = target_date.split("/")
            target_date = f"{int(month)}/{int(day)}"
    except Exception:
        pass

    for key, schedule_data in list(data.items()):
        if schedule_data.get("period") != period:
            continue

        if schedule_data.get("car") != car:
            continue

        schedule_date = schedule_data.get("date")

        try:
            if "/" in schedule_date:
                month, day = schedule_date.split("/")
                schedule_date = f"{int(month)}/{int(day)}"
        except Exception:
            pass

        if schedule_date != target_date:
            continue

        del data[key]
        save_all(data)
        return True

    return False