# -*- coding: utf-8 -*-
"""数据库访问基础设施：基于 PyMySQL 的请求级连接 + 事务上下文管理器。

设计要点：
1. 每个 HTTP 请求复用同一个连接（存放在 flask.g），请求结束由
   teardown_appcontext 自动关闭，避免连接泄漏。
2. 连接默认 autocommit，读操作无需关心事务；需要保证多条 SQL 一起成功或
   一起失败时，使用 transaction() 上下文管理器显式开启事务。
3. 查询统一返回 dict（字段名 -> 值），模板里可直接用点号访问。
"""
from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Any, Iterator

import pymysql
from flask import current_app, g
from pymysql.cursors import DictCursor

from app.exceptions import DatabaseError

logger = logging.getLogger(__name__)


def _connect(with_db: bool = True) -> pymysql.connections.Connection:
    """按应用配置创建一条 MySQL 连接。"""
    cfg = current_app.config
    params: dict[str, Any] = {
        "host": cfg["MYSQL_HOST"],
        "port": cfg["MYSQL_PORT"],
        "user": cfg["MYSQL_USER"],
        "password": cfg["MYSQL_PASSWORD"],
        "charset": cfg["MYSQL_CHARSET"],
        "cursorclass": DictCursor,
        "autocommit": True,
        "connect_timeout": 5,
    }
    if with_db:
        params["database"] = cfg["MYSQL_DB"]
    try:
        return pymysql.connect(**params)
    except pymysql.MySQLError as exc:
        logger.error("MySQL 连接失败: %s", exc)
        raise DatabaseError(
            "无法连接数据库，请检查 config.py 中的 MySQL 配置以及服务是否已启动"
        ) from exc


def get_connection() -> pymysql.connections.Connection:
    """获取当前请求的数据库连接（惰性创建）。"""
    if "db_conn" not in g:
        g.db_conn = _connect()
    conn = g.db_conn
    try:
        # 连接可能被服务端 wait_timeout 断开，这里做一次存活检测
        conn.ping(reconnect=True)
    except pymysql.MySQLError as exc:
        logger.warning("数据库连接已失效，重新建立: %s", exc)
        g.db_conn = _connect()
        conn = g.db_conn
    return conn


def close_connection(exc: BaseException | None = None) -> None:
    """请求结束时关闭连接（注册到 app.teardown_appcontext）。"""
    conn = g.pop("db_conn", None)
    if conn is not None:
        try:
            conn.close()
        except Exception:
            pass


def init_app(app) -> None:
    """把数据库连接的生命周期挂到 Flask 应用上。"""
    app.teardown_appcontext(close_connection)


def _normalize_args(args: tuple | list | None):
    """把空参数规范化为 None。

    PyMySQL 只要 args 不为 None 就会对 SQL 做 % 格式化，因此空元组会让 SQL 里的
    字面量 % （例如 LIKE 'worker%'）被误当作占位符。统一转成 None 可以避免踩坑。
    """
    return args if args else None


def query_all(sql: str, args: tuple | list = ()) -> list[dict]:
    """执行查询并返回全部结果。"""
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute(sql, _normalize_args(args))
        return list(cur.fetchall())


def query_one(sql: str, args: tuple | list = ()) -> dict | None:
    """执行查询并返回第一行，没有数据返回 None。"""
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute(sql, _normalize_args(args))
        return cur.fetchone()


def query_value(sql: str, args: tuple | list = (), default: Any = None) -> Any:
    """执行查询并返回第一行第一列（常用于 count / sum 聚合）。"""
    row = query_one(sql, args)
    if not row:
        return default
    value = next(iter(row.values()))
    return default if value is None else value


def execute(sql: str, args: tuple | list = ()) -> int:
    """执行写操作，返回自增主键（INSERT）或受影响行数（UPDATE / DELETE）。"""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            affected = cur.execute(sql, _normalize_args(args))
            last_id = cur.lastrowid
        return last_id if last_id else affected
    except pymysql.MySQLError as exc:
        logger.error("SQL 执行失败: %s | SQL=%s | args=%s", exc, sql, args)
        raise DatabaseError("数据库操作失败，请稍后重试") from exc


@contextmanager
def transaction() -> Iterator[DictCursor]:
    """显式事务上下文：块内出现任意异常都会回滚。

    典型用法（提交工单：写主表 + 写图片表 + 写日志，要么全成功要么全失败）：

        with transaction() as cur:
            cur.execute("INSERT INTO repair_order(...) VALUES(...)", args)
            order_id = cur.lastrowid
            cur.executemany("INSERT INTO order_image(...) VALUES(%s,%s)", rows)
    """
    conn = get_connection()
    conn.begin()
    cursor = conn.cursor()
    try:
        yield cursor
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
