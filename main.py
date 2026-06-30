import asyncio

import discord
from discord.ext import commands

from config import TOKEN


EXTENSIONS = [
    "cogs.reminder_cog",
    "cogs.admin_cog",
    "cogs.test_cog",
    "cogs.profile_cog",
    "cogs.booking_cog",
    "cogs.cancel_cog",
    "cogs.query_cog",
    "cogs.recruit_cog",
    "cogs.s6_report_cog"
]


intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)

bot.boarding_reminded = set()
bot.s6_reminded = set()
bot.emergency_recruited = set()

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"排班機器人已上線：{bot.user}")
    print("Slash 指令已同步")


async def main():
    async with bot:
        for extension in EXTENSIONS:
            await bot.load_extension(extension)

        await bot.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())