from dataclasses import dataclass, field
from typing import Any


DEFAULT_TIME_SLOTS = [
    "0000-0100",
    "0100-0200",
    "0200-0300",
    "0300-0400",
    "0400-0500",
    "0500-0600",
    "0600-0700",
    "0700-0800",
    "0800-0900",
    "0900-1000",
    "1000-1100",
    "1100-1200",
    "1200-1300",
    "1300-1400",
    "1400-1500",
    "1500-1600",
    "1600-1700",
    "1700-1800",
    "1800-1900",
    "1900-2000",
    "2000-2100",
    "2100-2200",
    "2200-2300",
    "2300-2400",
]


@dataclass
class TimeSlot:
    time: str

    slot_1: Any = ""
    slot_2: Any = ""
    slot_3: Any = ""
    slot_4: Any = ""
    slot_5: Any = ""

    backup: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class Schedule:
    period: str
    car: str
    date: str
    channel_id: int | None = None
    message_id: int | None = None

    rows: list[TimeSlot] = field(default_factory=list)


def create_empty_schedule(period: str, car: str, date: str) -> Schedule:
    rows = [
        TimeSlot(time=time)
        for time in DEFAULT_TIME_SLOTS
    ]

    return Schedule(
        period=period,
        car=car,
        date=date,
        channel_id=None,
        message_id=None,
        rows=rows
    )