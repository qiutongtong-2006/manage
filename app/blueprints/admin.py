# -*- coding: utf-8 -*-
"""管理员视图：用户管理、工单检索与删除、数据统计。"""
from __future__ import annotations

from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from app.constants import MANAGED_ROLES, ROLE_ADMIN
from app.dao import order_dao, review_dao
from app.exceptions import BusinessError
from app.services import (
    category_service,
    order_service,
    stats_service,
    user_service,
)
from app.utils.decorators import role_required

bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.route("/dashboard")
@role_required(ROLE_ADMIN)
def dashboard():
    """管理端首页：核心指标 + 最近工单。"""
    return render_template("admin/dashboard.html", stats=stats_service.admin_dashboard())


@bp.route("/statistics")
@role_required(ROLE_ADMIN)
def statistics():
    """工单数据统计页：状态分布、类别分布、楼栋分布、月度趋势、维修工排名。"""
    return render_template("admin/statistics.html", stats=stats_service.admin_dashboard())


# ------------------------------------------------------------------ 用户管理
@bp.route("/users")
@role_required(ROLE_ADMIN)
def user_list():
    """用户列表：可按角色、关键词筛选，支持新增 / 删除 / 重置密码。"""
    role = request.args.get("role")
    role = role if role in MANAGED_ROLES + (ROLE_ADMIN,) else None
    keyword = (request.args.get("keyword") or "").strip() or None
    users, pagination, counts = user_service.list_users(role, keyword)
    return render_template(
        "admin/users.html",
        users=users,
        pagination=pagination,
        counts=counts,
        role=role,
        keyword=keyword or "",
    )


@bp.route("/users/create", methods=["POST"])
@role_required(ROLE_ADMIN)
def user_create():
    try:
        user_service.create_user(request.form)
    except BusinessError as exc:
        flash(exc.message, "danger")
        return redirect(url_for("admin.user_list"))
    role_label = "学生" if request.form.get("role") == "student" else "维修人员"
    flash(f"{role_label}账号 {request.form.get('username')} 创建成功", "success")
    return redirect(url_for("admin.user_list"))


@bp.route("/users/<int:user_id>/delete", methods=["POST"])
@role_required(ROLE_ADMIN)
def user_delete(user_id: int):
    try:
        name = user_service.delete_user(session["user_id"], user_id)
    except BusinessError as exc:
        flash(exc.message, "danger")
        return redirect(url_for("admin.user_list"))
    flash(f"账号 {name} 已删除", "success")
    return redirect(url_for("admin.user_list"))


@bp.route("/users/<int:user_id>/reset-password", methods=["POST"])
@role_required(ROLE_ADMIN)
def user_reset_password(user_id: int):
    try:
        username = user_service.reset_password(user_id, request.form.get("new_password"))
    except BusinessError as exc:
        flash(exc.message, "danger")
        return redirect(url_for("admin.user_list"))
    flash(f"账号 {username} 的密码已重置", "success")
    return redirect(url_for("admin.user_list"))


# ------------------------------------------------------------------ 工单管理
@bp.route("/orders")
@role_required(ROLE_ADMIN)
def order_list():
    """工单检索：关键词、状态、类别、楼栋、时间范围、删除状态。"""
    filters = order_service.build_admin_filters(request.args)
    orders, pagination = order_service.admin_search_orders(filters)
    return render_template(
        "admin/orders.html",
        orders=orders,
        pagination=pagination,
        filters=filters,
        categories=category_service.list_active(),
    )


@bp.route("/orders/<int:order_id>")
@role_required(ROLE_ADMIN)
def order_detail(order_id: int):
    try:
        order = order_service.get_order_for_admin(order_id)
    except BusinessError as exc:
        flash(exc.message, "danger")
        return redirect(url_for("admin.order_list"))
    return render_template(
        "admin/order_detail.html",
        order=order,
        images=order_dao.get_images(order_id),
        logs=order_dao.get_logs(order_id),
        step=order_service.status_step(order["status"]),
    )


@bp.route("/orders/<int:order_id>/delete", methods=["POST"])
@role_required(ROLE_ADMIN)
def order_delete(order_id: int):
    """删除无效工单（逻辑删除，可恢复）。"""
    try:
        order_no = order_service.delete_order(
            session["user_id"], order_id, request.form.get("reason")
        )
    except BusinessError as exc:
        flash(exc.message, "danger")
        return redirect(url_for("admin.order_detail", order_id=order_id))
    flash(f"工单 {order_no} 已删除（可在“已删除”筛选中恢复）", "success")
    return redirect(url_for("admin.order_list"))


@bp.route("/orders/<int:order_id>/restore", methods=["POST"])
@role_required(ROLE_ADMIN)
def order_restore(order_id: int):
    try:
        order_no = order_service.restore_order(session["user_id"], order_id)
    except BusinessError as exc:
        flash(exc.message, "danger")
        return redirect(url_for("admin.order_detail", order_id=order_id))
    flash(f"工单 {order_no} 已恢复", "success")
    return redirect(url_for("admin.order_detail", order_id=order_id))


@bp.route("/reviews")
@role_required(ROLE_ADMIN)
def review_list():
    """所有评价一览（附带工单与学生信息）。"""
    keyword = (request.args.get("keyword") or "").strip() or None
    return render_template(
        "admin/reviews.html",
        reviews=review_dao.list_recent(keyword, limit=100),
        keyword=keyword or "",
        avg_score=stats_service.admin_dashboard()["avg_score"],
    )
