# -*- coding: utf-8 -*-
"""评价业务：工单完成后由提交人（学生）打分并填写评价内容。"""
from __future__ import annotations

from app.constants import STATUS_COMPLETED
from app.dao import order_dao, review_dao
from app.exceptions import BusinessError
from app.utils.db import transaction
from app.utils.helpers import parse_int


def submit_review(student_id: int, order_id: int, form) -> int:
    order = order_dao.get_detail(order_id)
    if not order or order["is_deleted"]:
        raise BusinessError("工单不存在或已被删除")
    if order["student_id"] != student_id:
        raise BusinessError("只能评价自己提交的工单")
    if order["status"] != STATUS_COMPLETED:
        raise BusinessError("工单维修完成后才能提交评价")
    if review_dao.get_by_order(order_id):
        raise BusinessError("该工单已经评价过了")

    score = parse_int(form.get("score"), "评分")
    if not 1 <= score <= 5:
        raise BusinessError("评分需要在 1-5 星之间")
    content = (form.get("content") or "").strip()
    if len(content) > 500:
        raise BusinessError("评价内容不能超过 500 字")

    with transaction() as cur:
        review_id = review_dao.create_review(
            order_id=order_id,
            student_id=student_id,
            score=score,
            content=content or None,
            cur=cur,
        )
        order_dao.add_log(
            order_id,
            operator_id=student_id,
            action="review",
            remark=f"学生已评价，评分 {score} 星",
            cur=cur,
        )
    return review_id


def list_worker_reviews(worker_id: int, limit: int = 10) -> list[dict]:
    return review_dao.list_by_worker(worker_id, limit)
