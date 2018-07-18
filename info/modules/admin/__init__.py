from flask import Blueprint
from flask import redirect
from flask import request
from flask import session

from info.utils.common import user_login_data

admin_blue = Blueprint("admin", __name__, url_prefix="/admin")

from . import views


# 只与后台关联的写在__init__.py
@admin_blue.before_request
@user_login_data
def check_admin():
    is_admin = session.get("is_admin", None)
    # 如果不是管理员,那么就不允许进入后台,并且不能让你访问后台的管理系统, 非admin只能通过/admin/login进入
    if not is_admin and not request.url.endswith("/admin/login"):
        return redirect('/')
