"""Flask 扩展实例集中定义。

各扩展在此创建为模块级单例，由工厂函数 `create_app` 调用 `init_app` 完成绑定，
以避免蓝图与模型之间的循环导入。
"""

from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message = "请先登录"
