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

from core.schedule_service import (
    get_row_by_time
)

from core.discord_message_service import (
    send_log_to_channel,
    update_schedule_message
)

from core.s6_reminder_service import (
    get_highest_runner_power
)

from core.schedule_edit_service import (
    fill_s6_schedule
)

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

    @discord.ui.button(
        label="接受S6",
        style=discord.ButtonStyle.success
    )
    async def accept_s6(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
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
            s6_power = int(
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
                "❌ S6報班失敗，請稍後再試。",
                ephemeral=True
            )
            return

        save_schedule(
            schedule
        )

        await update_schedule_message(
            self.bot,
            schedule
        )

        display_name = get_slot_display(
            slot_data
        )

        update_text = f"✅ 班表已更新 `{self.car} {self.date}`\n"

        update_text += (
            f"S6報班：`{self.time}` ~ "
            f"`{self.time}`：`{display_name}`"
        )

        for child in self.children:
            child.disabled = True

        await interaction.response.edit_message(
            view=self
        )

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
        await interaction.response.send_message(
            "已取消本次 S6 邀請。",
            ephemeral=True
        )