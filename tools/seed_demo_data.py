# -*- coding: utf-8 -*-
"""演示数据生成脚本：为课程设计答辩准备一批贴近真实的报修数据。

会创建：
    - 6 名学生演示账号（demo_stu01 ~ demo_stu06，密码 123456）
    - 2 名维修人员演示账号（demo_wrk01、demo_wrk02，密码 123456）
    - 近 6 个月约 30 条报修工单（含待受理 / 维修中 / 已完成 / 已评价 / 已删除）
    - 对应的工单流转日志与维修评价

使用方式::

    python tools/seed_demo_data.py            # 生成演示数据
    python tools/seed_demo_data.py --clear    # 删除演示数据（不影响其它数据）

所有演示工单号统一以 RXDEMO 开头，便于识别与清理。
"""
from __future__ import annotations

import argparse
import os
import random
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from werkzeug.security import generate_password_hash  # noqa: E402

from app import create_app  # noqa: E402
from app.utils import db  # noqa: E402

ORDER_PREFIX = "RXDEMO"

STUDENTS = [
    ("demo_stu01", "李欣然", "D20230101", "1号楼 208", "13910000001"),
    ("demo_stu02", "陈子豪", "D20230102", "2号楼 315", "13910000002"),
    ("demo_stu03", "王雨桐", "D20230103", "3号楼 512", "13910000003"),
    ("demo_stu04", "刘一鸣", "D20230104", "4号楼 106", "13910000004"),
    ("demo_stu05", "赵思远", "D20230105", "5号楼 601", "13910000005"),
    ("demo_stu06", "孙梦琪", "D20230106", "研究生公寓 302", "13910000006"),
]

WORKERS = [
    ("demo_wrk01", "赵师傅", "W2001", "水电维修", "13710000001"),
    ("demo_wrk02", "周师傅", "W2002", "门窗家具", "13710000002"),
]

# 各类别常见的报修描述，让演示数据看起来更真实
DESCRIPTIONS = {
    "水电维修": [
        "洗手台下水管道漏水，地面已经积水，晚上开始出现",
        "宿舍水龙头关不紧，一直在滴水，比较浪费水",
        "卫生间下水道堵塞，排水很慢，洗漱后积水下不去",
        "淋浴花洒出水很小且有异响，影响正常洗澡",
    ],
    "照明电路": [
        "宿舍进门处的灯不亮了，开关按下去没有反应",
        "书桌上方的灯管闪烁，有时还会自动熄灭",
        "插座没有电，插充电器无法充电，怀疑跳闸",
    ],
    "门窗家具": [
        "宿舍门锁卡涩，关门后需要用力反复扭动钥匙",
        "阳台推拉窗推不动，轨道好像变形了",
        "上床的爬梯焊点松动，踩上去晃动，存在安全隐患",
    ],
    "网络通信": [
        "宿舍网口没有信号，网线插上后指示灯不亮",
        "无线网络连接频繁断开，重启路由器也无法解决",
    ],
    "空调制冷": [
        "空调开机后不制冷，出风温度接近室温",
        "空调外机噪音很大，晚上影响休息",
        "空调遥控器失灵，无法调节温度",
    ],
    "其他": [
        "宿舍墙壁有渗水痕迹，担心后续会影响电路",
        "阳台晾衣杆断裂，衣服无法晾晒",
    ],
}

REVIEW_TEXTS = {
    5: ["师傅上门很快，处理专业，非常满意", "维修及时，态度很好，问题一次解决", "响应速度快，服务态度赞"],
    4: ["维修比较及时，问题解决了", "师傅态度不错，就是来得稍晚一些"],
    3: ["问题解决了，不过等待时间有点长"],
}

BUILDINGS = ["1号楼", "2号楼", "3号楼", "4号楼", "5号楼", "6号楼", "研究生公寓"]


def ensure_user(username: str, real_name: str, role: str, phone: str,
                student_no=None, dorm_no=None, worker_no=None, skill=None) -> int:
    """账号不存在则创建，返回用户 id。"""
    user_id = db.query_value("SELECT id FROM sys_user WHERE username = %s", (username,))
    if user_id:
        return user_id
    db.execute(
        "INSERT INTO sys_user (username, password_hash, role, real_name, phone, "
        "student_no, dorm_no, worker_no, skill) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
        (username, generate_password_hash("123456", method="pbkdf2:sha256", salt_length=16),
         role, real_name, phone, student_no, dorm_no, worker_no, skill),
    )
    return db.query_value("SELECT id FROM sys_user WHERE username = %s", (username,))


def clear_demo_orders() -> int:
    """删除所有 RXDEMO 开头的演示工单及其关联数据。"""
    ids = [r["id"] for r in db.query_all(
        "SELECT id FROM repair_order WHERE order_no LIKE %s", (f"{ORDER_PREFIX}%",))]
    for order_id in ids:
        for table in ("repair_review", "order_log", "order_image"):
            db.execute(f"DELETE FROM {table} WHERE order_id = %s", (order_id,))
        db.execute("DELETE FROM repair_order WHERE id = %s", (order_id,))
    return len(ids)


def main() -> int:
    parser = argparse.ArgumentParser(description="生成宿舍报修系统演示数据")
    parser.add_argument("--clear", action="store_true", help="只删除演示数据，不生成新数据")
    parser.add_argument("--seed", type=int, default=20261016, help="随机种子，保证数据可复现")
    args = parser.parse_args()

    app = create_app()
    random.seed(args.seed)

    with app.app_context():
        removed = clear_demo_orders()
        print(f"[信息] 已清理历史演示工单 {removed} 条")
        if args.clear:
            print("[完成] 演示数据已删除")
            return 0

        # 1. 演示账号
        student_ids = [
            ensure_user(username, name, "student", phone, student_no=student_no, dorm_no=dorm_no)
            for username, name, student_no, dorm_no, phone in STUDENTS
        ]
        worker_ids = [
            ensure_user(username, name, "worker", phone, worker_no=worker_no, skill=skill)
            for username, name, worker_no, skill, phone in WORKERS
        ]
        # 复用系统自带的维修人员，让统计排名更丰富
        built_in_workers = [r["id"] for r in db.query_all(
            "SELECT id FROM sys_user WHERE role = 'worker' AND username LIKE %s", ("worker%",))]
        all_workers = worker_ids + built_in_workers
        categories = db.query_all("SELECT id, name FROM fault_category WHERE is_active = 1")

        # 2. 生成近 6 个月的工单
        today = datetime.now()
        created_count = reviewed_count = 0
        for month_offset in range(5, -1, -1):
            # 以每月 1 号为基准，往前推 month_offset 个月
            base = (today.replace(day=1) - timedelta(days=month_offset * 30)).replace(day=1)
            orders_this_month = random.randint(4, 7)
            for _ in range(orders_this_month):
                category = random.choice(categories)
                description = random.choice(
                    DESCRIPTIONS.get(category["name"], ["宿舍设施出现故障，需要维修"]))
                student_index = random.randrange(len(student_ids))
                student_id = student_ids[student_index]
                dorm_no = STUDENTS[student_index][3]
                building = random.choice(BUILDINGS)
                created_at = base + timedelta(
                    days=random.randint(0, 27), hours=random.randint(8, 21),
                    minutes=random.randint(0, 59))
                if created_at > today:
                    created_at = today - timedelta(hours=random.randint(1, 48))

                # 当月最后几天的工单留一部分未完成，更贴近真实情况
                recent = month_offset == 0
                roll = random.random()
                if recent and roll < 0.45:
                    status = "pending"
                elif recent and roll < 0.75:
                    status = "processing"
                else:
                    status = "completed"

                worker_id = None
                accepted_at = completed_at = None
                if status in ("processing", "completed"):
                    worker_id = random.choice(all_workers)
                    accepted_at = created_at + timedelta(hours=random.randint(1, 20))
                if status == "completed":
                    completed_at = accepted_at + timedelta(
                        hours=random.randint(1, 26), minutes=random.randint(0, 59))
                    if completed_at > today:
                        completed_at = today

                order_no = f"{ORDER_PREFIX}{created_at:%Y%m%d}{random.randint(1000, 9999)}"
                order_id = db.execute(
                    "INSERT INTO repair_order (order_no, student_id, worker_id, category_id, building, "
                    "dorm_no, description, phone, status, created_at, accepted_at, completed_at) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                    (order_no, student_id, worker_id, category["id"], building, dorm_no,
                     description, STUDENTS[student_index][4], status,
                     created_at, accepted_at, completed_at),
                )
                created_count += 1

                # 流转日志
                db.execute(
                    "INSERT INTO order_log (order_id, operator_id, action, status, remark, created_at) "
                    "VALUES (%s, %s, 'create', 'pending', %s, %s)",
                    (order_id, student_id, f"学生提交报修申请，故障类别：{category['name']}", created_at),
                )
                if accepted_at:
                    db.execute(
                        "INSERT INTO order_log (order_id, operator_id, action, status, remark, created_at) "
                        "VALUES (%s, %s, 'accept', 'processing', '维修人员已接单，准备上门处理', %s)",
                        (order_id, worker_id, accepted_at),
                    )
                if completed_at:
                    db.execute(
                        "INSERT INTO order_log (order_id, operator_id, action, status, remark, created_at) "
                        "VALUES (%s, %s, 'complete', 'completed', %s, %s)",
                        (order_id, worker_id, f"故障已处理完成：{description[:14]}（已测试正常）", completed_at),
                    )

                # 评价：已完成工单中约 80% 有评价
                if status == "completed" and random.random() < 0.8:
                    score = random.choices([5, 4, 3], weights=[6, 3, 1])[0]
                    review_time = completed_at + timedelta(hours=random.randint(1, 40))
                    if review_time > today:
                        review_time = today
                    db.execute(
                        "INSERT INTO repair_review (order_id, student_id, score, content, created_at) "
                        "VALUES (%s, %s, %s, %s, %s)",
                        (order_id, student_id, score, random.choice(REVIEW_TEXTS[score]), review_time),
                    )
                    db.execute(
                        "INSERT INTO order_log (order_id, operator_id, action, remark, created_at) "
                        "VALUES (%s, %s, 'review', %s, %s)",
                        (order_id, student_id, f"学生已评价，评分 {score} 星", review_time),
                    )
                    reviewed_count += 1

        # 3. 造两条无效工单（逻辑删除），用于演示管理员删除功能
        deleted_ids = [r["id"] for r in db.query_all(
            "SELECT id FROM repair_order WHERE status = 'pending' ORDER BY id DESC LIMIT 2")]
        for order_id in deleted_ids:
            db.execute("UPDATE repair_order SET is_deleted = 1 WHERE id = %s", (order_id,))
            db.execute(
                "INSERT INTO order_log (order_id, operator_id, action, remark) "
                "SELECT id, NULL, 'admin_delete', '演示数据：学生重复提交，管理员判定为无效工单' "
                "FROM repair_order WHERE id = %s", (order_id,))

        total = db.query_value("SELECT COUNT(*) AS c FROM repair_order")
        print(f"[完成] 演示数据生成成功：新增工单 {created_count} 条（含评价 {reviewed_count} 条），"
              f"逻辑删除 {len(deleted_ids)} 条")
        print(f"        当前库内工单总数：{total} 条")
        print("\n        演示账号（密码均为 123456）：")
        print("          - 学生：demo_stu01 ~ demo_stu06")
        print("          - 维修：demo_wrk01、demo_wrk02")
    return 0


if __name__ == "__main__":
    sys.exit(main())
