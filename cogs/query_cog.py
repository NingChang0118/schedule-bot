import discord
from discord import app_commands
from discord.ext import commands

from config import (
    SCHEDULE_ADMIN_ROLE_ID
)

from core.settings_storage import (
    get_current_period
)

from core.storage import (
    get_schedule
)

from core.schedule_utils import (
    normalize_car,
    normalize_date
)

from core.stats_service import (
    get_user_hours,
    build_current_hours_text,
    build_history_hours_text,
    build_period_total_hours_text
)

from core.my_schedule_service import (
    get_user_schedule_records,
    build_my_schedule_text
)

from core.backup_service import (
    build_backup_list_text,
    get_backup_list
)

from core.pusher_storage import (
    get_pusher
)

from core.runner_storage import (
    get_runner
)

from core.s6_pusher_storage import (
    get_s6_pusher
)

from core.discord_message_service import (
    send_schedule_image_response
)

class QueryCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def is_schedule_admin(
        self,
        interaction: discord.Interaction
    ) -> bool:
        if not hasattr(interaction.user, "roles"):
            return False

        return any(
            role.id == SCHEDULE_ADMIN_ROLE_ID
            for role in interaction.user.roles
        )

    @app_commands.command(
        name="我的班表",
        description="查看自己目前期數的所有報班"
    )
    async def my_schedule(
        self,
        interaction: discord.Interaction
    ):
        current_period = get_current_period()

        records = get_user_schedule_records(
            interaction.user.id,
            current_period
        )

        text = build_my_schedule_text(records)

        await interaction.response.send_message(
            text,
            ephemeral=True
        )

    @app_commands.command(
        name="候補查詢",
        description="查看指定時段的候補順位"
    )
    async def backup_list(
        self,
        interaction: discord.Interaction,
        car: str,
        date: str,
        time: str
    ):
        await interaction.response.defer(
            ephemeral=True
        )

        period = get_current_period()
        car = normalize_car(car)
        date = normalize_date(date)

        schedule = get_schedule(
            period,
            car,
            date
        )

        if schedule is None:
            await interaction.followup.send(
                f"❌ 找不到 `{car} {date}` 的排班。",
                ephemeral=True
            )
            return

        result = get_backup_list(
            schedule,
            time
        )

        if not result["ok"]:
            await interaction.followup.send(
                f"❌ 找不到時間 `{result['target_time']}`。",
                ephemeral=True
            )
            return

        target_time = result["target_time"]
        backups = result["backups"]

        if not backups:
            await interaction.followup.send(
                f"📋 `{car} {date} {target_time}` 目前沒有候補。",
                ephemeral=True
            )
            return

        text = build_backup_list_text(
            car,
            date,
            target_time,
            backups
        )

        await interaction.followup.send(
            text,
            ephemeral=True
        )

    @app_commands.command(
        name="查詢當期時數",
        description="查看自己目前期數的報班時數"
    )
    async def current_hours(
        self,
        interaction: discord.Interaction
    ):
        current_period = get_current_period()

        stats = get_user_hours(
            interaction.user.id,
            current_period
        )

        text = build_current_hours_text(
            current_period,
            stats
        )

        await interaction.response.send_message(
            text,
            ephemeral=True
        )

    @app_commands.command(
        name="查詢歷史時數",
        description="查看自己所有期數的累積報班時數"
    )
    async def history_hours(
        self,
        interaction: discord.Interaction
    ):
        stats = get_user_hours(
            interaction.user.id
        )

        text = build_history_hours_text(
            stats
        )

        await interaction.response.send_message(
            text,
            ephemeral=True
        )

    @app_commands.command(
        name="當期總時數",
        description="查看當期所有成員的累積時數"
    )
    async def period_total_hours(
        self,
        interaction: discord.Interaction
    ):
        if not self.is_schedule_admin(interaction):
            await interaction.response.send_message(
                "❌ 你沒有查看當期總時數的權限。",
                ephemeral=True
            )
            return

        current_period = get_current_period()

        text = build_period_total_hours_text(
            current_period
        )

        await interaction.response.send_message(
            text,
            ephemeral=True
        )

    @app_commands.command(
        name="查詢推車登記資料",
        description="查看自己的推車手登記資料"
    )
    async def query_pusher_profile(
        self,
        interaction: discord.Interaction
    ):
        pusher = get_pusher(interaction.user.id)

        if pusher is None:
            await interaction.response.send_message(
                "❌ 你目前沒有推車手登記資料。",
                ephemeral=True
            )
            return

        name = pusher.get("name", "未填寫")
        rate = pusher.get("rate", "未填寫")
        power = pusher.get("power", "未填寫")

        text = (
            "📋 推車手登記資料\n"
            f"名稱：{name}\n"
            f"倍率：{rate}\n"
            f"綜合力：{power}"
        )

        await interaction.response.send_message(
            text,
            ephemeral=True
        )

    @app_commands.command(
        name="查詢跑者登記資料",
        description="查看自己的跑者登記資料"
    )
    async def query_runner_profile(
        self,
        interaction: discord.Interaction
    ):
        runner = get_runner(interaction.user.id)

        if runner is None:
            await interaction.response.send_message(
                "❌ 你目前沒有跑者登記資料。",
                ephemeral=True
            )
            return

        name = runner.get("name", "未填寫")
        power = runner.get("power", "未填寫")

        text = (
            "📋 跑者登記資料\n"
            f"名稱：{name}\n"
            f"綜合力：{power}"
        )

        await interaction.response.send_message(
            text,
            ephemeral=True
        )

    @app_commands.command(
        name="查詢s6登記資料",
        description="查看自己的 S6 推車手登記資料"
    )
    async def query_s6_pusher_profile(
        self,
        interaction: discord.Interaction
    ):
        s6_pusher = get_s6_pusher(interaction.user.id)

        if s6_pusher is None:
            await interaction.response.send_message(
                "❌ 你目前沒有 S6 推車手登記資料。",
                ephemeral=True
            )
            return

        rate = s6_pusher.get("rate", "未填寫")
        power = s6_pusher.get("power", "未填寫")

        text = (
            "📋 S6 推車手登記資料\n"
            f"倍率：{rate}\n"
            f"綜合力：{power}"
        )

        await interaction.response.send_message(
            text,
            ephemeral=True
        )

    @app_commands.command(
        name="查看班表",
        description="查看指定的班表"
    )
    async def view_schedule(
        self,
        interaction: discord.Interaction,
        car: str,
        date: str
    ):
        period = get_current_period()
        car = normalize_car(car)
        date = normalize_date(date)

        schedule = get_schedule(period, car, date)

        if schedule is None:
            await interaction.response.send_message(
                f"❌ 找不到 `{car} {date}` 的班表。",
                ephemeral=True
            )
            return

        await send_schedule_image_response(
            interaction,
            car,
            date,
            schedule
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(QueryCog(bot))