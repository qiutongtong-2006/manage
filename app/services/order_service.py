# -*- coding: utf-8 -*-
"""报修工单核心业务：提交、接单、更新进度、查询、删除。

工单状态流转（完整业务闭环）：
    pending(待受理) --接单--> processing(维修中) --维修完成--> completed(已完成) --学生评价--> 已评价
"""
from __future__ import annotations

from app.constants import (
    DORM_BUILDINGS,
    ORDER_STATUSES,
    ORDER_STATUS_LABEL,
    STATUS_COMPLETED,
    STATUS_PENDING,
    STATUS_PROCESSING,
)
from app.dao import category_dao, order_dao, review_dao
from app.exceptions import BusinessError
from app.utils.db import transaction
from app.utils.helpers import (
    Pagination,
    delete_upload_file,
    generate_order_no,
    get_page_args,
    parse_optional_int,
    require,
    save_upload_files,
    validate_phone,
)


def status_label(status: str) -> str:
    return ORDER_STATUS_LABEL.get(status, status)


def status_step(status: str) -> int:
    """返回状态在流程中的步骤序号（用于详情页进度条）。"""
    return {STATUS_PENDING: 1, STATUS_PROCESSING: 2, STATUS_COMPLETED: 3}.get(status, 0)


def submit_order(student_id: int, form, files) -> dict:
    """学生提交报修工单：校验表单 -> 保存图片 -> 事务写入工单 + 图片 + 日志。"""
    # 1. 故障类别校验
    category_id = parse_optional_int(form.get("category_id"))
    if not category_id:
        raise BusinessError("请选择故障类别")
    category = category_dao.get_category(category_id)
    if not category or not category["is_active"]:
        raise BusinessError("所选故障类别不存在，请重新选择")

    # 2. 宿舍信息校验
    building = require(form.get("building"), "宿舍楼栋", 30)
    if building not in DORM_BUILDINGS:
        raise BusinessError("请选择有效的宿舍楼栋")
    dorm_no = require(form.get("dorm_no"), "宿舍号", 30)

    # 3. 故障描述与联系方式校验
    description = require(form.get("description"), "故障详细描述", 500)
    if len(description) < 5:
        raise BusinessError("故障描述太简短了，请至少填写 5 个字，便于维修人员判断")
    phone = validate_phone(form.get("phone"))

    # 4. 保存上传图片（内部含扩展名与大小校验）
    images = save_upload_files(files)

    order_no = generate_order_no()
    try:
        # 5. 事务：主表 + 图片表 + 流转日志一起提交
        with transaction() as cur:
            order_id = order_dao.create_order(
                order_no=order_no,
                student_id=student_id,
                category_id=category_id,
                building=building,
                dorm_no=dorm_no,
                description=description,
                phone=phone,
                cur=cur,
            )
            if images:
                order_dao.add_images(order_id, images, cur)
            order_dao.add_log(
                order_id,
                operator_id=student_id,
                action="create",
                status=STATUS_PENDING,
                remark=f"学生提交报修申请，故障类别：{category['name']}",
                cur=cur,
            )
    except Exception:
        # 写库失败时清理刚落盘的图片，避免产生孤儿文件
        for path in images:
            delete_upload_file(path)
        raise
    return {"id": order_id, "order_no": order_no}


def list_student_orders(student_id: int, status: str | None, keyword: str | None):
    """学生查看自己提交的全部工单。"""
    page, per_page = get_page_args()
    filters = dict(status=status, keyword=keyword, student_id=student_id)
    pagination = Pagination(page, per_page, order_dao.count_orders(**filters))
    orders = order_dao.list_orders(offset=pagination.offset, limit=per_page, **filters)
    return orders, pagination, order_dao.count_by_status_for_student(student_id)


def get_order_for_student(student_id: int, order_id: int) -> dict:
    order = order_dao.get_detail(order_id)
    if not order or order["is_deleted"]:
        raise BusinessError("工单不存在或已被删除")
    if order["student_id"] != student_id:
        raise BusinessError("只能查看自己提交的工单")
    return order


def list_pending_orders(keyword: str | None, category_id: int | None):
    """维修人员查看全部待受理工单（越早提交越靠前）。"""
    page, per_page = get_page_args()
    filters = dict(status=STATUS_PENDING, keyword=keyword, category_id=category_id)
    pagination = Pagination(page, per_page, order_dao.count_orders(**filters))
    orders = order_dao.list_orders(
        offset=pagination.offset, limit=per_page, order_by="o.created_at ASC", **filters
    )
    return orders, pagination


def list_worker_orders(worker_id: int, status: str | None, keyword: str | None):
    """维修人员查看自己已接的工单。"""
    page, per_page = get_page_args()
    filters = dict(worker_id=worker_id, status=status, keyword=keyword)
    pagination = Pagination(page, per_page, order_dao.count_orders(**filters))
    orders = order_dao.list_orders(offset=pagination.offset, limit=per_page, **filters)
    return orders, pagination, order_dao.count_by_status_for_worker(worker_id)


def accept_order(worker_id: int, order_id: int) -> str:
    """维修人员接单。用「条件更新」避免两个人同时抢到同一个工单。"""
    order = order_dao.get_detail(order_id)
    if not order or order["is_deleted"]:
        raise BusinessError("工单不存在或已被删除")
    if order["status"] != STATUS_PENDING:
        raise BusinessError(f"该工单当前状态为「{status_label(order['status'])}」，无法接单")
    with transaction() as cur:
        affected = order_dao.accept_order(order_id, worker_id, cur)
        if not affected:
            # 条件更新影响 0 行，说明工单刚被其他维修人员抢走
            raise BusinessError("手慢了一步，该工单已被其他维修人员接单")
        order_dao.add_log(
            order_id,
            operator_id=worker_id,
            action="accept",
            status=STATUS_PROCESSING,
            remark="维修人员已接单，准备上门处理",
            cur=cur,
        )
    return order["order_no"]


def update_progress(worker_id: int, order_id: int, form) -> str:
    """维修人员更新维修状态并填写维修备注。"""
    order = order_dao.get_detail(order_id)
    if not order or order["is_deleted"]:
        raise BusinessError("工单不存在或已被删除")
    if order["worker_id"] != worker_id:
        raise BusinessError("只能更新自己接单的工单")
    if order["status"] == STATUS_COMPLETED:
        raise BusinessError("该工单已标记完成，不能再修改")

    status = (form.get("status") or "").strip()
    if status not in (STATUS_PROCESSING, STATUS_COMPLETED):
        raise BusinessError("请选择有效的维修状态")
    remark = (form.get("remark") or "").strip()
    if len(remark) > 500:
        raise BusinessError("维修备注不能超过 500 字")
    if status == order["status"] and not remark:
        raise BusinessError("维修状态与备注均未发生变化，无需提交")

    if status == STATUS_COMPLETED:
        action, log_remark = "complete", remark or "维修完成，已恢复正常使用"
    elif status == order["status"]:
        action, log_remark = "remark", remark
    else:
        action, log_remark = "processing", remark or "已开始维修，正在处理中"

    with transaction() as cur:
        order_dao.update_status(order_id, status, worker_id, cur)
        order_dao.add_log(
            order_id,
            operator_id=worker_id,
            action=action,
            status=status,
            remark=log_remark,
            cur=cur,
        )
    return status


def get_order_for_worker(worker_id: int, order_id: int) -> dict:
    """维修人员可查看待受理工单详情，或自己接单的工单详情。"""
    order = order_dao.get_detail(order_id)
    if not order or order["is_deleted"]:
        raise BusinessError("工单不存在或已被删除")
    if order["worker_id"] != worker_id and order["status"] != STATUS_PENDING:
        raise BusinessError("该工单已被其他维修人员接单，无法查看")
    return order


def worker_profile_stats(worker_id: int) -> dict:
    """维修人员个人工作台统计。"""
    counts = order_dao.count_by_status_for_worker(worker_id)
    return {
        "processing": counts.get(STATUS_PROCESSING, 0),
        "completed": counts.get(STATUS_COMPLETED, 0),
        "total": sum(counts.values()),
        "avg_score": review_dao.average_score_for_worker(worker_id),
    }


def admin_search_orders(filters: dict):
    """管理员综合检索工单：关键词、状态、类别、楼栋、时间范围、删除状态。"""
    page, per_page = get_page_args()
    pagination = Pagination(page, per_page, order_dao.count_orders(**filters))
    orders = order_dao.list_orders(offset=pagination.offset, limit=per_page, **filters)
    return orders, pagination


def get_order_for_admin(order_id: int) -> dict:
    order = order_dao.get_detail(order_id)
    if not order:
        raise BusinessError("工单不存在")
    return order


def delete_order(admin_id: int, order_id: int, reason: str | None = None) -> str:
    """删除无效工单（逻辑删除，保留历史数据用于统计，必要时可恢复）。"""
    order = order_dao.get_detail(order_id)
    if not order:
        raise BusinessError("工单不存在")
    if order["is_deleted"]:
        raise BusinessError("该工单已经是删除状态")
    remark = (reason or "").strip() or "管理员判定为无效工单，已删除"
    with transaction() as cur:
        order_dao.soft_delete(order_id, cur)
        order_dao.add_log(
            order_id, operator_id=admin_id, action="admin_delete", remark=remark, cur=cur
        )
    return order["order_no"]


def restore_order(admin_id: int, order_id: int) -> str:
    order = order_dao.get_detail(order_id)
    if not order:
        raise BusinessError("工单不存在")
    if not order["is_deleted"]:
        raise BusinessError("该工单未被删除，无需恢复")
    with transaction() as cur:
        order_dao.restore(order_id, cur)
        order_dao.add_log(
            order_id,
            operator_id=admin_id,
            action="admin_restore",
            remark="管理员恢复该工单",
            cur=cur,
        )
    return order["order_no"]


def normalize_status(value: str | None) -> str | None:
    """把 URL 参数里的状态过滤成合法值，非法则忽略。"""
    value = (value or "").strip()
    return value if value in ORDER_STATUSES else None


def build_admin_filters(args) -> dict:
    """从 request.args 提取管理端检索条件。"""
    deleted = args.get("deleted")
    return dict(
        keyword=(args.get("keyword") or "").strip() or None,
        status=normalize_status(args.get("status")),
        category_id=parse_optional_int(args.get("category_id")),
        building=(args.get("building") or "").strip() or None,
        date_from=(args.get("date_from") or "").strip() or None,
        date_to=(args.get("date_to") or "").strip() or None,
        deleted=deleted if deleted in ("active", "deleted", "all") else "active",
    )
