# -*- coding: utf-8 -*-
"""统计业务：为管理员数据看板准备图表数据。"""
from __future__ import annotations

from datetime import date

from flask import current_app

from app.constants import (
    ORDER_STATUS_LABEL,
    STATUS_COMPLETED,
    STATUS_PENDING,
    STATUS_PROCESSING,
)
from app.dao import stats_dao


def _recent_months(months: int) -> list[str]:
    """返回最近 N 个月的 'YYYY-MM' 列表（从早到晚，含当月）。"""
    today = date.today()
    result: list[str] = []
    year, month = today.year, today.month
    for _ in range(months):
        result.append(f"{year:04d}-{month:02d}")
        month -= 1
        if month == 0:
            month = 12
            year -= 1
    return list(reversed(result))


def admin_dashboard() -> dict:
    """管理员首页 / 统计页所需的全部指标。"""
    months = current_app.config.get("STAT_MONTHS", 6)
    status_counts = stats_dao.count_by_status()
    total = stats_dao.total_orders()

    status_list = []
    for status in (STATUS_PENDING, STATUS_PROCESSING, STATUS_COMPLETED):
        count = status_counts.get(status, 0)
        status_list.append(
            {
                "status": status,
                "label": ORDER_STATUS_LABEL[status],
                "count": count,
                "percent": round(count * 100 / total, 1) if total else 0.0,
            }
        )

    # 近 N 个月趋势：SQL 只返回有数据的月份，这里补齐空缺月份便于画折线图
    raw_trend = {row["ym"]: row for row in stats_dao.monthly_trend(months)}
    trend = []
    for ym in _recent_months(months):
        row = raw_trend.get(ym)
        trend.append(
            {
                "ym": ym,
                "label": ym[5:] + "月",
                "total": int(row["total"]) if row else 0,
                "completed": int(row["completed"] or 0) if row else 0,
            }
        )

    categories = stats_dao.count_by_category()
    max_category = max([c["total"] or 0 for c in categories], default=0) or 1
    for item in categories:
        item["total"] = int(item["total"] or 0)
        item["completed"] = int(item["completed"] or 0)
        item["percent"] = round(item["total"] * 100 / max_category, 1)

    buildings = stats_dao.count_by_building()
    max_building = max([b["total"] or 0 for b in buildings], default=0) or 1
    for item in buildings:
        item["total"] = int(item["total"] or 0)
        item["completed"] = int(item["completed"] or 0)
        item["unfinished"] = int(item["unfinished"] or 0)
        item["percent"] = round(item["total"] * 100 / max_building, 1)

    scores = {row["score"]: row["c"] for row in stats_dao.score_distribution()}

    return {
        "total": total,
        "status_list": status_list,
        "pending": status_counts.get(STATUS_PENDING, 0),
        "processing": status_counts.get(STATUS_PROCESSING, 0),
        "completed": status_counts.get(STATUS_COMPLETED, 0),
        "reviewed": sum(scores.values()),
        "avg_score": stats_dao.average_score(),
        "avg_duration": stats_dao.average_duration_hours(),
        "trend": trend,
        "categories": categories,
        "buildings": buildings,
        "workers": stats_dao.worker_ranking(),
        "user_counts": stats_dao.count_users_by_role(),
        "recent_orders": stats_dao.recent_orders(8),
        "scores": scores,
    }
