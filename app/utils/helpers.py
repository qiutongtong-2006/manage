# -*- coding: utf-8 -*-
"""通用工具函数：工单号生成、图片上传、分页、脱敏等。"""
from __future__ import annotations

import os
import random
import re
import uuid
from datetime import datetime
from typing import Iterable

from flask import current_app
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from app.exceptions import BusinessError


def generate_order_no() -> str:
    """生成形如 RX2026101615301234 的工单号（RX + 时间戳 + 2 位随机数）。"""
    stamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"RX{stamp}{random.randint(10, 99)}"


_PHONE_RE = re.compile(r"^1[3-9]\d{9}$")


def require(value: str | None, field_name: str, max_len: int = 255) -> str:
    """必填校验：去空格 + 非空 + 长度限制。"""
    text = (value or "").strip()
    if not text:
        raise BusinessError(f"{field_name}不能为空")
    if len(text) > max_len:
        raise BusinessError(f"{field_name}长度不能超过 {max_len} 个字符")
    return text


def validate_phone(phone: str | None) -> str:
    """校验手机号格式（11 位、1 开头）。"""
    text = require(phone, "联系电话", 20)
    if not _PHONE_RE.match(text):
        raise BusinessError("联系电话格式不正确，请填写 11 位手机号")
    return text


def parse_int(value, field_name: str = "参数") -> int:
    """把表单 / 路由参数转成整数，失败时抛出业务异常。"""
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        raise BusinessError(f"{field_name}必须是数字") from None


def parse_optional_int(value):
    """可选整数：空值返回 None。"""
    text = ("" if value is None else str(value)).strip()
    return int(text) if text.isdigit() else None


def allowed_file(filename: str) -> bool:
    """判断文件扩展名是否在上传白名单内。"""
    if "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in current_app.config["ALLOWED_EXTENSIONS"]


def save_upload_files(files: Iterable[FileStorage]) -> list[str]:
    """保存上传的图片，返回相对 static 的访问路径列表。

    处理逻辑：
    - 忽略没有选择文件的空 input；
    - 校验扩展名与单张图片大小，超限抛出 BusinessError；
    - 文件名用 uuid 重命名，规避中文名、重名和路径穿越问题；
    - 按年月分目录存放，便于管理和清理。
    """
    saved: list[str] = []
    upload_root = current_app.config["UPLOAD_FOLDER"]
    sub_dir = datetime.now().strftime("%Y-%m")
    target_dir = os.path.join(upload_root, sub_dir)
    os.makedirs(target_dir, exist_ok=True)

    for storage in files:
        if storage is None or not storage.filename:
            continue
        if len(saved) >= current_app.config["MAX_UPLOAD_FILES"]:
            raise BusinessError(
                f"最多上传 {current_app.config['MAX_UPLOAD_FILES']} 张图片"
            )
        if not allowed_file(storage.filename):
            exts = "、".join(sorted(current_app.config["ALLOWED_EXTENSIONS"]))
            raise BusinessError(f"只支持 {exts} 格式的图片")
        data = storage.read()
        if not data:
            continue
        if len(data) > current_app.config["MAX_IMAGE_SIZE"]:
            limit_mb = current_app.config["MAX_IMAGE_SIZE"] // 1024 // 1024
            raise BusinessError(f"单张图片不能超过 {limit_mb}MB")
        storage.stream.seek(0)
        ext = secure_filename(storage.filename).rsplit(".", 1)[1].lower()
        filename = f"{datetime.now():%Y%m%d%H%M%S}_{uuid.uuid4().hex[:8]}.{ext}"
        storage.save(os.path.join(target_dir, filename))
        saved.append(f"{current_app.config['UPLOAD_URL_PREFIX']}/{sub_dir}/{filename}")
    return saved


def delete_upload_file(relative_path: str | None) -> None:
    """删除磁盘上的图片文件（入参为相对 static 的路径）。"""
    if not relative_path or relative_path.startswith("http"):
        return
    abs_path = os.path.join(
        current_app.root_path, "static", relative_path.replace("/", os.sep)
    )
    try:
        if os.path.isfile(abs_path):
            os.remove(abs_path)
    except OSError:
        pass


class Pagination:
    """极简分页对象，供模板渲染页码条。"""

    def __init__(self, page: int, per_page: int, total: int):
        self.page = max(page, 1)
        self.per_page = per_page
        self.total = total
        self.pages = max((total + per_page - 1) // per_page, 1)
        if self.page > self.pages:
            self.page = self.pages

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.per_page

    @property
    def has_prev(self) -> bool:
        return self.page > 1

    @property
    def has_next(self) -> bool:
        return self.page < self.pages

    @property
    def iter_pages(self) -> list:
        """返回需要渲染的页码列表，跨度太大时用 None 表示省略号。"""
        if self.pages <= 7:
            return list(range(1, self.pages + 1))
        window = {1, 2, self.pages - 1, self.pages, self.page - 1, self.page, self.page + 1}
        pages = [p for p in sorted(window) if 1 <= p <= self.pages]
        result: list = []
        prev = 0
        for p in pages:
            if prev and p - prev > 1:
                result.append(None)
            result.append(p)
            prev = p
        return result


def get_page_args() -> tuple[int, int]:
    """从查询串读取 page / per_page（带异常保护）。"""
    from flask import request

    try:
        page = int(request.args.get("page", 1))
    except (TypeError, ValueError):
        page = 1
    return max(page, 1), current_app.config["PER_PAGE"]


def mask_phone(phone: str | None) -> str:
    """手机号脱敏，用于列表页展示。"""
    if not phone or len(phone) < 7:
        return phone or "-"
    return f"{phone[:3]}****{phone[-4:]}"
