# -*- coding: utf-8 -*-
"""学生端视图：提交报修、查看我的工单、提交评价。"""
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

from app.constants import ROLE_STUDENT
from app.dao import order_dao
from app.exceptions import BusinessError
from app.services import category_service, order_service, review_service
from app.utils.decorators import role_required

bp = Blueprint("student", __name__, url_prefix="/student")


@bp.route("/orders/new", methods=["GET", "POST"])
@role_required(ROLE_STUDENT)
def create_order():
    """提交报修工单（含图片上传）。"""
    categories = category_service.list_active()
    if request.method == "POST":
        try:
            result = order_service.submit_order(
                session["user_id"], request.form, request.files.getlist("images")
            )
        except BusinessError as exc:
            flash(exc.message, "danger")
            # 回填用户已填写的内容，避免重新输入
            return render_template(
                "student/order_form.html", categories=categories, form=request.form
            ), 200
        flash(
            f"报修提交成功！工单号 {result['order_no']}，请耐心等待维修人员接单",
            "success",
        )
        return redirect(url_for("student.order_detail", order_id=result["id"]))

    return render_template("student/order_form.html", categories=categories)


@bp.route("/orders")
@role_required(ROLE_STUDENT)
def order_list():
    """查看自己提交的全部报修工单（支持按状态筛选与关键词搜索）。"""
    status = order_service.normalize_status(request.args.get("status"))
    keyword = (request.args.get("keyword") or "").strip() or None
    orders, pagination, counts = order_service.list_student_orders(
        session["user_id"], status, keyword
    )
    return render_template(
        "student/order_list.html",
        orders=orders,
        pagination=pagination,
        counts=counts,
        status=status,
        keyword=keyword or "",
    )


@bp.route("/orders/<int:order_id>")
@role_required(ROLE_STUDENT)
def order_detail(order_id: int):
    """工单详情：维修进度时间线 + 图片 + 评价入口。"""
    try:
        order = order_service.get_order_for_student(session["user_id"], order_id)
    except BusinessError as exc:
        flash(exc.message, "danger")
        return redirect(url_for("student.order_list"))
    return render_template(
        "student/order_detail.html",
        order=order,
        images=order_dao.get_images(order_id),
        logs=order_dao.get_logs(order_id),
        step=order_service.status_step(order["status"]),
    )


@bp.route("/orders/<int:order_id>/review", methods=["POST"])
@role_required(ROLE_STUDENT)
def submit_review(order_id: int):
    """维修完成后提交评价与打分。"""
    try:
        review_service.submit_review(session["user_id"], order_id, request.form)
    except BusinessError as exc:
        flash(exc.message, "danger")
        return redirect(url_for("student.order_detail", order_id=order_id))
    flash("感谢您的评价，我们会继续改进服务！", "success")
    return redirect(url_for("student.order_detail", order_id=order_id))


@bp.route("/orders/<int:order_id>/review")
@role_required(ROLE_STUDENT)
def review_form(order_id: int):
    """单独的评价页面（详情页也有内嵌评价表单）。"""
    try:
        order = order_service.get_order_for_student(session["user_id"], order_id)
    except BusinessError as exc:
        flash(exc.message, "danger")
        return redirect(url_for("student.order_list"))
    if order["status"] != "completed":
        flash("工单维修完成后才能评价", "warning")
        return redirect(url_for("student.order_detail", order_id=order_id))
    return render_template("student/review.html", order=order)
