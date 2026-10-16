# -*- coding: utf-8 -*-
"""评价表（repair_review）数据访问。"""
from __future__ import annotations

from app.dao.base import execute_dml, fetch_all, fetch_one, fetch_value


def create_review(
    *, order_id: int, student_id: int, score: int, content: str | None, cur=None
) -> int:
    sql = """
        INSERT INTO repair_review (order_id, student_id, score, content)
        VALUES (%s, %s, %s, %s)
    """
    return execute_dml(sql, (order_id, student_id, score, content), cur)


def get_by_order(order_id: int, cur=None) -> dict | None:
    return fetch_one(
        "SELECT id, order_id, student_id, score, content, created_at "
        "FROM repair_review WHERE order_id = %s",
        (order_id,),
        cur,
    )


def list_by_worker(worker_id: int, limit: int = 20, cur=None) -> list[dict]:
    """某个维修工收到的评价列表。"""
    sql = """
        SELECT r.id, r.score, r.content, r.created_at,
               o.order_no, o.building, o.dorm_no, c.name AS category_name,
               s.real_name AS student_name
        FROM repair_review r
        JOIN repair_order o ON o.id = r.order_id
        JOIN fault_category c ON c.id = o.category_id
        JOIN sys_user s ON s.id = r.student_id
        WHERE o.worker_id = %s
        ORDER BY r.id DESC
        LIMIT %s
    """
    return fetch_all(sql, (worker_id, limit), cur)


def average_score_for_worker(worker_id: int, cur=None) -> float:
    sql = """
        SELECT ROUND(AVG(r.score), 1) AS avg_score
        FROM repair_review r
        JOIN repair_order o ON o.id = r.order_id
        WHERE o.worker_id = %s
    """
    return fetch_value(sql, (worker_id,), cur, 0) or 0


def list_recent(keyword: str | None = None, limit: int = 100, cur=None) -> list[dict]:
    """全部评价列表（管理端使用），可按工单号 / 学生 / 维修工搜索。"""
    where, args = "", []
    if keyword:
        like = f"%{keyword}%"
        where = (
            " WHERE o.order_no LIKE %s OR s.real_name LIKE %s "
            "OR w.real_name LIKE %s OR r.content LIKE %s"
        )
        args = [like] * 4
    sql = f"""
        SELECT r.id, r.score, r.content, r.created_at,
               o.id AS order_id, o.order_no, o.building, o.dorm_no,
               c.name AS category_name,
               s.real_name AS student_name,
               IFNULL(w.real_name, '-') AS worker_name
        FROM repair_review r
        JOIN repair_order o ON o.id = r.order_id
        JOIN fault_category c ON c.id = o.category_id
        JOIN sys_user s ON s.id = r.student_id
        LEFT JOIN sys_user w ON w.id = o.worker_id
        {where}
        ORDER BY r.id DESC
        LIMIT %s
    """
    return fetch_all(sql, tuple(args + [limit]), cur)
