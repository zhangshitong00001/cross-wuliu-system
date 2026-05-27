"""
物流状态跟踪模型
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from app.models.base import BaseModel, db


class TrackingRecord(BaseModel, db.Model):
    """物流跟踪记录"""
    __tablename__ = 'tracking_records'
    tracking_no = Column(String(50), comment='跟踪编号')
    order_no = Column(String(50), comment='订单号')
    waybill_no = Column(String(50), comment='运单号')
    batch_no = Column(String(50), comment='批次号')
    current_stage = Column(String(30), comment='当前环节：collecting-集货中，sorted-已分装，transporting-运输中，customs-报关中，cleared-已清关，distributing-配送中，signed-已签收')
    stage_detail = Column(Text, comment='环节详情')
    operator = Column(String(50), comment='操作人')
    operation_time = Column(DateTime, comment='操作时间')
    certificate = Column(String(500), comment='凭证信息')
    remark = Column(Text, comment='备注')
