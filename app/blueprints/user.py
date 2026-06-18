"""个人中心蓝图：资料、改密、改昵称、换头像、简介、收藏看板。

昵称修改受冷却限制（默认 30 天一次）。
"""

from datetime import datetime, timedelta

from flask import (
	Blueprint,
	current_app,
	flash,
	jsonify,
	redirect,
	render_template,
	request,
	url_for,
)
from flask_login import current_user, login_required

from ..extensions import db
from ..models import (
	Favorite,
	Gallery,
	Image,
	TARGET_GALLERY,
	TARGET_IMAGE,
	User,
)
from ..utils import allowed_file, save_avatar

user_bp = Blueprint("user", __name__)


@user_bp.route("/api/users")
def list_users():
	"""分页列出全站用户（供首页/分类页侧栏使用，公开只读）。

	查询参数：
		page (int): 页码，默认 1，每页 20 人。

	Returns:
		flask.Response: JSON，items 含头像、昵称、角色；附分页信息。
	"""
	page = request.args.get("page", 1, type=int)
	pagination = (
		User.query.order_by(User.created_at.asc())
		.paginate(page=page, per_page=20, error_out=False)
	)
	items = [
		{
			"id": u.id,
			"nickname": u.nickname,
			"role": u.role,
			"avatar": (
				url_for("static", filename="avatars/" + u.avatar) if u.avatar else ""
			),
			"initial": u.nickname[0] if u.nickname else "?",
		}
		for u in pagination.items
	]
	return jsonify(
		items=items,
		page=pagination.page,
		pages=pagination.pages,
		total=pagination.total,
		has_next=pagination.has_next,
		has_prev=pagination.has_prev,
	)


@user_bp.route("/me")
@login_required
def profile():
	"""个人资料页。"""
	return render_template("profile.html", active="", title="个人中心")


@user_bp.route("/me/password", methods=["POST"])
@login_required
def change_password():
	"""修改密码：需校验原密码。"""
	old = request.form.get("old_password") or ""
	new = request.form.get("new_password") or ""
	if not current_user.check_password(old):
		flash("原密码错误", "error")
		return redirect(url_for("user.profile"))
	if len(new) < 6:
		flash("新密码至少 6 位", "error")
		return redirect(url_for("user.profile"))
	current_user.set_password(new)
	db.session.commit()
	flash("密码已更新", "ok")
	return redirect(url_for("user.profile"))


@user_bp.route("/me/nickname", methods=["POST"])
@login_required
def change_nickname():
	"""修改昵称：唯一校验 + 冷却限制。"""
	nickname = (request.form.get("nickname") or "").strip()
	if not nickname or len(nickname) > 32:
		flash("昵称长度不合法", "error")
		return redirect(url_for("user.profile"))

	cooldown = current_app.config["NICKNAME_CHANGE_DAYS"]
	last = current_user.nickname_changed_at
	if last and datetime.utcnow() - last < timedelta(days=cooldown):
		remain = cooldown - (datetime.utcnow() - last).days
		flash(f"昵称每 {cooldown} 天仅可改一次，还需 {remain} 天", "error")
		return redirect(url_for("user.profile"))

	if nickname == current_user.nickname:
		flash("昵称未变化", "error")
		return redirect(url_for("user.profile"))
	if User.query.filter_by(nickname=nickname).first():
		flash("昵称已被占用", "error")
		return redirect(url_for("user.profile"))

	current_user.nickname = nickname
	current_user.nickname_changed_at = datetime.utcnow()
	db.session.commit()
	flash("昵称已更新", "ok")
	return redirect(url_for("user.profile"))


@user_bp.route("/me/avatar", methods=["POST"])
@login_required
def change_avatar():
	"""更换头像。"""
	file_storage = request.files.get("avatar")
	if not file_storage or not file_storage.filename:
		flash("请选择头像图片", "error")
		return redirect(url_for("user.profile"))
	if not allowed_file(file_storage.filename):
		flash("头像格式不支持", "error")
		return redirect(url_for("user.profile"))
	current_user.avatar = save_avatar(file_storage)
	db.session.commit()
	flash("头像已更新", "ok")
	return redirect(url_for("user.profile"))


@user_bp.route("/me/bio", methods=["POST"])
@login_required
def change_bio():
	"""更新个人简介。"""
	bio = (request.form.get("bio") or "").strip()
	if len(bio) > 500:
		flash("简介过长", "error")
		return redirect(url_for("user.profile"))
	current_user.bio = bio
	db.session.commit()
	flash("简介已更新", "ok")
	return redirect(url_for("user.profile"))


@user_bp.route("/me/favorites")
@login_required
def favorites():
	"""收藏看板：分别展示收藏的图组与单图。"""
	favs = Favorite.query.filter_by(user_id=current_user.id).order_by(
		Favorite.created_at.desc()
	).all()

	gallery_ids = [f.target_id for f in favs if f.target_type == TARGET_GALLERY]
	image_ids = [f.target_id for f in favs if f.target_type == TARGET_IMAGE]

	fav_galleries = (
		Gallery.query.filter(Gallery.id.in_(gallery_ids)).all() if gallery_ids else []
	)
	fav_images = Image.query.filter(Image.id.in_(image_ids)).all() if image_ids else []

	return render_template(
		"favorites.html",
		fav_galleries=fav_galleries,
		fav_images=fav_images,
		active="fav",
		title="我的收藏",
	)
