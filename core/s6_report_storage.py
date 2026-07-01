import json
import os

from core.settings_storage import (
    get_current_period
)

S6_REPORT_FILE = "data/s6_reports.json"


def load_s6_reports():
    if not os.path.exists(S6_REPORT_FILE):
        return []

    with open(S6_REPORT_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def save_s6_reports(reports):
    os.makedirs(
        os.path.dirname(S6_REPORT_FILE),
        exist_ok=True
    )

    with open(S6_REPORT_FILE, "w", encoding="utf-8") as file:
        json.dump(
            reports,
            file,
            ensure_ascii=False,
            indent=4
        )


def add_s6_report(
    user_id,
    name,
    car,
    date,
    time,
    reported_by_user_id,
    reported_by_name,
    period=None
):
    if period is None:
        period = get_current_period()

    period = int(period)

    reports = load_s6_reports()

    report = {
        "period": period,
        "user_id": str(user_id),
        "name": name,
        "car": car,
        "date": date,
        "time": time,
        "reported_by_user_id": str(reported_by_user_id),
        "reported_by_name": reported_by_name
    }

    reports.append(report)

    save_s6_reports(reports)

    return report


def get_s6_reports(
    period=None,
    user_id=None
):
    reports = load_s6_reports()

    filtered_reports = []

    for report in reports:
        if period is not None:
            if int(report.get("period")) != int(period):
                continue

        if user_id is not None:
            if str(report.get("user_id")) != str(user_id):
                continue

        filtered_reports.append(report)

    return filtered_reports