# -*- coding: utf-8 -*-
"""数据库初始化脚本：一键完成建库、建表、写入演示数据。

使用方式::

    python init_db.py            # 首次初始化，已存在的表不会被重建
    python init_db.py --reset    # 删除全部业务表后重建（清空数据，谨慎使用）
    python init_db.py --host 127.0.0.1 --user root --password 你的密码

脚本读取 config.py 中的 MySQL 配置（也可用命令行参数或 .env 覆盖）。
"""
from __future__ import annotations

import argparse
import os
import re
import sys

import pymysql

from config import Config

SCHEMA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sql", "schema.sql")

# 禁止被当作 --reset 目标删除的系统库
PROTECTED_SCHEMAS = {"mysql", "sys", "information_schema", "performance_schema"}


def split_sql_statements(sql_text: str) -> list[str]:
    """把 schema.sql 拆成单条可执行语句：去掉 -- 注释行，按分号切分。"""
    cleaned_lines = []
    for line in sql_text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("--"):
            continue
        cleaned_lines.append(line)
    statements = []
    for chunk in "\n".join(cleaned_lines).split(";"):
        statement = chunk.strip()
        if statement:
            statements.append(statement)
    return statements


def connect(host: str, port: int, user: str, password: str, database: str | None = None):
    return pymysql.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database=database,
        charset=Config.MYSQL_CHARSET,
        autocommit=True,
        connect_timeout=8,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="宿舍报修管理系统数据库初始化")
    parser.add_argument("--host", default=Config.MYSQL_HOST)
    parser.add_argument("--port", type=int, default=Config.MYSQL_PORT)
    parser.add_argument("--user", default=Config.MYSQL_USER)
    parser.add_argument("--password", default=Config.MYSQL_PASSWORD)
    parser.add_argument("--database", default=Config.MYSQL_DB)
    parser.add_argument("--reset", action="store_true", help="删除已有业务表后重建")
    args = parser.parse_args()

    if not os.path.isfile(SCHEMA_FILE):
        print(f"[错误] 未找到建表脚本：{SCHEMA_FILE}")
        return 1

    with open(SCHEMA_FILE, encoding="utf-8") as fp:
        schema_text = fp.read()
    # 如果命令行指定了别的库名，直接把脚本里的库名替换掉
    if args.database != Config.MYSQL_DB:
        schema_text = schema_text.replace(f"`{Config.MYSQL_DB}`", f"`{args.database}`")
    statements = split_sql_statements(schema_text)

    if not re.fullmatch(r"[A-Za-z0-9_]+", args.database):
        print(f"[错误] 数据库名不合法：{args.database}")
        return 1

    try:
        # 第一步：连接 MySQL（不指定库），创建数据库并执行建表语句
        conn = connect(args.host, args.port, args.user, args.password)
    except pymysql.MySQLError as exc:
        print("[错误] 无法连接 MySQL，请检查用户名、密码与端口是否正确。")
        print(f"       原始错误：{exc}")
        return 1

    try:
        with conn.cursor() as cur:
            if args.reset:
                # 保护系统库，避免误删
                if args.database.lower() in PROTECTED_SCHEMAS:
                    print(f"[错误] 拒绝重置系统数据库：{args.database}")
                    return 1
                cur.execute(f"DROP DATABASE IF EXISTS `{args.database}`")
                print(f"[信息] 已删除数据库 {args.database}（--reset），接下来将重新创建")

            executed = 0
            for statement in statements:
                cur.execute(statement)
                executed += 1
            print(f"[信息] 建库建表完成，共执行 {executed} 条 SQL 语句")

        # 第二步：校验表结构与演示数据
        with conn.cursor() as cur:
            conn.select_db(args.database)
            summary = []
            for table in ("sys_user", "fault_category", "repair_order",
                          "order_image", "order_log", "repair_review"):
                cur.execute(f"SELECT COUNT(*) FROM `{table}`")
                summary.append((table, cur.fetchone()[0]))
            cur.execute("SELECT role, COUNT(*) FROM `sys_user` GROUP BY role")
            roles = cur.fetchall()
    finally:
        conn.close()

    print("\n[完成] 数据库初始化成功！")
    print(f"        数据库：{args.database}    连接：{args.user}@{args.host}:{args.port}")
    print("        数据表记录数：")
    for table, count in summary:
        print(f"          - {table:<16} {count} 条")
    print("        账号角色分布：" + "，".join(f"{role} {count} 个" for role, count in roles))
    print("\n        演示账号（初始密码均为 123456）：")
    print("          - 管理员    admin")
    print("          - 维修人员  worker001 / worker002")
    print("          - 学生      student001")
    print("\n        下一步：python run.py  然后浏览器访问 http://127.0.0.1:5000")
    return 0


if __name__ == "__main__":
    sys.exit(main())
