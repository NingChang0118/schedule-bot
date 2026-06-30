import discord
from discord import app_commands
from discord.ext import commands


from core.storage import (
    save_schedule,
    get_schedule
)

from core.schedule_utils import (
    normalize_car,
    normalize_date,
    expand_time_range
)

from core.schedule_service import (
    get_row_by_time
)

from core.slot_utils import (
    make_slot
)

from core.rebalance_service import (
    rebalance_row
)

from core.s6_pusher_storage import (
    save_s6_pusher
)

from config import (
    SCHEDULE_ADMIN_ROLE_ID
)

from core.settings_storage import (
    get_current_period
)

from core.discord_message_service import (
    update_schedule_message
)


class TestCog(commands.Cog):

    def __init__(self, bot):
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
        name="測試",
        description="測試排班機器人是否正常運作"
    )
    async def test(
        self,
        interaction: discord.Interaction
    ):
        await interaction.response.send_message(
            "排班機器人正常運作 ✅",
            ephemeral=True
        )

    @app_commands.command(
        name="測試共跑",
        description="建立共跑測試資料"
    )
    async def test_shared_run(
        self,
        interaction: discord.Interaction,
        car: str,
        date: str,
        time: str
    ):
        if not self.is_schedule_admin(interaction):
            await interaction.response.send_message(
                "❌ 你沒有測試排班的權限。",
                ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        period = get_current_period()
        car = normalize_car(car)
        date = normalize_date(date)
        target_time = expand_time_range(time)[0]

        schedule = get_schedule(period, car, date)

        if schedule is None:
            await interaction.followup.send(
                f"❌ 找不到 `{car} {date}` 的排班。",
                ephemeral=True
            )
            return

        target_row = get_row_by_time(schedule, target_time)

        if target_row is None:
            await interaction.followup.send(
                f"❌ 找不到時間 `{target_time}`。",
                ephemeral=True
            )
            return

        target_row.slot_1 = make_slot(
            "test_runner_1",
            "跑者A",
            "runner",
            power="35.0"
        )

        target_row.slot_2 = make_slot(
            "test_runner_2",
            "跑者B",
            "runner",
            power="36.0"
        )

        target_row.slot_3 = make_slot(
            "test_pusher_1",
            "推車A",
            "pusher",
            "3.88",
            power="30.0"
        )

        target_row.slot_4 = make_slot(
            "test_pusher_2",
            "推車B",
            "pusher",
            "3.80",
            power="30.0"
        )

        target_row.slot_5 = make_slot(
            "test_pusher_3",
            "推車C",
            "pusher",
            "3.70",
            power="30.0"
        )

        save_s6_pusher(
            "test_pusher_1",
            "3.88",
            "39.0"
        )

        target_row.backup = [
            make_slot(
                "test_pusher_4",
                "推車D",
                "pusher",
                "3.64"
            ),
            make_slot(
                "test_pusher_5",
                "推車E",
                "pusher",
                "3.60"
            )
        ]

        rebalance_row(target_row)

        save_schedule(schedule)

        await update_schedule_message(
            self.bot,
            schedule
        )

        await interaction.followup.send(
            f"✅ 已建立 `{car} {date} {target_time}` 的共跑測試資料。",
            ephemeral=True
        )

    @app_commands.command(
        name="測試新增成員",
        description="手動新增測試跑者 / 推車手 / S6 / 候補"
    )
    async def test_add_member(
        self,
        interaction: discord.Interaction,
        car: str,
        date: str,
        time: str,
        position: str,
        role_type: str,
        display: str,
        rate: str = "",
        power: str = "",
        car_type: str = "",
        user_id: str = ""
    ):
        if not self.is_schedule_admin(interaction):
            await interaction.response.send_message(
                "❌ 你沒有測試排班的權限。",
                ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        period = get_current_period()
        car = normalize_car(car)
        date = normalize_date(date)
        target_time = expand_time_range(time)[0]

        position_map = {
            "1": "slot_1",
            "2": "slot_2",
            "3": "slot_3",
            "4": "slot_4",
            "5": "slot_5"
        }

        position = position_map.get(
            position,
            position
        )

        if not user_id:
            user_id = str(interaction.user.id)

        schedule = get_schedule(period, car, date)

        if schedule is None:
            await interaction.followup.send(
                f"❌ 找不到 `{car} {date}` 的排班。",
                ephemeral=True
            )
            return

        target_row = get_row_by_time(schedule, target_time)

        if target_row is None:
            await interaction.followup.send(
                f"❌ 找不到時間 `{target_time}`。",
                ephemeral=True
            )
            return

        if role_type not in ["runner", "pusher", "s6"]:
            await interaction.followup.send(
                "❌ role_type 只能是 `runner`、`pusher` 或 `s6`。",
                ephemeral=True
            )
            return

        if position not in [
            "slot_1",
            "slot_2",
            "slot_3",
            "slot_4",
            "slot_5",
            "backup",
            "s6"
        ]:
            await interaction.followup.send(
                "❌ position 只能是 `slot_1`、`slot_2`、`slot_3`、`slot_4`、`slot_5`、`backup` 或 `s6`。",
                ephemeral=True
            )
            return

        if position == "s6" and role_type != "s6":
            await interaction.followup.send(
                "❌ position 是 `s6` 時，role_type 必須是 `s6`。",
                ephemeral=True
            )
            return

        if role_type == "s6" and position != "s6":
            await interaction.followup.send(
                "❌ role_type 是 `s6` 時，position 必須是 `s6`。",
                ephemeral=True
            )
            return

        slot_data = make_slot(
            user_id,
            display,
            role_type,
            rate,
            power=power
        )

        if position == "backup":
            target_row.backup.append(slot_data)

        elif position == "s6":
            target_row.s6 = slot_data

            if rate or power:
                save_s6_pusher(
                    user_id,
                    rate,
                    power
                )

        else:
            setattr(
                target_row,
                position,
                slot_data
            )

        if role_type == "runner" and car_type:
            target_row.car_type = car_type

        rebalance_row(target_row)

        save_schedule(schedule)

        await update_schedule_message(
            self.bot,
            schedule
        )

        await interaction.followup.send(
            f"✅ 已新增測試成員 `{display}` 到 `{car} {date} {target_time}` 的 `{position}`。",
            ephemeral=True
        )

    @app_commands.command(
        name="測試移除位置",
        description="手動清空指定 slot / S6 / 候補"
    )
    async def test_remove_position(
        self,
        interaction: discord.Interaction,
        car: str,
        date: str,
        time: str,
        position: str,
        backup_index: int = 1
    ):
        if not self.is_schedule_admin(interaction):
            await interaction.response.send_message(
                "❌ 你沒有測試排班的權限。",
                ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        period = get_current_period()
        car = normalize_car(car)
        date = normalize_date(date)
        target_time = expand_time_range(time)[0]

        position_map = {
            "1": "slot_1",
            "2": "slot_2",
            "3": "slot_3",
            "4": "slot_4",
            "5": "slot_5"
        }

        position = position_map.get(
            position,
            position
        )

        schedule = get_schedule(period, car, date)

        if schedule is None:
            await interaction.followup.send(
                f"❌ 找不到 `{car} {date}` 的排班。",
                ephemeral=True
            )
            return

        target_row = get_row_by_time(schedule, target_time)

        if target_row is None:
            await interaction.followup.send(
                f"❌ 找不到時間 `{target_time}`。",
                ephemeral=True
            )
            return

        if position not in [
            "slot_1",
            "slot_2",
            "slot_3",
            "slot_4",
            "slot_5",
            "backup",
            "s6"
        ]:
            await interaction.followup.send(
                "❌ position 只能是 `slot_1`、`slot_2`、`slot_3`、`slot_4`、`slot_5`、`backup` 或 `s6`。",
                ephemeral=True
            )
            return

        if position == "backup":
            target_index = backup_index - 1

            if target_index < 0 or target_index >= len(target_row.backup):
                await interaction.followup.send(
                    f"❌ 找不到第 `{backup_index}` 位候補。",
                    ephemeral=True
                )
                return

            target_row.backup.pop(target_index)

        elif position == "s6":
            target_row.s6 = ""

        else:
            setattr(
                target_row,
                position,
                ""
            )

        rebalance_row(target_row)

        save_schedule(schedule)

        await update_schedule_message(
            self.bot,
            schedule
        )

        await interaction.followup.send(
            f"✅ 已清空 `{car} {date} {target_time}` 的 `{position}`。",
            ephemeral=True
        )


async def setup(bot):
    await bot.add_cog(TestCog(bot))