"""认证蓝图：注册、登录、登出、邮箱验证码与图片验证码。

登录与注册均需图片验证码（4 位字符）；邮箱验证码受配置开关控制。
"""

from datetime import datetime

from flask import (
	Blueprint,
	flash,
	jsonify,
	redirect,
	render_template,
	request,
	send_file,
	session,
	url_for,
)
from flask_login import current_user, login_required, login_user, logout_user

from ..email_service import send_code_email
from ..extensions import db
from ..models import EmailCode, ROLE_USER, User
from ..utils import gen_captcha_text, gen_code, render_captcha_image

auth_bp = Blueprint("auth", __name__)


def _normalize_email(email):
	"""统一邮箱大小写与首尾空白。"""
	return (email or "").strip().lower()


@auth_bp.route("/captcha")
def captcha():
	"""返回图片验证码 PNG，并将答案写入会话。"""
	text = gen_captcha_text()
	session["captcha"] = text.upper()
	buffer = render_captcha_image(text)
	resp = send_file(buffer, mimetype="image/png")
	resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
	return resp


def _verify_captcha(form_value):
	"""校验图片验证码（大小写不敏感），校验后清除会话答案。

	Returns:
		bool: 是否匹配。
	"""
	answer = session.pop("captcha", "")
	return bool(answer) and (form_value or "").strip().upper() == answer


@auth_bp.route("/api/send_code", methods=["POST"])
def send_code():
	"""发送邮箱验证码（注册 / 登录通用）。

	请求体 JSON：email、purpose（register / login）。
	校验重发间隔与邮箱占用状态后写库并发送。
	"""
	data = request.get_json(silent=True) or {}
	email = _normalize_email(data.get("email"))
	purpose = data.get("purpose")

	if not email or "@" not in email:
		return jsonify(ok=False, msg="邮箱格式不正确"), 400
	if purpose not in ("register", "login"):
		return jsonify(ok=False, msg="用途参数错误"), 400

	exists = User.query.filter_by(email=email).first()
	if purpose == "register" and exists:
		return jsonify(ok=False, msg="该邮箱已注册"), 400
	if purpose == "login" and not exists:
		return jsonify(ok=False, msg="该邮箱未注册"), 400

	record = EmailCode.query.filter_by(email=email, purpose=purpose).first()
	if record:
		from flask import current_app

		elapsed = (datetime.utcnow() - record.sent_at).total_seconds()
		if elapsed < current_app.config["CODE_RESEND_GAP"]:
			wait = int(current_app.config["CODE_RESEND_GAP"] - elapsed)
			return jsonify(ok=False, msg=f"请 {wait} 秒后再试"), 429

	code = gen_code()
	if record:
		record.code = code
		record.sent_at = datetime.utcnow()
	else:
		record = EmailCode(email=email, purpose=purpose, code=code)
		db.session.add(record)
	db.session.commit()

	if not send_code_email(email, code):
		return jsonify(ok=False, msg="验证码发送失败，请稍后再试"), 500
	return jsonify(ok=True, msg="验证码已发送")


def _verify_code(email, purpose, code):
	"""校验验证码是否有效，成功后消费（删除）。

	Returns:
		tuple[bool, str]: (是否通过, 错误信息)。
	"""
	from flask import current_app

	record = EmailCode.query.filter_by(email=email, purpose=purpose).first()
	if not record:
		return False, "请先获取验证码"
	if (datetime.utcnow() - record.sent_at).total_seconds() > current_app.config["CODE_TTL"]:
		return False, "验证码已过期"
	if record.code != (code or "").strip():
		return False, "验证码错误"
	db.session.delete(record)
	db.session.commit()
	return True, ""


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
	"""用户注册：邮箱验证码 + 唯一昵称 + 密码。"""
	if current_user.is_authenticated:
		return redirect(url_for("gallery.index"))

	if request.method == "GET":
		return render_template("register.html")

	email = _normalize_email(request.form.get("email"))
	nickname = (request.form.get("nickname") or "").strip()
	password = request.form.get("password") or ""
	code = request.form.get("code")

	if not _verify_captcha(request.form.get("captcha")):
		flash("图片验证码错误", "error")
		return render_template("register.html")
	if not (email and nickname and password):
		flash("请填写完整信息", "error")
		return render_template("register.html")
	if len(nickname) > 32:
		flash("昵称过长", "error")
		return render_template("register.html")
	if User.query.filter_by(email=email).first():
		flash("该邮箱已注册", "error")
		return render_template("register.html")
	if User.query.filter_by(nickname=nickname).first():
		flash("昵称已被占用", "error")
		return render_template("register.html")

	from flask import current_app

	if current_app.config["REQUIRE_EMAIL_CODE"]:
		ok, msg = _verify_code(email, "register", code)
		if not ok:
			flash(msg, "error")
			return render_template("register.html")

	user = User(email=email, nickname=nickname, role=ROLE_USER)
	user.set_password(password)
	db.session.add(user)
	db.session.commit()

	login_user(user)
	flash("注册成功，欢迎！", "ok")
	return redirect(url_for("gallery.index"))


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
	"""用户登录：邮箱 + 密码 + 验证码。"""
	if current_user.is_authenticated:
		return redirect(url_for("gallery.index"))

	if request.method == "GET":
		return render_template("login.html")

	email = _normalize_email(request.form.get("email"))
	password = request.form.get("password") or ""
	code = request.form.get("code")

	if not _verify_captcha(request.form.get("captcha")):
		flash("图片验证码错误", "error")
		return render_template("login.html")

	user = User.query.filter_by(email=email).first()
	if not user or not user.check_password(password):
		flash("邮箱或密码错误", "error")
		return render_template("login.html")

	from flask import current_app

	if current_app.config["REQUIRE_EMAIL_CODE"]:
		ok, msg = _verify_code(email, "login", code)
		if not ok:
			flash(msg, "error")
			return render_template("login.html")

	login_user(user)
	flash("登录成功", "ok")
	return redirect(url_for("gallery.index"))


@auth_bp.route("/logout")
@login_required
def logout():
	"""退出登录。"""
	logout_user()
	return redirect(url_for("gallery.index"))
