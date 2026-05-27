"""
Redis客户端 - 缓存、Session、验证码存储
"""
import json
import redis
from datetime import timedelta

REDIS_CONFIG = {
    'host': '127.0.0.1',
    'port': 6379,
    'db': 0,
    'password': 'fRVfyvJyXDh8UJvm0v9AplyGm843H',
    'decode_responses': True,
    'socket_connect_timeout': 3,
}

# 连接池
_pool = None


def get_redis():
    global _pool
    if _pool is None:
        _pool = redis.ConnectionPool(**REDIS_CONFIG)
    return redis.Redis(connection_pool=_pool)


# ===== 验证码 =====
def save_captcha(code_id, code, expire=300):
    """保存验证码到Redis，默认5分钟过期"""
    r = get_redis()
    r.setex(f'captcha:{code_id}', expire, code)


def verify_captcha(code_id, code):
    """验证验证码（验证后立即删除）"""
    r = get_redis()
    key = f'captcha:{code_id}'
    saved = r.get(key)
    if saved and saved.lower() == code.lower():
        r.delete(key)
        return True
    return False


# ===== 登录Session =====
def save_session_token(user_id, token, expire=7200):
    """保存登录session，默认2小时过期"""
    r = get_redis()
    r.setex(f'session:{token}', expire, str(user_id))


def get_session_user(token):
    """获取session对应的用户ID"""
    r = get_redis()
    val = r.get(f'session:{token}')
    return int(val) if val else None


def delete_session(token):
    """删除session"""
    r = get_redis()
    r.delete(f'session:{token}')


# ===== 登录失败计数 =====
def incr_login_fail(ip):
    """记录登录失败次数"""
    r = get_redis()
    key = f'login_fail:{ip}'
    count = r.incr(key)
    r.expire(key, 1800)  # 30分钟重置
    return count


def get_login_fail_count(ip):
    """获取登录失败次数"""
    r = get_redis()
    val = r.get(f'login_fail:{ip}')
    return int(val) if val else 0


def reset_login_fail(ip):
    """重置登录失败计数"""
    r = get_redis()
    r.delete(f'login_fail:{ip}')
