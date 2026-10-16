# -*- coding: utf-8 -*-
"""首页与角色工作台。"""
from __future__ import annotations

from flask import Blueprint, redirect, render_template, session, url_for

from app.constants import ROLE_ADMIN, ROLE_STUDENT, ROLE_WORKER
from app.services import order_service, review_service, stats_service
from app.utils.decorators import login_required

bp = Blueprint("main", __name__)


@bp.route("/")
def index():
    """未登录展示系统介绍页；已登录直接进入对应工作台。"""
    if session.get("user_id"):
        return redirect(url_for("main.dashboard"))
    return render_template("index.html")


@bp.route("/dashboard")
@login_required
def dashboard():
    """根据登录角色渲染不同的首页。"""
    role = session.get("role")
    if role == ROLE_ADMIN:
        return render_template("admin/dashboard.html", stats=stats_service.admin_dashboard())

    if role == ROLE_WORKER:
        profile = order_service.worker_profile_stats(session["user_id"])
        pending_orders, pagination = order_service.list_pending_orders(None, None)
        reviews = review_service.list_worker_reviews(session["user_id"], limit=5)
        return render_template(
            "worker/dashboard.html",
            profile=profile,
            orders=pending_orders,
            pagination=pagination,
            reviews=reviews,
        )

    # 学生工作台
    orders, pagination, counts = order_service.list_student_orders(
        session["user_id"], None, None
    )
    return render_template(
        "student/dashboard.html",
        orders=orders,
        pagination=pagination,
        counts=counts,
    )
