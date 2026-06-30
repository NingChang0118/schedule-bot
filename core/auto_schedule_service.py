import discord

from core.models import create_empty_schedule
from core.storage import get_schedule, save_schedule
from core.renderer import render_schedule
from core.discord_message_service import send_log_to_channel
from config import (
    RECRUIT_CARS,
    SCHEDULE_UPDATE_CHANNEL_ID,
    FORMAL_SCHEDULE_CHANNEL_ID
)

from core.settings_storage import (
    get_current_period
)


def is_formal_car(car: str) -> bool:
    return car in RECRUIT_CARS


async def ensure_schedule_for_booking(
    bot,
    interaction: discord.Interaction,
    car: str,
    date: str
):
    current_period = get_current_period()

    schedule = get_schedule(
        current_period,
        car,
        date
    )

    if schedule is not None:
        return schedule, False

    if not is_formal_car(car):
        return None, False

    schedule = create_empty_schedule(
        current_period,
        car,
        date
    )

    image_path = render_schedule(schedule)

    schedule_channel = bot.get_channel(
        FORMAL_SCHEDULE_CHANNEL_ID
    )

    if schedule_channel is None:
        schedule_channel = await bot.fetch_channel(
            FORMAL_SCHEDULE_CHANNEL_ID
        )

    message = await schedule_channel.send(
        file=discord.File(
            str(image_path),
            filename="schedule.png"
        )
    )

    schedule.channel_id = schedule_channel.id
    schedule.message_id = message.id

    save_schedule(schedule)

    await send_log_to_channel(
        bot,
        SCHEDULE_UPDATE_CHANNEL_ID,
        (
            f"🆕 自動建立正式車班表\n"
            f"車輛：`{car}`\n"
            f"日期：`{date}`\n"
            f"班表頻道：{schedule_channel.mention}\n"
            f"觸發者：{interaction.user.mention}"
        )
    )

    return schedule, True