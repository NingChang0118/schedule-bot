import discord
from discord import app_commands
from discord.ext import commands

from core.pusher_storage import (
    save_pusher,
    get_pusher
)

from core.runner_storage import (
    save_runner
)

from core.s6_pusher_storage import (
    save_s6_pusher
)

from core.profile_sync_service import (
    sync_profile_to_all_current_schedules
)


class ProfileCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="登記推車資料",
        description="登記自己的倍率資料"
    )
    async def register_pusher(
        self,
        interaction: discord.Interaction,
        名稱: str,
        倍率: str,
        綜合: str
    ):
        await interaction.response.defer(
            ephemeral=True
        )

        save_pusher(
            interaction.user.id,
            名稱,
            倍率,
            綜合
        )

        updated_schedule_count, updated_slot_count = (
            await sync_profile_to_all_current_schedules(
                self.bot,
                interaction.user.id,
                "pusher",
                名稱,
                倍率,
                綜合
            )
        )

        await interaction.followup.send(
            f"✅ 已登記推車手資料\n"
            f"名稱：{名稱}\n"
            f"倍率：{倍率}\n"
            f"綜合：{綜合}\n"
            f"已同步班表：{updated_schedule_count} 張\n"
            f"已更新報班資料：{updated_slot_count} 筆",
            ephemeral=True
        )

    @app_commands.command(
        name="登記跑者資料",
        description="登記自己的跑者資料"
    )
    async def register_runner(
        self,
        interaction: discord.Interaction,
        名稱: str,
        綜合: str
    ):
        await interaction.response.defer(
            ephemeral=True
        )

        save_runner(
            interaction.user.id,
            名稱,
            綜合
        )

        updated_schedule_count, updated_slot_count = (
            await sync_profile_to_all_current_schedules(
                self.bot,
                interaction.user.id,
                "runner",
                名稱,
                None,
                綜合
            )
        )

        await interaction.followup.send(
            f"✅ 已登記跑者資料\n"
            f"名稱：{名稱}\n"
            f"綜合：{綜合}\n"
            f"已同步班表：{updated_schedule_count} 張\n"
            f"已更新報班資料：{updated_slot_count} 筆",
            ephemeral=True
        )

    @app_commands.command(
        name="登記s6資料",
        description="登記自己的S6倍率與綜合"
    )
    async def register_s6_pusher(
        self,
        interaction: discord.Interaction,
        倍率: str,
        綜合: str
    ):
        await interaction.response.defer(
            ephemeral=True
        )

        pusher_data = get_pusher(
            interaction.user.id
        )

        if pusher_data is None:
            await interaction.followup.send(
                "❌ 你還沒有登記推車資料。\n"
                "請先使用 `/登記推車資料` 登記名稱與倍率。",
                ephemeral=True
            )
            return

        save_s6_pusher(
            interaction.user.id,
            倍率,
            綜合
        )

        await interaction.followup.send(
            f"✅ 已登記S6資料\n"
            f"名稱：{pusher_data['name']}\n"
            f"倍率：{倍率}\n"
            f"綜合：{綜合}",
            ephemeral=True
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(ProfileCog(bot))