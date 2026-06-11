import json
from pathlib import Path


DATA_DIR = Path("data")
PUSHER_FILE = DATA_DIR / "pushers.json"


def ensure_pusher_file():
    DATA_DIR.mkdir(exist_ok=True)

    if not PUSHER_FILE.exists():
        PUSHER_FILE.write_text("{}", encoding="utf-8")


def load_pushers() -> dict:
    ensure_pusher_file()

    with PUSHER_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_pushers(data: dict):
    ensure_pusher_file()

    with PUSHER_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def save_pusher(user_id: int, name: str, rate: str):
    data = load_pushers()

    data[str(user_id)] = {
        "name": name,
        "rate": rate
    }

    save_pushers(data)


def get_pusher(user_id: int) -> dict | None:
    data = load_pushers()

    return data.get(str(user_id))


def format_pusher_name(user_id: int, default_name: str) -> str:
    pusher = get_pusher(user_id)

    if pusher is None:
        return default_name

    name = pusher.get("name", default_name)
    rate = pusher.get("rate", "")

    if not rate:
        return name

    return f"{name}({rate})"