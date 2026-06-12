import discord
from discord import app_commands
from discord.ext import commands, tasks

from core.models import create_empty_schedule
from core.storage import save_schedule, get_schedule, delete_schedule, load_all, dict_to_schedule, save_all
from config import (
    SCHEDULE_ADMIN_ROLE_ID,
    CURRENT_PERIOD,
    PUSHER_ROLE_ID,
    RUNNER_ROLE_ID,
    RECRUIT_ROLE_ID,
    S6_REMINDER_CHANNEL_ID
)
from core.pusher_storage import (
    save_pusher,
    get_pusher
)
from core.slot_utils import make_slot, get_slot_display, is_same_user
from config import EMERGENCY_RECRUIT_ROLE_ID, BOARDING_REMINDER_CHANNEL_IDS, SCHEDULE_UPDATE_CHANNEL_ID
from core.schedule_utils import (
    normalize_car,
    normalize_date,
    normalize_time,
    expand_time_range
)

from core.schedule_service import get_row_by_time

from core.rebalance_service import (
    rebalance_row,
)

from core.boarding_reminder_service import (
    get_boarding_reminder_user_ids,
    get_boarding_reminder_key,
    get_boarding_reminder_channel_id,
    build_boarding_reminder_message,
    has_boarding_reminder_been_sent,
    mark_boarding_reminder_sent,
    is_5_minutes_before_slot
)

from core.emergency_recruit_service import (
    is_15_minutes_before_slot,
    needs_emergency_recruit,
    has_emergency_recruit_been_sent,
    mark_emergency_recruit_sent,
    get_missing_count,
    build_emergency_recruit_message
)

from core.recruit_service import (
    build_recruit_message,
    get_recruit_rows
)

from core.stats_service import (
    get_user_hours,
    build_current_hours_text,
    build_history_hours_text,
    build_period_total_hours_text
)

from core.my_schedule_service import get_user_schedule_records, build_my_schedule_text

from core.backup_service import (
    build_backup_list_text,
    get_backup_list
)

from core.schedule_edit_service import (
    fill_pusher_schedule,
    fill_runner_schedule,
    cancel_user_schedule
)

from core.discord_message_service import (
    send_log_to_channel,
    update_schedule_message,
    send_schedule_image_response
)

from core.profile_sync_service import (
    sync_profile_to_all_current_schedules
)

from core.runner_storage import (
    save_runner,
    get_runner
)

from core.s6_pusher_storage import (
    save_s6_pusher,
    get_s6_pusher
)

from core.s6_reminder_service import (
    get_s6_reminder_user_ids,
    has_s6_reminder_been_sent,
    mark_s6_reminder_sent,
    is_5_minutes_before_s6_slot,
    build_s6_reminder_message
)

class ScheduleCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.emergency_recruited = set()
        self.emergency_recruit_loop.start()
        self.boarding_reminded = set()
        self.boarding_reminder_loop.start()
        self.s6_reminded = set()
        self.s6_reminder_loop.start()


    def has_role(self, interaction: discord.Interaction, role_id: int) -> bool:
        if not hasattr(interaction.user, "roles"):
            return False

        return any(
            role.id == role_id
            for role in interaction.user.roles
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

    @tasks.loop(minutes=1)
    async def emergency_recruit_loop(self):

        print("[緊急招募] 開始掃描")

        all_data = load_all()

        schedules = [
            dict_to_schedule(schedule_data)
            for schedule_data in all_data.values()
        ]

        print(f"[緊急招募] 讀到 {len(schedules)} 張班表")

        for schedule in schedules:
            print(
                f"[緊急招募] 檢查班表："
                f"{schedule.car} "
                f"{schedule.date} "
                f"共 {len(schedule.rows)} 個時段"
            )

            for row in schedule.rows:
                if not is_15_minutes_before_slot(
                    schedule,
                    row
                ):
                    continue

                if not needs_emergency_recruit(row):
                    continue

                print(
                    f"[緊急招募] 找到缺額："
                    f"{schedule.car} "
                    f"{schedule.date} "
                    f"{row.time} "
                    f"缺 {get_missing_count(row)} 人"
                )

                if has_emergency_recruit_been_sent(
                    schedule,
                    row
                ):
                    continue

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

                mark_emergency_recruit_sent(
                    self.emergency_recruited,
                    schedule,
                    row
                )

    @emergency_recruit_loop.before_loop
    async def before_emergency_recruit_loop(self):
        await self.bot.wait_until_ready()

    @tasks.loop(minutes=1)
    async def boarding_reminder_loop(self):

        print("[上車提醒] 開始掃描")

        all_data = load_all()

        schedules = [
            dict_to_schedule(schedule_data)
            for schedule_data in all_data.values()
        ]

        print(f"[上車提醒] 讀到 {len(schedules)} 張班表")

        for schedule in schedules:
            print(
                f"[上車提醒] 檢查班表："
                f"{schedule.car} "
                f"{schedule.date} "
                f"共 {len(schedule.rows)} 個時段"
            )

            for row in schedule.rows:
                if not is_5_minutes_before_slot(
                    schedule,
                    row
                ):
                    continue

                if has_boarding_reminder_been_sent(
                    self.boarding_reminded,
                    schedule,
                    row
                ):
                    continue

                user_ids = get_boarding_reminder_user_ids(
                    row
                )

                if not user_ids:
                    print(
                        f"[上車提醒] 無通知對象："
                        f"{schedule.car} "
                        f"{schedule.date} "
                        f"{row.time}"
                    )
                    continue

                channel_id = get_boarding_reminder_channel_id(
                    schedule
                )

                if channel_id is None:
                    print(
                        f"[上車提醒] 找不到對應頻道："
                        f"{schedule.car}"
                    )
                    continue

                channel = self.bot.get_channel(channel_id)

                if channel is None:
                    channel = await self.bot.fetch_channel(
                        channel_id
                    )

                message = build_boarding_reminder_message(
                    schedule,
                    row,
                    user_ids
                )

                await channel.send(message)

                mark_boarding_reminder_sent(
                    self.boarding_reminded,
                    schedule,
                    row
                )

                print(
                    f"[上車提醒] 已發送："
                    f"{schedule.car} "
                    f"{schedule.date} "
                    f"{row.time}"
                )

    @boarding_reminder_loop.before_loop
    async def before_boarding_reminder_loop(self):
        await self.bot.wait_until_ready()

    @tasks.loop(minutes=1)
    async def s6_reminder_loop(self):

        print("[S6提醒] 開始掃描")

        all_data = load_all()

        schedules = [
            dict_to_schedule(schedule_data)
            for schedule_data in all_data.values()
        ]

        print(f"[S6提醒] 讀到 {len(schedules)} 張班表")

        for schedule in schedules:
            print(
                f"[S6提醒] 檢查班表："
                f"{schedule.car} "
                f"{schedule.date} "
                f"共 {len(schedule.rows)} 個時段"
            )

            for row in schedule.rows:

                if not is_5_minutes_before_s6_slot(
                    schedule,
                    row
                ):
                    continue

                if has_s6_reminder_been_sent(
                    self.s6_reminded,
                    schedule,
                    row
                ):
                    continue

                user_ids = get_s6_reminder_user_ids(
                    row
                )

                if not user_ids:
                    continue

                print(
                    f"[S6提醒] 找到通知對象："
                    f"{schedule.car} "
                    f"{schedule.date} "
                    f"{row.time} "
                    f"{user_ids}"
                )

                message = build_s6_reminder_message(
                    schedule,
                    row,
                    user_ids
                )

                channel = self.bot.get_channel(
                    S6_REMINDER_CHANNEL_ID
                )

                if channel is None:
                    channel = await self.bot.fetch_channel(
                        S6_REMINDER_CHANNEL_ID
                    )

                await channel.send(
                    message
                )               

                mark_s6_reminder_sent(
                    self.s6_reminded,
                    schedule,
                    row
                )

    @s6_reminder_loop.before_loop
    async def before_s6_reminder_loop(self):
        await self.bot.wait_until_ready()

    @app_commands.command(
        name="推車報班",
        description="填入指定時間的推車手"
    )
    async def fill_pusher(
        self,
        interaction: discord.Interaction,
        car: str,
        date: str,
        time: str
    ):
        if not self.has_role(interaction, PUSHER_ROLE_ID):
            await interaction.response.send_message(
                "❌ 你沒有推車手報班權限。",
                ephemeral=True
            )
            return

        period = CURRENT_PERIOD
        car = normalize_car(car)
        date = normalize_date(date)

        pusher_data = get_pusher(interaction.user.id)

        if pusher_data is None:
            await interaction.response.send_message(
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

        display_name = get_slot_display(slot_data)

        schedule = get_schedule(period, car, date)

        if schedule is None:
            await interaction.response.send_message(
                f"❌ 找不到 `{car} {date}` 的排班。",
                ephemeral=True
            )
            return

        result = fill_pusher_schedule(
            schedule,
            interaction.user.id,
            slot_data,
            time
        )

        if not result["ok"]:
            if result["error"] == "time_not_found":
                await interaction.response.send_message(
                    f"❌ 找不到時間 `{result['target_time']}`。\n"
                    f"請使用格式例如：`21-22`、`21-24` 或 `2100-2200`",
                    ephemeral=True
                )
                return

            if result["error"] == "already_joined":
                await interaction.response.send_message(
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

        await interaction.response.send_message(
            public_text
        )

        await send_log_to_channel(
            self.bot,
            SCHEDULE_UPDATE_CHANNEL_ID,
            update_text
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

    @app_commands.command(
        name="跑者報班",
        description="填入指定時間的跑者"
    )
    async def fill_runner(
        self,
        interaction: discord.Interaction,
        car: str,
        date: str,
        time: str
    ):

        if not self.has_role(interaction, RUNNER_ROLE_ID):
            await interaction.response.send_message(
                "❌ 你沒有跑者報班權限。",
                ephemeral=True
            )
            return

        period = CURRENT_PERIOD
        car = normalize_car(car)
        date = normalize_date(date)

        runner_data = get_runner(
            interaction.user.id
        )

        if runner_data is None:
            await interaction.response.send_message(
                "❌ 你還沒有登記跑者資料。\n"
                "請先使用 `/登記跑者資料` 登記名稱與綜合。",
                ephemeral=True
            )
            return

        runner_name = runner_data["name"] + "R"
        slot_data = make_slot(
            user_id=interaction.user.id,
            name=runner_name,
            role_type="runner",
            power=runner_data["power"]
        )

        display_name = get_slot_display(slot_data)

        schedule = get_schedule(period, car, date)

        if schedule is None:
            await interaction.response.send_message(
                f"❌ 找不到 `{car} {date}` 的排班。",
                ephemeral=True
            )
            return

        result = fill_runner_schedule(
            schedule,
            interaction.user.id,
            slot_data,
            time
        )

        if not result["ok"]:
            if result["error"] == "time_not_found":
                await interaction.response.send_message(
                    f"❌ 找不到時間 `{result['target_time']}`。\n"
                    f"請使用格式例如：`21-22`、`21-24` 或 `2100-2200`",
                    ephemeral=True
                )
                return

            if result["error"] == "already_joined":
                await interaction.response.send_message(
                    f"❌ `{result['target_time']}` 你已經報過跑者了。",
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

        update_text += (
            f"跑者報班：`{joined_times[0]}` ~ "
            f"`{joined_times[-1]}`：`{display_name}`"
        )

        await interaction.response.send_message(
            public_text
        )

        await send_log_to_channel(
            self.bot,
            SCHEDULE_UPDATE_CHANNEL_ID,
            update_text
        )

    @app_commands.command(
        name="推車砍班",
        description="取消自己指定時段或整天的推車報班"
    )
    async def cancel_pusher_schedule(
        self,
        interaction: discord.Interaction,
        car: str,
        date: str,
        time: str = "",
        all_day: bool = False
    ):
        if not self.has_role(interaction, PUSHER_ROLE_ID):
            await interaction.response.send_message(
                "❌ 你沒有推車手砍班權限。",
                ephemeral=True
            )
            return

        period = CURRENT_PERIOD
        car = normalize_car(car)
        date = normalize_date(date)

        schedule = get_schedule(period, car, date)

        if schedule is None:
            await interaction.response.send_message(
                f"❌ 找不到 `{car} {date}` 的排班。",
                ephemeral=True
            )
            return

        result = cancel_user_schedule(
            schedule,
            interaction.user.id,
            "pusher",
            time,
            all_day
        )

        if not result["ok"]:
            if result["error"] == "missing_time":
                await interaction.response.send_message(
                    "❌ 請輸入要砍班的時間，或將 `all_day` 設為 `True`。",
                    ephemeral=True
                )
                return

            if result["error"] == "time_not_found":
                await interaction.response.send_message(
                    f"❌ 找不到時間 `{result['target_time']}`。\n"
                    f"請使用格式例如：`21-22`、`21-24` 或 `2100-2200`",
                    ephemeral=True
                )
                return

        removed_records = result["removed_records"]
        all_promoted_slots = result["promoted_slots"]

        if not removed_records:
            await interaction.response.send_message(
                f"⚠️ 沒有找到你在 `{car} {date}` 的推車報班資料。",
                ephemeral=True
            )
            return

        for promoted_slot in all_promoted_slots:
            if not isinstance(promoted_slot, dict):
                continue

            if promoted_slot.get("type") != "pusher":
                continue

            user_id = promoted_slot.get("user_id")

            try:
                user = await self.bot.fetch_user(int(user_id))

                await user.send(
                    f"🎉 你已由候補轉為正式班！\n\n"
                    f"車輛：{car}\n"
                    f"日期：{date}\n"
                    f"名稱：{promoted_slot.get('display')}\n\n"
                    f"請記得準時上車。"
                )

            except Exception as e:
                print("遞補轉正通知失敗：", user_id, e)

        save_schedule(schedule)

        await update_schedule_message(
            self.bot,
            schedule
        )

        removed_times = [
            record.split("：")[0]
            for record in removed_records
        ]

        removed_names = [
            record.split("：")[1]
            for record in removed_records
        ]

        display_name = removed_names[0]

        public_text = (
            f"推車砍班成功 {car} {date} "
            f"{time}"
        )

        update_text = f"✅ 班表已更新 `{car} {date}`\n"

        update_text += (
            f"推車砍班：`{removed_times[0]}` ~ "
            f"`{removed_times[-1]}`：`{display_name}`"
        )

        await interaction.response.send_message(
            public_text
        )

        await send_log_to_channel(
            self.bot,
            SCHEDULE_UPDATE_CHANNEL_ID,
            update_text
        )

    @app_commands.command(
        name="跑者砍班",
        description="取消自己指定時段或整天的跑者報班"
    )
    async def cancel_runner_schedule(
        self,
        interaction: discord.Interaction,
        car: str,
        date: str,
        time: str = "",
        all_day: bool = False
    ):
        if not self.has_role(interaction, RUNNER_ROLE_ID):
            await interaction.response.send_message(
                "❌ 你沒有跑者砍班權限。",
                ephemeral=True
            )
            return

        period = CURRENT_PERIOD
        car = normalize_car(car)
        date = normalize_date(date)

        schedule = get_schedule(period, car, date)

        if schedule is None:
            await interaction.response.send_message(
                f"❌ 找不到 `{car} {date}` 的排班。",
                ephemeral=True
            )
            return

        result = cancel_user_schedule(
            schedule,
            interaction.user.id,
            "runner",
            time,
            all_day
        )

        if not result["ok"]:
            if result["error"] == "missing_time":
                await interaction.response.send_message(
                    "❌ 請輸入要砍班的時間，或將 `all_day` 設為 `True`。",
                    ephemeral=True
                )
                return

            if result["error"] == "time_not_found":
                await interaction.response.send_message(
                    f"❌ 找不到時間 `{result['target_time']}`。\n"
                    f"請使用格式例如：`21-22`、`21-24` 或 `2100-2200`",
                    ephemeral=True
                )
                return

        removed_records = result["removed_records"]

        if not removed_records:
            await interaction.response.send_message(
                f"⚠️ 沒有找到你在 `{car} {date}` 的跑者報班資料。",
                ephemeral=True
            )
            return

        save_schedule(schedule)

        await update_schedule_message(
            self.bot,
            schedule
        )

        removed_times = [
            record.split("：")[0]
            for record in removed_records
        ]

        removed_names = [
            record.split("：")[1]
            for record in removed_records
        ]

        display_name = removed_names[0]

        public_text = (
            f"跑者砍班成功 {car} {date} "
            f"{time}"
        )

        update_text = f"✅ 班表已更新 `{car} {date}`\n"

        update_text += (
            f"跑者砍班：`{removed_times[0]}` ~ "
            f"`{removed_times[-1]}`：`{display_name}`"
        )

        await interaction.response.send_message(
            public_text
        )

        await send_log_to_channel(
            self.bot,
            SCHEDULE_UPDATE_CHANNEL_ID,
            update_text
        )

    @app_commands.command(
        name="我的班表",
        description="查看自己目前期數的所有報班"
    )
    async def my_schedule(
        self,
        interaction: discord.Interaction
    ):
        records = get_user_schedule_records(
            interaction.user.id,
            CURRENT_PERIOD
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
        await interaction.response.defer(ephemeral=True)

        period = CURRENT_PERIOD
        car = normalize_car(car)
        date = normalize_date(date)

        schedule = get_schedule(period, car, date)

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
        stats = get_user_hours(
            interaction.user.id,
            CURRENT_PERIOD
        )

        text = build_current_hours_text(
            CURRENT_PERIOD,
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

        text = build_period_total_hours_text(
            CURRENT_PERIOD
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
        period = CURRENT_PERIOD
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
        await interaction.response.defer(ephemeral=True)

        if not self.is_schedule_admin(interaction):
            await interaction.followup.send(
                "❌ 你沒有使用此指令的權限。",
                ephemeral=True
            )
            return

        period = CURRENT_PERIOD
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
                倍率
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
                名稱
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

        period = CURRENT_PERIOD
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
            power="350000"
        )

        target_row.slot_2 = make_slot(
            "test_runner_2",
            "跑者B",
            "runner",
            power="360000"
        )

        target_row.slot_3 = make_slot(
            "test_pusher_1",
            "推車A",
            "pusher",
            "4.5",
            power="300000"
        )

        target_row.slot_4 = make_slot(
            "test_pusher_2",
            "推車B",
            "pusher",
            "4.2",
            power="300000"
        )

        target_row.slot_5 = make_slot(
            "test_pusher_3",
            "推車C",
            "pusher",
            "4.0",
            power="300000"
        )

        save_s6_pusher(
            "test_pusher_1",
            "4.5",
            "400000"
        )

        target_row.backup = [
            make_slot(
                "test_pusher_4",
                "推車D",
                "pusher",
                "3.8"
            ),
            make_slot(
                "test_pusher_5",
                "推車E",
                "pusher",
                "3.5"
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

async def setup(bot: commands.Bot):
    await bot.add_cog(ScheduleCog(bot))