# -*- coding: utf-8 -*-
"""用户表（sys_user）数据访问。"""
from __future__ import annotations

from app.dao.base import execute_dml, fetch_all, fetch_one, fetch_value

_COLUMNS = (
    "id, username, password_hash, role, real_name, phone, student_no, dorm_no, "
    "worker_no, skill, is_active, created_at, last_login_at"
)


def create_user(
    *,
    username: str,
    password_hash: str,
    role: str,
    real_name: str,
    phone: str | None = None,
    student_no: str | None = None,
    dorm_no: str | None = None,
    worker_no: str | None = None,
    skill: str | None = None,
    cur=None,
) -> int:
    sql = """
        INSERT INTO sys_user
            (username, password_hash, role, real_name, phone,
             student_no, dorm_no, worker_no, skill)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    args = (username, password_hash, role, real_name, phone,
            student_no, dorm_no, worker_no, skill)
    return execute_dml(sql, args, cur)


def get_by_id(user_id: int, cur=None) -> dict | None:
    return fetch_one(f"SELECT {_COLUMNS} FROM sys_user WHERE id = %s", (user_id,), cur)


def get_by_username(username: str, cur=None) -> dict | None:
    return fetch_one(
        f"SELECT {_COLUMNS} FROM sys_user WHERE username = %s", (username,), cur
    )


def exists_username(username: str, exclude_id: int | None = None, cur=None) -> bool:
    sql = "SELECT COUNT(*) AS c FROM sys_user WHERE username = %s"
    args: list = [username]
    if exclude_id:
        sql += " AND id <> %s"
        args.append(exclude_id)
    return fetch_value(sql, tuple(args), cur, 0) > 0


def exists_field(field: str, value: str, exclude_id: int | None = None, cur=None) -> bool:
    """通用唯一性判断（用于学号 / 工号）。field 仅允许内部传入固定列名。"""
    if field not in {"student_no", "worker_no"}:
        raise ValueError("非法的唯一字段")
    sql = f"SELECT COUNT(*) AS c FROM sys_user WHERE {field} = %s"
    args: list = [value]
    if exclude_id:
        sql += " AND id <> %s"
        args.append(exclude_id)
    return fetch_value(sql, tuple(args), cur, 0) > 0


def _filter_sql(role: str | None, keyword: str | None) -> tuple[str, list]:
    where, args = [], []
    if role:
        where.append("role = %s")
        args.append(role)
    if keyword:
        like = f"%{keyword}%"
        where.append(
            "(username LIKE %s OR real_name LIKE %s OR phone LIKE %s "
            "OR student_no LIKE %s OR worker_no LIKE %s)"
        )
        args.extend([like] * 5)
    return (" WHERE " + " AND ".join(where)) if where else "", args


def list_users(
    role: str | None = None,
    keyword: str | None = None,
    offset: int = 0,
    limit: int = 10,
    cur=None,
) -> list[dict]:
    where, args = _filter_sql(role, keyword)
    sql = f"""
        SELECT {_COLUMNS} FROM sys_user
        {where}
        ORDER BY id DESC
        LIMIT %s OFFSET %s
    """
    return fetch_all(sql, tuple(args + [limit, offset]), cur)


def count_users(role: str | None = None, keyword: str | None = None, cur=None) -> int:
    where, args = _filter_sql(role, keyword)
    return fetch_value(f"SELECT COUNT(*) AS c FROM sys_user {where}", tuple(args), cur, 0)


def update_last_login(user_id: int, cur=None) -> None:
    execute_dml(
        "UPDATE sys_user SET last_login_at = NOW() WHERE id = %s", (user_id,), cur
    )


def update_password(user_id: int, password_hash: str, cur=None) -> int:
    return execute_dml(
        "UPDATE sys_user SET password_hash = %s WHERE id = %s",
        (password_hash, user_id),
        cur,
    )


def update_profile(
    user_id: int, real_name: str, phone: str | None, dorm_no: str | None, cur=None
) -> int:
    return execute_dml(
        "UPDATE sys_user SET real_name = %s, phone = %s, dorm_no = %s WHERE id = %s",
        (real_name, phone, dorm_no, user_id),
        cur,
    )


def delete_user(user_id: int, cur=None) -> int:
    return execute_dml("DELETE FROM sys_user WHERE id = %s", (user_id,), cur)


def count_orders_for_user(user_id: int, cur=None) -> int:
    """统计与该用户相关的工单数量：删除用户前的关联校验。"""
    sql = """
        SELECT COUNT(*) AS c FROM repair_order
        WHERE student_id = %s OR worker_id = %s
    """
    return fetch_value(sql, (user_id, user_id), cur, 0)
