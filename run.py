#!/usr/bin/env python3
"""
跨境物流管理系统 - 启动入口
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def get_app():
    """延迟创建 Flask 应用实例（避免在参数解析时连接数据库）"""
    from app import create_app
    return create_app(os.environ.get('FLASK_CONFIG') or 'default')


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='跨境物流管理系统')
    parser.add_argument('--init-db', action='store_true', help='初始化数据库并创建默认数据')
    parser.add_argument('--host', default='0.0.0.0', help='监听地址')
    parser.add_argument('--port', type=int, default=5000, help='监听端口')
    args = parser.parse_args()

    app = get_app()

    debug = os.environ.get('FLASK_DEBUG', '0') == '1'

    if args.init_db:
        with app.app_context():
            from app.models import db, User, Role, Permission
            from app.models.base import BaseModel

            # 创建所有表
            db.create_all()

            # 检查是否已有数据
            if User.query.count() == 0:
                # 创建角色
                roles_data = {
                    'super_admin': '甲方超级管理员',
                    'admin': '运营管理员',
                    'finance': '财务人员',
                    'warehouse_op': '仓库操作员',
                    'transport': '运输人员',
                    'customs_broker': '报关专员',
                    'sorting_op': '分装人员',
                    'point_admin': '收件点管理员',
                    'customer': '客户'
                }
                roles = {}
                for code, name in roles_data.items():
                    role = Role(code=code, name=name)
                    role.save()
                    roles[code] = role

                # 创建默认管理员
                admin = User(
                    username='admin',
                    real_name='系统管理员',
                    role_id=roles['super_admin'].id,
                    status=1
                )
                admin.set_password('admin123')
                admin.save()

                # 创建测试用户
                test_users = [
                    ('warehouse_op', '仓库操作员', '仓库操作员'),
                    ('transport', '运输人员', '运输人员'),
                    ('customs_broker', '报关专员', '报关专员'),
                    ('sorting_op', '分装人员', '分装人员'),
                    ('finance', '财务人员', '财务人员'),
                ]
                for role_code, username, real_name in test_users:
                    user = User(
                        username=username,
                        real_name=real_name,
                        role_id=roles[role_code].id,
                        status=1
                    )
                    user.set_password(f'{username}1')
                    user.save()

                print(f'✓ 已创建 {len(roles_data)} 个角色')
                print(f'✓ 已创建 {1 + len(test_users)} 个用户')
                print(f'  管理员: admin / admin123')
                for _, username, _ in test_users:
                    print(f'  {username}: {username}1')
            else:
                print('数据库已有数据，跳过初始化')

        print('数据库初始化完成！')
    else:
        app.run(host=args.host, port=args.port, debug=debug, use_reloader=debug)
