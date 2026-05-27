"""
用户、角色、权限模型
"""
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Table, Text
from app.models.base import BaseModel, db


class Permission(BaseModel, db.Model):
    __tablename__ = 'permissions'
    code = Column(String(50), unique=True, nullable=False, comment='权限编码')
    name = Column(String(100), nullable=False, comment='权限名称')
    module = Column(String(50), comment='所属模块')
    description = Column(Text, comment='权限描述')


class Role(BaseModel, db.Model):
    __tablename__ = 'roles'
    code = Column(String(50), unique=True, nullable=False, comment='角色编码')
    name = Column(String(100), nullable=False, comment='角色名称')
    description = Column(Text, comment='角色描述')
    
    permissions = db.relationship('Permission', secondary='role_permissions', lazy='subquery')


role_permissions = db.Table('role_permissions',
    Column('role_id', Integer, ForeignKey('roles.id'), primary_key=True),
    Column('permission_id', Integer, ForeignKey('permissions.id'), primary_key=True)
)


class User(UserMixin, BaseModel, db.Model):
    __tablename__ = 'users'
    username = Column(String(50), unique=True, nullable=False, comment='用户名')
    password_hash = Column(String(256), nullable=False, comment='密码哈希')
    real_name = Column(String(50), comment='真实姓名')
    email = Column(String(100), comment='邮箱')
    phone = Column(String(20), comment='手机号')
    avatar = Column(String(256), comment='头像')
    role_id = Column(Integer, ForeignKey('roles.id'), comment='角色ID')
    status = Column(Integer, default=1, comment='状态：1-启用，0-禁用')
    last_login_at = Column(DateTime, comment='最后登录时间')
    last_login_ip = Column(String(50), comment='最后登录IP')
    
    role = db.relationship('Role', backref='users', lazy='joined')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def has_permission(self, permission_code):
        if self.role and self.role.permissions:
            return any(p.code == permission_code for p in self.role.permissions)
        return False

    @property
    def is_admin(self):
        return self.role and self.role.code == 'super_admin'

    def to_dict(self, exclude=None):
        exclude = exclude or ['password_hash']
        return super().to_dict(exclude)
