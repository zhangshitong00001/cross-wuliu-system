"""
文件生成管理 - 装车文件、报关文件模型
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from app.models.base import BaseModel, db


class Document(BaseModel, db.Model):
    """文件"""
    __tablename__ = 'documents'
    doc_no = Column(String(50), unique=True, nullable=False, comment='文件编号')
    doc_type = Column(String(30), nullable=False, comment='文件类型：loading-装车文件，customs-报关文件，invoice-商业发票，packing_list-装箱单，coo-原产地证明')
    title = Column(String(200), comment='文件标题')
    batch_no = Column(String(50), comment='关联批次号')
    content_json = Column(Text, comment='文件内容(JSON格式)')
    file_path = Column(String(500), comment='文件存储路径')
    file_format = Column(String(20), default='pdf', comment='文件格式：pdf，xlsx，docx')
    status = Column(String(20), default='draft', comment='状态：draft-草稿，final-定稿，archived-已归档')
    version = Column(Integer, default=1, comment='当前版本号')
    created_by = Column(Integer, ForeignKey('users.id'), comment='创建人')
    is_exported = Column(Integer, default=0, comment='是否已导出')


class DocumentVersion(BaseModel, db.Model):
    """文件版本"""
    __tablename__ = 'document_versions'
    doc_id = Column(Integer, ForeignKey('documents.id'), comment='文件ID')
    version_no = Column(Integer, comment='版本号')
    content_json = Column(Text, comment='版本内容')
    file_path = Column(String(500), comment='版本文件路径')
    change_summary = Column(Text, comment='变更摘要')
    operator_id = Column(Integer, ForeignKey('users.id'), comment='操作人')
