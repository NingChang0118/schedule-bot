import discord
from discord import app_commands
from discord.ext import commands, tasks

from core.models import create_empty_schedule
from core.storage import save_schedule, get_schedule, delete_schedule, load_all, dict_to_schedule, save_all
from core.renderer import render_schedule
from config import (
    SCHEDULE_ADMIN_ROLE_ID,
    CURRENT_PERIOD,
    PUSHER_ROLE_ID,
    RUNNER_ROLE_ID,
    RECRUIT_ROLE_ID
)
from core.pusher_storage import (
    save_pusher,
    get_pusher
)
from core.slot_utils import make_slot, get_slot_display, is_same_user
from config import EMERGENCY_RECRUIT_ROLE_ID, BOARDING_REMINDER_CHANNEL_IDS

class ScheduleCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.emergency_recruited = set()
        self.emergency_recruit_loop.start()
        self.boarding_reminded = set()
        self.boarding_reminder_loop.start()

    def get_boarding_reminder_user_ids(self, row) -> list[int]:
        """
        取得上車提醒通知對象

        包含：
        - 正式班所有人
        - 候補第 1 位
        """

        user_ids = []

        slots = [
            row.slot_1,
            row.slot_2,
            row.slot_3,
            row.slot_4,
            row.slot_5
        ]

        for slot in slots:
            if not isinstance(slot, dict):
                continue

            user_id = slot.get("user_id")

            if user_id is None:
                continue

            if user_id not in user_ids:
                user_ids.append(user_id)

        if row.backup:
            first_backup = row.backup[0]

            if isinstance(first_backup, dict):
                user_id = first_backup.get("user_id")

                if user_id is not None and user_id not in user_ids:
                    user_ids.append(user_id)

        return user_ids

    def get_boarding_reminder_key(self, schedule, row) -> str:
        """
        上車提醒唯一 Key
        """

        return (
            f"{schedule.car}_"
            f"{schedule.date}_"
            f"{row.time}"
        )

    def has_boarding_reminder_been_sent(
        self,
        schedule,
        row
    ) -> bool:
        """
        是否已發送上車提醒
        """

        key = self.get_boarding_reminder_key(
            schedule,
            row
        )

        return key in self.boarding_reminded

    def mark_boarding_reminder_sent(
        self,
        schedule,
        row
    ):
        """
        標記已發送上車提醒
        """

        key = self.get_boarding_reminder_key(
            schedule,
            row
        )

        self.boarding_reminded.add(key)

    def get_boarding_reminder_channel_id(
        self,
        schedule
    ) -> int | None:
        """
        根據車輛取得對應衝榜頻道
        """

        return BOARDING_REMINDER_CHANNEL_IDS.get(
            schedule.car
        )

    def build_boarding_reminder_message(
        self,
        schedule,
        row
    ) -> str:
        """
        建立發車提醒訊息
        """

        user_ids = self.get_boarding_reminder_user_ids(
            row
        )

        mentions = " ".join(
            f"<@{user_id}>"
            for user_id in user_ids
        )

        return (
            f"{mentions}\n\n"
            f"🚗 發車提醒\n\n"
            f"車輛：{schedule.car}\n"
            f"日期：{schedule.date}\n"
            f"時段：{row.time}\n\n"
            f"請準備上車。"
        )

    def is_5_minutes_before_slot(self, schedule, row) -> bool:
        """
        判斷目前時間是否剛好是該時段發車前 5 分鐘
        支援跨年，例如 12/31 23:55 提醒 1/1 00:00
        """

        from datetime import datetime, timedelta

        try:
            now = datetime.now()

            month, day = map(int, schedule.date.split("/"))

            start_time = row.time.split("-")[0]
            hour = int(start_time[:2])
            minute = int(start_time[2:])

            slot_start = datetime(
                year=now.year,
                month=month,
                day=day,
                hour=hour,
                minute=minute
            )

            if slot_start < now - timedelta(days=180):
                slot_start = slot_start.replace(
                    year=now.year + 1
                )

            target_time = slot_start - timedelta(minutes=5)

            return (
                now.year == target_time.year
                and now.month == target_time.month
                and now.day == target_time.day
                and now.hour == target_time.hour
                and now.minute == target_time.minute
            )

        except Exception as e:
            print("[上車提醒] 時間判斷失敗：", e)
            return False

    def is_15_minutes_before_slot(self, schedule, row) -> bool:
        """
        判斷目前時間是否剛好是該時段發車前 15 分鐘
        """

        from datetime import datetime, timedelta

        try:
            now = datetime.now()

            month, day = map(int, schedule.date.split("/"))

            start_time = row.time.split("-")[0]
            hour = int(start_time[:2])
            minute = int(start_time[2:])

            slot_start = datetime(
                year=now.year,
                month=month,
                day=day,
                hour=hour,
                minute=minute
            )

            if slot_start < now - timedelta(days=180):
                slot_start = slot_start.replace(
                    year=now.year + 1
                )

            target_time = slot_start - timedelta(minutes=15)

            return (
                now.year == target_time.year
                and now.month == target_time.month
                and now.day == target_time.day
                and now.hour == target_time.hour
                and now.minute == target_time.minute
            )

        except Exception as e:
            print("[緊急招募] 時間判斷失敗：", e)
            return False

    def needs_emergency_recruit(self, row) -> bool:
        """
        判斷該時段是否需要緊急招募

        條件：
        - 有跑者
        - 總人數未滿 5 人
        """

        slots = [
            row.slot_1,
            row.slot_2,
            row.slot_3,
            row.slot_4,
            row.slot_5
        ]

        has_runner = False
        filled_count = 0

        for slot in slots:
            if not slot:
                continue

            filled_count += 1

            if isinstance(slot, dict) and slot.get("type") == "runner":
                has_runner = True

        return has_runner and filled_count < 5

    def get_emergency_key(self, schedule, row) -> str:
        """
        產生緊急招募唯一 Key
        """

        return (
            f"{schedule.car}_"
            f"{schedule.date}_"
            f"{row.time}"
        )

    def has_emergency_recruit_been_sent(
        self,
        schedule,
        row
    ) -> bool:
        """
        是否已經發送過緊急招募
        """

        key = self.get_emergency_key(schedule, row)

        return key in self.emergency_recruited

    def mark_emergency_recruit_sent(
        self,
        schedule,
        row
    ):
        """
        標記已發送
        """

        key = self.get_emergency_key(schedule, row)

        self.emergency_recruited.add(key)

    def get_missing_count(self, row) -> int:
        """
        計算該時段缺幾人
        滿班為 5 人
        """

        slots = [
            row.slot_1,
            row.slot_2,
            row.slot_3,
            row.slot_4,
            row.slot_5
        ]

        filled_count = 0

        for slot in slots:
            if slot:
                filled_count += 1

        return 5 - filled_count

    def build_emergency_recruit_message(
        self,
        schedule,
        row
    ) -> str:

        missing_count = self.get_missing_count(row)

        display_time = row.time

        if len(display_time) == 9:
            display_time = (
                f"{display_time[0:2]}-"
                f"{display_time[5:7]}"
            )

        return (
            f"<@&{EMERGENCY_RECRUIT_ROLE_ID}>\n"
            f"{schedule.car} {display_time} @{missing_count}"
        )

    def get_row_by_time(self, schedule, time: str):
        """
        從 schedule.rows 裡找指定時段的 row
        """
        for row in schedule.rows:
            if row.time == time:
                return row
        return None

    def analyze_recruit_slots(self, row):
        formal_slots = [
            row.slot_1,
            row.slot_2,
            row.slot_3,
            row.slot_4,
            row.slot_5,
        ]

        occupied_slots = [
            slot
            for slot in formal_slots
            if slot
        ]

        total_count = len(occupied_slots)
        missing_count = max(0, 5 - total_count)

        return {
            "total_count": total_count,
            "missing_count": missing_count,
        }

    def build_recruit_message(
        self,
        role_id: int,
        car: str,
        date: str,
        recruit_rows: list
    ):
        """
        建立整天缺額招募訊息

        recruit_rows:
        [
            ("2000-2100", 1),
            ("2100-2200", 2),
        ]
        """

        role_mention = f"<@&{role_id}>"

        text = (
            f"{role_mention}\n\n"
            f"🚨 **缺額招募** 🚨\n\n"
            f"車輛：{car}\n"
            f"日期：{date}\n\n"
        )

        for time_text, missing_count in recruit_rows:
            text += (
                f"• {time_text}"
                f"（缺 {missing_count} 人）\n"
            )

        text += (
            "\n請使用 `/報班` 補班。"
        )

        return text

    def normalize_car(self, car: str) -> str:
        car_map = {
            "1": "一車",
            "2": "二車",
            "3": "三車",
            "4": "四車",
            "5": "五車",
            "一": "一車",
            "二": "二車",
            "三": "三車",
            "四": "四車",
            "五": "五車",
        }

        return car_map.get(car, car)

    def normalize_date(self, date: str) -> str:
        date = date.strip()

        if "/" in date:
            month, day = date.split("/")
            return f"{int(month)}/{int(day)}"

        if len(date) == 4 and date.isdigit():
            month = int(date[:2])
            day = int(date[2:])
            return f"{month}/{day}"

        return date

    def get_slot_rate(self, slot) -> float:
        if not slot:
            return 0.0

        if isinstance(slot, str):
            if "(" not in slot or ")" not in slot:
                return 0.0

            try:
                rate_text = slot.split("(")[-1].split(")")[0]
                return float(rate_text)
            except ValueError:
                return 0.0

        try:
            return float(slot.get("rate") or 0.0)
        except ValueError:
            return 0.0

    def is_runner_slot(self, slot) -> bool:
        if not slot:
            return False

        if isinstance(slot, str):
            return "(" not in slot or ")" not in slot

        return slot.get("type") == "runner"

    def is_pusher_slot(self, slot) -> bool:
        if not slot:
            return False

        if isinstance(slot, str):
            return "(" in slot and ")" in slot

        return slot.get("type") == "pusher"

    def has_role(self, interaction: discord.Interaction, role_id: int) -> bool:
        if not hasattr(interaction.user, "roles"):
            return False

        return any(
            role.id == role_id
            for role in interaction.user.roles
        )

    def sort_row_by_rate(self, row):
        self.rebalance_row(row)

    def fill_first_empty_slot(self, row, slot_data) -> bool:
        if not row.slot_1:
            row.slot_1 = slot_data
            return True

        if not row.slot_2:
            row.slot_2 = slot_data
            return True

        if not row.slot_3:
            row.slot_3 = slot_data
            return True

        if not row.slot_4:
            row.slot_4 = slot_data
            return True

        if not row.slot_5:
            row.slot_5 = slot_data
            return True

        return False

    def already_in_row(self, row, user_id, role_type: str) -> bool:
        slots = [
            row.slot_1,
            row.slot_2,
            row.slot_3,
            row.slot_4,
            row.slot_5,
        ]

        for slot in slots:
            if not is_same_user(slot, user_id):
                continue

            if isinstance(slot, dict) and slot.get("type") == role_type:
                return True
        
        for slot in row.backup:
            if not is_same_user(slot, user_id):
                continue

            if isinstance(slot, dict) and slot.get("type") == role_type:
                return True

        return False

    def get_official_keys(self, row):
        keys = set()

        for slot in [
            row.slot_1,
            row.slot_2,
            row.slot_3,
            row.slot_4,
            row.slot_5
        ]:
            if not isinstance(slot, dict):
                continue

            keys.add(
                (
                    str(slot["user_id"]),
                    slot["type"]
                )
            )

        return keys

    def is_row_full(self, row) -> bool:
        return (
            row.slot_1
            and row.slot_2
            and row.slot_3
            and row.slot_4
            and row.slot_5
        )

    def count_runners(self, row) -> int:
        slots = [
            row.slot_1,
            row.slot_2,
            row.slot_3,
            row.slot_4,
            row.slot_5
        ]

        return sum(
            1
            for slot in slots
            if self.is_runner_slot(slot)
        )

    def has_runner_in_row(self, row) -> bool:
        slots = [
            row.slot_1,
            row.slot_2,
            row.slot_3,
            row.slot_4,
            row.slot_5
        ]

        return any(
            self.is_runner_slot(slot)
            for slot in slots
        )

    def count_pushers(self, row) -> int:
        slots = [
            row.slot_1,
            row.slot_2,
            row.slot_3,
            row.slot_4,
            row.slot_5
        ]

        return sum(
            1
            for slot in slots
            if self.is_pusher_slot(slot)
        )

    def rebalance_row(self, row):
        slots = [
            row.slot_1,
            row.slot_2,
            row.slot_3,
            row.slot_4,
            row.slot_5
        ]

        runners = [
            slot
            for slot in slots
            if self.is_runner_slot(slot)
        ]

        pushers = [
            slot
            for slot in slots
            if self.is_pusher_slot(slot)
        ]

        backup_pushers = [
            slot
            for slot in row.backup
            if isinstance(slot, dict) and slot.get("type") == "pusher"
        ]

        all_pushers = pushers + backup_pushers

        all_pushers.sort(
            key=self.get_slot_rate,
            reverse=True
        )

        max_pusher_count = 5 - len(runners)

        if max_pusher_count < 0:
            max_pusher_count = 0

        active_pushers = all_pushers[:max_pusher_count]
        backup_pushers = all_pushers[max_pusher_count:]

        sorted_members = runners + active_pushers

        row.slot_1 = sorted_members[0] if len(sorted_members) > 0 else ""
        row.slot_2 = sorted_members[1] if len(sorted_members) > 1 else ""
        row.slot_3 = sorted_members[2] if len(sorted_members) > 2 else ""
        row.slot_4 = sorted_members[3] if len(sorted_members) > 3 else ""
        row.slot_5 = sorted_members[4] if len(sorted_members) > 4 else ""

        row.backup = backup_pushers

    def remove_member_from_row(self, row, user_id) -> list[str]:
        removed = []

        before_keys = self.get_official_keys(row)

        if is_same_user(row.slot_1, user_id):
            removed.append(get_slot_display(row.slot_1))
            row.slot_1 = ""

        if is_same_user(row.slot_2, user_id):
            removed.append(get_slot_display(row.slot_2))
            row.slot_2 = ""

        if is_same_user(row.slot_3, user_id):
            removed.append(get_slot_display(row.slot_3))
            row.slot_3 = ""

        if is_same_user(row.slot_4, user_id):
            removed.append(get_slot_display(row.slot_4))
            row.slot_4 = ""

        if is_same_user(row.slot_5, user_id):
            removed.append(get_slot_display(row.slot_5))
            row.slot_5 = ""

        for backup_slot in row.backup[:]:
            if is_same_user(backup_slot, user_id):
                removed.append(
                    get_slot_display(backup_slot)
                )

                row.backup.remove(backup_slot)

        self.rebalance_row(row)

        after_keys = self.get_official_keys(row)

        promoted_keys = after_keys - before_keys

        print("遞補轉正：", promoted_keys)

        promoted_slots = []

        for slot in [
            row.slot_1,
            row.slot_2,
            row.slot_3,
            row.slot_4,
            row.slot_5
        ]:
            if not isinstance(slot, dict):
                continue

            key = (
                str(slot["user_id"]),
                slot["type"]
            )

            if key in promoted_keys:
                promoted_slots.append(slot)

        print("遞補轉正資料：", promoted_slots)

        return removed, promoted_slots

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

    def normalize_time(self, time_str: str) -> str:
        if "-" not in time_str:
            return time_str

        try:
            start, end = time_str.split("-")

            start = int(start)
            end = int(end)

            return f"{start:02d}00-{end:02d}00"

        except ValueError:
            return time_str

    def expand_time_range(self, time_str: str) -> list[str]:
        if "-" not in time_str:
            return [self.normalize_time(time_str)]

        try:
            start, end = time_str.split("-")

            start = int(start)
            end = int(end)

            if end <= start:
                return [self.normalize_time(time_str)]

            times = []

            for hour in range(start, end):
                times.append(f"{hour:02d}00-{hour + 1:02d}00")

            return times

        except ValueError:
            return [self.normalize_time(time_str)]

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
                if not self.is_15_minutes_before_slot(
                    schedule,
                    row
                ):
                    continue

                if not self.needs_emergency_recruit(row):
                    continue

                print(
                    f"[緊急招募] 找到缺額："
                    f"{schedule.car} "
                    f"{schedule.date} "
                    f"{row.time} "
                    f"缺 {self.get_missing_count(row)} 人"
                )

                if self.has_emergency_recruit_been_sent(
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

                message = self.build_emergency_recruit_message(
                    schedule,
                    row
                )

                await channel.send(message)

                self.mark_emergency_recruit_sent(
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
                if not self.is_5_minutes_before_slot(
                    schedule,
                    row
                ):
                    continue

                if self.has_boarding_reminder_been_sent(
                    schedule,
                    row
                ):
                    continue

                user_ids = self.get_boarding_reminder_user_ids(
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

                channel_id = self.get_boarding_reminder_channel_id(
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

                message = self.build_boarding_reminder_message(
                    schedule,
                    row
                )

                await channel.send(message)

                self.mark_boarding_reminder_sent(
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

    @app_commands.command(
        name="報班",
        description="填入指定時間的推車手"
    )
    async def fill_schedule(
        self,
        interaction: discord.Interaction,
        car: str,
        date: str,
        time: str
    ):
        await interaction.response.defer(ephemeral=True)

        if not self.has_role(interaction, PUSHER_ROLE_ID):
            await interaction.followup.send(
                "❌ 你沒有推車手報班權限。",
                ephemeral=True
            )
            return

        period = CURRENT_PERIOD
        car = self.normalize_car(car)
        date = self.normalize_date(date)

        pusher_data = get_pusher(interaction.user.id)

        if pusher_data is None:
            await interaction.followup.send(
                "❌ 你還沒有登記推車資料。\n"
                "請先使用 `/登記推車資料` 登記名稱與倍率。",
                ephemeral=True
            )
            return

        slot_data = make_slot(
            user_id=interaction.user.id,
            name=pusher_data["name"],
            role_type="pusher",
            rate=pusher_data["rate"]
        )

        display_name = get_slot_display(slot_data)

        times = self.expand_time_range(time)

        schedule = get_schedule(period, car, date)

        if schedule is None:
            await interaction.followup.send(
                f"❌ 找不到 `{car} {date}` 的排班。",
                ephemeral=True
            )
            return

        target_rows = []

        for target_time in times:
            target_row = None

            for row in schedule.rows:
                if row.time == target_time:
                    target_row = row
                    break

            if target_row is None:
                await interaction.followup.send(
                    f"❌ 找不到時間 `{target_time}`。\n"
                    f"請使用格式例如：`21-22`、`21-24` 或 `2100-2200`",
                    ephemeral=True
                )
                return

            target_rows.append((target_time, target_row))

        for target_time, target_row in target_rows:
            if self.already_in_row(target_row, interaction.user.id, "pusher"):
                await interaction.followup.send(
                    f"❌ `{target_time}` 你已經報過班了。",
                    ephemeral=True
                )
                return

            if self.is_row_full(target_row):
                continue

        joined_times = []
        backup_times = []

        for target_time, target_row in target_rows:
            target_row.backup.append(slot_data)

            self.sort_row_by_rate(target_row)

            user_is_active = any(
                is_same_user(slot, interaction.user.id)
                and isinstance(slot, dict)
                and slot.get("type") == "pusher"
                for slot in [
                    target_row.slot_1,
                    target_row.slot_2,
                    target_row.slot_3,
                    target_row.slot_4,
                    target_row.slot_5
                ]
            )

            if user_is_active:
                joined_times.append(target_time)

            else:
                backup_times.append(target_time)

        save_schedule(schedule)

        await self.update_schedule_message(schedule)

        text = f"✅ 已更新 `{car} {date}`\n"

        if joined_times:
            text += f"正式報班：`{joined_times[0]}` ~ `{joined_times[-1]}`：`{display_name}`\n"

        if backup_times:
            text += f"候補排隊：`{backup_times[0]}` ~ `{backup_times[-1]}`：`{display_name}`"

        await interaction.followup.send(
            text,
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
        await interaction.response.defer(ephemeral=True)

        if not self.has_role(interaction, RUNNER_ROLE_ID):
            await interaction.followup.send(
                "❌ 你沒有跑者報班權限。",
                ephemeral=True
            )
            return

        period = CURRENT_PERIOD
        car = self.normalize_car(car)
        date = self.normalize_date(date)

        runner_name = interaction.user.display_name.split("/")[0].strip() + "R"

        slot_data = make_slot(
            user_id=interaction.user.id,
            name=runner_name,
            role_type="runner"
        )

        display_name = get_slot_display(slot_data)

        times = self.expand_time_range(time)

        schedule = get_schedule(period, car, date)

        if schedule is None:
            await interaction.followup.send(
                f"❌ 找不到 `{car} {date}` 的排班。",
                ephemeral=True
            )
            return

        target_rows = []

        for target_time in times:
            target_row = None

            for row in schedule.rows:
                if row.time == target_time:
                    target_row = row
                    break

            if target_row is None:
                await interaction.followup.send(
                    f"❌ 找不到時間 `{target_time}`。\n"
                    f"請使用格式例如：`21-22`、`21-24` 或 `2100-2200`",
                    ephemeral=True
                )
                return

            target_rows.append((target_time, target_row))

        for target_time, target_row in target_rows:
            if self.already_in_row(target_row, interaction.user.id, "runner"):
                await interaction.followup.send(
                    f"❌ `{target_time}` 你已經報過跑者了。",
                    ephemeral=True
                )
                return

            if self.is_row_full(target_row):
                continue

        joined_times = []

        for target_time, target_row in target_rows:
            self.fill_first_empty_slot(target_row, slot_data)

            self.sort_row_by_rate(target_row)

            joined_times.append(target_time)

        save_schedule(schedule)

        await self.update_schedule_message(schedule)

        text = f"✅ 已更新跑者 `{car} {date}`\n"
        text += f"正式報班：`{joined_times[0]}` ~ `{joined_times[-1]}`：`{display_name}`"

        await interaction.followup.send(
            text,
            ephemeral=True
        )

    @app_commands.command(
        name="砍班",
        description="取消自己指定時段或整天的報班"
    )
    async def cancel_schedule(
        self,
        interaction: discord.Interaction,
        car: str,
        date: str,
        time: str = "",
        all_day: bool = False
    ):
        await interaction.response.defer(ephemeral=True)

        period = CURRENT_PERIOD
        car = self.normalize_car(car)
        date = self.normalize_date(date)

        schedule = get_schedule(period, car, date)

        if schedule is None:
            await interaction.followup.send(
                f"❌ 找不到 `{car} {date}` 的排班。",
                ephemeral=True
            )
            return

        if all_day:
            target_rows = [
                (row.time, row)
                for row in schedule.rows
            ]
        else:
            if not time:
                await interaction.followup.send(
                    "❌ 請輸入要砍班的時間，或將 `all_day` 設為 `True`。",
                    ephemeral=True
                )
                return

            times = self.expand_time_range(time)
            target_rows = []

            for target_time in times:
                target_row = None

                for row in schedule.rows:
                    if row.time == target_time:
                        target_row = row
                        break

                if target_row is None:
                    await interaction.followup.send(
                        f"❌ 找不到時間 `{target_time}`。\n"
                        f"請使用格式例如：`21-22`、`21-24` 或 `2100-2200`",
                        ephemeral=True
                    )
                    return

                target_rows.append((target_time, target_row))

        removed_records = []
        all_promoted_slots = []

        for target_time, target_row in target_rows:
            removed_names, promoted_slots = self.remove_member_from_row(
                target_row,
                interaction.user.id
            )

            all_promoted_slots.extend(promoted_slots)

            for removed_name in removed_names:
                removed_records.append(
                    f"{target_time}：{removed_name}"
                )

        if not removed_records:
            await interaction.followup.send(
                f"⚠️ 沒有找到你在 `{car} {date}` 的報班資料。",
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

        await self.update_schedule_message(schedule)

        removed_text = "\n".join(removed_records)

        await interaction.followup.send(
            f"✅ 已取消 `{car} {date}` 的報班：\n{removed_text}",
            ephemeral=True
        )

    @app_commands.command(
        name="我的班表",
        description="查看自己目前期數的所有報班"
    )
    async def my_schedule(
        self,
        interaction: discord.Interaction
    ):
        await interaction.response.defer(ephemeral=True)

        user_id = str(interaction.user.id)

        all_data = load_all()

        records = []

        for schedule_data in all_data.values():
            schedule = dict_to_schedule(schedule_data)

            if schedule.period != CURRENT_PERIOD:
                continue

            for row in schedule.rows:
                slots = [
                    row.slot_1,
                    row.slot_2,
                    row.slot_3,
                    row.slot_4,
                    row.slot_5,
                ]

                slots.extend(row.backup)

                found = False

                for slot in slots:
                    if is_same_user(slot, user_id):
                        found = True
                        break

                if found:
                    records.append({
                        "date": schedule.date,
                        "car": schedule.car,
                        "time": row.time
                    })

        if not records:
            await interaction.followup.send(
                "你目前沒有任何報班紀錄。",
                ephemeral=True
            )
            return

        records.sort(
            key=lambda item: (
                item["date"],
                item["car"],
                item["time"]
            )
        )

        text = "📋 **我的班表**\n\n"

        current_group = None

        for record in records:
            group = f"{record['date']} {record['car']}"

            if group != current_group:
                if current_group is not None:
                    text += "\n"

                text += f"**{group}**\n"
                current_group = group

            text += f"- {record['time']}\n"

        await interaction.followup.send(
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
        car = self.normalize_car(car)
        date = self.normalize_date(date)

        schedule = get_schedule(period, car, date)

        if schedule is None:
            await interaction.followup.send(
                f"❌ 找不到 `{car} {date}` 的排班。",
                ephemeral=True
            )
            return
        
        target_time = self.expand_time_range(time)[0]

        target_row = None

        for row in schedule.rows:
            if row.time == target_time:
                target_row = row
                break

        if target_row is None:
            await interaction.followup.send(
                f"❌ 找不到時間 `{target_time}`。",
                ephemeral=True
            )
            return
            
        backups = [
            slot
            for slot in target_row.backup
            if isinstance(slot, dict)
        ]

        if not backups:
            await interaction.followup.send(
                f"📋 `{car} {date} {target_time}` 目前沒有候補。",
                ephemeral=True
            )
            return

        text = f"📋 **候補順位**\n\n"
        text += f"`{car} {date} {target_time}`\n\n"

        for index, slot in enumerate(backups, start=1):
            text += f"{index}. {slot.get('display')}\n"

        text += f"\n目前候補人數：{len(backups)}"

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
        await interaction.response.defer(ephemeral=True)

        user_id = str(interaction.user.id)
        all_data = load_all()

        pusher_hours = 0
        runner_hours = 0

        for schedule_data in all_data.values():
            schedule = dict_to_schedule(schedule_data)

            if schedule.period != CURRENT_PERIOD:
                continue

            for row in schedule.rows:
                slots = [
                    row.slot_1,
                    row.slot_2,
                    row.slot_3,
                    row.slot_4,
                    row.slot_5,
                    row.backup
                ]

                for slot in slots:
                    if not is_same_user(slot, user_id):
                        continue

                    if not isinstance(slot, dict):
                        continue

                    if slot.get("type") == "pusher":
                        pusher_hours += 1

                    elif slot.get("type") == "runner":
                        runner_hours += 1

        total_hours = pusher_hours - runner_hours

        await interaction.followup.send(
            f"📊 **{CURRENT_PERIOD}期時數統計**\n\n"
            f"推車時數：{pusher_hours}\n"
            f"跑者時數：{runner_hours}\n"
            f"結算時數：{total_hours}",
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
        await interaction.response.defer(ephemeral=True)

        user_id = str(interaction.user.id)
        all_data = load_all()

        pusher_hours = 0
        runner_hours = 0

        for schedule_data in all_data.values():
            schedule = dict_to_schedule(schedule_data)

            for row in schedule.rows:
                slots = [
                    row.slot_1,
                    row.slot_2,
                    row.slot_3,
                    row.slot_4,
                    row.slot_5,
                    row.backup
                ]

                for slot in slots:
                    if not is_same_user(slot, user_id):
                        continue

                    if not isinstance(slot, dict):
                        continue

                    if slot.get("type") == "pusher":
                        pusher_hours += 1

                    elif slot.get("type") == "runner":
                        runner_hours += 1

        total_hours = pusher_hours - runner_hours

        await interaction.followup.send(
            f"📊 **歷史時數統計**\n\n"
            f"推車時數：{pusher_hours}\n"
            f"跑者時數：{runner_hours}\n"
            f"結算時數：{total_hours}",
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
        await interaction.response.defer(ephemeral=True)

        if not self.is_schedule_admin(interaction):
            await interaction.followup.send(
                "❌ 你沒有查看當期總時數的權限。",
                ephemeral=True
            )
            return

        all_data = load_all()

        runner_hours = {}
        pusher_hours = {}

        for schedule_data in all_data.values():
            schedule = dict_to_schedule(schedule_data)

            if schedule.period != CURRENT_PERIOD:
                continue

            for row in schedule.rows:
                slots = [
                    row.slot_1,
                    row.slot_2,
                    row.slot_3,
                    row.slot_4,
                    row.slot_5,
                ]

                for slot in slots:
                    if not isinstance(slot, dict):
                        continue

                    name = slot.get("name")
                    role_type = slot.get("type")

                    if not name:
                        continue

                    if role_type == "runner":
                        runner_hours[name] = runner_hours.get(name, 0) + 1

                    elif role_type == "pusher":
                        pusher_hours[name] = pusher_hours.get(name, 0) + 1

        text = "📊 **當期累積時數統計**\n\n"

        text += "**時數結算 R**\n"

        if runner_hours:
            sorted_runners = sorted(
                runner_hours.items(),
                key=lambda item: item[1],
                reverse=True
            )

            for name, hours in sorted_runners:
                text += f"{name}    {hours}\n"
        else:
            text += "目前沒有跑者時數\n"

        text += "\n**時數結算 H**\n"

        if pusher_hours:
            sorted_pushers = sorted(
                pusher_hours.items(),
                key=lambda item: item[1],
                reverse=True
            )

            for name, hours in sorted_pushers:
                text += f"{name}    {hours}\n"
        else:
            text += "目前沒有推車時數\n"

        await interaction.followup.send(
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
        car = self.normalize_car(car)
        date = self.normalize_date(date)

        schedule = get_schedule(period, car, date)

        if schedule is None:
            await interaction.response.send_message(
                f"❌ 找不到 `{car} {date}` 的班表。",
                ephemeral=True
            )
            return

        image_path = render_schedule(schedule)

        file = discord.File(
            image_path,
            filename=image_path.name
        )

        await interaction.response.send_message(
            content=f"📅 {car} {date}",
            file=file
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
        car = self.normalize_car(car)
        date = self.normalize_date(date)

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

        recruit_rows = []

        for row in schedule.rows:
            if not self.has_runner_in_row(row):
                continue

            stats = self.analyze_recruit_slots(row)

            if stats["missing_count"] <= 0:
                continue

            recruit_rows.append(
                (
                    row.time,
                    stats["missing_count"]
                )
            )

        if not recruit_rows:
            await interaction.followup.send(
                "✅ 目前沒有需要招募的時段。",
                ephemeral=True
            )
            return
        
        recruit_message = self.build_recruit_message(
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
        car = self.normalize_car(car)
        date = self.normalize_date(date)

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
        car = self.normalize_car(car)
        date = self.normalize_date(date)

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
        car = self.normalize_car(car)
        date = self.normalize_date(date)

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

        car = self.normalize_car(car)
        date = self.normalize_date(date)

        all_data = load_all()

        target_key = None
        target_schedule = None

        for key, schedule_data in all_data.items():
            schedule = dict_to_schedule(schedule_data)

            schedule_date = self.normalize_date(schedule.date)

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
        name="登記推車資料",
        description="登記自己的倍率資料"
    )
    async def register_pusher(
        self,
        interaction: discord.Interaction,
        名稱: str,
        倍率: str
    ):
        save_pusher(
            interaction.user.id,
            名稱,
            倍率
        )

        await interaction.response.send_message(
            f"✅ 已登記推車手資料\n"
            f"名稱：{名稱}\n"
            f"倍率：{倍率}",
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
        car = self.normalize_car(car)
        date = self.normalize_date(date)
        target_time = self.expand_time_range(time)[0]

        schedule = get_schedule(period, car, date)

        if schedule is None:
            await interaction.followup.send(
                f"❌ 找不到 `{car} {date}` 的排班。",
                ephemeral=True
            )
            return

        target_row = None

        for row in schedule.rows:
            if row.time == target_time:
                target_row = row
                break

        if target_row is None:
            await interaction.followup.send(
                f"❌ 找不到時間 `{target_time}`。",
                ephemeral=True
            )
            return

        target_row.slot_1 = make_slot(
            "test_runner_1",
            "跑者A",
            "runner"
        )

        target_row.slot_2 = make_slot(
            "test_runner_2",
            "跑者B",
            "runner"
        )

        target_row.slot_3 = make_slot(
            "test_pusher_1",
            "推車A",
            "pusher",
            "4.5"
        )

        target_row.slot_4 = make_slot(
            "test_pusher_2",
            "推車B",
            "pusher",
            "4.2"
        )

        target_row.slot_5 = make_slot(
            "test_pusher_3",
            "推車C",
            "pusher",
            "4.0"
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

        self.rebalance_row(target_row)

        save_schedule(schedule)

        await self.update_schedule_message(schedule)

        await interaction.followup.send(
            f"✅ 已建立 `{car} {date} {target_time}` 的共跑測試資料。",
            ephemeral=True
        )

    @app_commands.command(
        name="測試",
        description="測試排班機器人是否正常運作"
    )
    async def test(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            "排班機器人正常運作 ✅",
            ephemeral=True
        )

async def setup(bot: commands.Bot):
    await bot.add_cog(ScheduleCog(bot))