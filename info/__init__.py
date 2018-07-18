from logging.handlers import RotatingFileHandler

import redis
import logging
from flask import Flask
from flask import g
from flask import render_template
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect  # 大写的CSRF!!!
from flask_wtf.csrf import generate_csrf  # 生成csrf
from flask_session import Session

from config import config

# 创建Mysql数据库对象


db = SQLAlchemy()
# 创建redis数据库对象
#                   下面的type:xxxxx声明表示: 在别的文件中导入redis_store变量的时候,会有和xxxxx相关的提示
redis_store = None  # type:redis.StrictRedis


def create_app(config_name):
    setup_log(config_name)

    app = Flask(__name__)

    app.config.from_object(config[config_name])

    # 初始化数据库mysql 和redis
    db.init_app(app)

    # 这里要注意的是配置redis_store要加声明全局
    global redis_store
    redis_store = redis.StrictRedis(host=config[config_name].REDIS_HOST, port=config[config_name].REDIS_PORT)

    # CSRF保护
    # 'WTF_CSRF_METHODS', ['POST', 'PUT', 'PATCH', 'DELETE']
    # get不受CSRF保护
    CSRFProtect(app)
    # session
    Session(app)

    # info相当于所有蓝图的父类, 所以扫尾工作都在这里(对应的__init__)写
    # (钩子函数实现)
    @app.after_request
    def after_request(response):
        csrf_token = generate_csrf()
        response.set_cookie("csrf_token", csrf_token)
        return response

    # 捕获全局的404异常
    from info.utils.common import user_login_data

    @app.errorhandler(404)
    @user_login_data
    def error_404_handler(error):
        user = g.user
        data = {
            "user_info": user.to_dict() if user else None
        }
        return render_template("new/404.html", data=data)

    # 添加自定义过滤器 ======
    from info.utils.common import do_index_class
    # 增加模板过滤器的函数: 参数1:函数名, 参数2:过滤器名
    app.add_template_filter(do_index_class, "index_class")

    # 注册蓝图 ========================================
    # 特别注意, 导入蓝图要放在创建db初始化db之后,因为蓝图里面要用到db
    # 如果导入蓝图在db之前,那么程序会报错: cannot import name "db"

    # 观察发现, 我们大多数的情况都是在返回app对象之前导入蓝图, 注册蓝图

    from info.modules.index import index_blue
    app.register_blueprint(index_blue)

    from info.modules.passport import passport_blue
    app.register_blueprint(passport_blue)

    from info.modules.news import news_blue
    app.register_blueprint(news_blue)

    from info.modules.profile import profile_blue
    app.register_blueprint(profile_blue)

    from info.modules.admin import admin_blue
    app.register_blueprint(admin_blue)

    return app


def setup_log(config_name):
    """配置日志"""

    # 设置日志的记录等级
    logging.basicConfig(level=config[config_name].LOG_LEVEL)

    # 创建日志记录器,指明日志保存的路径,每个日志文件的最大大小,保存的日志文件个数上限
    file_log_handler = RotatingFileHandler("logs/log", maxBytes=1024 * 1024 * 100, backupCount=10)

    # 创建日志记录的格式, 日志等级, 输入日志信息的文件名 行数 日志信息
    formatter = logging.Formatter('%(levelname)s %(filename)s:%(lineno)d %(message)s')
    # 为刚创建的日志记录器设置日志记录格式
    file_log_handler.setFormatter(formatter)
    # 为全局的日志工具对象(flask_ap使用的)添加日志记录器
    logging.getLogger().addHandler(file_log_handler)

# class Author(db.Model):
#     __tablename__ = "authors"
#     id = db.Column(db.Integer, primary_key=True)
#     name = db.Column(db.String(128))
#     books = db.relationship("Book", backref="author")
#
#     def __repr__(self):
#         return "Author = %s" % self.name
#
#
# class Book(db.Model):
#     __tablename__ = "books"
#     id = db.Column(db.Integer, primary_key=True)
#     name = db.Column(db.String(128))
#     author_id = db.Column(db.Integer, db.ForeignKey("authors.id"))
