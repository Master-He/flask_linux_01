from flask_script import Manager
from flask_migrate import Migrate, MigrateCommand
from info import create_app, db

from info import models
from info.models import User

app = create_app('development')

manager = Manager(app)
Migrate(app, db)
manager.add_command("db", MigrateCommand)


# 在终端运行三条命令
# 1.python3 manager db init 生成Migrations迁移目录
# 2.python3 manager db migrate -m "initial" 生成迁移脚本文件
# 3.python3 manager db upgrade 生成具体的数据库表


# 就是可以用脚本给下面被装饰的函数进行传参
# 类似于argv传参
# -n:表示在使用脚本传输数据的时候,需要用到的值
@manager.option('-n', '--name', dest='name')
@manager.option('-p', '--password', dest='password')
def create_super_user(name, password):

    if not all([name, password]):
        print('参数不足')
        return

    # 初始化管理员
    user = User()
    user.nick_name = name
    user.mobile = name
    user.password = password
    user.is_admin = True

    try:
        db.session.add(user)
        db.session.commit()
        print("创建成功")
    except Exception as e:
        print(e)
        db.session.rollback()

if __name__ == '__main__':
    manager.run()
