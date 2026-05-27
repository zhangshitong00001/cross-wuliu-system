"""
哈国口岸进口清关管理模型
"""
from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, Text, DECIMAL
from app.models.base import BaseModel, db


class ClearanceRecord(BaseModel, db.Model):
    """清关记录"""
    __tablename__ = 'clearance_records'
    clearance_no = Column(String(50), unique=True, nullable=False, comment='清关编号')
    batch_no = Column(String(50), comment='批次号')
    declaration_no = Column(String(50), comment='关联报关单号')
    status = Column(String(30), default='pending', comment='状态：pending-待清关，processing-清关中，cleared-已清关，rejected-驳回')
    submitted_at = Column(DateTime, comment='提交时间')
    cleared_at = Column(DateTime, comment='清关完成时间')
    handler_id = Column(Integer, ForeignKey('users.id'), comment='处理人')
    remark = Column(Text, comment='备注')


class ClearanceFee(BaseModel, db.Model):
    """清关费用"""
    __tablename__ = 'clearance_fees'
    clearance_id = Column(Integer, ForeignKey('clearance_records.id'), comment='清关记录ID')
    batch_no = Column(String(50), comment='批次号')
    fee_type = Column(String(50), comment='费用类型：tariff-关税，vat-增值税，inspection-查验费，storage-仓储费，other-其他')
    amount = Column(DECIMAL(12, 2), comment='金额')
    currency = Column(String(10), default='KZT', comment='币种')
    pay_status = Column(String(20), default='unpaid', comment='支付状态：unpaid-未支付，paid-已支付')
    remark = Column(Text, comment='备注')
