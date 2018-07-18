# 添加10000条假数据
import datetime
import random

from info import db
from info.models import User
from manage import app


def add_test_users():
    users = []
    now = datetime.datetime.now()  # {datetime}2018-07-11 22:10:51.674202
    for num in range(0, 10000):
        try:
            user = User()
            # 11位数,不足11位的前面补零
            user.nick_name = "%011d" % num  # 例子'00000000000'
            user.mobile = "%011d" % num  # 例子'00000000000'
            user.password_hash = "pbkdf2:sha256:50000$SgZPAbEj$a253b9220b7a916e03bf27119d401c48ff4a1c81d7e00644e0aaf6f3a8c55829"

            # 2678400秒 是 31天
            # a = datetime.timedelta(seconds=random.randint(0, 2678400)) # 例子{ timedelta } 16 days, 5:30:01

            user.last_login = now - datetime.timedelta(seconds=random.randint(0, 2678400)) # 例子:2018-06-19 17:49:23.674202
            users.append(user)
            print(user.mobile)
        except Exception as e:
            print(e)
    # 手动开启一个app的上下文
    # 只有在上下文环境中才能进行数据库操作
    with app.app_context():
        db.session.add_all(users)
        db.session.commit()
    print('OK')


if __name__ == '__main__':
    add_test_users()
