# from info.modules.passport import passport_blue
import random
import re
from datetime import datetime

from flask import session

from info.lib.yuntongxun.sms import CCP
from info.models import User

from . import passport_blue

# current_app不太懂
from flask import current_app, jsonify
from flask import make_response
from flask import request

from info import constants, db
from info import redis_store
from info.utils.captcha.captcha import captcha
from info.utils.response_code import RET


@passport_blue.route('/image_code')
def get_image_code():
    # 1.获取图片当前编号id
    code_id = request.args.get('code_id')

    # 2.生成验证码
    name, text, image = captcha.generate_captcha()

    print("图片验证码是:", text)

    # 保存当前的图片验证码内容
    try:
        redis_store.setex('ImageCode_' + code_id, constants.IMAGE_CODE_REDIS_EXPIRES, text)
    except Exception as e:
        current_app.logger.error(e)
        return make_response(jsonify(errno=RET.DATAERR, errmsg='保存图片验证码失败'))

    # 生成返回响应内容
    resp = make_response(image)

    # 设置内容类型, 头部是Content-Type: image/jpg
    resp.headers['Content-Type'] = 'image/jpg'
    return resp


@passport_blue.route('/smscode', methods=["GET", "POST"])
def send_sms():
    """
    1.接受参数并判断是否有值
    2.校验手机号是否正确
    3.通过传入的图片编码取redis中查询真实的图片验证码内容
    4.进行验证码内容的比对
    5.生成发送短信的内容并发送短信
    6.redis中保存短信验证码内容
    7.返回发送成功的响应

    :return:
    """

    # 1.接受参数并判断是否有值
    # 取到请求值中的内容
    param_dict = request.json
    mobile = param_dict.get("mobile")
    image_code = param_dict.get("image_code")
    image_code_id = param_dict.get("image_code_id")

    if not all([mobile, image_code, image_code_id]):
        # 参数不全
        return jsonify(errno=RET.PARAMERR, errmsg="参数不全")

    # 2.校验手机号是否正确
    if not re.match("^1[34578][0-9]{9}$", mobile):
        # 提示手机号不正确
        return jsonify(errno=RET.DATAERR, errmsg="手机号不正确")

    # 3.通过传入的图片编码去redis中查询真实的图片验证码内容
    try:
        real_image_code = redis_store.get("ImageCode_" + image_code_id)
        # 如果能够取出来值,删除redis中缓存的内容
        if real_image_code:
            real_image_code = real_image_code.decode()
            redis_store.delete("ImageCode_" + image_code_id)
    except Exception as e:
        current_app.logger.error(e)
        # 获取图片验证码失败
        return jsonify(errno=RET.DBERR, errmsg="获取图片验证码失败")
    # 3.1
    if not real_image_code:
        # 验证码已过期
        return jsonify(errno=RET.NODATA, errmsg="验证码已过期")

    # 4.进行验证码内容的比对
    if image_code.lower() != real_image_code.lower():
        # 验证码输入错误
        return jsonify(errno=RET.DATAERR, errmsg="验证码输入错误")
    # 4.1校验该手机是否已经注册
    try:
        user = User.query.filter_by(mobile=mobile).first()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="数据库查询错误")
    if user:
        # 该手机已被注册
        return jsonify(errno=RET.DATAEXIST, errmsg="该手机已被注册")

    # 5.生成发送短信的内容并发送短信
    result = random.randint(0, 999999)
    sms_code = "%06d" % result
    current_app.logger.debug("短信验证码的内容:%s" % sms_code)
    # 第一个参数是手机号码
    # 第二个参数是个列表,是短信发送平台模板的变量,
    # 第三个参数是采用的模板
    # 下面需要用到再去掉注释
    """
    result = CCP().send_template_sms(mobile, [sms_code, constants.SMS_CODE_REDIS_EXPIRES / 60], "1")
    if result != 0:
        # 发送短信失败
        return jsonify(errno=RET.THIRDERR, errmsg="发送短信失败")
    """

    # 6. redis中保存短信验证码内容
    try:
        redis_store.set("SMS_" + mobile, sms_code, constants.SMS_CODE_REDIS_EXPIRES)
    except Exception as e:
        current_app.logger.error(e)
        # 保存短信验证码失败
        return jsonify(errno=RET.DBERR, errmsg="保存短信验证码失败")

    # 7.返回发送成功的响应
    return jsonify(error=RET.OK, errmsg="发送成功")


@passport_blue.route('/register', methods=["POST"])
def register():
    """
    1.获取参数和判断是否有值
    2.从redis中获取制定手机号对应的短信验证码
    3.校验验证码
    4.初始化user模型,并设置数据,然后添加到数据库
    5.保存当前用户的状态
    6.返回注册的结果
    :return:
    """

    # 1.获取参数和判断是否有值
    json_data = request.json
    mobile = json_data.get("mobile")
    sms_code = json_data.get("smscode")
    password = json_data.get("password")

    if not all([mobile, sms_code, password]):
        # 参数不全
        return jsonify(errno=RET.PARAMERR, errmsg="参数不全")

    # 2.从redis中获取指定手机号对应的短信验证码
    try:
        # ========原句
        # real_sms_code = redis_store.get("SMS_" + mobile)
        # ========新句
        real_sms_code = redis_store.get("SMS_" + mobile).decode()
    except Exception as e:
        current_app.logger.error(e)
        # 获取本地验证码失败
        return jsonify(error=RET.DBERR, errmsg="获取本地验证码失败")
    if not real_sms_code:
        return jsonify(errno=RET.NODATA, errmsg="短信验证码过期")

    # 3.校验验证码

    print(sms_code)
    print(real_sms_code)
    # sms_code = sms_code.encode()
    #
    # print(sms_code.lower())
    # print(real_sms_code.lower())

    if sms_code != real_sms_code:
        return jsonify(errno=RET.DATAERR, errmsg="短信验证码错误")
    # 删除短信验证码
    try:
        redis_store.delete("SMS_" + mobile)
    except Exception as e:
        current_app.logger.error(e)

    # 4.初始化 user 模型,并设置数据并添加到数据库
    user = User()
    # 新知识 ================================================
    user.nick_name = mobile
    user.mobile = mobile
    # 对密码进行处理
    user.password = password

    try:
        db.session.add(user)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(e)
        # 数据保存错误
        return jsonify(errno=RET.DATAERR, errmsg="数据保存错误")

    # 5.保存用户登录状态
    session["user.id"] = user.id
    session["nick_name"] = user.nick_name
    session["mobile"] = user.mobile

    # 6. 返回注册结果
    return jsonify(errno=RET.OK, errmsg="OK")


@passport_blue.route('/login', methods=["POST"])
def login():
    """
    1. 获取参数和判断是否有值
    2. 从数据库查询出指定的用户
    3. 校验密码
    4. 保存用户登录状态
    5. 返回结果
    :return:
    """
    jason_data = request.json
    mobile = jason_data.get("mobile")
    password = jason_data.get("password")

    # 1. 获取参数和判断是否有值
    if not all([mobile, password]):
        # 将关键字参数转换成jason参数用jsonify
        return jsonify(errno=RET.DATAERR, errmsg="参数不全")

    # 2. 从数据库查询出指定的用户
    try:
        user = User.query.filter_by(mobile=mobile).first()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.USERERR, errmsg="查询数据错误")

    if not user:
        return jsonify(errno=RET.USERERR, errmsg="用户不存在")

    # 3. 校验密码
    # check_password是flask系统提供给我们用的
    if not user.check_password(password):
        return jsonify(error=RET.PWDERR, errmsg="密码错误")

    # 4. 保存用户登录状态
    # session已经和redis关联在一起了
    session["user_id"] = user.id
    session["nick_name"] = user.nick_name
    session["mobile"] = user.mobile
    # 记录用户最后一次登录时间
    user.last_login = datetime.now()
    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)

    # 5.登录成功
    print("登录成功")
    return jsonify(errno=RET.OK, errmsg="OK")


@passport_blue.route('/logout')
def logout():
    session.pop("user_id", None)
    session.pop("nick_name", None)
    session.pop("mobile", None)
    session["is_admin"] = False
    return jsonify(errno=RET.OK, errmsg="退出成功")
