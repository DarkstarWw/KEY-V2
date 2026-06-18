"""图组蓝图：首页、分类、搜索、详情、上传与删除。

仅管理员（含站长）可上传与删除图组；上传时需选择封面图。
"""

import os

from flask import (
	Blueprint,
	abort,
	current_app,
	flash,
	redirect,
	render_template,
	request,
	url_for,
)
from flask_login import current_user, login_required

from ..extensions import db
from ..models import Gallery, Image
from ..utils import admin_required, allowed_file, save_image

gallery_bp = Blueprint("gallery", __name__)


def _valid_categories():
	"""返回合法分类标识集合。"""
	return {key for key, _ in current_app.config["CATEGORIES"]}


@gallery_bp.route("/")
def index():
	"""首页：所有分类最新图组按上传时间倒序混合展示（分页）。"""
	page = request.args.get("page", 1, type=int)
	pagination = (
		Gallery.query.order_by(Gallery.created_at.desc())
		.paginate(page=page, per_page=current_app.config["PER_PAGE"], error_out=False)
	)
	return render_template(
		"index.html", galleries=pagination.items, pagination=pagination,
		active="home", title="首页",
	)


@gallery_bp.route("/c/<category>")
def category(category):
	"""分类页：仅展示该分类下的图组（分页）。"""
	if category not in _valid_categories():
		abort(404)
	page = request.args.get("page", 1, type=int)
	pagination = (
		Gallery.query.filter_by(category=category)
		.order_by(Gallery.created_at.desc())
		.paginate(page=page, per_page=current_app.config["PER_PAGE"], error_out=False)
	)
	label = dict(current_app.config["CATEGORIES"]).get(category, category)
	return render_template(
		"index.html", galleries=pagination.items, pagination=pagination,
		active=category, title=label,
	)


@gallery_bp.route("/search")
def search():
	"""搜索：按图组标题关键词或上传者昵称匹配（分页）。"""
	from ..models import User

	keyword = (request.args.get("q") or "").strip()
	page = request.args.get("page", 1, type=int)
	pagination = None
	galleries = []
	if keyword:
		like = f"%{keyword}%"
		pagination = (
			Gallery.query.join(User, Gallery.uploader_id == User.id)
			.filter(db.or_(Gallery.title.ilike(like), User.nickname.ilike(like)))
			.order_by(Gallery.created_at.desc())
			.paginate(page=page, per_page=current_app.config["PER_PAGE"], error_out=False)
		)
		galleries = pagination.items
	return render_template(
		"search.html", galleries=galleries, pagination=pagination,
		keyword=keyword, active="", title="搜索",
	)


@gallery_bp.route("/gallery/<int:gid>")
def detail(gid):
	"""图组详情：一行多图排布，支持评论、评分、收藏。"""
	gallery = db.session.get(Gallery, gid)
	if not gallery:
		abort(404)
	return render_template("gallery_detail.html", gallery=gallery, active="", title=gallery.title)


@gallery_bp.route("/upload", methods=["GET", "POST"])
@login_required
@admin_required
def upload():
	"""上传图组（管理员）：填写标题、分类、多图，并指定封面。"""
	if request.method == "GET":
		return render_template("upload.html", active="", title="上传图组")

	title = (request.form.get("title") or "").strip()
	description = (request.form.get("description") or "").strip()
	category = request.form.get("category")
	cover_index = request.form.get("cover_index", "0")
	files = request.files.getlist("images")

	if not title or category not in _valid_categories():
		flash("请填写标题并选择正确分类", "error")
		return render_template("upload.html", active="", title="上传图组")
	files = [f for f in files if f and f.filename]
	if not files:
		flash("请至少选择一张图片", "error")
		return render_template("upload.html", active="", title="上传图组")

	gallery = Gallery(
		title=title,
		description=description,
		category=category,
		uploader_id=current_user.id,
	)
	db.session.add(gallery)
	db.session.flush()  # 取得 gallery.id

	try:
		cover_idx = int(cover_index)
	except ValueError:
		cover_idx = 0

	saved_images = []
	for idx, file_storage in enumerate(files):
		if not allowed_file(file_storage.filename):
			continue
		name, thumb = save_image(file_storage)
		image = Image(
			gallery_id=gallery.id,
			filename=name,
			thumb_filename=thumb,
			order_index=idx,
		)
		db.session.add(image)
		saved_images.append((idx, image))

	if not saved_images:
		db.session.rollback()
		flash("图片格式不支持", "error")
		return render_template("upload.html", active="", title="上传图组")

	db.session.flush()
	# 设置封面：匹配选中索引，越界则取第一张
	cover_image = next((img for i, img in saved_images if i == cover_idx), saved_images[0][1])
	gallery.cover_image_id = cover_image.id
	db.session.commit()

	flash("上传成功", "ok")
	return redirect(url_for("gallery.detail", gid=gallery.id))


@gallery_bp.route("/gallery/<int:gid>/delete", methods=["POST"])
@login_required
@admin_required
def delete(gid):
	"""删除图组（管理员）：同时清理磁盘上的图片文件。"""
	gallery = db.session.get(Gallery, gid)
	if not gallery:
		abort(404)

	folder = current_app.config["UPLOAD_FOLDER"]
	for image in gallery.images:
		for fname in (image.filename, image.thumb_filename):
			path = os.path.join(folder, fname)
			if os.path.exists(path):
				try:
					os.remove(path)
				except OSError:
					current_app.logger.warning("删除文件失败：%s", path)

	db.session.delete(gallery)
	db.session.commit()
	flash("已删除图组", "ok")
	return redirect(url_for("gallery.index"))
