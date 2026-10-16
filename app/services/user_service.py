# -*- coding: utf-8 -*-
"""用户管理业务（管理员使用）：新增 / 查询 / 删除 / 重置密码。"""
from __future__ import annotations

from app.constants import MANAGED_ROLES, ROLE_LABEL, ROLE_WORKER
from app.dao import user_dao
from app.exceptions import BusinessError
from app.services.auth_service import (
    hash_password,
    validate_password,
    validate_username,
)
from app.utils.helpers import Pagination, get_page_args, require, validate_phone


def create_user(form) -> int:
    """管理员新增学生 / 维修工账号。"""
    role = (form.get("role") or "").strip()
    if role not in MANAGED_ROLES:
        raise BusinessError("只能创建学生或维修人员账号")

    username = validate_username(form.get("username"))
    password = validate_password(form.get("password"))
    real_name = require(form.get("real_name"), "姓名", 50)
    phone = validate_phone(form.get("phone"))

    if user_dao.exists_username(username):
        raise BusinessError(f"账号 {username} 已存在")

    student_no = worker_no = dorm_no = skill = None
    if role == ROLE_WORKER:
        worker_no = require(form.get("worker_no"), "工号", 30)
        skill = require(form.get("skill"), "工种", 50)
        if user_dao.exists_field("worker_no", worker_no):
            raise BusinessError(f"工号 {worker_no} 已存在")
    else:
        student_no = require(form.get("student_no"), "学号", 30)
        dorm_no = require(form.get("dorm_no"), "宿舍号", 30)
        if user_dao.exists_field("student_no", student_no):
            raise BusinessError(f"学号 {student_no} 已存在")

    return user_dao.create_user(
        username=username,
        password_hash=hash_password(password),
        role=role,
        real_name=real_name,
        phone=phone,
        student_no=student_no,
        dorm_no=dorm_no,
        worker_no=worker_no,
        skill=skill,
    )


def list_users(role: str | None, keyword: str | None) -> tuple[list[dict], Pagination, dict]:
    """分页查询用户列表，同时返回各角色人数统计。"""
    page, per_page = get_page_args()
    pagination = Pagination(page, per_page, user_dao.count_users(role, keyword))
    users = user_dao.list_users(
        role=role, keyword=keyword, offset=pagination.offset, limit=per_page
    )
    counts = {
        "total": user_dao.count_users(),
        "student": user_dao.count_users("student"),
        "worker": user_dao.count_users("worker"),
        "admin": user_dao.count_users("admin"),
    }
    return users, pagination, counts


def delete_user(operator_id: int, user_id: int) -> str:
    """删除账号：做了三重保护，返回被删除用户的姓名。"""
    if operator_id == user_id:
        raise BusinessError("不能删除当前登录的账号")
    user = user_dao.get_by_id(user_id)
    if not user:
        raise BusinessError("账号不存在或已被删除")
    if user["role"] not in MANAGED_ROLES:
        raise BusinessError("管理员账号不允许被删除")

    related = user_dao.count_orders_for_user(user_id)
    if related:
        raise BusinessError(
            f"该账号关联了 {related} 条报修工单，为保证数据完整性不能删除；"
            "如需停用请改用重置密码"
        )
    user_dao.delete_user(user_id)
    return f"{user['real_name']}（{ROLE_LABEL[user['role']]}）"


def reset_password(user_id: int, new_password: str) -> str:
    """管理员重置用户密码，返回用户名。"""
    user = user_dao.get_by_id(user_id)
    if not user:
        raise BusinessError("账号不存在")
    new_password = validate_password(new_password)
    user_dao.update_password(user_id, hash_password(new_password))
    return user["username"]
