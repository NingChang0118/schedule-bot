import discord

from config import SCHEDULE_UPDATE_CHANNEL_ID

from core.storage import (
    get_schedule,
    save_schedule
)

from core.pusher_storage import (
    get_pusher
)

from core.s6_pusher_storage import (
    get_s6_pusher
)

from core.slot_utils import (
    make_slot,
    get_slot_display
)

from core.discord_message_service import (
    send_log_to_channel,
    update_schedule_message
)

from core.s6_reminder_service import (
    get_highest_runner_power,
    is_user_valid_s6_candidate
)

from core.schedule_edit_service import (
    fill_s6_schedule
)

from core.schedule_service import get_row_by_time

def is_user_already_in_row(row, user_id: int):
    user_id = str(user_id)

    slots = [
        row.slot_1,
        row.slot_2,
        row.slot_3,
        row.slot_4,
        row.slot_5,
        row.s6
    ]

    if isinstance(row.backup, list):
        slots.extend(row.backup)

    for slot in slots:
        if not isinstance(slot, dict):
            continue

        if str(slot.get("user_id")) == user_id:
            return True

    return False


class S6ReminderView(discord.ui.View):
    def __init__(
        self,
        bot,
        schedule,
        row
    ):
        super().__init__(
            timeout=300
        )

        self.bot = bot
        self.period = schedule.period
        self.car = schedule.car
        self.date = schedule.date
        self.time = row.time
        self.closed = False

    async def close_view(
        self,
        interaction: discord.Interaction
    ):
        self.closed = True

        for child in self.children:
            child.disabled = True

        await interaction.response.edit_message(
            view=self
        )

    @discord.ui.button(
        label="接受S6",
        style=discord.ButtonStyle.success
    )
    async def accept_s6(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        if self.closed:
            await interaction.response.send_message(
                "❌ 這個 S6 邀請已經被處理過了。",
                ephemeral=True
            )
            return

        schedule = get_schedule(
            self.period,
            self.car,
            self.date
        )

        if schedule is None:
            await interaction.response.send_message(
                "❌ 找不到這張班表，無法填入 S6。",
                ephemeral=True
            )
            return

        row = get_row_by_time(
            schedule,
            self.time
        )

        if row is None:
            await interaction.response.send_message(
                "❌ 找不到這個時段，無法填入 S6。",
                ephemeral=True
            )
            return

        if not is_user_valid_s6_candidate(
            row,
            interaction.user.id
        ):
            await interaction.response.send_message(
                "❌ 你不是這個時段的 S6 提醒對象，不能接這個 S6。",
                ephemeral=True
            )
            return

        if row.s6:
            await interaction.response.send_message(
                "❌ 這個時段已經有人接 S6 了。",
                ephemeral=True
            )
            return

        pusher_data = get_pusher(
            interaction.user.id
        )

        if pusher_data is None:
            await interaction.response.send_message(
                "❌ 你還沒有登記推車資料。\n"
                "請先使用 `/登記推車資料` 登記名稱與倍率。",
                ephemeral=True
            )
            return

        s6_data = get_s6_pusher(
            interaction.user.id
        )

        if s6_data is None:
            await interaction.response.send_message(
                "❌ 你還沒有登記 S6 資料。",
                ephemeral=True
            )
            return

        highest_runner_power = get_highest_runner_power(
            row
        )

        try:
            s6_power = float(
                s6_data.get("power", 0)
            )

        except Exception:
            s6_power = 0

        if s6_power <= highest_runner_power:
            await interaction.response.send_message(
                "❌ 你的 S6 綜合力沒有大於車上最高跑者，無法接 S6。",
                ephemeral=True
            )
            return

        slot_data = make_slot(
            user_id=interaction.user.id,
            name=pusher_data["name"],
            role_type="s6",
            rate=s6_data["rate"],
            power=s6_data["power"]
        )

        result = fill_s6_schedule(
            schedule,
            interaction.user.id,
            slot_data,
            self.time
        )

        if not result["ok"]:
            await interaction.response.send_message(
                f"❌ S6報班失敗\nerror: {result.get('error')}\ntarget_time: {result.get('target_time')}",
                ephemeral=True
            )
            return

        save_schedule(schedule)

        await update_schedule_message(
            self.bot,
            schedule
        )

        display_name = get_slot_display(
            slot_data
        )

        update_text = f"✅ 班表已更新 `{self.car} {self.date}`\n"

        update_text += (
            f"S6報班：`{self.time}`：`{display_name}`"
        )

        await self.close_view(interaction)

        await interaction.followup.send(
            f"✅ S6報班成功 {self.car} {self.date} {self.time}",
            ephemeral=True
        )

        await send_log_to_channel(
            self.bot,
            SCHEDULE_UPDATE_CHANNEL_ID,
            update_text
        )

    @discord.ui.button(
        label="拒絕S6",
        style=discord.ButtonStyle.danger
    )
    async def reject_s6(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        if self.closed:
            await interaction.response.send_message(
                "❌ 這個 S6 邀請已經被處理過了。",
                ephemeral=True
            )
            return

        if not interaction.message:
            await interaction.response.send_message(
                "已取消本次 S6 邀請。",
                ephemeral=True
            )
            return

        await self.close_view(interaction)

        await interaction.followup.send(
            "已取消本次 S6 邀請。",
            ephemeral=True
        )