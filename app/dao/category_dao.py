# -*- coding: utf-8 -*-
"""故障类别表（fault_category）数据访问。"""
from __future__ import annotations

from app.dao.base import execute_dml, fetch_all, fetch_one, fetch_value


def list_categories(only_active: bool = True, cur=None) -> list[dict]:
    sql = "SELECT id, name, sort_order, is_active FROM fault_category"
    if only_active:
        sql += " WHERE is_active = 1"
    sql += " ORDER BY sort_order ASC, id ASC"
    return fetch_all(sql, (), cur)


def get_category(category_id: int, cur=None) -> dict | None:
    return fetch_one(
        "SELECT id, name, is_active FROM fault_category WHERE id = %s",
        (category_id,),
        cur,
    )


def exists_name(name: str, cur=None) -> bool:
    return fetch_value(
        "SELECT COUNT(*) AS c FROM fault_category WHERE name = %s", (name,), cur, 0
    ) > 0


def create_category(name: str, sort_order: int = 0, cur=None) -> int:
    return execute_dml(
        "INSERT INTO fault_category (name, sort_order) VALUES (%s, %s)",
        (name, sort_order),
        cur,
    )


def count_orders(category_id: int, cur=None) -> int:
    return fetch_value(
        "SELECT COUNT(*) AS c FROM repair_order WHERE category_id = %s",
        (category_id,),
        cur,
        0,
    )
