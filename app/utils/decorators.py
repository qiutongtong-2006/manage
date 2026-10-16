# -*- coding: utf-8 -*-
"""视图装饰器：登录校验与角色校验。"""
from __future__ import annotations

from functools import wraps

from flask import flash, redirect, request, session, url_for


def login_required(view):
    """未登录用户重定向到登录页，并记住原地址（登录后自动跳回）。"""

    @wraps(view)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            flash("请先登录后再进行操作", "warning")
            return redirect(url_for("auth.login", next=request.full_path))
        return view(*args, **kwargs)

    return wrapper


def role_required(*roles: str):
    """限定只有指定角色可以访问，例如 @role_required('admin')。"""

    def decorator(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            if not session.get("user_id"):
                flash("请先登录后再进行操作", "warning")
                return redirect(url_for("auth.login", next=request.full_path))
            if session.get("role") not in roles:
                flash("没有权限访问该页面", "danger")
                return redirect(url_for("main.dashboard"))
            return view(*args, **kwargs)

        return wrapper

    return decorator
