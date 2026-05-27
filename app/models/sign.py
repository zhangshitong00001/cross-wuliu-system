"""
签收入库管理模型
"""
from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, Text
from app.models.base import BaseModel, db


class SignRecord(BaseModel, db.Model):
    """签收记录"""
    __tablename__ = 'sign_records'
    sign_no = Column(String(50), unique=True, nullable=False, comment='签收编号')
    package_no = Column(String(50), comment='包裹编号')
    point_id = Column(Integer, ForeignKey('collection_points.id'), comment='收件点ID')
    sign_type = Column(String(20), default='manual', comment='签收方式：scan-扫码签收，manual-手动签收')
    signer = Column(String(50), comment='签收人')
    sign_time = Column(DateTime, comment='签收时间')
    package_status = Column(String(30), comment='包裹状态：normal-正常，damaged-破损，short-短缺')
    damage_desc = Column(Text, comment='破损/短缺说明')
    status = Column(String(20), default='signed', comment='状态：signed-已签收，stored-已入库')
    operator_id = Column(Integer, ForeignKey('users.id'), comment='操作人')


class SignCertificate(BaseModel, db.Model):
    """签收凭证"""
    __tablename__ = 'sign_certificates'
    sign_id = Column(Integer, ForeignKey('sign_records.id'), comment='签收记录ID')
    cert_type = Column(String(20), comment='凭证类型：photo-照片，signature-电子签名')
    file_path = Column(String(500), comment='文件路径')
    file_name = Column(String(200), comment='文件名')
    uploaded_at = Column(DateTime, comment='上传时间')
