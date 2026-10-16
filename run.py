# -*- coding: utf-8 -*-
"""宿舍报修管理系统 —— 启动入口。

使用方式: python run.py
启动后浏览器访问 http://127.0.0.1:5000
"""
from app import create_app

app = create_app()

if __name__ == "__main__":
    # debug=True 便于开发阶段自动重载，正式部署请关闭
    app.run(host="127.0.0.1", port=5000, debug=True)
