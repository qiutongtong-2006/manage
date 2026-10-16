# -*- coding: utf-8 -*-
"""DAO 公共执行入口。

每个 DAO 函数都可以接收一个可选的事务游标 cur：
- 传入 cur 时，SQL 会在调用方开启的事务中执行（多条写操作需要原子性时使用）；
- 不传 cur 时，走 app.utils.db 的请求级连接（单条 SQL 场景）。
这样既保证分层清晰，又避免为了事务把所有方法写两遍。
"""
from __future__ import annotations

from app.utils import db


def fetch_all(sql: str, args: tuple | list = (), cur=None) -> list[dict]:
    if cur is not None:
        cur.execute(sql, args if args else None)
        return list(cur.fetchall())
    return db.query_all(sql, args)


def fetch_one(sql: str, args: tuple | list = (), cur=None) -> dict | None:
    if cur is not None:
        cur.execute(sql, args if args else None)
        return cur.fetchone()
    return db.query_one(sql, args)


def fetch_value(sql: str, args: tuple | list = (), cur=None, default=None):
    row = fetch_one(sql, args, cur)
    if not row:
        return default
    value = next(iter(row.values()))
    return default if value is None else value


def execute_dml(sql: str, args: tuple | list = (), cur=None) -> int:
    """执行写操作：INSERT 返回自增 id，UPDATE / DELETE 返回影响行数。"""
    if cur is not None:
        cur.execute(sql, args if args else None)
        return cur.lastrowid or cur.rowcount
    return db.execute(sql, args)
