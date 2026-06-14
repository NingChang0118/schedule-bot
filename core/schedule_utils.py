def normalize_car(car: str) -> str:
    car_map = {
        "1": "一車",
        "2": "二車",
        "3": "三車",
        "4": "四車",
        "5": "五車",
        "一": "一車",
        "二": "二車",
        "三": "三車",
        "四": "四車",
        "五": "五車",
    }

    if car in ["測試", "測試車", "test"]:
        return "測試車"

    return car_map.get(car, car)


def normalize_date(date: str) -> str:
    date = date.strip()

    if "/" in date:
        month, day = date.split("/")
        return f"{int(month)}/{int(day)}"

    if len(date) == 4 and date.isdigit():
        month = int(date[:2])
        day = int(date[2:])
        return f"{month}/{day}"

    return date


def normalize_time(time_str: str) -> str:
    time_str = time_str.strip()

    if "-" not in time_str:
        return time_str

    try:
        start, end = time_str.split("-")

        start = parse_time_hour(start)
        end = parse_time_hour(end)

        return f"{start:02d}00-{end:02d}00"

    except ValueError:
        return time_str


def parse_time_hour(text: str) -> int:
    text = text.strip()

    if len(text) == 4 and text.isdigit():
        return int(text[:2])

    return int(text)


def expand_time_range(time_str: str) -> list[str]:
    time_str = time_str.strip()

    if "-" not in time_str:
        return [normalize_time(time_str)]

    try:
        start, end = time_str.split("-")

        start = parse_time_hour(start)
        end = parse_time_hour(end)

        if end <= start:
            return [normalize_time(time_str)]

        times = []

        for hour in range(start, end):
            times.append(f"{hour:02d}00-{hour + 1:02d}00")

        return times

    except ValueError:
        return [normalize_time(time_str)]