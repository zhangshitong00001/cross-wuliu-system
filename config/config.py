"""
跨境物流管理系统 - 配置文件
"""
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'cross-border-logistics-secret-key-2026'
    
    # PostgreSQL数据库配置
    DB_USER = os.environ.get('DB_USER') or 'zhangshitong'
    DB_PASSWORD = os.environ.get('DB_PASSWORD') or 'zhangshitong123'
    DB_HOST = os.environ.get('DB_HOST') or '127.0.0.1'
    DB_PORT = os.environ.get('DB_PORT') or '5432'
    DB_NAME = os.environ.get('DB_NAME') or 'logistics_db'

    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        f'postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,
        'pool_recycle': 3600,
        'pool_pre_ping': True,
    }
    
    # 文件上传
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB
    
    # 分页
    ITEMS_PER_PAGE = 20
    
    # 日志
    LOG_DIR = os.path.join(BASE_DIR, 'logs')
    
    # Redis配置
    REDIS_HOST = os.environ.get('REDIS_HOST') or '127.0.0.1'
    REDIS_PORT = os.environ.get('REDIS_PORT') or 6379
    REDIS_DB = os.environ.get('REDIS_DB') or 0

    # 会话过期时间（秒）
    SESSION_TIMEOUT = 7200  # 2小时

    # 验证码过期时间（秒）
    CAPTCHA_EXPIRE = 300  # 5分钟

    # 登录失败锁定
    LOGIN_FAIL_LIMIT = 5  # 5次失败后需要验证码
    LOGIN_LOCK_MINUTES = 30  # 锁定30分钟

    # 备份
    BACKUP_DIR = os.path.join(BASE_DIR, 'backup')
    
    @staticmethod
    def init_app(app):
        pass


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig,
}
