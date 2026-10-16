# -*- coding: utf-8 -*-
"""管理员数据统计相关查询。

统计口径统一排除被逻辑删除的工单（is_deleted = 1）。
"""
from __future__ import annotations

from app.dao.base import fetch_all, fetch_value


def total_orders(keyword_days: int | None = None) -> int:
    sql = "SELECT COUNT(*) AS c FROM repair_order WHERE is_deleted = 0"
    args: tuple = ()
    if keyword_days:
        sql += " AND created_at >= DATE_SUB(NOW(), INTERVAL %s DAY)"
        args = (keyword_days,)
    return fetch_value(sql, args, None, 0)


def count_by_status() -> dict:
    rows = fetch_all(
        "SELECT status, COUNT(*) AS c FROM repair_order "
        "WHERE is_deleted = 0 GROUP BY status"
    )
    return {row["status"]: row["c"] for row in rows}


def count_by_category() -> list[dict]:
    sql = """
        SELECT c.name AS category_name,
               COUNT(o.id) AS total,
               SUM(o.status = 'completed') AS completed,
               ROUND(AVG(r.score), 1) AS avg_score
        FROM fault_category c
        LEFT JOIN repair_order o ON o.category_id = c.id AND o.is_deleted = 0
        LEFT JOIN repair_review r ON r.order_id = o.id
        GROUP BY c.id, c.name, c.sort_order
        ORDER BY total DESC, c.sort_order ASC
    """
    return fetch_all(sql)


def count_by_building() -> list[dict]:
    sql = """
        SELECT building,
               COUNT(*) AS total,
               SUM(status = 'completed') AS completed,
               SUM(status <> 'completed') AS unfinished
        FROM repair_order
        WHERE is_deleted = 0
        GROUP BY building
        ORDER BY total DESC
    """
    return fetch_all(sql)


def monthly_trend(months: int = 6) -> list[dict]:
    """近 N 个月每月新增工单数与完成数。"""
    sql = """
        SELECT DATE_FORMAT(created_at, '%%Y-%%m') AS ym,
               COUNT(*) AS total,
               SUM(status = 'completed') AS completed
        FROM repair_order
        WHERE is_deleted = 0
          AND created_at >= DATE_SUB(DATE_FORMAT(NOW(), '%%Y-%%m-01'), INTERVAL %s MONTH)
        GROUP BY ym
        ORDER BY ym ASC
    """
    return fetch_all(sql, (months - 1,))


def average_score() -> float:
    value = fetch_value("SELECT ROUND(AVG(score), 2) AS s FROM repair_review", default=0)
    return float(value or 0)


def average_duration_hours() -> float:
    """从接单到完成的平均耗时（小时）。"""
    sql = """
        SELECT ROUND(AVG(TIMESTAMPDIFF(MINUTE, accepted_at, completed_at)) / 60, 1) AS h
        FROM repair_order
        WHERE is_deleted = 0 AND accepted_at IS NOT NULL AND completed_at IS NOT NULL
    """
    return float(fetch_value(sql, default=0) or 0)


def worker_ranking() -> list[dict]:
    """维修工工作量与评分排名。"""
    sql = """
        SELECT u.id, u.real_name, u.username, IFNULL(u.skill, '-') AS skill,
               IFNULL(t.total_count, 0) AS total_count,
               IFNULL(t.completed_count, 0) AS completed_count,
               IFNULL(t.processing_count, 0) AS processing_count,
               IFNULL(s.avg_score, 0) AS avg_score
        FROM sys_user u
        LEFT JOIN (
            SELECT worker_id,
                   COUNT(*) AS total_count,
                   SUM(status = 'completed') AS completed_count,
                   SUM(status = 'processing') AS processing_count
            FROM repair_order
            WHERE is_deleted = 0 AND worker_id IS NOT NULL
            GROUP BY worker_id
        ) t ON t.worker_id = u.id
        LEFT JOIN (
            SELECT o.worker_id, ROUND(AVG(r.score), 1) AS avg_score
            FROM repair_review r
            JOIN repair_order o ON o.id = r.order_id
            GROUP BY o.worker_id
        ) s ON s.worker_id = u.id
        WHERE u.role = 'worker'
        ORDER BY completed_count DESC, total_count DESC, u.id ASC
    """
    return fetch_all(sql)


def count_users_by_role() -> dict:
    rows = fetch_all("SELECT role, COUNT(*) AS c FROM sys_user GROUP BY role")
    return {row["role"]: row["c"] for row in rows}


def score_distribution() -> list[dict]:
    rows = fetch_all(
        "SELECT score, COUNT(*) AS c FROM repair_review GROUP BY score ORDER BY score"
    )
    return rows


def recent_orders(limit: int = 8) -> list[dict]:
    sql = """
        SELECT o.id, o.order_no, o.status, o.created_at, o.building, o.dorm_no,
               c.name AS category_name, s.real_name AS student_name,
               IFNULL(w.real_name, '-') AS worker_name
        FROM repair_order o
        JOIN sys_user s ON s.id = o.student_id
        JOIN fault_category c ON c.id = o.category_id
        LEFT JOIN sys_user w ON w.id = o.worker_id
        WHERE o.is_deleted = 0
        ORDER BY o.id DESC
        LIMIT %s
    """
    return fetch_all(sql, (limit,))
