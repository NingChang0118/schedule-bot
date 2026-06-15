from datetime import datetime
from zoneinfo import ZoneInfo

from discord.ext import commands, tasks

from core.schedule_utils import normalize_date

from config import RECRUIT_CHANNEL_ID

from core.reminder_scan_service import (
    run_boarding_reminder_scan,
    run_emergency_recruit_scan,
    run_s6_reminder_scan
)

from core.daily_recruit_service import (
    has_sent_daily_recruit,
    mark_daily_recruit_sent,
    build_today_daily_recruit_message
)

TAIPEI_TZ = ZoneInfo("Asia/Taipei")

class ReminderCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

        if not hasattr(self.bot, "emergency_recruited"):
            self.bot.emergency_recruited = set()

        if not hasattr(self.bot, "boarding_reminded"):
            self.bot.boarding_reminded = set()

        if not hasattr(self.bot, "s6_reminded"):
            self.bot.s6_reminded = set()

        self.emergency_recruit_loop.start()
        self.boarding_reminder_loop.start()
        self.s6_reminder_loop.start()
        self.daily_recruit_loop.start()

    def cog_unload(self):
        self.emergency_recruit_loop.cancel()
        self.boarding_reminder_loop.cancel()
        self.s6_reminder_loop.cancel()
        self.daily_recruit_loop.cancel()

    @tasks.loop(minutes=1)
    async def emergency_recruit_loop(self):
        print("[ReminderCog] emergency_recruit_loop tick")

        await run_emergency_recruit_scan(
            self.bot,
            self.bot.emergency_recruited
        )

    @emergency_recruit_loop.before_loop
    async def before_emergency_recruit_loop(self):
        await self.bot.wait_until_ready()

    @tasks.loop(minutes=1)
    async def boarding_reminder_loop(self):
        print("[ReminderCog] boarding_reminder_loop tick")

        await run_boarding_reminder_scan(
            self.bot,
            self.bot.boarding_reminded
        )

    @boarding_reminder_loop.before_loop
    async def before_boarding_reminder_loop(self):
        await self.bot.wait_until_ready()

    @tasks.loop(minutes=1)
    async def s6_reminder_loop(self):
        print("[ReminderCog] s6_reminder_loop tick")

        await run_s6_reminder_scan(
            self.bot,
            self.bot.s6_reminded
        )

    @s6_reminder_loop.before_loop
    async def before_s6_reminder_loop(self):
        await self.bot.wait_until_ready()

    @tasks.loop(minutes=1)
    async def daily_recruit_loop(self):
        print("[ReminderCog] daily_recruit_loop tick")

        now = datetime.now(TAIPEI_TZ)
 
        if now.hour != 0 or now.minute != 0:
            return

        today = normalize_date(
            f"{now.month}/{now.day}"
        )

        if has_sent_daily_recruit(today):
            print(
                f"[ReminderCog] daily recruit already sent: {today}"
            )
            return

        message = build_today_daily_recruit_message(today)

        if message is None:
            print(
                f"[ReminderCog] no recruit slots: {today}"
            )
            mark_daily_recruit_sent(today)
            return

        channel = self.bot.get_channel(RECRUIT_CHANNEL_ID)

        if channel is None:
            print("[ReminderCog] recruit channel not found")
            return

        await channel.send(message)

        mark_daily_recruit_sent(today)

        print(
            f"[ReminderCog] daily recruit sent: {today}"
        )


    @daily_recruit_loop.before_loop
    async def before_daily_recruit_loop(self):
        await self.bot.wait_until_ready()

async def setup(bot: commands.Bot):
    await bot.add_cog(ReminderCog(bot))