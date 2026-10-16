# -*- coding: utf-8 -*-
"""全局常量：角色、工单状态、页面提示文案映射。"""

# ----------------------------------------------------------------- 用户角色
ROLE_STUDENT = "student"
ROLE_WORKER = "worker"
ROLE_ADMIN = "admin"

ROLE_LABEL = {
    ROLE_STUDENT: "学生",
    ROLE_WORKER: "维修人员",
    ROLE_ADMIN: "管理员",
}

# 管理员可以创建的角色（不允许再造管理员，避免越权）
MANAGED_ROLES = (ROLE_STUDENT, ROLE_WORKER)

# ----------------------------------------------------------------- 工单状态
STATUS_PENDING = "pending"        # 待受理
STATUS_PROCESSING = "processing"  # 维修中
STATUS_COMPLETED = "completed"    # 已完成

ORDER_STATUSES = (STATUS_PENDING, STATUS_PROCESSING, STATUS_COMPLETED)

ORDER_STATUS_LABEL = {
    STATUS_PENDING: "待受理",
    STATUS_PROCESSING: "维修中",
    STATUS_COMPLETED: "已完成",
}

# 状态对应的 Bootstrap 5 badge 颜色，模板中直接使用
ORDER_STATUS_BADGE = {
    STATUS_PENDING: "warning text-dark",
    STATUS_PROCESSING: "info text-dark",
    STATUS_COMPLETED: "success",
}

# 工单流转日志的动作说明
ACTION_LABEL = {
    "create": "提交报修",
    "accept": "维修人员接单",
    "processing": "更新为维修中",
    "remark": "补充维修备注",
    "complete": "维修完成",
    "review": "学生评价",
    "admin_delete": "管理员删除工单",
    "admin_restore": "管理员恢复工单",
}

# 宿舍楼栋（提交报修时的下拉选项，也用于管理端按楼栋统计）
DORM_BUILDINGS = (
    "1号楼",
    "2号楼",
    "3号楼",
    "4号楼",
    "5号楼",
    "6号楼",
    "研究生公寓",
    "其他",
)

# 维修工工种（管理员新增维修账号时选择）
WORKER_SKILLS = ("水电维修", "门窗家具", "网络通信", "空调制冷", "综合维修")
