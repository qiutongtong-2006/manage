# -*- coding: utf-8 -*-
"""端到端自检脚本：用 Flask 测试客户端把整条业务链路跑一遍。

覆盖流程：
    学生注册 -> 登录 -> 提交带图片的报修工单 -> 维修工接单 -> 更新维修进度
    -> 标记完成 -> 学生评价 -> 管理员检索/统计/删除与恢复工单 -> 权限校验

运行方式（需要 MySQL 已启动且已执行过 python init_db.py）::

    python tools/smoke_test.py

脚本结束后会自动清理本次创建的测试数据（工单、图片文件与账号）。
"""
from __future__ import annotations

import io
import os
import random
import string
import sys

# 允许直接以 python tools/smoke_test.py 运行
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app  # noqa: E402
from app.utils import db  # noqa: E402

PASSED = 0
FAILED: list[str] = []


def check(condition: bool, message: str) -> None:
    """断言并打印结果，失败时只记录不中断，便于一次性看到全部问题。"""
    global PASSED
    if condition:
        PASSED += 1
        print(f"  [通过] {message}")
    else:
        FAILED.append(message)
        print(f"  [失败] {message}")


def body(response) -> str:
    return response.get_data(as_text=True)


def main() -> int:
    app = create_app()
    suffix = "".join(random.choices(string.digits, k=5))
    student_username = f"smoke_stu_{suffix}"
    worker_username = f"smoke_wrk_{suffix}"
    password = "test123456"
    order_ids: list[int] = []
    student_id = worker_id = None
    order: dict = {}

    print("\n=== 宿舍报修管理系统 端到端自检 ===")
    try:
        with app.app_context():
            # -------------------------------------------- 1. 学生注册与登录
            print("\n[1] 学生注册、登录")
            client = app.test_client()
            register_data = {
                "username": student_username,
                "password": password,
                "confirm_password": password,
                "real_name": "自检学生",
                "student_no": f"S{suffix}",
                "phone": "13900001234",
                "dorm_no": "5号楼 606",
            }
            check(body(client.post("/auth/register", data=register_data, follow_redirects=True)).find("注册成功") >= 0,
                  "学生注册成功")
            row = db.query_one("SELECT id, role FROM sys_user WHERE username = %s", (student_username,))
            check(row is not None and row["role"] == "student", "注册的学生账号已写入 sys_user 表")
            student_id = row["id"] if row else None

            response = client.post("/auth/register", data=register_data, follow_redirects=True)
            check("已被注册" in body(response), "重复注册被业务规则拦截")

            response = client.post("/auth/login", data={"username": student_username, "password": password},
                                   follow_redirects=True)
            check("我的工作台" in body(response), "学生登录成功并进入工作台")

            response = app.test_client().post(
                "/auth/login", data={"username": student_username, "password": "wrong-password"},
                follow_redirects=True)
            check("账号或密码错误" in body(response), "错误密码登录被拒绝")

            # ---------------------------------------- 2. 提交报修工单（含图片）
            print("\n[2] 提交报修工单（含图片上传与表单校验）")
            category_id = db.query_value("SELECT id FROM fault_category ORDER BY sort_order LIMIT 1")
            response = client.post(
                "/student/orders/new",
                data={
                    "building": "5号楼",
                    "dorm_no": "606",
                    "category_id": str(category_id),
                    "phone": "13900001234",
                    "description": "洗手台下水管漏水，地面已积水，需要尽快处理",
                    "images": (io.BytesIO(b"\x89PNG\r\n\x1a\n" + b"0" * 512), "site.png"),
                },
                content_type="multipart/form-data",
                follow_redirects=True,
            )
            check("报修提交成功" in body(response), "工单提交成功并弹出提示")
            order = db.query_one(
                "SELECT id, order_no, status, worker_id FROM repair_order "
                "WHERE student_id = %s ORDER BY id DESC LIMIT 1", (student_id,))
            check(order is not None, "工单已写入 repair_order 表")
            order_ids.append(order["id"])
            check(order["status"] == "pending", "新工单初始状态为「待受理」")
            image_paths = [r["file_path"] for r in db.query_all(
                "SELECT file_path FROM order_image WHERE order_id = %s", (order["id"],))]
            check(len(image_paths) == 1, "上传的图片已关联到工单（order_image 表）")
            check(db.query_value("SELECT COUNT(*) AS c FROM order_log WHERE order_id = %s",
                                 (order["id"],)) == 1, "提交动作写入了流转日志")
            order_url = f"/student/orders/{order['id']}"

            response = client.post(
                "/student/orders/new",
                data={"building": "5号楼", "dorm_no": "606", "category_id": str(category_id),
                      "phone": "13900001234", "description": "坏了"},
                content_type="multipart/form-data", follow_redirects=True)
            check("故障描述太简短" in body(response), "过短的故障描述被拦截")

            response = client.post(
                "/student/orders/new",
                data={"building": "5号楼", "dorm_no": "606", "category_id": str(category_id),
                      "phone": "12345", "description": "卫生间灯不亮了，需要更换灯管"},
                content_type="multipart/form-data", follow_redirects=True)
            check("联系电话格式不正确" in body(response), "非法手机号被拦截")

            # ------------------------------------ 3. 管理员新增维修人员账号
            print("\n[3] 管理员新增维修人员账号")
            admin_client = app.test_client()
            admin_client.post("/auth/login", data={"username": "admin", "password": "123456"},
                              follow_redirects=True)
            response = admin_client.post(
                "/admin/users/create",
                data={"role": "worker", "username": worker_username, "password": password,
                      "real_name": "自检维修工", "phone": "13700005678",
                      "worker_no": f"W{suffix}", "skill": "水电维修"},
                follow_redirects=True)
            check("创建成功" in body(response), "管理员成功新增维修人员账号")
            row = db.query_one("SELECT id FROM sys_user WHERE username = %s", (worker_username,))
            worker_id = row["id"] if row else None
            check(worker_id is not None, "维修人员账号已写入数据库")

            # ---------------------------------- 4. 维修工接单与更新维修进度
            print("\n[4] 维修人员接单、更新维修进度")
            worker_client = app.test_client()
            worker_client.post("/auth/login", data={"username": worker_username, "password": password},
                               follow_redirects=True)
            check(order["order_no"] in body(worker_client.get("/worker/orders/pending")),
                  "待受理列表展示了该工单")

            response = worker_client.post(f"/worker/orders/pending/{order['id']}/accept",
                                          follow_redirects=True)
            check("接单成功" in body(response), "维修人员接单成功")
            row = db.query_one("SELECT status, worker_id, accepted_at FROM repair_order WHERE id = %s",
                               (order["id"],))
            check(row["status"] == "processing" and row["worker_id"] == worker_id,
                  "接单后状态变为「维修中」并绑定维修人员")
            check(row["accepted_at"] is not None, "接单时间已记录")

            other_client = app.test_client()
            other_client.post("/auth/login", data={"username": "worker001", "password": "123456"},
                              follow_redirects=True)
            response = other_client.post(f"/worker/orders/pending/{order['id']}/accept",
                                         follow_redirects=True)
            check("无法接单" in body(response), "已被接单的工单不能被其他维修工重复接单")

            response = worker_client.post(f"/worker/orders/{order['id']}/update",
                                          data={"status": "processing",
                                                "remark": "已上门检查，需要更换下水管配件"},
                                          follow_redirects=True)
            check("工单已更新" in body(response), "维修备注更新成功")
            check(db.query_value("SELECT remark FROM order_log WHERE order_id = %s AND action = 'remark'",
                                 (order["id"],)) is not None, "维修备注写入流转日志")

            response = worker_client.post(f"/worker/orders/{order['id']}/update",
                                          data={"status": "completed",
                                                "remark": "已更换下水管并做防水测试，恢复正常"},
                                          follow_redirects=True)
            check("已完成" in body(response), "维修人员标记工单完成")
            row = db.query_one("SELECT status, completed_at FROM repair_order WHERE id = %s",
                               (order["id"],))
            check(row["status"] == "completed" and row["completed_at"] is not None,
                  "完成后状态与完成时间正确写入")

            response = worker_client.post(f"/worker/orders/{order['id']}/update",
                                          data={"status": "processing", "remark": "再次修改"},
                                          follow_redirects=True)
            check("不能再修改" in body(response), "已完成工单禁止再次修改")

            response = other_client.post(f"/worker/orders/{order['id']}/update",
                                         data={"status": "completed", "remark": "越权修改"},
                                         follow_redirects=True)
            check("只能更新自己接单的工单" in body(response), "维修工不能更新他人接单的工单")

            # ------------------------------------------------- 5. 学生评价
            print("\n[5] 学生查看维修进度并提交评价")
            html = body(client.get(order_url))
            check("维修进度记录" in html and "已完成" in html, "学生可查看工单详情与维修进度")
            check("已更换下水管" in html, "维修备注对学生可见")

            response = client.post(f"/student/orders/{order['id']}/review",
                                   data={"score": "5", "content": "师傅上门很快，处理专业，非常满意"},
                                   follow_redirects=True)
            check("感谢您的评价" in body(response), "学生评价提交成功")
            review = db.query_one("SELECT score, content FROM repair_review WHERE order_id = %s",
                                  (order["id"],))
            check(review is not None and review["score"] == 5, "评价记录写入 repair_review 表")

            response = client.post(f"/student/orders/{order['id']}/review",
                                   data={"score": "1", "content": "重复评价"}, follow_redirects=True)
            check("已经评价过" in body(response), "重复评价被拦截")
            check(db.query_value("SELECT COUNT(*) AS c FROM repair_review WHERE order_id = %s",
                                 (order["id"],)) == 1, "数据库中仍只有一条评价记录")

            db.execute(
                "INSERT INTO repair_order (order_no, student_id, category_id, building, dorm_no, "
                "description, phone) VALUES (%s, %s, %s, '1号楼', '101', '自检用未完成工单', '13900001234')",
                (f"RXSMOKE{suffix}", student_id, category_id))
            pending_id = db.query_value("SELECT id FROM repair_order WHERE order_no = %s",
                                        (f"RXSMOKE{suffix}",))
            order_ids.append(pending_id)
            response = client.post(f"/student/orders/{pending_id}/review",
                                   data={"score": "5", "content": "提前评价"}, follow_redirects=True)
            check("完成" in body(response), "未完成工单不允许评价")

            # ------------------------------------- 6. 管理员检索与数据统计
            print("\n[6] 管理员工单检索、数据统计")
            check(order["order_no"] in body(admin_client.get(f"/admin/orders?keyword={order['order_no']}")),
                  "按工单号检索到目标工单")
            check(order["order_no"] in body(admin_client.get("/admin/orders?status=completed&keyword=606")),
                  "按状态 + 关键词组合检索正常")
            check(admin_client.get("/admin/orders?deleted=deleted").status_code == 200,
                  "「已删除工单」筛选页可正常打开")
            html = body(admin_client.get("/admin/statistics"))
            check("工单数据统计" in html and "维修人员工作量与评分排名" in html, "数据统计页面正常渲染")
            check(worker_username in body(admin_client.get("/admin/users")), "用户管理页展示新建账号")
            check("非常满意" in body(admin_client.get("/admin/reviews")), "评价记录页展示评价内容")
            check(admin_client.get("/admin/dashboard").status_code == 200, "管理端概览页正常")

            # -------------------------------------- 7. 删除无效工单与恢复
            print("\n[7] 管理员删除无效工单与恢复")
            response = admin_client.post(f"/admin/orders/{pending_id}/delete",
                                         data={"reason": "自检产生的无效工单"},
                                         follow_redirects=True)
            check("已删除" in body(response), "管理员删除无效工单成功")
            check(db.query_value("SELECT is_deleted FROM repair_order WHERE id = %s",
                                 (pending_id,)) == 1, "删除采用逻辑删除（is_deleted = 1）")
            check(f"RXSMOKE{suffix}" not in body(client.get("/student/orders")),
                  "被删除工单不再对学生展示")
            response = admin_client.post(f"/admin/orders/{pending_id}/restore", follow_redirects=True)
            check("已恢复" in body(response), "管理员恢复工单成功")

            # -------------------------------------- 8. 权限控制与异常页面
            print("\n[8] 权限控制与异常页面")
            check("没有权限访问" in body(client.get("/admin/users", follow_redirects=True)),
                  "学生访问管理页面被拒绝")
            check(client.get("/worker/orders/pending", follow_redirects=True).status_code == 200,
                  "角色越权访问时安全重定向")
            anonymous = app.test_client()
            check("请先登录" in body(anonymous.get("/student/orders", follow_redirects=True)),
                  "未登录访问受保护页面被拦截")
            check(anonymous.get("/not-exist-page").status_code == 404, "404 页面正常返回")
            check(anonymous.get("/").status_code == 200, "未登录可正常访问系统首页")

            # ------------------------------------------------ 9. 清理数据
            print("\n[9] 清理自检产生的测试数据")
            uploaded: list[str] = []
            for oid in order_ids:
                uploaded += [r["file_path"] for r in db.query_all(
                    "SELECT file_path FROM order_image WHERE order_id = %s", (oid,))]
                for table in ("repair_review", "order_log", "order_image"):
                    db.execute(f"DELETE FROM {table} WHERE order_id = %s", (oid,))
                db.execute("DELETE FROM repair_order WHERE id = %s", (oid,))
            db.execute("DELETE FROM sys_user WHERE id = %s", (student_id,))
            db.execute("DELETE FROM sys_user WHERE id = %s", (worker_id,))
            check(db.query_value("SELECT COUNT(*) AS c FROM sys_user WHERE username = %s",
                                 (student_username,)) == 0, "测试账号与其工单已清理")
            for relative in uploaded:
                abs_path = os.path.join(app.root_path, "static", relative.replace("/", os.sep))
                if os.path.isfile(abs_path):
                    os.remove(abs_path)
    except Exception as exc:
        FAILED.append(f"脚本异常：{type(exc).__name__}: {exc}")
        print(f"\n[异常] {type(exc).__name__}: {exc}")
        raise
    finally:
        print("\n================ 自检结果 ================")
        print(f"通过：{PASSED} 项    失败：{len(FAILED)} 项")
        for item in FAILED:
            print(f"  - 未通过：{item}")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
