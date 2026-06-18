"""邮件服务。

封装验证码邮件发送：配置了 SMTP 授权码时通过 QQ 邮箱发送，
否则回退到控制台打印（本地测试用）。
"""

import smtplib
from email.mime.text import MIMEText
from email.header import Header

from flask import current_app


def send_code_email(to_email, code):
	"""发送验证码邮件。

	未配置 SMTP 账号或授权码时，自动回退为控制台打印，便于本地测试。

	Args:
		to_email: 收件邮箱。
		code: 验证码字符串。

	Returns:
		bool: 发送（或控制台兜底）是否成功。
	"""
	cfg = current_app.config
	username = cfg.get("MAIL_USERNAME")
	password = cfg.get("MAIL_PASSWORD")

	subject = "图床网站 - 邮箱验证码"
	body = f"您的验证码为：{code}，{cfg['CODE_TTL'] // 60} 分钟内有效。如非本人操作请忽略。"

	if not username or not password:
		# 本地测试兜底：直接打印到控制台
		current_app.logger.warning("[邮件未配置] 发往 %s 的验证码：%s", to_email, code)
		return True

	msg = MIMEText(body, "plain", "utf-8")
	msg["Subject"] = Header(subject, "utf-8")
	msg["From"] = cfg.get("MAIL_SENDER") or username
	msg["To"] = to_email

	try:
		with smtplib.SMTP_SSL(cfg["MAIL_SERVER"], cfg["MAIL_PORT"], timeout=10) as server:
			server.login(username, password)
			server.sendmail(msg["From"], [to_email], msg.as_string())
		return True
	except (smtplib.SMTPException, OSError) as exc:
		current_app.logger.error("发送验证码邮件失败：%s", exc)
		return False
