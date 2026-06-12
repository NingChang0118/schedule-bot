import discord

from core.renderer import render_schedule

async def send_log_to_channel(
    bot,
    channel_id: int,
    text: str
):
    channel = bot.get_channel(
        channel_id
    )

    if channel is None:
        channel = await bot.fetch_channel(
            channel_id
        )

    await channel.send(
        text
    )

async def update_schedule_message(
    bot,
    schedule
):
    image_path = render_schedule(
        schedule
    )

    channel = bot.get_channel(
        schedule.channel_id
    )

    if channel is None:
        channel = await bot.fetch_channel(
            schedule.channel_id
        )

    message = await channel.fetch_message(
        schedule.message_id
    )

    await message.edit(
        attachments=[
            discord.File(
                str(image_path),
                filename="schedule.png"
            )
        ]
    )

async def send_schedule_image_response(
    interaction,
    car: str,
    date: str,
    schedule
):
    image_path = render_schedule(
        schedule
    )

    file = discord.File(
        image_path,
        filename=image_path.name
    )

    await interaction.response.send_message(
        content=f"📅 {car} {date}",
        file=file
    )

