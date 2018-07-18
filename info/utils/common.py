import functools

from flask import current_app
from flask import g
from flask import session

from info import constants
from info.models import News, Category


def do_index_class(index):
    """自定义过滤器,过滤点击排序html的class"""
    if index == 0:
        return "first"
    elif index == 1:
        return "second"
    elif index == 2:
        return "third"
    else:
        return ""


def user_login_data(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        # 获取到当前登录用户的id
        user_id = session.get("user_id")
        # 通过id获取到用户信息
        user = None
        if user_id:
            from info.models import User
            user = User.query.get(user_id)

        g.user = user
        return f(*args,**kwargs)
    return wrapper


def new_rank_list(f):
    @functools.wraps(f)
    def wrapper(*args,**kwargs):
        news_list = None
        try:
            news_list = News.query.order_by(News.clicks.desc()).limit(constants.CLICK_RANK_MAX_NEWS)
        except Exception as e:
            current_app.logger.error(e)

        click_news_list = []
        for news in news_list if news_list else []:
            click_news_list.append(news.to_basic_dict())

        # 获取新闻分类数据
        categories = Category.query.all()
        # 定义列表保存分类数据
        categories_dicts = []
        for category in categories:
            # 拼接内容
            categories_dicts.append(category.to_dict())

        g.click_news_list = click_news_list
        return f(*args,**kwargs)
    return wrapper