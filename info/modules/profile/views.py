from flask import abort
from flask import current_app
from flask import g, jsonify
from flask import request
from flask import session

from info import constants
from info import db
from info.models import Category, News, User
from info.utils.image_storage import storage
from info.utils.response_code import RET
from . import profile_blue
from flask import render_template
from info.utils.common import user_login_data

from flask import redirect


@profile_blue.route('/info')
@user_login_data
def get_user_info():
    """
    获取用户信息
    1.获取到当前登录的用户模型
    2.返回模型中指定内容
    :return:
    """
    user = g.user
    if not user:
        # 用户未登录,重定向到主页
        return redirect('/')

    data = {
        "user_info": user.to_dict(),
    }

    return render_template("new/user.html", data=data)


@profile_blue.route('/base_info', methods=["GET", "POST"])
@user_login_data
def base_info():
    """
    用户基本信息
    1. 获取用户登录信息
    2. 获取到传入参数
    3. 更新并保存数据
    4. 返回结果
    :return:
    """
    # 1.获取用户登录信息
    user = g.user

    if request.method == "GET":
        data = {
            "user_info": user.to_dict(),
        }
        return render_template("new/user_base_info.html", data=data)

    # 2.获取传入参数
    # POST方法
    nick_name = request.json.get("nick_name")
    signature = request.json.get("signature")
    gender = request.json.get("gender")

    if not all([nick_name, gender, signature]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

    if gender not in (['MAN', 'WOMAN']):
        return jsonify(errno=RET.PARAMERR, errmsg="参数有误")

    # 3.更新并保存数据
    user.nick_name = nick_name
    user.gender = gender
    user.signature = signature
    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="保存数据失败")

    # 将session中保存的数据进行实时更新
    session["nick_name"] = nick_name

    # 4.返回响应
    return jsonify(errno=RET.OK, errmsg="更新成功")


@profile_blue.route('/pic_info', methods=["GET", "POST"])
@user_login_data
def pic_info():
    user = g.user
    # print("进入pic_info试图函数")

    if request.method == "GET":
        data = {"user_info": user.to_dict()}
        # print("退出pic_info试图函数")
        return render_template('new/user_pic_info.html', data=data)

    # 1.获取到上传的文件
    try:
        avatar_file = request.files.get("avatar").read()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.PARAMERR, errmsg="读取文件出错")

    # 2.再将文件上传到七牛云
    try:
        url = storage(avatar_file)
        # print("url = ", url)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.THIRDERR, errmsg="上传图片错误")

    # 3.将头像信息更新到当前用户的模型中
    # 设置用户模型相关数据
    user.avatar_url = url

    # 将数据保存到数据库
    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(error=RET.DBERR, errmsg="保存用户数据错误")

    # 4. 返回上传的结果<avatar_url>
    data = {
        "user_info": user.to_dict(),
        "avatar_url": constants.QINIU_DOMIN_PREFIX + url
    }

    print("avatar_url : ", constants.QINIU_DOMIN_PREFIX + url)
    # print("头像图片上传成功")
    return jsonify(errno=RET.OK, errmsg="上传成功", data=data)


@profile_blue.route('/pass_info', methods=["GET", "POST"])
@user_login_data
def pass_info():
    user = g.user

    if request.method == "GET":
        return render_template('new/user_pass_info.html')

    old_password = request.json.get("old_password")
    new_password = request.json.get("new_password")

    if not all([old_password, new_password]):
        print("参数不全")
        return jsonify(errno=RET.DATAERR, errmsg="参数不全")

    # 判断旧密码是否正确
    if not user.check_password(old_password):
        print("密码错误")
        return jsonify(errno=RET.PWDERR, errmsg="密码错误")

    user.password = new_password

    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="保存数据失败")

    return jsonify(errno=RET.OK, errmsg="修改成功")


@profile_blue.route('/collection')
@user_login_data
def user_collection():
    user = g.user
    # 获取当前页数,get请求获取参数
    p = request.args.get("p", 1)

    try:
        p = int(p)
        # 如果p不是数字,那么报错,然后强制p=1
    except Exception as e:
        current_app.logger.error(e)
        p = 1

    collection = []  # 分页数据
    current_page = 1  # 当前页
    total_page = 1  # 总页数

    try:
        # 进行分页数据查询
        paginate = user.collection_news.paginate(p, constants.USER_COLLECTION_MAX_NEWS, False)
        # 获取分页数据
        collection = paginate.items
        # 获取当前页
        current_page = paginate.page
        # 获取总页数
        total_page = paginate.pages
    except Exception as e:
        # 分页失败就报错
        current_app.logger.error(e)

    # 分页数来的数据是模型类列表, 把它转换成json对象
    collection_dict_li = []
    for news in collection:
        collection_dict_li.append(news.to_basic_dict())

    data = {
        "total_page": total_page,
        "current_page": current_page,
        "collections": collection_dict_li
    }

    # print("请求新闻收藏成功")
    return render_template('new/user_collection.html', data=data)


@profile_blue.route('/news_release', methods=["GET", "POST"])
@user_login_data
def news_release():
    print("进入新闻发布")
    user = g.user
    if request.method == "GET":
        categorys = Category.query.all()

        # 模型类转换成json类
        categories_dicts = []
        for category in categorys:
            categories_dicts.append(category.to_dict())

        # 删除第0个位置的元素, 最新的数据
        categories_dicts.pop(0)
        data = {
            "categories": categories_dicts
        }
        return render_template("new/user_news_release.html", data=data)

    # 1.获取要提交的数据
    title = request.form.get("title")
    category_id = request.form.get("category_id")
    digest = request.form.get("digest")
    # 注意图片是用files形式获取
    index_image = request.files.get("index_image")
    content = request.form.get("content")

    source = "个人发布"

    # 1.1 判断数据是否有值
    if not all([title, source, digest, content, index_image, category_id]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数不全")

    # 1.2 尝试读取图片
    try:
        index_image = index_image.read()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.PARAMERR, errmsg="图片读取失败")

    # 2.将标题图片上传到七牛
    try:
        key = storage(index_image)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.THIRDERR, errmsg="上传图片到七牛发生错误")

    # 3.初始化新闻模型,并设置相关数据
    # 注意,这个对着News类的定义来写的
    news = News()
    news.title = title
    news.digest = digest
    news.source = source
    news.content = content
    news.index_image_url = constants.QINIU_DOMIN_PREFIX + key
    news.category_id = category_id
    news.user_id = g.user.id
    # 1代表待审核状态
    news.status = 1

    # 4.保存到数据库
    try:
        db.session.add(news)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="保存数据失败")

    # 5.返回结果
    return jsonify(errno=RET.OK, errmsg="发布成功,等待审核")


@profile_blue.route('/news_list')
@user_login_data
def news_list():
    user = g.user

    page = request.args.get('p', 1)  # 如果p取值不到,要给默认值1

    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)
        page = 1

    # 分页前的准备
    news_li = []
    current_page = 1
    total_page = 1

    paginate = user.news_list.paginate(page, 10, False)
    news_li = paginate.items
    current_page = paginate.page
    total_page = paginate.pages

    # 模型类转换成json类
    news_dict_li = []
    for news in news_li:
        news_dict_li.append(news.to_review_dict())

    data = {
        "current_page":current_page,
        "total_page":total_page,
        "news_list":news_dict_li
    }

    return render_template('new/user_news_list.html',data=data)


@profile_blue.route('/user_follow')
@user_login_data
def user_follow():
    # 获取页数
    p = request.args.get("p", 1)
    try:
        p = int(p)
    except Exception as e:
        current_app.logger.error(e)
        p = 1

    user = g.user

    follows = []
    current_page = 1
    total_page = 1
    try:
        paginate = user.followed.paginate(p, constants.USER_FOLLOWED_MAX_COUNT, False)
        # 获取当前页数据
        follows = paginate.items
        # 获取当前页
        current_page = paginate.page
        # 获取总页数
        total_page = paginate.pages
    except Exception as e:
        current_app.logger.error(e)

    user_dict_li = []

    for follow_user in follows:
        user_dict_li.append(follow_user.to_dict())
    data = {"users": user_dict_li, "total_page": total_page, "current_page": current_page}
    print("返回user_follow.html模板页面!")
    return render_template('new/user_follow.html', data=data)


@profile_blue.route('/other_news_list')
def other_news_list():
    # 获取页数
    p = request.args.get("p", 1)
    user_id = request.args.get("user_id")
    try:
        p = int(p)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

    if not all([p, user_id]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

    try:
        user = User.query.get(user_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="数据查询错误")

    if not user:
        return jsonify(errno=RET.NODATA, errmsg="用户不存在")

    try:
        paginate = News.query.filter(News.user_id == user.id).paginate(p, constants.OTHER_NEWS_PAGE_MAX_COUNT, False)
        # 获取当前页数据
        news_li = paginate.items
        # 获取当前页
        current_page = paginate.page
        # 获取总页数
        total_page = paginate.pages
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="数据查询错误")

    news_dict_li = []

    for news_item in news_li:
        news_dict_li.append(news_item.to_review_dict())
    data = {"news_list": news_dict_li, "total_page": total_page, "current_page": current_page}
    return jsonify(errno=RET.OK, errmsg="OK", data=data)


@profile_blue.route('/other_info')
@user_login_data
def other_info():
    """查看其他用户信息"""
    user = g.user

    # 如果用户没登录,那么就不能查看其他哟过户信息
    if not user:
        return redirect("/")

    # 获取其他用户id
    user_id = request.args.get("id")
    if not user_id:
        abort(404)
    # 查询用户模型
    other = None
    try:
        other = User.query.get(user_id)
    except Exception as e:
        current_app.logger.error(e)
    if not other:
        abort(404)

    # 判断当前登录用户是否关注过该用户
    is_followed = False
    if g.user:
        if other.followers.filter(User.id == user.id).count() > 0:
            is_followed = True

    # 组织数据，并返回
    data = {
        "user_info": user.to_dict(),
        "other_info": other.to_dict(),
        "is_followed": is_followed
    }
    return render_template('new/other.html', data=data)