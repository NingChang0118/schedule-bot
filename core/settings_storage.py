import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
SETTINGS_FILE = DATA_DIR / "settings.json"

DEFAULT_SETTINGS = {
    "current_period": 172
}


def ensure_settings_file():
    DATA_DIR.mkdir(exist_ok=True)

    if not SETTINGS_FILE.exists():
        save_settings(DEFAULT_SETTINGS)


def load_settings() -> dict:
    ensure_settings_file()

    with SETTINGS_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_settings(data: dict):
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    with SETTINGS_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_current_period() -> int:
    data = load_settings()

    return int(
        data.get(
            "current_period",
            DEFAULT_SETTINGS["current_period"]
        )
    )


def set_current_period(period: int):
    data = load_settings()

    old_period = int(
        data.get(
            "current_period",
            DEFAULT_SETTINGS["current_period"]
        )
    )

    data["current_period"] = int(period)

    save_settings(data)

    return old_period, int(period)