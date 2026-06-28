import discord
from discord import app_commands
from discord.ext import commands

from core.pusher_storage import (
    save_pusher,
    get_pusher,
    update_pusher_rate,
    update_pusher_power
)

from core.runner_storage import (
    save_runner,
    get_runner,
    update_runner_rate,
    update_runner_power
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
        await interaction.response.defer()

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
        )


    @app_commands.command(
        name="登記跑者資料",
        description="登記自己的跑者資料"
    )
    async def register_runner(
        self,
        interaction: discord.Interaction,
        名稱: str,
        倍率: str,
        綜合: str
    ):
        await interaction.response.defer()

        save_runner(
            interaction.user.id,
            名稱,
            倍率,
            綜合
        )

        updated_schedule_count, updated_slot_count = (
            await sync_profile_to_all_current_schedules(
                self.bot,
                interaction.user.id,
                "runner",
                名稱,
                倍率,
                綜合
            )
        )

        await interaction.followup.send(
            f"✅ 已登記跑者資料\n"
            f"名稱：{名稱}\n"
            f"倍率：{倍率}\n"
            f"綜合：{綜合}\n"
            f"已同步班表：{updated_schedule_count} 張\n"
            f"已更新報班資料：{updated_slot_count} 筆",
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
        await interaction.response.defer()

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
        )


    @app_commands.command(
        name="更新跑者倍率",
        description="更新自己的跑者倍率"
    )
    async def update_runner_rate_command(
        self,
        interaction: discord.Interaction,
        倍率: str
    ):
        await interaction.response.defer(
            ephemeral=True
        )

        runner_data = get_runner(
            interaction.user.id
        )

        if runner_data is None:
            await interaction.followup.send(
                "❌ 你還沒有登記跑者資料。\n"
                "請先使用 `/登記跑者資料` 登記。",
                ephemeral=True
            )
            return

        update_runner_rate(
            interaction.user.id,
            倍率
        )

        updated_schedule_count, updated_slot_count = (
            await sync_profile_to_all_current_schedules(
                self.bot,
                interaction.user.id,
                "runner",
                runner_data["name"],
                倍率,
                runner_data["power"]
            )
        )

        await interaction.followup.send(
            f"✅ 已更新跑者倍率\n"
            f"名稱：{runner_data['name']}\n"
            f"倍率：{倍率}\n"
            f"綜合：{runner_data['power']}\n"
            f"已同步班表：{updated_schedule_count} 張\n"
            f"已更新報班資料：{updated_slot_count} 筆",
            ephemeral=True
        )


    @app_commands.command(
        name="更新跑者綜合",
        description="更新自己的跑者綜合"
    )
    async def update_runner_power_command(
        self,
        interaction: discord.Interaction,
        綜合: str
    ):
        await interaction.response.defer(
            ephemeral=True
        )

        runner_data = get_runner(
            interaction.user.id
        )

        if runner_data is None:
            await interaction.followup.send(
                "❌ 你還沒有登記跑者資料。\n"
                "請先使用 `/登記跑者資料` 登記。",
                ephemeral=True
            )
            return

        update_runner_power(
            interaction.user.id,
            綜合
        )

        updated_schedule_count, updated_slot_count = (
            await sync_profile_to_all_current_schedules(
                self.bot,
                interaction.user.id,
                "runner",
                runner_data["name"],
                runner_data["rate"],
                綜合
            )
        )

        await interaction.followup.send(
            f"✅ 已更新跑者綜合\n"
            f"名稱：{runner_data['name']}\n"
            f"倍率：{runner_data['rate']}\n"
            f"綜合：{綜合}\n"
            f"已同步班表：{updated_schedule_count} 張\n"
            f"已更新報班資料：{updated_slot_count} 筆",
            ephemeral=True
        )


    @app_commands.command(
        name="更新推車倍率",
        description="更新自己的推車倍率"
    )
    async def update_pusher_rate_command(
        self,
        interaction: discord.Interaction,
        倍率: str
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
                "請先使用 `/登記推車資料` 登記。",
                ephemeral=True
            )
            return

        update_pusher_rate(
            interaction.user.id,
            倍率
        )

        updated_schedule_count, updated_slot_count = (
            await sync_profile_to_all_current_schedules(
                self.bot,
                interaction.user.id,
                "pusher",
                pusher_data["name"],
                倍率,
                pusher_data["power"]
            )
        )

        await interaction.followup.send(
            f"✅ 已更新推車倍率\n"
            f"名稱：{pusher_data['name']}\n"
            f"倍率：{倍率}\n"
            f"綜合：{pusher_data['power']}\n"
            f"已同步班表：{updated_schedule_count} 張\n"
            f"已更新報班資料：{updated_slot_count} 筆",
            ephemeral=True
        )


    @app_commands.command(
        name="更新推車綜合",
        description="更新自己的推車綜合"
    )
    async def update_pusher_power_command(
        self,
        interaction: discord.Interaction,
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
                "請先使用 `/登記推車資料` 登記。",
                ephemeral=True
            )
            return

        update_pusher_power(
            interaction.user.id,
            綜合
        )

        updated_schedule_count, updated_slot_count = (
            await sync_profile_to_all_current_schedules(
                self.bot,
                interaction.user.id,
                "pusher",
                pusher_data["name"],
                pusher_data["rate"],
                綜合
            )
        )

        await interaction.followup.send(
            f"✅ 已更新推車綜合\n"
            f"名稱：{pusher_data['name']}\n"
            f"倍率：{pusher_data['rate']}\n"
            f"綜合：{綜合}\n"
            f"已同步班表：{updated_schedule_count} 張\n"
            f"已更新報班資料：{updated_slot_count} 筆",
            ephemeral=True
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(ProfileCog(bot))