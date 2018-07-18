import time
# import datetime
from datetime import datetime, timedelta

from flask import current_app, jsonify
from flask import g
from flask import redirect
from flask import render_template
from flask import request
from flask import session
from flask import url_for

from info.models import User, News, Category
from info.utils.image_storage import storage
from info.utils.response_code import RET
from . import admin_blue
from info.utils.common import user_login_data
from info import constants, db


@admin_blue.route('/index')
@user_login_data
def admin_index():
    user = g.user
    # 用钩子函数处理(已经写在__init__.py)
    # if not user.is_admin:
    #     return redirect("/")

    data = {
        "user": user.to_dict() if user else None
    }

    return render_template("admin/index.html", data=data)


@admin_blue.route('/login', methods=["GET", "POST"])
def admin_login():
    if request.method == "GET":
        # 判断当前登录的用户是否是管理员,并且已经登陆,这样就可以不需要重复登陆
        is_admin = session.get("is_admin", None)
        user_id = session.get("user_id", None)
        if user_id and is_admin:
            return redirect(url_for("admin.admin_index"))
        return render_template("admin/login.html")

    username = request.form.get("username")
    password = request.form.get("password")
    if not all([username, password]):
        return render_template('admin/login.html', errmsg="参数不足")

    try:
        # 查询数据库表中里面是否有当前登陆的用户(  不包含普通用户  )
        #  User.is_admin == True: 只能让管理员进行登陆,不能让普通用户进来
        user = User.query.filter(User.mobile == username, User.is_admin == True).first()
    except Exception as e:
        current_app.logger.error(e)
        return render_template('admin/login.html', errmsg="数据查询失败")

    # 判断当前用户是否存在
    if not user:
        return render_template("admin/login.html", errmsg="没有这个用户")

    if not user.check_password(password):
        return render_template("admin/login.html", errmsg="密码错误")

    session["user_id"] = user.id
    session["nick_name"] = user.nick_name
    session["mobile"] = user.mobile
    session["is_admin"] = True

    return redirect(url_for("admin.admin_index"))


@admin_blue.route("/user_count", methods=["GET", "POST"])
def user_count():
    # 数据都默认是0

    # 当前的总人数
    total_count = 0
    # 每个月新增人数
    mon_count = 0
    # 每天新增人数
    day_count = 0

    # 1.查看总人数===============================
    # 管理员是公司员工, 不算是用户, 所以需要去掉
    total_count = User.query.filter(User.is_admin == False).count()

    # 2.查询本月的新增用户==========================
    # 获取到本地时间
    # time.localtime() 的返回值是 (tm_year, tm_mon, tm_mday, tm_hour, tm_min,tm_sec, tm_wday, tm_yday, tm_isdst)
    t = time.localtime()
    # 2018-07-01
    mon_time = "%d-%02d-01" % (t.tm_year, t.tm_mon)
    # Python time strptime() 函数根据指定的格式把一个时间字符串解析为时间元组。
    # 2018-07-01 0点0分0秒
    mon_time_begin = datetime.strptime(mon_time, "%Y-%m-%d")  # 格式化时间字符串
    print()
    # 查询本月的新增用户
    mon_count = User.query.filter(User.is_admin == False, User.create_time > mon_time_begin).count()

    # 3.查询今天的新增用户==========================
    # 获取本地时间
    t = time.localtime()
    day_time = "%d-%02d-%02d" % (t.tm_year, t.tm_mon, t.tm_mday)
    day_time_begin = datetime.strptime(day_time, "%Y-%m-%d")  # 格式化时间字符串
    # 查询今天的新增用户
    day_count = User.query.filter(User.is_admin == False, User.create_time > day_time_begin).count()

    # 计算到今天为止的一个月,每天的用户登录活跃数
    t = time.localtime()
    today_begin = "%d-%02d-%02d" % (t.tm_year, t.tm_mon, t.tm_mday)
    today_begin_date = datetime.strptime(today_begin, "%Y-%m-%d")  # 格式化时间字符串

    # 人数
    active_count = []
    # 时间
    active_time = []
    for i in range(0, 31):
        # timedelta是时间差
        # begin_date得到前i天的时间
        begin_date = today_begin_date - timedelta(days=i)
        # end_date得到前i+1天的时间
        end_date = today_begin_date - timedelta(days=(i - 1))
        # 计算前i天到前i+1天的用户数量
        count = User.query.filter(User.is_admin == False, User.create_time > begin_date,
                                  User.create_time < end_date).count()

        active_count.append(count)
        active_time.append(begin_date.strftime("%Y-%m-%d"))

    # active_count = active_count.reverse()
    # active_time = active_time.reverse()
    active_count.reverse()
    active_time.reverse()

    data = {
        "total_count": total_count,
        "mon_count": mon_count,
        "day_count": day_count,
        "active_count": active_count,
        "active_date": active_time
    }

    return render_template("admin/user_count.html", data=data)


@admin_blue.route('/user_list')
def user_list():
    # 1.获取参数
    # 前端给出的是参数是: 页面
    page = request.args.get("p", 1)

    # 2.校验参数
    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)
        page = 1

    # 3.处理业务逻辑, 这里的业务逻辑是要换返回分页的用户数据
    # 设置默认返回值
    users = []
    current_page = 1
    total_page = 1

    # 用户不包含管理员
    try:
        paginate = User.query.filter(User.is_admin == False).order_by(User.last_login.desc()).paginate(page,
                                                                                                       constants.ADMIN_USER_PAGE_MAX_COUNT,
                                                                                                       False)
        users = paginate.items
        current_page = paginate.page
        total_page = paginate.pages
    except Exception as e:
        current_app.logger.error(e)

    # 4.返回
    # 将模型列表转换成字典列表
    users_list = []
    for user in users:
        users_list.append(user.to_admin_dict())

    data = {
        "users": users_list,
        "current_page": current_page,
        "total_page": total_page
    }

    return render_template("admin/user_list.html", data=data)


@admin_blue.route('/news_review')
def news_review():
    # 获取
    page = request.args.get("p", 1)
    # 注意如果keywords没取到,默认给""
    keywords = request.args.get("keywords", "")

    # 校验
    try:
        page = int(page)
    except Exception as e:
        page = 1
        current_app.logger.error(e)

    # 业务
    news = []
    current_page = 1
    total_page = 1

    my_filter = [News.status != 0]
    if keywords:
        # filter.append(keywords)
        my_filter.append(News.title.contains(keywords))
    try:
        paginate = News.query.filter(*my_filter).order_by(News.create_time.desc()).paginate(page,
                                                                                            constants.ADMIN_NEWS_PAGE_MAX_COUNT,
                                                                                            False)
        news = paginate.items
        current_page = paginate.page
        total_page = paginate.pages
    except Exception as e:
        current_app.logger.error(e)

    # 将模型列表转换成字典列表
    news_list = []
    for item in news:
        news_list.append(item.to_review_dict())

    data = {
        "current_page": current_page,
        "total_page": total_page,
        "news_list": news_list
    }

    # 返回
    return render_template("admin/news_review.html", data=data)


@admin_blue.route('/news_review_detail', methods=["GET", "POST"])
def news_review_detail():
    if request.method == "GET":
        # 获取
        news_id = request.args.get("news_id")
        # 校验
        if not news_id:
            data = {
                "errmsg": "未查询到此新闻",
            }
            return render_template("admin/news_review_detail.html", data=data)

        # 业务
        # 根据id查新闻
        news = None  # type:News
        try:
            news = News.query.get(news_id)
        except Exception as e:
            current_app.logger.error(e)

        if not news:
            data = {
                "errmsg": "未查询到此新闻"
            }
            return render_template("admin/news_review_detail.html", data=data)

        # 返回
        # 因为news不是模型列表,它只是一个模型
        data = {
            "news": news.to_dict()
        }
        a = data["news"]
        b = a["id"]
        return render_template("admin/news_review_detail.html", data=data)

    # 以下是methods = "POST"
    # 获取参数
    action = request.json.get("action")
    news_id = request.json.get("news_id")
    print(news_id)

    # 判断参数
    if not all([action, news_id]):
        return jsonify(errno=RET.OK, errmsg="参数不全")
    if action not in ("accept", "reject"):
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

    # 业务逻辑
    news = None
    try:
        news = News.query.get(news_id)
    except Exception as e:
        current_app.logger.error(e)

    if not news:
        return jsonify(errno=RET.NODATA, errmsg="新闻不存在")

    # 根据不同的参数设置不同的status
    if action == "accept":
        news.status = 0
    else:
        # 拒绝通过需要获取拒绝原因
        reason = request.json.get("reason")
        if not reason:
            return jsonify(errno=RET.PARAMERR, errmsg="参数错误")
        news.reason = reason
        news.status = -1

    # 保存到数据库
    try:
        db.session.commit()
        print("保存到数据库成功")
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="数据保存失败")

    # 返回
    return jsonify(errno=RET.OK, errmsg="操作成功")


@admin_blue.route('/news_edit')
def news_edit():
    # 获取数据
    page = request.args.get("p", 1)
    keywords = request.args.get("keywords", "")

    # 验证数据
    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)
        page = 1

    # 业务逻辑
    # 设置参数
    news = []
    current_page = 1
    total_page = 1

    my_filter = []
    if keywords:
        my_filter.append(News.title.contains(keywords))
    paginate = News.query.filter(*my_filter).order_by(News.create_time.desc()).paginate(page,
                                                                                        constants.ADMIN_NEWS_PAGE_MAX_COUNT,
                                                                                        False)
    news = paginate.items
    current_page = paginate.page
    total_page = paginate.pages

    # 模型列表转换成字典列表
    news_list = []
    for item in news:
        news_list.append(item.to_dict())
    # 返回数据
    data = {
        "news_list": news_list,
        "current_page": current_page,
        "total_page": total_page
    }
    return render_template("admin/news_edit.html", data=data)


@admin_blue.route('/news_edit_detail',methods=["GET","POST"])
def news_edit_detail():
    """新闻编辑详情"""

    if request.method == "GET":
        # 获取参数
        news_id = request.args.get("news_id")
        if not news_id:
            return render_template("admin/news_edit_detail.html",data={"errmsg":"未查询到此新闻"})


        # 查询新闻
        news= None  # type:News
        try:
            # news = News.query.get("news_id")  # 注意不能加双引号
            news = News.query.get(news_id)
        except Exception as e:
            current_app.logger.error(e)
        if not news:
            return render_template("admin/news_edit_detail.html",data={"errmsg":"未查询到此新闻"})

        # 查询分类的数据
        catagories = Category.query.all()
        categories_li = []
        for category in catagories:
            c_dict = category.to_dict()
            c_dict["is_selected"] = False
            if Category.id  == news.category_id: # 对新闻所属的类标记被选择
                c_dict["is_selected"] = True
            categories_li.append(c_dict)
        # 移除"最新"分类
        categories_li.pop(0)

        data = {
            "news":news.to_dict(),
            "categories":categories_li
        }
        return render_template("admin/news_edit_detail.html",data=data)

    news_id = request.form.get("news_id")
    title = request.form.get("title")
    digest = request.form.get("digest")
    content = request.form.get("content")
    index_image = request.files.get("index_image")
    category_id = request.form.get("category_id")

    # 1.1 判断数据是否有值
    if not all([title, digest, content, category_id]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数有误")

    news = None
    try:
        news = News.query.get(news_id)
    except Exception as e:
        current_app.logger.error(e)
    if not news:
        return jsonify(errno=RET.NODATA, errmsg="未查询到新闻数据")

    # 1.2 尝试读取图片
    if index_image:
        try:
            index_image = index_image.read()
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.PARAMERR, errmsg="参数有误")

        # 2. 将标题图片上传到七牛
        try:
            key = storage(index_image)
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.THIRDERR, errmsg="上传图片错误")
        news.index_image_url = constants.QINIU_DOMIN_PREFIX + key

    # 3. 设置相关数据
    news.title = title
    news.digest = digest
    news.content = content
    news.category_id = category_id

    # 4. 保存到数据库
    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="保存数据失败")
    # 5. 返回结果
    return jsonify(errno=RET.OK, errmsg="编辑成功")


@admin_blue.route('/news_category')
def get_news_category():
    # 获取所有的分类数据
    categories = Category.query.all()
    # 定义列表保存分类数据
    categories_dicts = []

    for category in categories:
        # 获取字典
        cate_dict = category.to_dict()
        # 拼接内容
        categories_dicts.append(cate_dict)

    categories_dicts.pop(0)
    # 返回内容
    return render_template('admin/news_type.html', data={"categories": categories_dicts})


@admin_blue.route('/add_category', methods=["POST"])
def add_category():
    """修改或者添加分类"""

    category_id = request.json.get("id")
    category_name = request.json.get("name")
    if not category_name:
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")
    # 判断是否有分类id
    if category_id:
        try:
            category = Category.query.get(category_id)
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.DBERR, errmsg="查询数据失败")

        if not category:
            return jsonify(errno=RET.NODATA, errmsg="未查询到分类信息")

        category.name = category_name
    else:
        # 如果没有分类id，则是添加分类
        category = Category()
        category.name = category_name
        db.session.add(category)

    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="保存数据失败")
    return jsonify(errno=RET.OK, errmsg="保存数据成功")