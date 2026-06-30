import discord
from discord.ext import commands

from config import (
    S6_REPORT_CHANNEL_ID
)

from core.settings_storage import (
    get_current_period
)

from core.storage import (
    get_schedule
)

from core.schedule_service import (
    get_row_by_time
)

from core.schedule_utils import (
    normalize_car,
    normalize_date,
    expand_time_range
)

from core.pusher_storage import (
    get_pusher,
    get_pusher_by_name
)

from core.slot_utils import (
    is_same_user
)

from core.stats_service import (
    is_full_car,
    is_finished_slot
)

from core.s6_report_storage import (
    add_s6_report,
    get_s6_reports
)


class S6ReportCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def parse_report_content(self, content: str):
        parts = content.strip().split()

        if len(parts) < 4:
            return None

        return {
            "date": parts[0],
            "time": parts[1],
            "car": parts[2],
            "name": parts[3]
        }

    def has_pusher_in_row(self, row, user_id):
        slots = [
            row.slot_1,
            row.slot_2,
            row.slot_3,
            row.slot_4,
            row.slot_5
        ]

        slots.extend(row.backup)

        for slot in slots:
            if not isinstance(slot, dict):
                continue

            if slot.get("type") != "pusher":
                continue

            if is_same_user(slot, user_id):
                return True

        return False

    def already_reported(self, user_id, car, date, time):
        current_period = get_current_period()
        
        reports = get_s6_reports(
            period=current_period,
            user_id=user_id
        )

        for report in reports:
            if report.get("car") != car:
                continue

            if report.get("date") != date:
                continue

            if report.get("time") != time:
                continue

            return True

        return False

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        if message.channel.id != S6_REPORT_CHANNEL_ID:
            return

        report_data = self.parse_report_content(
            message.content
        )

        if report_data is None:
            await message.reply(
                "❌ S6 回報格式錯誤。\n\n"
                "請使用：`6/29 22-23 一車 璃音 搶一小`"
            )
            return

        car = normalize_car(report_data["car"])
        date = normalize_date(report_data["date"])
        times = expand_time_range(
            report_data["time"]
        )

        time = times[0]
        name = report_data["name"]

        pusher_data = get_pusher_by_name(name)

        if pusher_data is None:
            await message.reply(
                f"❌ 找不到推車資料：`{name}`\n"
                "請確認名稱是否與登記推車資料一致。"
            )
            return

        current_period = get_current_period()

        schedule = get_schedule(
            current_period,
            car,
            date
        )

        if schedule is None:
            await message.reply(
                f"❌ 找不到班表：`{car} {date}`"
            )
            return

        row = get_row_by_time(
            schedule,
            time
        )

        if row is None:
            await message.reply(
                f"❌ 找不到時間：`{time}`"
            )
            return

        if not is_full_car(row):
            await message.reply(
                f"❌ `{car} {date} {time}` 尚未成車，不能回報 S6。"
            )
            return

        if not is_finished_slot(schedule, row):
            await message.reply(
                f"❌ `{car} {date} {time}` 尚未結束，不能提前回報 S6。"
            )
            return

        if not self.has_pusher_in_row(
            row,
            pusher_data["user_id"]
        ):
            await message.reply(
                f"❌ 找不到 `{name}` 在 `{car} {date} {time}` 的推車報班資料。"
            )
            return

        if self.already_reported(
            pusher_data["user_id"],
            car,
            date,
            time
        ):
            await message.reply(
                f"⚠️ `{name}` 已經回報過 `{car} {date} {time}` 的 S6。"
            )
            return

        reporter_data = get_pusher(
            message.author.id
        )

        reported_by_name = message.author.display_name

        if reporter_data is not None:
            reported_by_name = reporter_data.get(
                "name",
                reported_by_name
            )

        add_s6_report(
            user_id=pusher_data["user_id"],
            name=pusher_data["name"],
            car=car,
            date=date,
            time=time,
            reported_by_user_id=message.author.id,
            reported_by_name=reported_by_name
        )

        await message.add_reaction("✅")


async def setup(bot: commands.Bot):
    await bot.add_cog(S6ReportCog(bot))