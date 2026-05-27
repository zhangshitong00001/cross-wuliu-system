"""
自定义认证装饰器 - 支持Redis Token验证
"""
from functools import wraps
from flask import request, jsonify, g
from app.models import User
from app.utils.redis_client import get_session_user, save_session_token
from config.config import Config


def token_required(f):
    """Token认证装饰器（替代Flask-Login的login_required）"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        # 从Header获取token
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]

        # 从参数获取
        if not token:
            token = request.args.get('token')

        # 从请求体获取
        if not token and request.is_json:
            data = request.get_json(silent=True)
            if data:
                token = data.get('token')

        if not token:
            return jsonify({'code': 401, 'message': '未登录，请先登录'})

        user_id = get_session_user(token)
        if not user_id:
            return jsonify({'code': 401, 'message': '登录已过期，请重新登录'})

        # 刷新过期时间
        save_session_token(user_id, token, Config.SESSION_TIMEOUT)

        user = User.query.get(user_id)
        if not user or user.status == 0:
            return jsonify({'code': 401, 'message': '用户不存在或已被禁用'})

        g.current_user = user
        g.current_token = token
        return f(*args, **kwargs)

    return decorated


def get_current_user():
    """获取当前用户"""
    return getattr(g, 'current_user', None)
