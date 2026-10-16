# -*- coding: utf-8 -*-
"""故障类别业务。"""
from __future__ import annotations

from app.dao import category_dao
from app.exceptions import BusinessError
from app.utils.helpers import require


def list_active() -> list[dict]:
    return category_dao.list_categories(only_active=True)


def create_category(name: str, sort_order: int = 0) -> int:
    name = require(name, "类别名称", 50)
    if category_dao.exists_name(name):
        raise BusinessError(f"类别「{name}」已存在")
    return category_dao.create_category(name, sort_order)


def get_name(category_id: int) -> str:
    category = category_dao.get_category(category_id)
    return category["name"] if category else "-"
