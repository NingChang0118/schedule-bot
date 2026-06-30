import discord
from discord import app_commands
from discord.ext import commands

from config import (
    SCHEDULE_ADMIN_ROLE_ID,
    RECRUIT_ROLE_ID
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

from core.recruit_service import (
    build_recruit_message,
    get_recruit_rows
)


class RecruitCog(commands.Cog):
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
        name="缺額招募",
        description="發送指定時段的缺額招募"
    )
    async def recruit_missing(
        self,
        interaction: discord.Interaction,
        car: str,
        date: str
    ):
        await interaction.response.defer(
            ephemeral=True
        )

        if not self.is_schedule_admin(interaction):
            await interaction.followup.send(
                "❌ 你沒有使用此指令的權限。",
                ephemeral=True
            )
            return

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
                f"❌ 找不到 `{car} {date}` 的班表。",
                ephemeral=True
            )
            return

        recruit_rows = get_recruit_rows(
            schedule
        )

        if not recruit_rows:
            await interaction.followup.send(
                "✅ 目前沒有需要招募的時段。",
                ephemeral=True
            )
            return

        recruit_message = build_recruit_message(
            role_id=RECRUIT_ROLE_ID,
            car=car,
            date=date,
            recruit_rows=recruit_rows
        )

        await interaction.channel.send(
            recruit_message
        )

        await interaction.followup.send(
            "✅ 已發送缺額招募。",
            ephemeral=True
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(RecruitCog(bot))