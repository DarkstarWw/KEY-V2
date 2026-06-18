"""互动蓝图：评论（楼中楼）、单图评分、收藏。

均以 JSON API 形式提供，前端通过 fetch 调用并局部刷新。
"""

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from ..extensions import db
from ..models import (
	Comment,
	Favorite,
	Image,
	Rating,
	TARGET_GALLERY,
	TARGET_IMAGE,
)

interact_bp = Blueprint("interact", __name__)

_VALID_TARGETS = (TARGET_GALLERY, TARGET_IMAGE)


def _avatar_url(user):
	"""返回用户头像可访问 URL，无头像则为空串。"""
	from flask import url_for

	if user.avatar:
		return url_for("static", filename=f"avatars/{user.avatar}")
	return ""


@interact_bp.route("/api/comments")
def list_comments():
	"""列出指定目标的全部评论（含楼中楼所需的 parent_id）。"""
	target_type = request.args.get("target_type")
	target_id = request.args.get("target_id", type=int)
	if target_type not in _VALID_TARGETS or not target_id:
		return jsonify(ok=False, msg="参数错误"), 400

	comments = (
		Comment.query.filter_by(target_type=target_type, target_id=target_id)
		.order_by(Comment.created_at.asc())
		.all()
	)
	me = current_user.id if current_user.is_authenticated else None
	is_admin = current_user.is_authenticated and current_user.is_admin
	items = [
		{
			"id": c.id,
			"parent_id": c.parent_id,
			"content": c.content,
			"nickname": c.user.nickname,
			"role": c.user.role,
			"avatar": _avatar_url(c.user),
			"created_at": c.created_at.strftime("%Y-%m-%d %H:%M"),
			"can_delete": is_admin or c.user_id == me,
		}
		for c in comments
	]
	return jsonify(ok=True, items=items)


@interact_bp.route("/api/comment", methods=["POST"])
@login_required
def add_comment():
	"""新增评论，可携带 parent_id 形成楼中楼。"""
	data = request.get_json(silent=True) or {}
	target_type = data.get("target_type")
	target_id = data.get("target_id")
	content = (data.get("content") or "").strip()
	parent_id = data.get("parent_id")

	if target_type not in _VALID_TARGETS or not target_id:
		return jsonify(ok=False, msg="参数错误"), 400
	if not content:
		return jsonify(ok=False, msg="评论内容不能为空"), 400
	if len(content) > 1000:
		return jsonify(ok=False, msg="评论过长"), 400

	comment = Comment(
		target_type=target_type,
		target_id=int(target_id),
		user_id=current_user.id,
		parent_id=int(parent_id) if parent_id else None,
		content=content,
	)
	db.session.add(comment)
	db.session.commit()
	return jsonify(ok=True)


@interact_bp.route("/api/comment/<int:cid>/delete", methods=["POST"])
@login_required
def delete_comment(cid):
	"""删除评论：作者本人或管理员可删。"""
	comment = db.session.get(Comment, cid)
	if not comment:
		return jsonify(ok=False, msg="评论不存在"), 404
	if comment.user_id != current_user.id and not current_user.is_admin:
		return jsonify(ok=False, msg="无权删除"), 403
	db.session.delete(comment)
	db.session.commit()
	return jsonify(ok=True)


@interact_bp.route("/api/rate", methods=["POST"])
@login_required
def rate_image():
	"""对单图打分（1-5）：每人一条记录，可覆盖修改。"""
	data = request.get_json(silent=True) or {}
	image_id = data.get("image_id")
	score = data.get("score")

	if not image_id or score not in (1, 2, 3, 4, 5):
		return jsonify(ok=False, msg="评分参数错误"), 400
	if not db.session.get(Image, int(image_id)):
		return jsonify(ok=False, msg="图片不存在"), 404

	rating = Rating.query.filter_by(image_id=int(image_id), user_id=current_user.id).first()
	if rating:
		rating.score = score
	else:
		rating = Rating(image_id=int(image_id), user_id=current_user.id, score=score)
		db.session.add(rating)
	db.session.commit()
	return jsonify(ok=True)


@interact_bp.route("/api/ratings")
def list_ratings():
	"""列出某图片的全部打分详情、平均分与当前用户评分。"""
	image_id = request.args.get("image_id", type=int)
	if not image_id:
		return jsonify(ok=False, msg="参数错误"), 400

	ratings = Rating.query.filter_by(image_id=image_id).all()
	items = [{"nickname": r.user.nickname, "score": r.score} for r in ratings]
	avg = round(sum(r.score for r in ratings) / len(ratings), 1) if ratings else 0
	my_score = 0
	if current_user.is_authenticated:
		mine = next((r for r in ratings if r.user_id == current_user.id), None)
		my_score = mine.score if mine else 0
	return jsonify(ok=True, items=items, avg=avg, count=len(ratings), my_score=my_score)


@interact_bp.route("/api/favorite", methods=["POST"])
@login_required
def toggle_favorite():
	"""收藏 / 取消收藏，目标可为图组或单图。"""
	data = request.get_json(silent=True) or {}
	target_type = data.get("target_type")
	target_id = data.get("target_id")
	if target_type not in _VALID_TARGETS or not target_id:
		return jsonify(ok=False, msg="参数错误"), 400

	fav = Favorite.query.filter_by(
		user_id=current_user.id, target_type=target_type, target_id=int(target_id)
	).first()
	if fav:
		db.session.delete(fav)
		db.session.commit()
		return jsonify(ok=True, favorited=False)

	fav = Favorite(user_id=current_user.id, target_type=target_type, target_id=int(target_id))
	db.session.add(fav)
	db.session.commit()
	return jsonify(ok=True, favorited=True)


@interact_bp.route("/api/favorite/status")
@login_required
def favorite_status():
	"""查询当前用户对某目标是否已收藏。"""
	target_type = request.args.get("target_type")
	target_id = request.args.get("target_id", type=int)
	if target_type not in _VALID_TARGETS or not target_id:
		return jsonify(ok=False, msg="参数错误"), 400
	fav = Favorite.query.filter_by(
		user_id=current_user.id, target_type=target_type, target_id=target_id
	).first()
	return jsonify(ok=True, favorited=bool(fav))
