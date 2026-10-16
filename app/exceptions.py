# -*- coding: utf-8 -*-
"""自定义异常：把"业务校验失败"与"程序错误"区分开。

服务层校验不通过时抛出 BusinessError，视图层捕获后转成 flash 提示；
其他未捕获异常交由全局 500 错误处理器统一记录。
"""


class BusinessError(Exception):
    """业务规则校验失败（例如：账号已存在、工单已被别人接单）。"""

    def __init__(self, message: str = "操作失败"):
        super().__init__(message)
        self.message = message


class DatabaseError(RuntimeError):
    """数据库连接或执行异常。"""
