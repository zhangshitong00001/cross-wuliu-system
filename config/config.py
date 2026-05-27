"""
跨境物流管理系统 - 配置文件
"""
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'cross-border-logistics-secret-key-2026'
    
    # MySQL数据库配置
    DB_USER = os.environ.get('DB_USER') or 'debian-sys-maint'
    DB_PASSWORD = os.environ.get('DB_PASSWORD') or 'Rlt13NjG3fP2mg0I'
    DB_HOST = os.environ.get('DB_HOST') or 'localhost'
    DB_PORT = os.environ.get('DB_PORT') or '3306'
    DB_NAME = os.environ.get('DB_NAME') or 'cross_border_logistics'
    
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        f'mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4'
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
    
    # 会话过期时间（秒）
    SESSION_TIMEOUT = 3600 * 8
    
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
