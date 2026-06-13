from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from core.models import Schedule
from core.slot_utils import get_slot_display


IMAGE_DIR = Path("data/images")


def safe_filename(text: str) -> str:
    return (
        text.replace("/", "-")
            .replace("\\", "-")
            .replace(":", "-")
            .replace("*", "-")
            .replace("?", "-")
            .replace('"', "-")
            .replace("<", "-")
            .replace(">", "-")
            .replace("|", "-")
    )

def draw_center_text(draw, box, text, font, fill="black"):
    x1, y1, x2, y2 = box

    text = str(text)

    bbox = draw.textbbox((0, 0), text, font=font)

    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    x = x1 + (x2 - x1 - text_width) / 2
    y = y1 + (y2 - y1 - text_height) / 2 - 1

    draw.text(
        (x, y),
        text,
        fill=fill,
        font=font
    )

def get_backup_display(backup):
    if not backup:
        return ""

    if isinstance(backup, str):
        return backup

    if isinstance(backup, dict):
        return get_slot_display(backup)

    if isinstance(backup, list):
        if not backup:
            return ""

        return get_slot_display(backup[0])
    
    return ""

def get_time_display(time_text: str) -> str:
    try:
        start, end = time_text.split("-")

        return (
            f"{start[:2]}-{end[:2]}"
        )

    except Exception:
        return time_text

def render_schedule(schedule: Schedule) -> Path:
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)

    safe_period = safe_filename(schedule.period)
    safe_car = safe_filename(schedule.car)
    safe_date = safe_filename(schedule.date)

    output_path = IMAGE_DIR / f"{safe_period}_{safe_car}_{safe_date}.png"

    headers = [
        f"{schedule.car}({schedule.date})",
        "1",
        "2",
        "3",
        "4",
        "5",
        "候補",
        "S6",
        "車種"
    ]

    col_widths = [150, 125, 125, 125, 125, 125, 145, 110, 125]
    row_height = 32

    width = sum(col_widths)
    height = row_height * (len(schedule.rows) + 1)

    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("msjh.ttc", 20)
    except OSError:
        font = ImageFont.load_default()

    x_positions = [0]
    for w in col_widths:
        x_positions.append(x_positions[-1] + w)

    # 表頭
    y = 0
    for i, header in enumerate(headers):
        x1 = x_positions[i]
        x2 = x_positions[i + 1]

        draw.rectangle(
            [x1, y, x2, y + row_height],
            fill="#5B7DB1",
            outline="black"
        )

        draw_center_text(
            draw,
            (x1, y, x2, y + row_height),
            header,
            font,
            fill="white"
        )

    # 內容
    for row_index, row in enumerate(schedule.rows):
        y = row_height * (row_index + 1)

        values = [
            get_time_display(row.time),
            get_slot_display(row.slot_1),
            get_slot_display(row.slot_2),
            get_slot_display(row.slot_3),
            get_slot_display(row.slot_4),
            get_slot_display(row.slot_5),
            get_backup_display(row.backup),
            get_slot_display(row.s6),
            row.car_type
        ]

        for col_index, value in enumerate(values):
            x1 = x_positions[col_index]
            x2 = x_positions[col_index + 1]

            if col_index == 6:
                fill = "#FFE5B4"
            elif col_index == 7:
                fill = "#D9F2D9"
            elif col_index == 8:
                fill = "#FFF8CC"
            else:
                fill = "white"

            draw.rectangle(
                [x1, y, x2, y + row_height],
                fill=fill,
                outline="black"
            )

            draw_center_text(
                draw,
                (x1, y, x2, y + row_height),
                value,
                font
            )

    img.save(output_path)
    return output_path