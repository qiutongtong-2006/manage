# -*- coding: utf-8 -*-
"""应用工厂：创建 Flask 应用并注册各层组件。

整体分层结构：

    app/blueprints  视图层（接收请求、渲染模板）
    app/services    业务层（校验规则、状态流转、事务编排）
    app/dao         数据访问层（SQL 语句）
    app/utils       基础设施（MySQL 连接、装饰器、工具函数）
"""
from __future__ import annotations

import logging
import os

from flask import Flask, g, redirect, render_template, request, session, url_for

from config import Config
from app.constants import (
    ACTION_LABEL,
    DORM_BUILDINGS,
    ORDER_STATUS_BADGE,
    ORDER_STATUS_LABEL,
    ORDER_STATUSES,
    ROLE_LABEL,
    STATUS_COMPLETED,
    STATUS_PENDING,
    STATUS_PROCESSING,
    WORKER_SKILLS,
)
from app.exceptions import DatabaseError
from app.services import auth_service
from app.utils import db


def create_app(config_object: type[Config] = Config) -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.from_object(config_object)
    # 让 jsonify 直接输出中文（Flask 2.3+ 通过 app.json 控制）
    app.json.ensure_ascii = False

    _configure_logging(app)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # 数据库连接生命周期
    db.init_app(app)

    _register_blueprints(app)
    _register_request_hooks(app)
    _register_template_context(app)
    _register_error_handlers(app)
    return app


def _configure_logging(app: Flask) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    app.logger.setLevel(logging.INFO)


def _register_blueprints(app: Flask) -> None:
    from app.blueprints.admin import bp as admin_bp
    from app.blueprints.auth import bp as auth_bp
    from app.blueprints.main import bp as main_bp
    from app.blueprints.student import bp as student_bp
    from app.blueprints.worker import bp as worker_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(worker_bp)
    app.register_blueprint(admin_bp)


def _register_request_hooks(app: Flask) -> None:
    @app.before_request
    def load_current_user():
        """每个请求开始时刷新当前登录用户信息，账号被删除/禁用会立即失效。"""
        g.user = None
        user_id = session.get("user_id")
        if not user_id:
            return None
        context = auth_service.current_user_context(user_id)
        if not context:
            session.clear()
            if request.endpoint not in ("static", "auth.login", "main.index"):
                return redirect(url_for("auth.login"))
            return None
        g.user = context
        return None


def _register_template_context(app: Flask) -> None:
    # 常量注册为 Jinja 全局变量：这样 {% from ... import 宏 %} 里也能访问到
    # （context_processor 注入的变量在被 import 的宏中不可见）
    app.jinja_env.globals.update(
        ROLE_LABEL=ROLE_LABEL,
        ORDER_STATUS_LABEL=ORDER_STATUS_LABEL,
        ORDER_STATUS_BADGE=ORDER_STATUS_BADGE,
        ORDER_STATUSES=ORDER_STATUSES,
        ACTION_LABEL=ACTION_LABEL,
        DORM_BUILDINGS=DORM_BUILDINGS,
        WORKER_SKILLS=WORKER_SKILLS,
        STATUS_PENDING=STATUS_PENDING,
        STATUS_PROCESSING=STATUS_PROCESSING,
        STATUS_COMPLETED=STATUS_COMPLETED,
    )

    @app.context_processor
    def inject_globals():
        """把当前登录用户注入所有模板，供导航栏等公共区域使用。"""
        return {"current_user": g.get("user")}

    @app.template_filter("dt")
    def format_datetime(value, fmt: str = "%Y-%m-%d %H:%M"):
        """模板里统一用 {{ order.created_at | dt }} 格式化时间。"""
        if not value:
            return "-"
        return value.strftime(fmt)

    @app.template_filter("stars")
    def stars(score):
        """评分渲染成 ★★★☆☆ 形式。"""
        if not score:
            return "暂无评分"
        score = int(round(float(score)))
        return "★" * score + "☆" * (5 - score)


def _register_error_handlers(app: Flask) -> None:
    @app.errorhandler(404)
    def not_found(error):
        return render_template("errors/404.html"), 404

    @app.errorhandler(403)
    def forbidden(error):
        return render_template("errors/403.html"), 403

    @app.errorhandler(413)
    def too_large(error):
        return render_template(
            "errors/500.html",
            message="上传的文件过大，图片请控制在 5MB 以内",
        ), 413

    @app.errorhandler(DatabaseError)
    def database_error(error):
        app.logger.error("数据库异常: %s", error)
        return render_template("errors/500.html", message=str(error)), 500

    @app.errorhandler(500)
    def server_error(error):
        app.logger.exception("服务器内部错误")
        return render_template(
            "errors/500.html", message="服务器内部错误，请稍后再试"
        ), 500
