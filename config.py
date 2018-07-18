import redis
import logging
import flask_session
from flask import Flask

class Config(object):
    # mysql数据库连接配置
    SQLALCHEMY_DATABASE_URI = "mysql://root:mysql@127.0.0.1:3306/information"

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False

    # redis配置信息
    REDIS_HOST = "127.0.0.1"
    REDIS_PORT = 6379

    # 工程配置
    SECRET_KEY = "ASDFSDwerqwerewrwerwewerweFQW"

    # flask_session的配置信息
    SESSION_TYPE = "redis"  # 指定session保存到redis中
    SESSION_USE_SIGNER = True  # 让cookie中的session_id 被加密签名处理
    SESSION_REDIS = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT)
    PERMANENT_SESSION_LIFETIME = 86400  # session的有效期-->86400/3600=24小时

    # 配置日志
    LOG_LEVEL = logging.DEBUG

class DevelopmentConfig(Config):
    # 开启调试
    DEBUG = True


class ProductionConfig(Config):
    LOG_LEVEL = logging.ERROR



config = {

    "development":DevelopmentConfig,
    "production":ProductionConfig

}
