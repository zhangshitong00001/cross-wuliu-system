"""
异常预警模型
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from app.models.base import BaseModel, db


class AlertRecord(BaseModel, db.Model):
    """预警记录"""
    __tablename__ = 'alert_records'
    alert_no = Column(String(50), unique=True, nullable=False, comment='预警编号')
    alert_type = Column(String(50), comment='预警类型：overdue_stay-货物滞留超期，material_miss-报关材料缺失，route_deviation-运输轨迹偏离，package_damage-包裹破损/丢失，sign_exception-签收异常，recon_diff-对账差异超标，settlement_overdue-结算逾期，invoice_fail-开票失败')
    alert_level = Column(String(20), default='medium', comment='预警级别：low-低，medium-中，high-高')
    related_business = Column(String(50), comment='关联业务类型')
    related_id = Column(Integer, comment='关联业务ID')
    description = Column(Text, comment='预警描述')
    status = Column(String(20), default='pending', comment='状态：pending-待处理，processing-处理中，resolved-已解决')
    notified_via = Column(String(100), comment='通知方式：system-系统消息，sms-短信，email-邮件')
    handler_id = Column(Integer, ForeignKey('users.id'), comment='处理人')
    handled_at = Column(DateTime, comment='处理时间')
    solution = Column(Text, comment='处理方案')
    result = Column(Text, comment='处理结果')
