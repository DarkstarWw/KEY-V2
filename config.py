"""应用配置模块。

集中管理站长账号、数据库、邮件 SMTP 与上传相关配置。
所有敏感项（如 SMTP 授权码、密钥）均可通过环境变量覆盖，避免硬编码。
"""

import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
	"""基础配置类。

	属性均为应用级常量，通过环境变量覆盖以适配本地测试与线上部署。
	"""

	# 安全密钥：生产环境务必通过环境变量 TU_SECRET_KEY 覆盖
	SECRET_KEY = os.environ.get("TU_SECRET_KEY", "dev-secret-change-me")

	# 数据库：本地 SQLite 单文件，存放于 instance 目录
	SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(BASE_DIR, "instance", "tu.db")
	SQLALCHEMY_TRACK_MODIFICATIONS = False

	# 站长账号：启动时自动创建（若不存在）并标记为站长（owner）
	OWNER_EMAIL = os.environ.get("TU_OWNER_EMAIL", "772649994@qq.com")
	OWNER_PASSWORD = os.environ.get("TU_OWNER_PASSWORD", "Wuxs1234")
	OWNER_NICKNAME = os.environ.get("TU_OWNER_NICKNAME", "Key")

	# 是否要求邮箱验证码（注册/登录）。本地测试关闭，免验证。
	REQUIRE_EMAIL_CODE = os.environ.get("TU_REQUIRE_EMAIL_CODE", "0") == "1"

	# 上传目录与限制
	UPLOAD_FOLDER = os.path.join(BASE_DIR, "app", "static", "uploads")
	AVATAR_FOLDER = os.path.join(BASE_DIR, "app", "static", "avatars")
	THUMB_SIZE = (480, 480)
	MAX_CONTENT_LENGTH = 64 * 1024 * 1024  # 单次请求最大 64MB
	ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

	# 邮件 SMTP（QQ 邮箱），授权码后续填入环境变量
	MAIL_SERVER = os.environ.get("TU_MAIL_SERVER", "smtp.qq.com")
	MAIL_PORT = int(os.environ.get("TU_MAIL_PORT", "465"))
	MAIL_USE_SSL = True
	MAIL_USERNAME = os.environ.get("TU_MAIL_USERNAME", "")  # 发件 QQ 邮箱地址
	MAIL_PASSWORD = os.environ.get("TU_MAIL_PASSWORD", "")  # QQ 邮箱 SMTP 授权码
	MAIL_SENDER = os.environ.get("TU_MAIL_SENDER", "") or MAIL_USERNAME

	# 验证码配置
	CODE_TTL = 600          # 验证码有效期（秒）
	CODE_RESEND_GAP = 60    # 重新发送最小间隔（秒）

	# 昵称改名冷却（天）
	NICKNAME_CHANGE_DAYS = 30

	# 列表每页图组数
	PER_PAGE = 20

	# 分类定义：键为内部标识，值为显示名（顺序即导航顺序）
	CATEGORIES = [
		("scene", "场照"),
		("outdoor", "外景"),
		("studio", "棚拍"),
	]
