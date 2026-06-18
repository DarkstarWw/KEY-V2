"""后台管理蓝图：站长管理用户角色（设/撤管理员）。

仅站长（owner）可访问；不可修改站长自身角色，亦不可将他人设为站长。
"""

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_login import login_required

from ..extensions import db
from ..models import ROLE_ADMIN, ROLE_OWNER, ROLE_USER, User
from ..utils import owner_required

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/admin")
@login_required
@owner_required
def dashboard():
	"""后台首页：用户列表与角色管理。"""
	users = User.query.order_by(User.created_at.asc()).all()
	return render_template("admin.html", users=users, active="", title="后台管理")


@admin_bp.route("/admin/role", methods=["POST"])
@login_required
@owner_required
def set_role():
	"""设置用户角色：仅允许在管理员与普通用户之间切换。"""
	user_id = request.form.get("user_id", type=int)
	role = request.form.get("role")

	if role not in (ROLE_ADMIN, ROLE_USER):
		flash("角色参数错误", "error")
		return redirect(url_for("admin.dashboard"))

	user = db.session.get(User, user_id)
	if not user:
		flash("用户不存在", "error")
		return redirect(url_for("admin.dashboard"))
	if user.is_owner:
		flash("不可修改站长角色", "error")
		return redirect(url_for("admin.dashboard"))

	user.role = role
	db.session.commit()
	flash("角色已更新", "ok")
	return redirect(url_for("admin.dashboard"))


@admin_bp.route("/admin/search_users")
@login_required
@owner_required
def search_users():
	"""按邮箱或昵称模糊搜索用户（供权限弹窗使用）。

	查询参数：
		q (str): 关键字，匹配邮箱或昵称，至少 1 个字符。

	Returns:
		flask.Response: JSON，items 为命中用户列表（含头像、角色）。
	"""
	keyword = (request.args.get("q") or "").strip()
	if not keyword:
		return jsonify(items=[])

	like = f"%{keyword}%"
	users = (
		User.query.filter(
			db.or_(User.email.ilike(like), User.nickname.ilike(like))
		)
		.order_by(User.created_at.asc())
		.limit(20)
		.all()
	)
	items = [
		{
			"id": u.id,
			"email": u.email,
			"nickname": u.nickname,
			"role": u.role,
			"is_owner": u.role == ROLE_OWNER,
			"avatar": (
				url_for("static", filename="avatars/" + u.avatar) if u.avatar else ""
			),
			"initial": u.nickname[0] if u.nickname else "?",
		}
		for u in users
	]
	return jsonify(items=items)
