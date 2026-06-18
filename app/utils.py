"""通用工具函数。

包含文件保存与缩略图生成、随机验证码、权限装饰器等公共逻辑。
"""

import os
import random
import string
from functools import wraps
from io import BytesIO

from flask import abort, current_app
from flask_login import current_user
from PIL import Image as PILImage
from PIL import ImageDraw, ImageFont

# 验证码字符集：剔除易混淆字符（0/O/1/I/L）
CAPTCHA_CHARS = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"


def allowed_file(filename):
	"""判断文件扩展名是否在允许列表内。

	Args:
		filename: 原始文件名。

	Returns:
		bool: 允许上传则为 True。
	"""
	if "." not in filename:
		return False
	ext = filename.rsplit(".", 1)[1].lower()
	return ext in current_app.config["ALLOWED_EXTENSIONS"]


def _unique_name(filename, default_ext="png"):
	"""基于随机串生成唯一文件名，保留原扩展名。

	Args:
		filename (str): 原始文件名，用于提取扩展名。
		default_ext (str): 无法提取扩展名时使用的兜底扩展名。

	Returns:
		str: 形如 "<16位随机串>.<ext>" 的唯一文件名。
	"""
	if "." in filename and filename.rsplit(".", 1)[1]:
		ext = filename.rsplit(".", 1)[1].lower()
	else:
		ext = default_ext
	token = "".join(random.choices(string.ascii_lowercase + string.digits, k=16))
	return f"{token}.{ext}"


def save_image(file_storage):
	"""保存上传图片并生成缩略图。

	Args:
		file_storage: Werkzeug FileStorage 对象。

	Returns:
		tuple[str, str]: (原图文件名, 缩略图文件名)。
	"""
	folder = current_app.config["UPLOAD_FOLDER"]
	os.makedirs(folder, exist_ok=True)

	name = _unique_name(file_storage.filename or "image.png")
	origin_path = os.path.join(folder, name)
	file_storage.save(origin_path)

	thumb_name = f"thumb_{name}"
	thumb_path = os.path.join(folder, thumb_name)
	try:
		with PILImage.open(origin_path) as img:
			img.thumbnail(current_app.config["THUMB_SIZE"])
			img.save(thumb_path)
	except (OSError, ValueError):
		# 缩略图生成失败时回退使用原图
		thumb_name = name
	return name, thumb_name


def save_avatar(file_storage):
	"""保存头像图片并返回文件名。"""
	folder = current_app.config["AVATAR_FOLDER"]
	os.makedirs(folder, exist_ok=True)
	name = _unique_name(file_storage.filename or "avatar.png")
	file_storage.save(os.path.join(folder, name))
	return name


def gen_code(length=6):
	"""生成指定长度的数字验证码。"""
	return "".join(random.choices(string.digits, k=length))


def gen_captcha_text(length=4):
	"""生成图片验证码文本（默认 4 位，使用非易混淆字符集）。"""
	return "".join(random.choices(CAPTCHA_CHARS, k=length))


def _load_font(size):
	"""加载字体，优先系统 Arial，失败回退 PIL 默认字体。"""
	for name in ("arial.ttf", "Arial.ttf", "DejaVuSans.ttf"):
		try:
			return ImageFont.truetype(name, size)
		except OSError:
			continue
	return ImageFont.load_default()


def render_captcha_image(text):
	"""将验证码文本渲染为 PNG 图片字节流。

	Args:
		text: 验证码字符串。

	Returns:
		BytesIO: PNG 图片二进制流，指针已置 0。
	"""
	width, height = 120, 44
	image = PILImage.new("RGB", (width, height), (245, 245, 247))
	draw = ImageDraw.Draw(image)
	font = _load_font(28)

	# 干扰线
	for _ in range(5):
		xy = [random.randint(0, width), random.randint(0, height),
			random.randint(0, width), random.randint(0, height)]
		draw.line(xy, fill=(random.randint(150, 210),) * 3, width=1)

	# 逐字符绘制，带轻微纵向抖动
	step = width // (len(text) + 1)
	for idx, ch in enumerate(text):
		color = (random.randint(20, 90), random.randint(20, 90), random.randint(20, 90))
		y = random.randint(2, 10)
		draw.text((step * (idx + 1) - 10, y), ch, font=font, fill=color)

	# 噪点
	for _ in range(120):
		draw.point((random.randint(0, width), random.randint(0, height)),
			fill=(random.randint(160, 220),) * 3)

	buffer = BytesIO()
	image.save(buffer, "PNG")
	buffer.seek(0)
	return buffer


def admin_required(view):
	"""装饰器：要求当前用户为管理员及以上。"""

	@wraps(view)
	def wrapper(*args, **kwargs):
		if not current_user.is_authenticated or not current_user.is_admin:
			abort(403)
		return view(*args, **kwargs)

	return wrapper


def owner_required(view):
	"""装饰器：要求当前用户为站长。"""

	@wraps(view)
	def wrapper(*args, **kwargs):
		if not current_user.is_authenticated or not current_user.is_owner:
			abort(403)
		return view(*args, **kwargs)

	return wrapper
