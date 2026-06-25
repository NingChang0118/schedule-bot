import json
from pathlib import Path


DATA_DIR = Path("data")
RUNNER_FILE = DATA_DIR / "runners.json"


def ensure_runner_file():
    DATA_DIR.mkdir(exist_ok=True)

    if not RUNNER_FILE.exists():
        RUNNER_FILE.write_text("{}", encoding="utf-8")


def load_runners() -> dict:
    ensure_runner_file()

    with RUNNER_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_runners(data: dict):
    ensure_runner_file()

    with RUNNER_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def save_runner(
    user_id: int,
    name: str,
    rate: float,
    power: float
):
    data = load_runners()

    data[str(user_id)] = {
        "name": name,
        "rate": rate,
        "power": power
    }

    save_runners(data)


def get_runner(user_id: int) -> dict | None:
    data = load_runners()

    return data.get(str(user_id))