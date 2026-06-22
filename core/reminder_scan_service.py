from config import (
    S6_REMINDER_CHANNEL_ID,
    EMERGENCY_RECRUIT_CHANNEL_IDS
)

from core.storage import load_all, dict_to_schedule

from core.boarding_reminder_service import (
    get_boarding_reminder_user_ids,
    get_boarding_reminder_channel_id,
    build_boarding_reminder_message,
    has_boarding_reminder_been_sent,
    mark_boarding_reminder_sent,
    is_5_minutes_before_slot
)

from core.s6_reminder_service import (
    get_s6_reminder_user_ids,
    has_s6_reminder_been_sent,
    mark_s6_reminder_sent,
    is_30_minutes_before_s6_slot,
    build_s6_reminder_message
)

from core.emergency_recruit_service import (
    is_15_minutes_before_slot,
    needs_emergency_recruit,
    has_emergency_recruit_been_sent,
    mark_emergency_recruit_sent,
    get_missing_count,
    build_emergency_recruit_message
)

from core.s6_reminder_view import S6ReminderView


async def send_boarding_reminder_for_row(
    bot,
    boarding_reminded,
    schedule,
    row,
    force_send: bool = False
):
    if not force_send and has_boarding_reminder_been_sent(
        boarding_reminded,
        schedule,
        row
    ):
        return False

    user_ids = get_boarding_reminder_user_ids(row)

    if not user_ids:
        print(
            f"[上車提醒] 無通知對象："
            f"{schedule.car} {schedule.date} {row.time}"
        )
        return False

    channel_id = get_boarding_reminder_channel_id(schedule)

    if channel_id is None:
        print(f"[上車提醒] 找不到對應頻道：{schedule.car}")
        return False

    channel = bot.get_channel(channel_id)

    if channel is None:
        channel = await bot.fetch_channel(channel_id)

    message = build_boarding_reminder_message(
        schedule,
        row,
        user_ids
    )

    await channel.send(message)

    mark_boarding_reminder_sent(
        boarding_reminded,
        schedule,
        row
    )

    print(
        f"[上車提醒] 已發送："
        f"{schedule.car} {schedule.date} {row.time}"
    )

    return True


async def run_boarding_reminder_scan(
    bot,
    boarding_reminded
):
    print("[上車提醒] 開始掃描")

    try:
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
                try:
                    if not is_5_minutes_before_slot(
                        schedule,
                        row
                    ):
                        continue

                    await send_boarding_reminder_for_row(
                        bot,
                        boarding_reminded,
                        schedule,
                        row
                    )

                except Exception as e:
                    print(
                        f"[上車提醒] 單一時段掃描失敗："
                        f"{schedule.car} {schedule.date} {row.time} "
                        f"{repr(e)}"
                    )

    except Exception as e:
        print(f"[上車提醒] 掃描失敗：{repr(e)}")


async def send_s6_reminder_for_row(
    bot,
    s6_reminded,
    schedule,
    row,
    force_send: bool = False
):
    if not force_send and has_s6_reminder_been_sent(
        s6_reminded,
        schedule,
        row
    ):
        return False

    user_ids = get_s6_reminder_user_ids(row)

    if not user_ids:
        print(
            f"[S6提醒] 無通知對象："
            f"{schedule.car} {schedule.date} {row.time}"
        )
        return False

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

    channel = bot.get_channel(S6_REMINDER_CHANNEL_ID)

    if channel is None:
        channel = await bot.fetch_channel(S6_REMINDER_CHANNEL_ID)

    view = S6ReminderView(
        bot,
        schedule,
        row
    )

    await channel.send(
        message,
        view=view
    )

    mark_s6_reminder_sent(
        s6_reminded,
        schedule,
        row
    )

    print(
        f"[S6提醒] 已發送："
        f"{schedule.car} {schedule.date} {row.time}"
    )

    return True


async def run_s6_reminder_scan(
    bot,
    s6_reminded
):
    print("[S6提醒] 開始掃描")

    try:
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
                try:
                    if not is_30_minutes_before_s6_slot(
                        schedule,
                        row
                    ):
                        continue

                    await send_s6_reminder_for_row(
                        bot,
                        s6_reminded,
                        schedule,
                        row
                    )

                except Exception as e:
                    print(
                        f"[S6提醒] 單一時段掃描失敗："
                        f"{schedule.car} {schedule.date} {row.time} "
                        f"{repr(e)}"
                    )

    except Exception as e:
        print(f"[S6提醒] 掃描失敗：{repr(e)}")


async def send_emergency_recruit_for_row(
    bot,
    emergency_recruited,
    schedule,
    row,
    force_send: bool = False
):
    if not needs_emergency_recruit(row):
        print(
            f"[緊急招募] 不符合缺額條件："
            f"{schedule.car} {schedule.date} {row.time}"
        )
        return False

    if not force_send and has_emergency_recruit_been_sent(
        emergency_recruited,
        schedule,
        row
    ):
        return False

    print(
        f"[緊急招募] 找到缺額："
        f"{schedule.car} "
        f"{schedule.date} "
        f"{row.time} "
        f"缺 {get_missing_count(row)} 人"
    )

    channel_id = EMERGENCY_RECRUIT_CHANNEL_IDS.get(schedule.car)

    if channel_id is None:
        print(f"[緊急招募] 找不到對應頻道：{schedule.car}")
        return False

    channel = bot.get_channel(channel_id)

    if channel is None:
        channel = await bot.fetch_channel(channel_id)

    message = build_emergency_recruit_message(
        schedule,
        row
    )

    await channel.send(message)

    mark_emergency_recruit_sent(
        emergency_recruited,
        schedule,
        row
    )

    print(
        f"[緊急招募] 已發送："
        f"{schedule.car} {schedule.date} {row.time}"
    )

    return True


async def run_emergency_recruit_scan(
    bot,
    emergency_recruited
):
    print("[緊急招募] 開始掃描")

    try:
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
                try:
                    if not is_15_minutes_before_slot(
                        schedule,
                        row
                    ):
                        continue

                    await send_emergency_recruit_for_row(
                        bot,
                        emergency_recruited,
                        schedule,
                        row
                    )

                except Exception as e:
                    print(
                        f"[緊急招募] 單一時段掃描失敗："
                        f"{schedule.car} {schedule.date} {row.time} "
                        f"{repr(e)}"
                    )

    except Exception as e:
        print(f"[緊急招募] 掃描失敗：{repr(e)}")