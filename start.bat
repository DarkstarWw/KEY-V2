@echo off
REM ===== 图床本地启动脚本 =====
REM 修改下面的环境变量后双击运行，或在命令行执行 start.bat

REM 站长账号：此邮箱+密码启动时自动创建为站长（owner）
set TU_OWNER_EMAIL=772649994@qq.com
set TU_OWNER_PASSWORD=Wuxs1234

REM 会话密钥：上线请改成随机长字符串
set TU_SECRET_KEY=please-change-this-secret

REM 邮箱验证码开关：0=关闭（免验证，本地测试），1=开启
set TU_REQUIRE_EMAIL_CODE=0

REM 启动后自动打开浏览器：1=开启（默认），0=关闭
set TU_AUTO_OPEN=1

REM ===== QQ 邮箱 SMTP（仅在开启验证码时需要）=====
set TU_MAIL_USERNAME=
set TU_MAIL_PASSWORD=
set TU_MAIL_SENDER=

python run.py
pause
