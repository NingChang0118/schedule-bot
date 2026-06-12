import discord
from discord.ext import commands
from config import TOKEN

intents = discord.Intents.default()

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)


@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"排班機器人已上線：{bot.user}")
    print("Slash 指令已同步")


async def main():
    async with bot:
        await bot.load_extension("cogs.schedule_cog")
        await bot.load_extension("cogs.admin_cog")
        await bot.load_extension("cogs.test_cog")
        await bot.start(TOKEN)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())