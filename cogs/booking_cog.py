import discord
from discord import app_commands
from discord.ext import commands

from config import (
    PUSHER_ROLE_ID,
    RUNNER_ROLE_ID,
    SCHEDULE_UPDATE_CHANNEL_ID
)

from core.storage import (
    save_schedule,
)

from core.pusher_storage import (
    get_pusher
)

from core.runner_storage import (
    get_runner
)

from core.slot_utils import (
    make_slot,
    get_slot_display
)

from core.schedule_utils import (
    normalize_car,
    normalize_date
)

from core.schedule_edit_service import (
    fill_pusher_schedule,
    fill_runner_schedule
)

from core.discord_message_service import (
    send_log_to_channel,
    update_schedule_message
)

from core.discord_permission_utils import (
    has_role
)

from core.auto_schedule_service import (
    ensure_schedule_for_booking
)

class BookingCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="推車報班",
        description="填入指定時間的推車手"
    )
    async def fill_pusher(
        self,
        interaction: discord.Interaction,
        car: str,
        date: str,
        time: str,
        double_rate: float | None = None
    ):
        if not has_role(interaction, PUSHER_ROLE_ID):
            await interaction.response.send_message(
                "❌ 你沒有推車手報班權限。",
                ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=False)

        car = normalize_car(car)
        date = normalize_date(date)

        pusher_data = get_pusher(interaction.user.id)

        if pusher_data is None:
            await interaction.followup.send(
                "❌ 你還沒有登記推車資料。\n"
                "請先使用 `/登記推車資料` 登記名稱與倍率。",
                ephemeral=True
            )
            return

        slot_data = make_slot(
            user_id=interaction.user.id,
            name=pusher_data["name"],
            role_type="pusher",
            rate=pusher_data["rate"],
            power=pusher_data["power"]
        )

        double_slot_data = None

        if double_rate is not None:
            double_slot_data = make_slot(
                user_id=interaction.user.id,
                name=pusher_data["name"],
                role_type="pusher",
                rate=double_rate,
                power=pusher_data["power"],
                is_double=True
            )

        display_name = get_slot_display(slot_data)

        schedule, _ = await ensure_schedule_for_booking(
            self.bot,
            interaction,
            car,
            date
        )

        if schedule is None:
            await interaction.followup.send(
                f"❌ 找不到 `{car} {date}` 的排班。",
                ephemeral=True
            )
            return

        result = fill_pusher_schedule(
            schedule,
            interaction.user.id,
            slot_data,
            time,
            double_slot_data
        )

        if not result["ok"]:
            if result["error"] == "time_not_found":
                await interaction.followup.send(
                    f"❌ 找不到時間 `{result['target_time']}`。\n"
                    f"請使用格式例如：`21-22`、`21-24` 或 `2100-2200`",
                    ephemeral=True
                )
                return

            if result["error"] == "already_joined":
                await interaction.followup.send(
                    f"❌ `{result['target_time']}` 你已經報過班了。",
                    ephemeral=True
                )
                return

        joined_times = result["joined_times"]
        backup_times = result["backup_times"]

        save_schedule(schedule)

        await update_schedule_message(
            self.bot,
            schedule
        )

        public_text = (
            f"報班成功 {car} {date} "
            f"{time}"
        )

        update_text = f"✅ 班表已更新 `{car} {date}`\n"

        if joined_times:
            update_text += (
                f"正式報班：`{joined_times[0]}` ~ "
                f"`{joined_times[-1]}`：`{display_name}`\n"
            )

        if backup_times:
            update_text += (
                f"候補排隊：`{backup_times[0]}` ~ "
                f"`{backup_times[-1]}`：`{display_name}`"
            )

        await interaction.followup.send(
            public_text
        )

        await send_log_to_channel(
            self.bot,
            SCHEDULE_UPDATE_CHANNEL_ID,
            update_text
        )

    @app_commands.command(
        name="跑者報班",
        description="填入指定時間的跑者"
    )
    async def fill_runner(
        self,
        interaction: discord.Interaction,
        car: str,
        date: str,
        time: str,
        car_type: str | None = None
    ):
        if not has_role(interaction, RUNNER_ROLE_ID):
            await interaction.response.send_message(
                "❌ 你沒有跑者報班權限。",
                ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=False)

        car = normalize_car(car)
        date = normalize_date(date)

        runner_data = get_runner(
            interaction.user.id
        )

        if runner_data is None:
            await interaction.followup.send(
                "❌ 你還沒有登記跑者資料。\n"
                "請先使用 `/登記跑者資料` 登記名稱、倍率與綜合。",
                ephemeral=True
            )
            return
        
        slot_data = make_slot(
            user_id=interaction.user.id,
            name=runner_data["name"],
            role_type="runner",
            rate=runner_data.get("rate", 0),
            power=runner_data["power"]
        )

        display_name = get_slot_display(slot_data)

        schedule, _ = await ensure_schedule_for_booking(
            self.bot,
            interaction,
            car,
            date
        )

        if schedule is None:
            await interaction.followup.send(
                f"❌ 找不到 `{car} {date}` 的排班。",
                ephemeral=True
            )
            return

        result = fill_runner_schedule(
            schedule,
            interaction.user.id,
            slot_data,
            time,
            car_type
        )

        if not result["ok"]:
            if result["error"] == "time_not_found":
                await interaction.followup.send(
                    f"❌ 找不到時間 `{result['target_time']}`。\n"
                    f"請使用格式例如：`21-22`、`21-24` 或 `2100-2200`",
                    ephemeral=True
                )
                return

            if result["error"] == "already_joined":
                await interaction.followup.send(
                    f"❌ `{result['target_time']}` 你已經報過跑者了。",
                    ephemeral=True
                )
                return
            
            if result["error"] == "car_type_locked":
                await interaction.followup.send(
                    f"❌ `{result['target_time']}` 車種已鎖定為 `{result['locked_car_type']}`，請選擇相同車種。",
                    ephemeral=True
                )
                return

        joined_times = result["joined_times"]

        save_schedule(schedule)

        await update_schedule_message(
            self.bot,
            schedule
        )

        public_text = (
            f"跑者報班成功 {car} {date} "
            f"{time}"
        )

        update_text = f"✅ 班表已更新 `{car} {date}`\n"

        if joined_times:
            update_text += (
                f"跑者報班：`{joined_times[0]}` ~ "
                f"`{joined_times[-1]}`：`{display_name}`"
            )
        else:
            update_text += (
                f"跑者報班：`{time}`：`{display_name}`"
            )

        await interaction.followup.send(
            public_text
        )

        await send_log_to_channel(
            self.bot,
            SCHEDULE_UPDATE_CHANNEL_ID,
            update_text
        )

async def setup(bot: commands.Bot):
    await bot.add_cog(BookingCog(bot))