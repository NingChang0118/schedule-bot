import discord
from discord import app_commands
from discord.ext import commands, tasks

from core.models import create_empty_schedule
from core.storage import save_schedule, get_schedule, delete_schedule, load_all, dict_to_schedule, save_all
from core.renderer import render_schedule
from config import (
    SCHEDULE_ADMIN_ROLE_ID,
    CURRENT_PERIOD,
    S6_REMINDER_CHANNEL_ID
)

from core.schedule_utils import (
    normalize_car,
    normalize_date,
    normalize_time
)

from core.emergency_recruit_service import (
    needs_emergency_recruit,
    get_missing_count,
    build_emergency_recruit_message
)

from core.reminder_scan_service import (
    send_s6_reminder_for_row
)

from core.schedule_edit_service import (
    fill_runner_schedule,
    fill_pusher_schedule,
    fill_s6_schedule
)

from core.boarding_reminder_service import (
    get_boarding_reminder_user_ids,
    get_boarding_reminder_channel_id,
    build_boarding_reminder_message
)

from core.schedule_service import get_row_by_time
from core.rebalance_service import rebalance_row

from core.manual_move_service import (
    move_formal_member
)

class AdminCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.force_s6_reminded = set()

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

    def get_slot_value(self, slot, key, default=None):
        if isinstance(slot, dict):
            return slot.get(key, default)

        return getattr(slot, key, default)

    def rebuild_schedule_from_current_data(self, schedule):
        new_schedule = create_empty_schedule(
            schedule.period,
            schedule.car,
            schedule.date
        )

        new_schedule.channel_id = schedule.channel_id
        new_schedule.message_id = schedule.message_id

        for row in schedule.rows:
            new_row = get_row_by_time(
                new_schedule,
                row.time
            )

            if new_row is None:
                continue

            new_row.car_type = row.car_type

            old_slots = [
                row.slot_1,
                row.slot_2,
                row.slot_3,
                row.slot_4,
                row.slot_5
            ]

            for slot in old_slots:
                if not isinstance(slot, dict):
                    continue

                new_row.backup.append(slot)

            for slot in row.backup:
                if not isinstance(slot, dict):
                    continue

                new_row.backup.append(slot)

            if isinstance(row.s6, dict):
                new_row.s6 = row.s6
                new_row.backup.append(row.s6)

            rebalance_row(new_row)

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

        old_count = 0
        new_count = 0

        for row in schedule.rows:
            for slot in [
                row.slot_1,
                row.slot_2,
                row.slot_3,
                row.slot_4,
                row.slot_5
            ]:
                if slot:
                    old_count += 1

            old_count += len(row.backup)

            if row.s6:
                old_count += 1

        for row in new_schedule.rows:
            for slot in [
                row.slot_1,
                row.slot_2,
                row.slot_3,
                row.slot_4,
                row.slot_5
            ]:
                if slot:
                    new_count += 1

            new_count += len(row.backup)

            if row.s6:
                new_count += 1

        if old_count > 0 and new_count == 0:
            await interaction.followup.send(
                "❌ 重建中止：原班表有資料，但重建結果為空。\n"
                "為避免資料被覆蓋，已取消儲存。",
                ephemeral=True
            )
            return


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

    @app_commands.command(
        name="強制發送s6提醒",
        description="不檢查時間，強制發送指定時段的 S6 提醒"
    )
    async def force_send_s6_reminder(
        self,
        interaction: discord.Interaction,
        car: str,
        date: str,
        time: str
    ):
        if not self.is_schedule_admin(interaction):
            await interaction.response.send_message(
                "❌ 你沒有強制發送 S6 提醒的權限。",
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
        
        time = normalize_time(time)

        if time is None:
            await interaction.followup.send(
                "❌ 時間格式錯誤。",
                ephemeral=True
            )
            return

        row = get_row_by_time(schedule, time)

        if row is None:
            await interaction.followup.send(
                f"❌ 找不到 `{time}` 時段。",
                ephemeral=True
            )
            return

        sent = await send_s6_reminder_for_row(
            self.bot,
            set(),
            schedule,
            row,
            force_send=True
        )

        if not sent:
            await interaction.followup.send(
                f"⚠️ `{car} {date} {time}` 沒有符合條件的 S6 通知對象。",
                ephemeral=True
            )
            return

        await interaction.followup.send(
            f"✅ 已強制發送 `{car} {date} {time}` 的 S6 提醒。",
            ephemeral=True
        )

    @app_commands.command(
        name="強制發送上車提醒",
        description="不檢查時間，強制發送指定時段的上車提醒"
    )
    async def force_send_boarding_reminder(
        self,
        interaction: discord.Interaction,
        car: str,
        date: str,
        time: str
    ):
        if not self.is_schedule_admin(interaction):
            await interaction.response.send_message(
                "❌ 你沒有強制發送上車提醒的權限。",
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

        time = normalize_time(time)

        if time is None:
            await interaction.followup.send(
                "❌ 時間格式錯誤。",
                ephemeral=True
            )
            return

        row = get_row_by_time(schedule, time)

        if row is None:
            await interaction.followup.send(
                f"❌ 找不到 `{time}` 時段。",
                ephemeral=True
            )
            return

        user_ids = get_boarding_reminder_user_ids(
            row
        )

        if not user_ids:
            await interaction.followup.send(
                f"⚠️ `{car} {date} {time}` 沒有上車提醒通知對象。",
                ephemeral=True
            )
            return

        channel_id = get_boarding_reminder_channel_id(
            schedule
        )

        if channel_id is None:
            await interaction.followup.send(
                f"❌ 找不到 `{car}` 對應的上車提醒頻道。",
                ephemeral=True
            )
            return

        channel = self.bot.get_channel(channel_id)

        if channel is None:
            channel = await self.bot.fetch_channel(channel_id)

        message = build_boarding_reminder_message(
            schedule,
            row,
            user_ids
        )

        await channel.send(message)

        await interaction.followup.send(
            f"✅ 已強制發送 `{car} {date} {time}` 的上車提醒。",
            ephemeral=True
        )

    @app_commands.command(
        name="強制發送緊急招募",
        description="不檢查時間，強制發送指定時段的緊急招募"
    )
    async def force_send_emergency_recruit(
        self,
        interaction: discord.Interaction,
        car: str,
        date: str,
        time: str
    ):
        if not self.is_schedule_admin(interaction):
            await interaction.response.send_message(
                "❌ 你沒有強制發送緊急招募的權限。",
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

        time = normalize_time(time)

        if time is None:
            await interaction.followup.send(
                "❌ 時間格式錯誤。",
                ephemeral=True
            )
            return

        row = get_row_by_time(schedule, time)

        if row is None:
            await interaction.followup.send(
                f"❌ 找不到 `{time}` 時段。",
                ephemeral=True
            )
            return

        if not needs_emergency_recruit(row):
            await interaction.followup.send(
                f"⚠️ `{car} {date} {time}` 目前沒有缺額，不發送緊急招募。",
                ephemeral=True
            )
            return

        channel = self.bot.get_channel(
            schedule.channel_id
        )

        if channel is None:
            channel = await self.bot.fetch_channel(
                schedule.channel_id
            )

        message = build_emergency_recruit_message(
            schedule,
            row
        )

        await channel.send(message)

        await interaction.followup.send(
            f"✅ 已強制發送 `{car} {date} {time}` 的緊急招募。\n"
            f"目前缺額：{get_missing_count(row)}",
            ephemeral=True
        )

    @app_commands.command(
        name="移動正式成員",
        description="手動調整正式成員位置"
    )
    async def move_formal_member_command(
        self,
        interaction: discord.Interaction,
        from_car: str,
        date: str,
        from_time: str,
        from_slot: int,
        to_car: str,
        to_time: str,
        to_slot: int
    ):
        if not self.is_schedule_admin(interaction):
            await interaction.response.send_message(
                "❌ 你沒有移動正式成員的權限。",
                ephemeral=True
            )
            return

        await interaction.response.defer(
            ephemeral=True
        )

        success, message = move_formal_member(
            period=CURRENT_PERIOD,
            from_car=from_car,
            date=date,
            from_time=from_time,
            from_slot=from_slot,
            to_car=to_car,
            to_time=to_time,
            to_slot=to_slot
        )

        if not success:
            await interaction.followup.send(
                message,
                ephemeral=True
            )
            return

        from_schedule = get_schedule(
            CURRENT_PERIOD,
            normalize_car(from_car),
            normalize_date(date)
        )

        to_schedule = get_schedule(
            CURRENT_PERIOD,
            normalize_car(to_car),
            normalize_date(date)
        )

        if from_schedule is not None:
            await self.update_schedule_message(
                from_schedule
            )

        if (
            to_schedule is not None
            and (
                from_car != to_car
                or from_schedule.message_id != to_schedule.message_id
            )
        ):
            await self.update_schedule_message(
                to_schedule
            )

        await interaction.followup.send(
            message,
            ephemeral=True
        )

async def setup(bot: commands.Bot):
    await bot.add_cog(AdminCog(bot))