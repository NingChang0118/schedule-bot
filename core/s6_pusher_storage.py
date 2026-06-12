import json
from pathlib import Path


DATA_DIR = Path("data")
S6_PUSHER_FILE = DATA_DIR / "s6_pushers.json"


def ensure_s6_pusher_file():
    DATA_DIR.mkdir(exist_ok=True)

    if not S6_PUSHER_FILE.exists():
        S6_PUSHER_FILE.write_text("{}", encoding="utf-8")


def load_s6_pushers() -> dict:
    ensure_s6_pusher_file()

    with S6_PUSHER_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_s6_pushers(data: dict):
    ensure_s6_pusher_file()

    with S6_PUSHER_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def save_s6_pusher(
    user_id: int,
    rate: str,
    power: str
):
    data = load_s6_pushers()

    data[str(user_id)] = {
        "rate": rate,
        "power": power
    }

    save_s6_pushers(data)


def get_s6_pusher(user_id: int) -> dict | None:
    data = load_s6_pushers()

    return data.get(str(user_id))