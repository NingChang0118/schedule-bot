import discord
from discord import app_commands
from discord.ext import commands, tasks

from core.models import create_empty_schedule
from core.storage import save_schedule, get_schedule, delete_schedule, load_all, dict_to_schedule, save_all
from core.renderer import render_schedule
from config import (
    SCHEDULE_ADMIN_ROLE_ID,
    CURRENT_PERIOD,
)

from core.schedule_utils import (
    normalize_car,
    normalize_date,
)

from core.schedule_edit_service import (
    fill_runner_schedule,
    fill_pusher_schedule,
    fill_s6_schedule
)

class AdminCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def update_schedule_message(self, schedule):
        image_path = render_schedule(schedule)

        channel = self.bot.get_channel(schedule.channel_id)

        if channel is None:
            channel = await self.bot.fetch_channel(schedule.channel_id)

        message = await channel.fetch_message(schedule.message_id)

        await message.edit(
            attachments=[
                discord.File(str(image_path), filename="schedule.png")
            ]
        )

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

    def rebuild_schedule_from_current_data(self, schedule):
        new_schedule = create_empty_schedule(
            schedule.period,
            schedule.car,
            schedule.date
        )

        new_schedule.channel_id = schedule.channel_id
        new_schedule.message_id = schedule.message_id

        for row in schedule.rows:
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

                slot_type = slot.get("type")
                user_id = slot.get("user_id")

                if user_id is None:
                    continue

                if slot_type == "runner":
                    fill_runner_schedule(
                        new_schedule,
                        user_id,
                        slot,
                        row.time,
                        row.car_type
                    )

                elif slot_type == "pusher":
                    fill_pusher_schedule(
                        new_schedule,
                        user_id,
                        slot,
                        row.time
                    )

            if isinstance(row.s6, dict):
                user_id = row.s6.get("user_id")

                if user_id is not None:
                    fill_s6_schedule(
                        new_schedule,
                        user_id,
                        row.s6,
                        row.time
                    )

        return new_schedule

    @app_commands.command(
        name="重建班表",
        description="重新產生班表圖片"
    )
    async def rebuild_schedule(
        self,
        interaction: discord.Interaction,
        car: str,
        date: str
    ):
        if not self.is_schedule_admin(interaction):
            await interaction.response.send_message(
                "❌ 你沒有重建班表的權限。",
                ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        period = CURRENT_PERIOD
        car = normalize_car(car)
        date = normalize_date(date)

        schedule = get_schedule(period, car, date)

        if schedule is None:
            await interaction.followup.send(
                f"❌ 找不到 `{car} {date}` 的班表。",
                ephemeral=True
            )
            return

        await self.update_schedule_message(schedule)

        await interaction.followup.send(
            f"✅ 已重建 `{car} {date}` 班表。",
            ephemeral=True
        )

    @app_commands.command(
        name="重建班表資料",
        description="依照目前報班資料重新計算並重建班表"
    )
    async def rebuild_schedule_data_command(
        self,
        interaction: discord.Interaction,
        car: str,
        date: str
    ):
        if not self.is_schedule_admin(interaction):
            await interaction.response.send_message(
                "❌ 你沒有重建班表資料的權限。",
                ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        period = CURRENT_PERIOD
        car = normalize_car(car)
        date = normalize_date(date)

        schedule = get_schedule(period, car, date)

        if schedule is None:
            await interaction.followup.send(
                f"❌ 找不到 `{car} {date}` 的班表。",
                ephemeral=True
            )
            return

        new_schedule = self.rebuild_schedule_from_current_data(
            schedule
        )

        save_schedule(
            new_schedule
        )

        await self.update_schedule_message(
            new_schedule
        )

        await interaction.followup.send(
            f"✅ 已依照目前報班資料重新建立 `{car} {date}` 班表。",
            ephemeral=True
        )

    @app_commands.command(
        name="建立班表",
        description="建立一張新的 24 小時排班表"
    )
    async def create_schedule(
        self,
        interaction: discord.Interaction,
        car: str,
        date: str
    ):
        
        if not self.is_schedule_admin(interaction):
            await interaction.response.send_message(
                "❌ 你沒有建立班表的權限。",
                ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        period = CURRENT_PERIOD
        car = normalize_car(car)
        date = normalize_date(date)

        existing = get_schedule(period, car, date)

        if existing is not None:
            await interaction.followup.send(
                f"⚠️ `{car} {date}` 的班表已經存在。",
                ephemeral=True
            )
            return

        schedule = create_empty_schedule(period, car, date)

        image_path = render_schedule(schedule)

        message = await interaction.channel.send(
            file=discord.File(str(image_path), filename="schedule.png")
        )

        schedule.channel_id = interaction.channel.id
        schedule.message_id = message.id

        save_schedule(schedule)

        await interaction.followup.send(
            f"✅ 已建立 `{car} {date}` 的 24 小時班表。",
            ephemeral=True
        )

    @app_commands.command(
        name="刪除班表",
        description="刪除指定的班表"
    )
    async def delete_schedule_command(
        self,
        interaction: discord.Interaction,
        car: str,
        date: str
    ):
        if not self.is_schedule_admin(interaction):
            await interaction.response.send_message(
                "❌ 你沒有刪除班表的權限。",
                ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        period = CURRENT_PERIOD
        car = normalize_car(car)
        date = normalize_date(date)

        success = delete_schedule(period, car, date)

        if not success:
            await interaction.followup.send(
                f"❌ 找不到 `{car} {date}` 的班表。",
                ephemeral=True
            )
            return

        await interaction.followup.send(
            f"🗑️ 已刪除 `{car} {date}` 的排班。",
            ephemeral=True
        )

    @app_commands.command(
        name="強制刪除班表",
        description="不管期數，強制刪除指定班表"
    )
    async def force_delete_schedule(
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
                "❌ 你沒有強制刪除班表的權限。",
                ephemeral=True
            )
            return

        car = normalize_car(car)
        date = normalize_date(date)

        all_data = load_all()

        target_key = None
        target_schedule = None

        for key, schedule_data in all_data.items():
            schedule = dict_to_schedule(schedule_data)

            schedule_date = normalize_date(schedule.date)

            if schedule.car != car:
                continue

            if schedule_date != date:
                continue

            target_key = key
            target_schedule = schedule
            break

        if target_key is None:
            await interaction.followup.send(
                f"❌ 找不到 `{car} {date}` 的班表。",
                ephemeral=True
            )
            return

        try:
            channel = self.bot.get_channel(
                target_schedule.channel_id
            )

            if channel is None:
                channel = await self.bot.fetch_channel(
                    target_schedule.channel_id
                )

            message = await channel.fetch_message(
                target_schedule.message_id
            )

            await message.delete()

        except Exception:
            pass

        del all_data[target_key]
        save_all(all_data)

        await interaction.followup.send(
            f"🗑️ 已強制刪除 `{car} {date}` 的班表。",
            ephemeral=True
        )

    @app_commands.command(
        name="班表列表",
        description="查看目前所有班表"
    )
    async def list_schedules(
        self,
        interaction: discord.Interaction
    ):
        await interaction.response.defer(
            ephemeral=True
        )

        if not self.is_schedule_admin(interaction):
            await interaction.followup.send(
                "❌ 你沒有查看班表列表的權限。",
                ephemeral=True
            )
            return

        all_data = load_all()

        schedules = [
            dict_to_schedule(schedule_data)
            for schedule_data in all_data.values()
        ]

        if not schedules:
            await interaction.followup.send(
                "目前沒有任何班表。",
                ephemeral=True
            )
            return

        schedules.sort(
            key=lambda schedule: (
                schedule.date,
                schedule.car
            )
        )

        text = "📋 **班表列表**\n\n"

        for schedule in schedules:
            text += (
                f"• {schedule.car} "
                f"{schedule.date}\n"
            )

        text += (
            f"\n共 {len(schedules)} 張班表"
        )

        await interaction.followup.send(
            text,
            ephemeral=True
        )

    @app_commands.command(
        name="強制刪除所有班表",
        description="不管期數，刪除所有班表資料與班表訊息"
    )
    async def force_delete_all_schedules(
        self,
        interaction: discord.Interaction,
        confirm: str
    ):
        await interaction.response.defer(
            ephemeral=True
        )

        if not self.is_schedule_admin(interaction):
            await interaction.followup.send(
                "❌ 你沒有強制刪除所有班表的權限。",
                ephemeral=True
            )
            return

        if confirm != "DELETE_ALL":
            await interaction.followup.send(
                "❌ 安全驗證失敗。\n"
                "請將 confirm 設為 `DELETE_ALL`。",
                ephemeral=True
            )
            return

        all_data = load_all()

        if not all_data:
            await interaction.followup.send(
                "目前沒有任何班表可以刪除。",
                ephemeral=True
            )
            return

        deleted_count = 0
        message_delete_failed_count = 0

        for schedule_data in all_data.values():
            schedule = dict_to_schedule(
                schedule_data
            )

            try:
                channel = self.bot.get_channel(
                    schedule.channel_id
                )

                if channel is None:
                    channel = await self.bot.fetch_channel(
                        schedule.channel_id
                    )

                message = await channel.fetch_message(
                    schedule.message_id
                )

                await message.delete()

            except Exception:
                message_delete_failed_count += 1

            deleted_count += 1

        save_all({})

        await interaction.followup.send(
            f"🗑️ 已強制刪除所有班表。\n"
            f"刪除資料數：{deleted_count}\n"
            f"班表訊息刪除失敗："
            f"{message_delete_failed_count}",
            ephemeral=True
        )

async def setup(bot: commands.Bot):
    await bot.add_cog(AdminCog(bot))