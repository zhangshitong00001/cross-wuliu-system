"""
资金结算管理模型
"""
from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, Text, DECIMAL
from app.models.base import BaseModel, db


class SettlementOrder(BaseModel, db.Model):
    """结算单"""
    __tablename__ = 'settlement_orders'
    settlement_no = Column(String(50), unique=True, nullable=False, comment='结算编号')
    recon_id = Column(Integer, ForeignKey('reconciliation_records.id'), comment='对账记录ID')
    total_amount = Column(DECIMAL(14, 2), comment='结算金额')
    settlement_cycle = Column(String(20), comment='结算周期')
    settlement_method = Column(String(30), default='bank_transfer', comment='结算方式：bank_transfer-银行转账，third_party-第三方支付')
    status = Column(String(20), default='pending_audit', comment='状态：pending_audit-待审核，pending_payment-待支付，paid-已支付，completed-已完成')
    audit_by = Column(Integer, ForeignKey('users.id'), comment='审核人')
    audit_at = Column(DateTime, comment='审核时间')
    audit_opinion = Column(Text, comment='审核意见')
    remark = Column(Text, comment='备注')


class SettlementFlow(BaseModel, db.Model):
    """资金流水"""
    __tablename__ = 'settlement_flows'
    settlement_id = Column(Integer, ForeignKey('settlement_orders.id'), comment='结算单ID')
    flow_no = Column(String(50), comment='流水号')
    amount = Column(DECIMAL(14, 2), comment='金额')
    flow_type = Column(String(20), comment='类型：payable-应付，receivable-应收')
    flow_time = Column(DateTime, comment='发生时间')
    counterparty = Column(String(100), comment='交易方')
    remark = Column(Text, comment='备注')
