import discord
from discord import app_commands
from discord.ext import commands

from config import (
    CURRENT_PERIOD,
    PUSHER_ROLE_ID,
    RUNNER_ROLE_ID,
    SCHEDULE_UPDATE_CHANNEL_ID,
    RUNNER_CANCEL_NOTICE_CHANNEL_ID
)

from core.schedule_service import get_row_by_time

from core.storage import (
    save_schedule,
    get_schedule
)

from core.schedule_utils import (
    normalize_car,
    normalize_date
)

from core.schedule_edit_service import (
    cancel_user_schedule
)

from core.discord_message_service import (
    send_log_to_channel,
    update_schedule_message
)

from core.discord_permission_utils import (
    has_role
)

from core.reminder_scan_service import (
    send_s6_reminder_for_row
)

class CancelCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="推車砍班",
        description="取消自己指定時段或整天的推車報班"
    )
    async def cancel_pusher_schedule(
        self,
        interaction: discord.Interaction,
        car: str,
        date: str,
        time: str = "",
        all_day: bool = False
    ):
        if not has_role(interaction, PUSHER_ROLE_ID):
            await interaction.response.send_message(
                "❌ 你沒有推車手砍班權限。",
                ephemeral=True
            )
            return

        period = CURRENT_PERIOD
        car = normalize_car(car)
        date = normalize_date(date)

        schedule = get_schedule(period, car, date)

        if schedule is None:
            await interaction.response.send_message(
                f"❌ 找不到 `{car} {date}` 的排班。",
                ephemeral=True
            )
            return

        result = cancel_user_schedule(
            schedule,
            interaction.user.id,
            "pusher",
            time,
            all_day
        )

        if not result["ok"]:
            if result["error"] == "missing_time":
                await interaction.response.send_message(
                    "❌ 請輸入要砍班的時間，或將 `all_day` 設為 `True`。",
                    ephemeral=True
                )
                return

            if result["error"] == "time_not_found":
                await interaction.response.send_message(
                    f"❌ 找不到時間 `{result['target_time']}`。\n"
                    f"請使用格式例如：`21-22`、`21-24` 或 `2100-2200`",
                    ephemeral=True
                )
                return

        removed_records = result["removed_records"]
        all_promoted_slots = result["promoted_slots"]

        if not removed_records:
            await interaction.response.send_message(
                f"⚠️ 沒有找到你在 `{car} {date}` 的推車報班資料。",
                ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=False)

        for promoted_slot in all_promoted_slots:
            if not isinstance(promoted_slot, dict):
                continue

            if promoted_slot.get("type") != "pusher":
                continue

            user_id = promoted_slot.get("user_id")

            try:
                user = await self.bot.fetch_user(int(user_id))

                await user.send(
                    f"🎉 你已由候補轉為正式班！\n\n"
                    f"車輛：{car}\n"
                    f"日期：{date}\n"
                    f"名稱：{promoted_slot.get('display')}\n\n"
                    f"請記得準時上車。"
                )

            except Exception as e:
                print("遞補轉正通知失敗：", user_id, e)

        save_schedule(schedule)

        await update_schedule_message(
            self.bot,
            schedule
        )

        removed_times = [
            record.split("：")[0]
            for record in removed_records
        ]

        removed_names = [
            record.split("：")[1]
            for record in removed_records
        ]

        display_name = removed_names[0]

        public_text = (
            f"推車砍班成功 {car} {date} "
            f"{time}"
        )

        update_text = f"✅ 班表已更新 `{car} {date}`\n"

        update_text += (
            f"推車砍班：`{removed_times[0]}` ~ "
            f"`{removed_times[-1]}`：`{display_name}`"
        )

        await interaction.followup.send(public_text)

        await send_log_to_channel(
            self.bot,
            SCHEDULE_UPDATE_CHANNEL_ID,
            update_text
        )

    @app_commands.command(
        name="跑者砍班",
        description="取消自己指定時段或整天的跑者報班"
    )
    async def cancel_runner_schedule(
        self,
        interaction: discord.Interaction,
        car: str,
        date: str,
        time: str = "",
        all_day: bool = False
    ):

        if not has_role(interaction, RUNNER_ROLE_ID):
            await interaction.response.send_message(
                "❌ 你沒有跑者砍班權限。",
                ephemeral=True
            )
            return

        period = CURRENT_PERIOD
        car = normalize_car(car)
        date = normalize_date(date)

        schedule = get_schedule(period, car, date)

        if schedule is None:
            await interaction.response.send_message(
                f"❌ 找不到 `{car} {date}` 的排班。",
                ephemeral=True
            )
            return

        result = cancel_user_schedule(
            schedule,
            interaction.user.id,
            "runner",
            time,
            all_day
        )

        if not result["ok"]:
            if result["error"] == "missing_time":
                await interaction.response.send_message(
                    "❌ 請輸入要砍班的時間，或將 `all_day` 設為 `True`。",
                    ephemeral=True
                )
                return

            if result["error"] == "time_not_found":
                await interaction.response.send_message(
                    f"❌ 找不到時間 `{result['target_time']}`。\n"
                    f"請使用格式例如：`21-22`、`21-24` 或 `2100-2200`",
                    ephemeral=True
                )
                return

        removed_records = result["removed_records"]
        cleared_slots = result["cleared_slots"]
        runner_removed_rows = result["runner_removed_rows"]

        if not removed_records:
            await interaction.response.send_message(
                f"⚠️ 沒有找到你在 `{car} {date}` 的跑者報班資料。",
                ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=False)

        
        if cleared_slots:
            notice_text = (
                "⚠️ **跑者砍班通知**\n\n"
                f"車輛：{car}\n"
                f"日期：{date}\n\n"
            )

            for slot in cleared_slots:
                role = "S6" if slot.get("type") == "s6" else "推車手"
                notice_text += (
                f"• {slot.get('display')} ({role})\n"
                f"  時間：{slot.get('time')}\n"
            )

            await send_log_to_channel(
                self.bot,
                RUNNER_CANCEL_NOTICE_CHANNEL_ID,
                notice_text
             )

        save_schedule(schedule)

        for runner_removed_row in runner_removed_rows:
            target_time = runner_removed_row.get("time")

            if not target_time:
                continue

            target_row = get_row_by_time(
                schedule,
                target_time
            )

            if target_row is None:
                continue

            await send_s6_reminder_for_row(
                self.bot,
                self.bot.s6_reminded,
                schedule,
                target_row
            )

        await update_schedule_message(
            self.bot,
            schedule
        )

        removed_times = [
            record.split("：")[0]
            for record in removed_records
        ]

        removed_names = [
            record.split("：")[1]
            for record in removed_records
        ]

        display_name = removed_names[0]

        public_text = (
            f"跑者砍班成功 {car} {date} "
            f"{time}"
        )

        update_text = f"✅ 班表已更新 `{car} {date}`\n"

        update_text += (
            f"跑者砍班：`{removed_times[0]}` ~ "
            f"`{removed_times[-1]}`：`{display_name}`"
        )

        await interaction.followup.send(public_text)

        await send_log_to_channel(
            self.bot,
            SCHEDULE_UPDATE_CHANNEL_ID,
            update_text
        )

async def setup(bot: commands.Bot):
    await bot.add_cog(CancelCog(bot))