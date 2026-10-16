# -*- coding: utf-8 -*-
"""维修人员视图：抢单大厅、我的工单、更新维修进度、查看评价。"""
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

from app.constants import ROLE_WORKER, STATUS_COMPLETED, STATUS_PROCESSING
from app.dao import order_dao
from app.exceptions import BusinessError
from app.services import category_service, order_service, review_service
from app.utils.decorators import role_required
from app.utils.helpers import parse_optional_int

bp = Blueprint("worker", __name__, url_prefix="/worker")


@bp.route("/orders/pending")
@role_required(ROLE_WORKER)
def pending_orders():
    """待受理工单列表（抢单大厅）。"""
    keyword = (request.args.get("keyword") or "").strip() or None
    category_id = parse_optional_int(request.args.get("category_id"))
    orders, pagination = order_service.list_pending_orders(keyword, category_id)
    return render_template(
        "worker/pending.html",
        orders=orders,
        pagination=pagination,
        categories=category_service.list_active(),
        keyword=keyword or "",
        category_id=category_id,
    )


@bp.route("/orders/pending/<int:order_id>/accept", methods=["POST"])
@role_required(ROLE_WORKER)
def accept_order(order_id: int):
    """接单：工单状态由「待受理」变为「维修中」。"""
    try:
        order_no = order_service.accept_order(session["user_id"], order_id)
    except BusinessError as exc:
        flash(exc.message, "danger")
        return redirect(url_for("worker.pending_orders"))
    flash(f"接单成功！工单 {order_no} 已进入维修中状态", "success")
    return redirect(url_for("worker.order_detail", order_id=order_id))


@bp.route("/orders")
@role_required(ROLE_WORKER)
def order_list():
    """我的工单：维修中 / 已完成的全部记录。"""
    status = order_service.normalize_status(request.args.get("status"))
    keyword = (request.args.get("keyword") or "").strip() or None
    orders, pagination, counts = order_service.list_worker_orders(
        session["user_id"], status, keyword
    )
    return render_template(
        "worker/order_list.html",
        orders=orders,
        pagination=pagination,
        counts=counts,
        status=status,
        keyword=keyword or "",
    )


@bp.route("/orders/<int:order_id>")
@role_required(ROLE_WORKER)
def order_detail(order_id: int):
    try:
        order = order_service.get_order_for_worker(session["user_id"], order_id)
    except BusinessError as exc:
        flash(exc.message, "danger")
        return redirect(url_for("worker.order_list"))
    return render_template(
        "worker/order_detail.html",
        order=order,
        images=order_dao.get_images(order_id),
        logs=order_dao.get_logs(order_id),
        step=order_service.status_step(order["status"]),
        is_owner=order["worker_id"] == session["user_id"],
        next_status_options=[
            (STATUS_PROCESSING, "维修中"),
            (STATUS_COMPLETED, "已完成"),
        ],
    )


@bp.route("/orders/<int:order_id>/update", methods=["POST"])
@role_required(ROLE_WORKER)
def update_order(order_id: int):
    """更新维修状态并填写维修备注。"""
    try:
        status = order_service.update_progress(session["user_id"], order_id, request.form)
    except BusinessError as exc:
        flash(exc.message, "danger")
        return redirect(url_for("worker.order_detail", order_id=order_id))
    flash(f"工单已更新为「{order_service.status_label(status)}」", "success")
    return redirect(url_for("worker.order_detail", order_id=order_id))


@bp.route("/reviews")
@role_required(ROLE_WORKER)
def reviews():
    """查看学生对我提交的评价。"""
    return render_template(
        "worker/reviews.html",
        reviews=review_service.list_worker_reviews(session["user_id"], limit=50),
        profile=order_service.worker_profile_stats(session["user_id"]),
    )
