from flask import current_app, jsonify
from flask import g
from flask import render_template

# from . import index_blue
from flask import request
from flask import session

from info.utils.common import user_login_data,new_rank_list

from info.models import User, News, Category
from info.modules.index import index_blue

from info import constants
from info.utils.response_code import RET


@index_blue.route('/')
@user_login_data
@new_rank_list
def index():
    # 从session中获取用户登录的数据, 如果有数据说明用户已经登录
    # 如果取出的代码为None, 说明用户没有登录
    """
    user_id = session.get("user_id")
    print(user_id)

    # 通过id 获取用户信息
    user = None
    if user_id:
        try:
            user = User.query.get(user_id)
        except Exception as e:
            current_app.logger.error(e)
    """
    # 需要把从数据库里面的user对象传递到前端的模板里面, 在模板里面进行if判断, 是否已经登录
    # 如果user有值就传值,没有值就传None


    # 获取点击排行数据
    # news_list = None
    # try:
    #     news_list = News.query.order_by(News.clicks.desc()).limit(constants.CLICK_RANK_MAX_NEWS)
    # except Exception as e:
    #     current_app.logger.error(e)
    #
    # click_news_list = []
    # for news in news_list if news_list else []:
    #     click_news_list.append(news.to_basic_dict())
    #



    # 获取新闻分类数据
    categories = Category.query.all()
    # 定义列表保存分类数据
    categories_dicts = []
    for category in categories:
        # 拼接内容
        categories_dicts.append(category.to_dict())



    data = {
        "user_info": g.user.to_dict() if g.user else None,
        "click_news_list": g.click_news_list,
        "categories": categories_dicts
    }

    return render_template("new/index.html", data=data)


@index_blue.route('/news_list')
def get_news_list():
    """
    获取指定分类的新闻列表
    1.获取参数
    2.校验参数
    3.查询参数
    4.返回数据
    :return:
    """
    # 1.获取参数 ,(请求方式的get)
    args_dict = request.args
    page = args_dict.get("page", '1')
    per_page = args_dict.get("per_page", constants.HOME_PAGE_MAX_NEWS)
    cid = args_dict.get("cid", "1")

    # 2.校验参数
    try:
        page = int(page)
        per_page = int(per_page)
        cid = int(cid)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

    # 3.查询数据并分页
    # paginate：作用是进行分页：
    # 第一个参数：表示当前页面
    # 第二个参数：表示每个页面有多少条数据
    # 第三个参数表示没有错误输出

    # News.status == 0 表示已经通过审核
    filters = [News.status == 0]
    # 如果分类id不为1,那么添加分类id的过滤
    if cid != 1:
        filters.append(News.category_id == cid)
    # if cid == '1':
    #     paginate = News.query.order_by(News.create_time.desc()).paginate(page, per_page, False)
    # else:
    #     paginate = News.query.filter(News.category_id == cid).order_by(News.create_time.desc()).paginate(page, per_page,
    try:
        paginate = News.query.filter(*filters).order_by(News.create_time.desc()).paginate(page, per_page, False)
        # 获取查询出来的数据
        items = paginate.items
        # 获取到总页数
        total_page = paginate.pages
        current_page = paginate.page
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="数据查询失败")

    # print(page)

    news_li = []
    for news in items:
        news_li.append(news.to_basic_dict())

    # 4.返回数据
    data = {
        "current_page": current_page,
        "total_page": total_page,
        "news_dict_li": news_li
    }
    return jsonify(errno=RET.OK, errmsg="OK", data=data)


@index_blue.route('/favicon.ico')
def favicon():
    return current_app.send_static_file('news/favicon.ico')


