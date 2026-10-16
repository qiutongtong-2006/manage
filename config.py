# -*- coding: utf-8 -*-
"""项目全局配置。

配置读取优先级：系统环境变量 > 项目根目录下的 .env 文件 > 本文件内的默认值。
这样既可以直接改这里的默认值交作业，也可以用环境变量覆盖，避免把数据库密码
硬编码到代码仓库里。
"""
from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


def _load_dotenv(path: Path) -> None:
    """极简 .env 解析器（避免额外引入 python-dotenv 依赖）。

    支持 KEY=VALUE、# 注释、值两侧的引号；已存在的环境变量不会被覆盖。
    """
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


_load_dotenv(BASE_DIR / ".env")


class Config:
    """Flask 应用配置类。"""

    # ---------------------------------------------------------------- Flask
    SECRET_KEY = os.environ.get("SECRET_KEY", "dorm-repair-system-secret-key-2026")

    # ----------------------------------------------------------- MySQL 连接
    MYSQL_HOST = os.environ.get("MYSQL_HOST", "127.0.0.1")
    MYSQL_PORT = int(os.environ.get("MYSQL_PORT", "3306"))
    MYSQL_USER = os.environ.get("MYSQL_USER", "root")
    MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "Qiu_200604")
    MYSQL_DB = os.environ.get("MYSQL_DB", "dorm_repair")
    MYSQL_CHARSET = "utf8mb4"

    # -------------------------------------------------------------- 图片上传
    UPLOAD_FOLDER = str(BASE_DIR / "app" / "static" / "uploads")
    UPLOAD_URL_PREFIX = "uploads"
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "bmp", "webp"}
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024
    MAX_IMAGE_SIZE = 5 * 1024 * 1024
    MAX_UPLOAD_FILES = 3

    # ---------------------------------------------------------------- 分页
    PER_PAGE = 10

    # ------------------------------------------------------------ 业务参数
    STAT_MONTHS = 6
