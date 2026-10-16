# -*- coding: utf-8 -*-
"""认证视图：注册、登录、退出、个人资料与密码。"""
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

from app.exceptions import BusinessError
from app.services import auth_service
from app.utils.decorators import login_required

bp = Blueprint("auth", __name__, url_prefix="/auth")


def _safe_next(default_endpoint: str) -> str:
    """防止开放重定向：只允许站内相对地址。"""
    target = request.args.get("next") or request.form.get("next") or ""
    if target.startswith("/") and not target.startswith("//"):
        return target
    return url_for(default_endpoint)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        try:
            user = auth_service.login(username, password)
        except BusinessError as exc:
            flash(exc.message, "danger")
            return render_template("auth/login.html", username=username), 200

        # 登录成功：重建 session，防止会话固定攻击
        session.clear()
        session["user_id"] = user["id"]
        session["username"] = user["username"]
        session["real_name"] = user["real_name"]
        session["role"] = user["role"]
        flash(f"欢迎回来，{user['real_name']}！", "success")
        return redirect(_safe_next("main.dashboard"))
    return render_template("auth/login.html")


@bp.route("/register", methods=["GET", "POST"])
def register():
    """学生自助注册账号。"""
    if request.method == "POST":
        try:
            auth_service.register_student(request.form)
        except BusinessError as exc:
            flash(exc.message, "danger")
            return render_template("auth/register.html", form=request.form), 200
        flash("注册成功，请使用新账号登录", "success")
        return redirect(url_for("auth.login"))
    return render_template("auth/register.html")


@bp.route("/logout")
def logout():
    session.clear()
    flash("已安全退出登录", "info")
    return redirect(url_for("auth.login"))


@bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    user_id = session["user_id"]
    if request.method == "POST":
        try:
            auth_service.update_profile(user_id, request.form)
        except BusinessError as exc:
            flash(exc.message, "danger")
            return render_template("auth/profile.html"), 200
        # 同步会话里的姓名，导航栏立即生效
        session["real_name"] = request.form.get("real_name", "").strip()
        flash("个人资料已更新", "success")
        return redirect(url_for("auth.profile"))
    return render_template("auth/profile.html")


@bp.route("/change-password", methods=["POST"])
@login_required
def change_password():
    try:
        auth_service.change_password(
            session["user_id"],
            request.form.get("old_password"),
            request.form.get("new_password"),
            request.form.get("confirm_password"),
        )
    except BusinessError as exc:
        flash(exc.message, "danger")
        return redirect(url_for("auth.profile"))
    flash("密码修改成功，请牢记新密码", "success")
    return redirect(url_for("auth.profile"))
