"""
支付开票系统模型
"""
from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, Text, DECIMAL
from app.models.base import BaseModel, db


class PaymentRecord(BaseModel, db.Model):
    """支付记录"""
    __tablename__ = 'payment_records'
    payment_no = Column(String(50), unique=True, nullable=False, comment='支付编号')
    settlement_id = Column(Integer, ForeignKey('settlement_orders.id'), comment='结算单ID')
    amount = Column(DECIMAL(14, 2), comment='支付金额')
    payment_method = Column(String(30), comment='支付方式：bank-银行转账，alipay-支付宝，wechat-微信支付')
    status = Column(String(20), default='pending', comment='状态：pending-待支付，processing-支付中，success-支付成功，failed-支付失败')
    paid_at = Column(DateTime, comment='支付时间')
    voucher_path = Column(String(500), comment='支付凭证路径')
    remark = Column(Text, comment='备注')


class InvoiceRecord(BaseModel, db.Model):
    """发票记录"""
    __tablename__ = 'invoice_records'
    invoice_no = Column(String(50), unique=True, nullable=False, comment='发票号码')
    settlement_id = Column(Integer, ForeignKey('settlement_orders.id'), comment='结算单ID')
    invoice_type = Column(String(20), comment='发票类型：special-增值税专用发票，normal-普通发票')
    amount = Column(DECIMAL(14, 2), comment='发票金额')
    invoice_status = Column(String(20), default='pending', comment='状态：pending-待开具，issued-已开具，cancelled-已作废，red_flush-已红冲')
    issued_at = Column(DateTime, comment='开具时间')
    file_path = Column(String(500), comment='发票文件路径')
    buyer_info = Column(Text, comment='购买方信息')
    seller_info = Column(Text, comment='销售方信息')
    remark = Column(Text, comment='备注')
