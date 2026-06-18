"""应用工厂。

负责创建 Flask 应用、绑定扩展、注册蓝图、建表，并在启动时
将配置中指定的站长邮箱对应用户标记为站长（owner）。
"""

import os

from flask import Flask

from config import Config

from .extensions import db, login_manager
from .models import ROLE_OWNER, User


def _ensure_dirs(app):
	"""确保实例目录与上传目录存在。"""
	os.makedirs(os.path.join(app.root_path, "..", "instance"), exist_ok=True)
	os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
	os.makedirs(app.config["AVATAR_FOLDER"], exist_ok=True)


def _ensure_owner(app):
	"""确保站长账号存在并具备 owner 角色。

	若配置邮箱对应用户不存在则自动创建（昵称与密码取自配置）；
	若已存在则仅校正角色为站长。
	"""
	owner_email = app.config.get("OWNER_EMAIL", "").strip().lower()
	if not owner_email:
		return

	user = User.query.filter_by(email=owner_email).first()
	if user:
		if user.role != ROLE_OWNER:
			user.role = ROLE_OWNER
			db.session.commit()
		return

	# 昵称去重：若占用则追加后缀
	nickname = app.config.get("OWNER_NICKNAME", "站长")
	if User.query.filter_by(nickname=nickname).first():
		nickname = f"{nickname}_{owner_email.split('@')[0]}"

	owner = User(email=owner_email, nickname=nickname, role=ROLE_OWNER)
	owner.set_password(app.config.get("OWNER_PASSWORD", "admin123"))
	db.session.add(owner)
	db.session.commit()


def create_app():
	"""创建并配置 Flask 应用实例。

	Returns:
		Flask: 已完成扩展绑定与蓝图注册的应用对象。
	"""
	app = Flask(__name__)
	app.config.from_object(Config)

	# instance 目录需在数据库连接前就绪
	instance_dir = os.path.join(os.path.dirname(app.root_path), "instance")
	os.makedirs(instance_dir, exist_ok=True)

	db.init_app(app)
	login_manager.init_app(app)

	# 注册蓝图
	from .blueprints.auth import auth_bp
	from .blueprints.gallery import gallery_bp
	from .blueprints.interact import interact_bp
	from .blueprints.user import user_bp
	from .blueprints.admin import admin_bp

	app.register_blueprint(auth_bp)
	app.register_blueprint(gallery_bp)
	app.register_blueprint(interact_bp)
	app.register_blueprint(user_bp)
	app.register_blueprint(admin_bp)

	# 模板全局：分类列表，供导航渲染
	@app.context_processor
	def inject_categories():
		return {"CATEGORIES": app.config["CATEGORIES"]}

	# 模板全局：翻页 URL 构造器（保留当前路由参数与搜索词）
	@app.context_processor
	def inject_pager():
		from flask import request, url_for

		def page_url(page):
			view_args = dict(request.view_args or {})
			params = {}
			keyword = request.args.get("q")
			if keyword:
				params["q"] = keyword
			return url_for(request.endpoint, page=page, **view_args, **params)

		return {"page_url": page_url}

	with app.app_context():
		_ensure_dirs(app)
		db.create_all()
		_ensure_owner(app)

	return app
