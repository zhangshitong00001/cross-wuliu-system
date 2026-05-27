"""
操作日志模型
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from app.models.base import BaseModel, db


class OperationLog(BaseModel, db.Model):
    """操作日志"""
    __tablename__ = 'operation_logs'
    user_id = Column(Integer, ForeignKey('users.id'), comment='操作人ID')
    username = Column(String(50), comment='操作人用户名')
    action = Column(String(50), comment='操作动作：create-创建，update-更新，delete-删除，export-导出，import-导入，login-登录，logout-登出')
    module = Column(String(50), comment='操作模块')
    target_id = Column(Integer, comment='操作对象ID')
    target_desc = Column(String(200), comment='操作对象描述')
    detail = Column(Text, comment='操作详情')
    ip_address = Column(String(50), comment='IP地址')
    operation_time = Column(DateTime, comment='操作时间')
