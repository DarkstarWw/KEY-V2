"""数据模型定义。

包含用户、图组、图片、评论、评分、收藏与邮箱验证码等核心实体。
角色分三级：owner（站长）、admin（管理员）、user（普通用户）。
"""

from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db, login_manager

# 角色常量
ROLE_OWNER = "owner"
ROLE_ADMIN = "admin"
ROLE_USER = "user"

# 收藏 / 评论目标类型
TARGET_GALLERY = "gallery"
TARGET_IMAGE = "image"


@login_manager.user_loader
def load_user(user_id):
	"""Flask-Login 回调：按主键加载用户。

	Args:
		user_id: 会话中存储的用户主键字符串。

	Returns:
		User | None: 对应用户对象，不存在则为 None。
	"""
	return db.session.get(User, int(user_id))


class User(UserMixin, db.Model):
	"""网站用户。"""

	__tablename__ = "users"

	id = db.Column(db.Integer, primary_key=True)
	email = db.Column(db.String(120), unique=True, nullable=False, index=True)
	nickname = db.Column(db.String(32), unique=True, nullable=False, index=True)
	password_hash = db.Column(db.String(256), nullable=False)
	role = db.Column(db.String(16), nullable=False, default=ROLE_USER)
	avatar = db.Column(db.String(256), default="")
	bio = db.Column(db.String(500), default="")
	nickname_changed_at = db.Column(db.DateTime)
	created_at = db.Column(db.DateTime, default=datetime.utcnow)

	def set_password(self, raw):
		"""设置密码（自动哈希存储）。"""
		self.password_hash = generate_password_hash(raw)

	def check_password(self, raw):
		"""校验明文密码是否匹配。"""
		return check_password_hash(self.password_hash, raw)

	@property
	def is_admin(self):
		"""是否具备管理员及以上权限（站长或管理员）。"""
		return self.role in (ROLE_OWNER, ROLE_ADMIN)

	@property
	def is_owner(self):
		"""是否为站长。"""
		return self.role == ROLE_OWNER


class Gallery(db.Model):
	"""图组：一组图片的集合，归属单一分类，由管理员上传。"""

	__tablename__ = "galleries"

	id = db.Column(db.Integer, primary_key=True)
	title = db.Column(db.String(120), nullable=False, index=True)
	description = db.Column(db.String(1000), default="")
	category = db.Column(db.String(32), nullable=False, index=True)
	cover_image_id = db.Column(db.Integer)
	uploader_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
	created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

	uploader = db.relationship("User", backref="galleries")
	images = db.relationship(
		"Image",
		backref="gallery",
		cascade="all, delete-orphan",
		order_by="Image.order_index",
	)

	@property
	def cover(self):
		"""返回封面图片对象：优先指定封面，否则取第一张。"""
		if self.cover_image_id:
			for img in self.images:
				if img.id == self.cover_image_id:
					return img
		return self.images[0] if self.images else None

	@property
	def image_count(self):
		"""图组内图片数量。"""
		return len(self.images)


class Image(db.Model):
	"""单张图片，隶属于某个图组。"""

	__tablename__ = "images"

	id = db.Column(db.Integer, primary_key=True)
	gallery_id = db.Column(db.Integer, db.ForeignKey("galleries.id"), nullable=False, index=True)
	filename = db.Column(db.String(256), nullable=False)        # 原图文件名
	thumb_filename = db.Column(db.String(256), nullable=False)  # 缩略图文件名
	order_index = db.Column(db.Integer, default=0)
	created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Comment(db.Model):
	"""评论，支持楼中楼（parent_id 指向父评论）。

	target_type 区分评论对象为图组还是单图。
	"""

	__tablename__ = "comments"

	id = db.Column(db.Integer, primary_key=True)
	target_type = db.Column(db.String(16), nullable=False)
	target_id = db.Column(db.Integer, nullable=False)
	user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
	parent_id = db.Column(db.Integer, db.ForeignKey("comments.id"))
	content = db.Column(db.String(1000), nullable=False)
	created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

	user = db.relationship("User")


class Rating(db.Model):
	"""单图评分，每位用户对同一张图仅一条记录，可修改。"""

	__tablename__ = "ratings"
	__table_args__ = (db.UniqueConstraint("image_id", "user_id", name="uq_rating"),)

	id = db.Column(db.Integer, primary_key=True)
	image_id = db.Column(db.Integer, db.ForeignKey("images.id"), nullable=False, index=True)
	user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
	score = db.Column(db.Integer, nullable=False)  # 1-5
	updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

	user = db.relationship("User")


class Favorite(db.Model):
	"""收藏，目标可为图组或单图，每位用户对同一目标仅一条。"""

	__tablename__ = "favorites"
	__table_args__ = (
		db.UniqueConstraint("user_id", "target_type", "target_id", name="uq_favorite"),
	)

	id = db.Column(db.Integer, primary_key=True)
	user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
	target_type = db.Column(db.String(16), nullable=False)
	target_id = db.Column(db.Integer, nullable=False)
	created_at = db.Column(db.DateTime, default=datetime.utcnow)


class EmailCode(db.Model):
	"""邮箱验证码，用于注册与登录。

	同一邮箱+用途仅保留最新一条，用于校验有效期与重发间隔。
	"""

	__tablename__ = "email_codes"
	__table_args__ = (db.UniqueConstraint("email", "purpose", name="uq_email_code"),)

	id = db.Column(db.Integer, primary_key=True)
	email = db.Column(db.String(120), nullable=False, index=True)
	purpose = db.Column(db.String(16), nullable=False)  # register / login
	code = db.Column(db.String(8), nullable=False)
	sent_at = db.Column(db.DateTime, default=datetime.utcnow)
