"""开发启动入口。

执行 `python run.py` 启动本地测试服务，默认监听 127.0.0.1:5000，
并按开关 TU_AUTO_OPEN 决定是否自动打开浏览器。
"""

import os
import threading
import webbrowser

from app import create_app

app = create_app()

HOST = os.environ.get("TU_HOST", "127.0.0.1")
PORT = int(os.environ.get("TU_PORT", "5000"))
# 自动打开浏览器开关：1=开启（默认），0=关闭
AUTO_OPEN = os.environ.get("TU_AUTO_OPEN", "1") == "1"
# 调试模式开关：1=开启（默认，本地用）；公网/隧道暴露时务必设 0，避免调试器被利用
DEBUG = os.environ.get("TU_DEBUG", "1") == "1"


def _open_browser():
	"""延迟打开浏览器，确保服务已就绪。"""
	webbrowser.open(f"http://{HOST}:{PORT}")


if __name__ == "__main__":
	# 仅在主进程（非 reloader 子进程）触发，避免重复打开
	if AUTO_OPEN and not os.environ.get("WERKZEUG_RUN_MAIN"):
		threading.Timer(1.2, _open_browser).start()
	app.run(host=HOST, port=PORT, debug=DEBUG)
