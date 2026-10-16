# -*- coding: utf-8 -*-
"""认证相关业务：注册、登录、修改密码、资料维护。"""
from __future__ import annotations

import re

from werkzeug.security import check_password_hash, generate_password_hash

from app.constants import ROLE_ADMIN, ROLE_STUDENT, ROLE_WORKER
from app.dao import user_dao
from app.exceptions import BusinessError
from app.utils.helpers import require, validate_phone

# 账号规则：4-20 位字母、数字或下划线
USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{4,20}$")


def hash_password(raw: str) -> str:
    """使用 pbkdf2 加盐哈希，绝不保存明文密码。"""
    return generate_password_hash(raw, method="pbkdf2:sha256", salt_length=16)


def verify_password(raw: str, hashed: str) -> bool:
    return check_password_hash(hashed, raw)


def validate_username(username: str) -> str:
    username = require(username, "登录账号", 20)
    if not USERNAME_RE.match(username):
        raise BusinessError("登录账号需为 4-20 位字母、数字或下划线")
    return username


def validate_password(password: str, confirm: str | None = None) -> str:
    password = require(password, "密码", 50)
    if len(password) < 6:
        raise BusinessError("密码长度不能少于 6 位")
    if confirm is not None and password != (confirm or ""):
        raise BusinessError("两次输入的密码不一致")
    return password


def login(username: str, password: str) -> dict:
    """校验账号密码，成功返回用户信息并更新最后登录时间。"""
    username = (username or "").strip()
    if not username or not password:
        raise BusinessError("请输入账号和密码")

    user = user_dao.get_by_username(username)
    if not user or not verify_password(password, user["password_hash"]):
        # 统一提示，避免暴露账号是否存在
        raise BusinessError("账号或密码错误")
    if not user["is_active"]:
        raise BusinessError("该账号已被禁用，请联系管理员")

    user_dao.update_last_login(user["id"])
    return user


def register_student(form) -> int:
    """学生自助注册（管理员账号与维修工账号只能由管理员创建）。"""
    username = validate_username(form.get("username"))
    password = validate_password(form.get("password"), form.get("confirm_password"))
    real_name = require(form.get("real_name"), "姓名", 50)
    phone = validate_phone(form.get("phone"))
    student_no = require(form.get("student_no"), "学号", 30)
    dorm_no = require(form.get("dorm_no"), "宿舍号", 30)

    if user_dao.exists_username(username):
        raise BusinessError(f"账号 {username} 已被注册，请更换")
    if user_dao.exists_field("student_no", student_no):
        raise BusinessError(f"学号 {student_no} 已被注册，请核对后重试")

    return user_dao.create_user(
        username=username,
        password_hash=hash_password(password),
        role=ROLE_STUDENT,
        real_name=real_name,
        phone=phone,
        student_no=student_no,
        dorm_no=dorm_no,
    )


def change_password(user_id: int, old_password: str, new_password: str, confirm) -> None:
    user = user_dao.get_by_id(user_id)
    if not user:
        raise BusinessError("用户不存在")
    if not verify_password(old_password or "", user["password_hash"]):
        raise BusinessError("原密码不正确")
    new_password = validate_password(new_password, confirm)
    if verify_password(new_password, user["password_hash"]):
        raise BusinessError("新密码不能与原密码相同")
    user_dao.update_password(user_id, hash_password(new_password))


def update_profile(user_id: int, form) -> None:
    """学生 / 维修工更新个人资料（姓名、电话、宿舍号）。"""
    user = user_dao.get_by_id(user_id)
    if not user:
        raise BusinessError("用户不存在")
    real_name = require(form.get("real_name"), "姓名", 50)
    phone = validate_phone(form.get("phone"))
    dorm_no = None
    if user["role"] == ROLE_STUDENT:
        dorm_no = require(form.get("dorm_no"), "宿舍号", 30)
    user_dao.update_profile(user_id, real_name, phone, dorm_no)


def current_user_context(user_id: int) -> dict:
    """读取会话中用户的最新信息，供导航栏展示与权限刷新。"""
    user = user_dao.get_by_id(user_id)
    if not user or not user["is_active"]:
        return {}
    return {
        "user_id": user["id"],
        "username": user["username"],
        "real_name": user["real_name"],
        "role": user["role"],
        "phone": user["phone"],
        "dorm_no": user["dorm_no"],
        "student_no": user["student_no"],
        "worker_no": user["worker_no"],
        "skill": user["skill"],
        "created_at": user["created_at"],
        "last_login_at": user["last_login_at"],
    }


def role_label(role: str) -> str:
    from app.constants import ROLE_LABEL

    return ROLE_LABEL.get(role, role)


__all__ = [
    "ROLE_ADMIN",
    "ROLE_STUDENT",
    "ROLE_WORKER",
    "login",
    "register_student",
    "change_password",
    "update_profile",
    "current_user_context",
    "hash_password",
    "verify_password",
    "role_label",
    "validate_username",
    "validate_password",
]
