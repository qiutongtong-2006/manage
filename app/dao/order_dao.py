# -*- coding: utf-8 -*-
"""报修工单表（repair_order）及其关联表（order_image / order_log）的数据访问。"""
from __future__ import annotations

from app.constants import ORDER_STATUSES, STATUS_COMPLETED, STATUS_PENDING
from app.dao.base import execute_dml, fetch_all, fetch_one, fetch_value

# 工单详情查询：一次性带出学生、维修工、类别、评价信息，列表与详情页共用
_DETAIL_SELECT = """
    SELECT o.id, o.order_no, o.student_id, o.worker_id, o.category_id,
           o.building, o.dorm_no, o.description, o.phone, o.status,
           o.created_at, o.accepted_at, o.completed_at, o.updated_at, o.is_deleted,
           c.name AS category_name,
           s.real_name AS student_name, s.student_no, s.username AS student_username,
           w.real_name AS worker_name, w.phone AS worker_phone,
           w.username AS worker_username, w.skill AS worker_skill,
           r.score, r.content AS review_content, r.created_at AS review_time
    FROM repair_order o
    JOIN sys_user s        ON s.id = o.student_id
    JOIN fault_category c  ON c.id = o.category_id
    LEFT JOIN sys_user w   ON w.id = o.worker_id
    LEFT JOIN repair_review r ON r.order_id = o.id
"""


def _build_filters(
    keyword: str | None = None,
    status: str | None = None,
    category_id: int | None = None,
    building: str | None = None,
    worker_id: int | None = None,
    student_id: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    deleted: str = "active",
) -> tuple[str, list]:
    """拼装动态查询条件。deleted 取值：active(未删除) / deleted(已删除) / all。"""
    where: list[str] = []
    args: list = []

    if deleted == "active":
        where.append("o.is_deleted = 0")
    elif deleted == "deleted":
        where.append("o.is_deleted = 1")

    if status in ORDER_STATUSES:
        where.append("o.status = %s")
        args.append(status)
    if category_id:
        where.append("o.category_id = %s")
        args.append(category_id)
    if building:
        where.append("o.building = %s")
        args.append(building)
    if worker_id:
        where.append("o.worker_id = %s")
        args.append(worker_id)
    if student_id:
        where.append("o.student_id = %s")
        args.append(student_id)
    if date_from:
        where.append("o.created_at >= %s")
        args.append(f"{date_from} 00:00:00")
    if date_to:
        where.append("o.created_at <= %s")
        args.append(f"{date_to} 23:59:59")
    if keyword:
        like = f"%{keyword}%"
        where.append(
            "(o.order_no LIKE %s OR o.dorm_no LIKE %s OR o.building LIKE %s "
            "OR o.description LIKE %s OR o.phone LIKE %s "
            "OR s.real_name LIKE %s OR s.student_no LIKE %s OR s.username LIKE %s)"
        )
        args.extend([like] * 8)

    clause = (" WHERE " + " AND ".join(where)) if where else ""
    return clause, args


# ------------------------------------------------------------------ 写入相关
def create_order(
    *,
    order_no: str,
    student_id: int,
    category_id: int,
    building: str,
    dorm_no: str,
    description: str,
    phone: str,
    cur=None,
) -> int:
    sql = """
        INSERT INTO repair_order
            (order_no, student_id, category_id, building, dorm_no, description, phone, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """
    args = (order_no, student_id, category_id, building, dorm_no,
            description, phone, STATUS_PENDING)
    return execute_dml(sql, args, cur)


def add_images(order_id: int, paths: list[str], cur=None) -> None:
    for path in paths:
        execute_dml(
            "INSERT INTO order_image (order_id, file_path) VALUES (%s, %s)",
            (order_id, path),
            cur,
        )


def add_log(
    order_id: int,
    *,
    operator_id: int | None,
    action: str,
    status: str | None = None,
    remark: str | None = None,
    cur=None,
) -> int:
    sql = """
        INSERT INTO order_log (order_id, operator_id, action, status, remark)
        VALUES (%s, %s, %s, %s, %s)
    """
    return execute_dml(
        sql, (order_id, operator_id, action, status, remark), cur
    )


def accept_order(order_id: int, worker_id: int, cur=None) -> int:
    """接单：仅当工单仍未受理且未被删除时才会更新成功（返回影响行数）。"""
    sql = """
        UPDATE repair_order
        SET worker_id = %s, status = 'processing', accepted_at = NOW()
        WHERE id = %s AND status = 'pending' AND is_deleted = 0
    """
    return execute_dml(sql, (worker_id, order_id), cur)


def update_status(order_id: int, status: str, worker_id: int, cur=None) -> int:
    """更新维修状态：状态变为已完成时写入完成时间。"""
    if status == STATUS_COMPLETED:
        sql = """
            UPDATE repair_order
            SET status = %s, completed_at = NOW(), worker_id = %s
            WHERE id = %s AND is_deleted = 0
        """
    else:
        sql = """
            UPDATE repair_order
            SET status = %s, worker_id = %s
            WHERE id = %s AND is_deleted = 0
        """
    return execute_dml(sql, (status, worker_id, order_id), cur)


def soft_delete(order_id: int, cur=None) -> int:
    """逻辑删除（标记 is_deleted=1），保留历史数据以便统计。"""
    return execute_dml(
        "UPDATE repair_order SET is_deleted = 1 WHERE id = %s", (order_id,), cur
    )


def restore(order_id: int, cur=None) -> int:
    return execute_dml(
        "UPDATE repair_order SET is_deleted = 0 WHERE id = %s", (order_id,), cur
    )


# ------------------------------------------------------------------ 查询相关
def get_detail(order_id: int, cur=None) -> dict | None:
    return fetch_one(_DETAIL_SELECT + " WHERE o.id = %s", (order_id,), cur)


def get_images(order_id: int, cur=None) -> list[dict]:
    return fetch_all(
        "SELECT id, file_path FROM order_image WHERE order_id = %s ORDER BY id",
        (order_id,),
        cur,
    )


def get_logs(order_id: int, cur=None) -> list[dict]:
    sql = """
        SELECT l.id, l.action, l.status, l.remark, l.created_at,
               u.real_name AS operator_name, u.role AS operator_role
        FROM order_log l
        LEFT JOIN sys_user u ON u.id = l.operator_id
        WHERE l.order_id = %s
        ORDER BY l.id ASC
    """
    return fetch_all(sql, (order_id,), cur)


def list_orders(
    *,
    offset: int = 0,
    limit: int = 10,
    order_by: str = "o.created_at DESC",
    **filters,
) -> list[dict]:
    where, args = _build_filters(**filters)
    sql = f"{_DETAIL_SELECT} {where} ORDER BY {order_by} LIMIT %s OFFSET %s"
    return fetch_all(sql, tuple(args + [limit, offset]))


def count_orders(**filters) -> int:
    where, args = _build_filters(**filters)
    sql = f"""
        SELECT COUNT(*) AS c
        FROM repair_order o
        JOIN sys_user s ON s.id = o.student_id
        {where}
    """
    return fetch_value(sql, tuple(args), None, 0)


def count_by_status_for_student(student_id: int) -> dict:
    """学生的个人统计：各状态工单数。"""
    sql = """
        SELECT status, COUNT(*) AS c
        FROM repair_order
        WHERE student_id = %s AND is_deleted = 0
        GROUP BY status
    """
    rows = fetch_all(sql, (student_id,))
    return {row["status"]: row["c"] for row in rows}


def count_by_status_for_worker(worker_id: int) -> dict:
    sql = """
        SELECT status, COUNT(*) AS c
        FROM repair_order
        WHERE worker_id = %s AND is_deleted = 0
        GROUP BY status
    """
    rows = fetch_all(sql, (worker_id,))
    return {row["status"]: row["c"] for row in rows}
