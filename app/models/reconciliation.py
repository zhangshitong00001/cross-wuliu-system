"""
对账管理模型
"""
from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, Text, DECIMAL
from app.models.base import BaseModel, db


class ReconciliationRecord(BaseModel, db.Model):
    """对账记录"""
    __tablename__ = 'reconciliation_records'
    recon_no = Column(String(50), unique=True, nullable=False, comment='对账编号')
    batch_no = Column(String(50), comment='批次号')
    recon_type = Column(String(20), default='monthly', comment='对账频率：daily-日结，weekly-周结，monthly-月结')
    recon_period_start = Column(DateTime, comment='对账周期开始')
    recon_period_end = Column(DateTime, comment='对账周期结束')
    total_amount = Column(DECIMAL(14, 2), comment='总金额')
    status = Column(String(20), default='pending', comment='状态：pending-待对账，processing-对账中，completed-已完成，差异-有差异')
    diff_count = Column(Integer, default=0, comment='差异数量')
    confirmed_by = Column(Integer, ForeignKey('users.id'), comment='确认人')
    confirmed_at = Column(DateTime, comment='确认时间')


class ReconciliationDetail(BaseModel, db.Model):
    """对账明细"""
    __tablename__ = 'reconciliation_details'
    recon_id = Column(Integer, ForeignKey('reconciliation_records.id'), comment='对账记录ID')
    order_no = Column(String(50), comment='订单号')
    waybill_no = Column(String(50), comment='运单号')
    fee_type = Column(String(50), comment='费用类型')
    expected_amount = Column(DECIMAL(12, 2), comment='预期金额')
    actual_amount = Column(DECIMAL(12, 2), comment='实际金额')
    diff_amount = Column(DECIMAL(12, 2), comment='差异金额')
    diff_type = Column(String(50), comment='差异类型：rate_diff-费率差异，surcharge_miss-附加费漏记，exchange_diff-汇率波动，duplicate-重复账单')
    diff_reason = Column(Text, comment='差异原因')
    solution = Column(Text, comment='处理方案')
    status = Column(String(20), default='pending', comment='状态：pending-待处理，processing-处理中，resolved-已解决')
    handler_id = Column(Integer, ForeignKey('users.id'), comment='处理人')
