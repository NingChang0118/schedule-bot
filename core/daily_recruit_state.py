import json
from pathlib import Path


DATA_DIR = Path("data")
STATE_FILE = DATA_DIR / "recruit_state.json"


def ensure_state_file():
    DATA_DIR.mkdir(exist_ok=True)

    if not STATE_FILE.exists():
        STATE_FILE.write_text(
            json.dumps(
                {
                    "last_daily_recruit_date": ""
                },
                ensure_ascii=False,
                indent=2
            ),
            encoding="utf-8"
        )


def load_recruit_state() -> dict:
    ensure_state_file()

    try:
        with STATE_FILE.open("r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {
            "last_daily_recruit_date": ""
        }


def save_recruit_state(state: dict):
    ensure_state_file()

    temp_file = STATE_FILE.with_suffix(".tmp")

    with temp_file.open("w", encoding="utf-8") as f:
        json.dump(
            state,
            f,
            ensure_ascii=False,
            indent=2
        )

    temp_file.replace(STATE_FILE)