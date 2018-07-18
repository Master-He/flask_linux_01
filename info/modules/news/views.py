from flask import abort, jsonify
from flask import current_app
from flask import g
from flask import request
from flask import session

from info import constants, db
from info.models import User, News, Comment, CommentLike
from info.utils.common import user_login_data, new_rank_list
from info.utils.response_code import RET
from . import news_blue

from flask import render_template


@news_blue.route('/<int:news_id>')
@user_login_data
@new_rank_list
def news_detail(news_id):
    # print("新闻id:", news_id)

    # 通过id 获取用户信息
    # user = None
    # if user_id:
    #     try:
    #         user = User.query.get(user_id)
    #     except Exception as e:
    #         current_app.logger.error(e)

    # 获取新闻排行
    # news_list = None
    # try:
    #     news_list = News.query.order_by(News.clicks.desc()).limit(constants.CLICK_RANK_MAX_NEWS)
    # except Exception as e:
    #     current_app.logger.error(e)
    #
    # click_news_list = []
    # for news in news_list if news_list else []:
    #     click_news_list.append(news.to_basic_dict())

    # 根据新闻id查询到新闻

    """新闻 详情"""
    news = None  # type:News
    try:
        news = News.query.get(news_id)
    except Exception as e:
        current_app.logger.error(e)
        abort(404)

    if not news:
        # 返回数据未找到的页面
        abort(404)
    # 然后点击量自增1
    news.clicks += 1

    """新闻 收藏与关注"""
    # 当前登录用户是否关注当前新闻作者,默认值是false
    is_followed = False

    # 判断用户是否收藏过该新闻,默认值为false
    is_collected = False

    if g.user:  # 是否有用户登录
        if news in g.user.collection_news:
            is_collected = True

        # 新闻的作者的粉丝(追随者) 包不包含当前登录用户
        # 讲义的方法
        # if news.user:
        #     if news.user.followers.filter(User.id == g.user.id).count() > 0:
        #         is_followed = True

        # 上课时说的方法
        if news.user in g.user.followed:
            is_followed = True

    """新闻 评论"""
    # 获取当前新闻的评论
    comments = []
    try:
        comments = Comment.query.filter(Comment.news_id == news_id).order_by(Comment.create_time.desc()).all()
    except Exception as e:
        current_app.logger.error(e)

    comment_like_ids = []
    if g.user:
        # 如果当前用户已经登录
        try:
            comment_ids = [comment.id for comment in comments]
            if len(comment_ids) > 0:
                # 取到当前用户在当前新闻的所有评论的点赞的记录
                comment_likes = CommentLike.query.filter(CommentLike.comment_id.in_(comment_ids),
                                                         CommentLike.user_id == g.user.id).all()
                # 取出记录中所有的评论id
                comment_like_ids = [comment_like.comment_id for comment_like in comment_likes]
        except Exception as e:
            current_app.logger.error(e)

    comment_list = []
    for item in comments if comments else []:
        comment_dict = item.to_dict()
        comment_dict["is_like"] = False
        # 判断用户是否点赞该评论
        if g.user and item.id in comment_like_ids:
            comment_dict["is_like"] = True
        comment_list.append(comment_dict)

    data = {
        "user_info": g.user.to_dict() if g.user else None,
        "click_news_list": g.click_news_list,
        "news": news.to_dict(),
        "is_collected": is_collected,
        "comments": comment_list,
        "is_followed": is_followed
    }
    # print("返回detail.html")
    return render_template('new/detail.html', data=data)


@news_blue.route('/news_collect', methods=["POST"])
@user_login_data
def news_collect():
    user = g.user

    json_data = request.json
    news_id = json_data.get("news_id")
    action = json_data.get("action")

    if not user:
        return jsonify(errno=RET.SESSIONERR, errmsg="用户未登录")
    if not news_id:
        return jsonify(errno=RET.PARAMERR, errmsg="news_id不存在")
    if action not in ("collect", "cancel_collect"):
        return jsonify(errno=RET.PARAMERR, errmsg="action参数错误")

    news = None
    try:
        news = News.query.get(news_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询数据失败")
    if not news:
        return jsonify(errno=RET.NODATA, errmsg="新闻数据不存在")

    if action == "collect":
        user.collection_news.append(news)
    else:
        user.collection_news.remove(news)
    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="保存失败")

    return jsonify(errno=RET.OK, errmsg="操作成功")


@news_blue.route('/news_comment', methods=["POST"])
@user_login_data
def add_news_comment():
    """添加评论"""
    user = g.user
    if not user:
        return jsonify(errno=RET.SESSIONERR, errmsg="用户未登录")

    # 获取参数
    json_data = request.json
    news_id = json_data.get("news_id")
    comment_str = json_data.get("comment")  # 评论的内容
    parent_id = json_data.get("parent_id")  # 回复的评论的id

    news = None
    if not all([news_id, comment_str]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数不足")
    try:
        news = News.query.get(news_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询数据失败")

    if not news:
        return jsonify(errno=RET.NODATA, errmsg="该新闻不存在")

    # 初始化模型.保存数据
    comment = Comment()
    comment.user_id = user.id
    comment.news_id = news_id
    comment.content = comment_str
    if parent_id:
        comment.parent_id = parent_id

    # 保存到数据库
    try:
        db.session.add(comment)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="保存评论数据失败")

    # 返回响应
    data = comment.to_dict()
    print("评论成功")
    return jsonify(errno=RET.OK, errmsg="评论成功", data=data)


@news_blue.route('/comment_like', methods=["POST"])
@user_login_data
def set_comment_like():
    user = g.user
    if not user:
        return jsonify(errno=RET.SESSIONERR, errmsg="用户未登录")

    # 获取参数
    json_data = request.json
    comment_id = json_data.get("comment_id")
    news_id = json_data.get("news_id")
    action = json_data.get("action")  # 点赞操作类型:add(点赞), remove(取消点赞)

    # 判断参数
    if not all([comment_id, news_id, action]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数不全")

    if action not in ("add", "remove"):
        return jsonify(errno=RET.PARAMERR, errmsg="action参数错误")

    # 查询评论数据
    try:
        comment = Comment.query.get(comment_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询数据失败")

    if not comment:
        return jsonify(errno=RET.NODATA, errmsg="评论数据不存在")

    if action == "add":
        comment_like = CommentLike.query.filter_by(comment_id=comment_id, user_id=user.id).first()
        if not comment_like:
            comment_like = CommentLike()
            comment_like.comment_id = comment_id
            comment_like.user_id = user.id
            db.session.add(comment_like)
            # print("增加点赞")
            # 增加点赞条数
            comment.like_count += 1
    else:
        # 删除点赞数据
        comment_like = CommentLike.query.filter_by(comment_id=comment_id, user_id=user.id).first()
        if comment_like:
            db.session.delete(comment_like)
            # 减少点赞条数
            comment.like_count -= 1

    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="操作失败")
    # print("点赞成功")

    # data = {"comments": comment.to_dict()}
    return jsonify(errno=RET.OK, errmsg="点赞成功")


@news_blue.route('/followed_user', methods=["POST"])
@user_login_data
def followed_user():
    """关注/取消关注用户"""
    if not g.user:
        return jsonify(errno=RET.SESSIONERR, errmsg="用户未登录")

    user_id = request.json.get("user_id")
    action = request.json.get("action")

    if not all([user_id, action]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

    if action not in ("follow", "unfollow"):
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

    # 查询到关注的用户信息
    try:
        target_user = User.query.get(user_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询数据库失败")

    if not target_user:
        return jsonify(errno=RET.NODATA, errmsg="未查询到用户数据")

    # 根据不同操作做不同逻辑
    if action == "follow":
        if target_user.followers.filter(User.id == g.user.id).count() > 0:
            return jsonify(errno=RET.DATAEXIST, errmsg="当前已关注")
        target_user.followers.append(g.user)
    else:
        if target_user.followers.filter(User.id == g.user.id).count() > 0:
            target_user.followers.remove(g.user)

    # 保存到数据库
    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="数据保存错误")

    return jsonify(errno=RET.OK, errmsg="操作成功")
