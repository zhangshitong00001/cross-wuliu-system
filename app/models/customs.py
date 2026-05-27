"""
霍尔果斯口岸出口报关管理模型
"""
from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, Text
from app.models.base import BaseModel, db


class CustomsDeclaration(BaseModel, db.Model):
    """报关单"""
    __tablename__ = 'customs_declarations'
    declaration_no = Column(String(50), unique=True, nullable=False, comment='报关单号')
    batch_no = Column(String(50), comment='批次号')
    transport_task_id = Column(Integer, ForeignKey('transport_tasks.id'), comment='运输任务ID')
    status = Column(String(30), default='pending', comment='状态：pending-待审核，reviewing-审核中，approved-审核通过，rejected-审核驳回')
    submitted_at = Column(DateTime, comment='提交时间')
    reviewed_at = Column(DateTime, comment='审核时间')
    reviewer_opinion = Column(Text, comment='审核意见')
    reject_reason = Column(Text, comment='驳回原因')
    submitted_by = Column(Integer, ForeignKey('users.id'), comment='提交人')
    confirmed_by = Column(Integer, ForeignKey('users.id'), comment='确认人')
    confirmed_at = Column(DateTime, comment='确认时间')


class CustomsMaterial(BaseModel, db.Model):
    """报关补充材料"""
    __tablename__ = 'customs_materials'
    declaration_id = Column(Integer, ForeignKey('customs_declarations.id'), comment='报关单ID')
    material_type = Column(String(50), comment='材料类型')
    file_path = Column(String(500), comment='文件路径')
    file_name = Column(String(200), comment='文件名')
    status = Column(String(20), default='pending', comment='状态：pending-待审核，approved-已通过，rejected-已驳回')
    uploaded_by = Column(Integer, ForeignKey('users.id'), comment='上传人')
    uploaded_at = Column(DateTime, comment='上传时间')
