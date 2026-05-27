"""
口岸至阿拉木图仓库运输管理模型
"""
from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, Text
from app.models.base import BaseModel, db


class PortTransportTask(BaseModel, db.Model):
    """口岸运输任务"""
    __tablename__ = 'port_transport_tasks'
    task_no = Column(String(50), unique=True, nullable=False, comment='任务编号')
    batch_no = Column(String(50), comment='批次号')
    vehicle_id = Column(Integer, ForeignKey('vehicles.id'), comment='车辆ID')
    driver_id = Column(Integer, ForeignKey('drivers.id'), comment='司机ID')
    departure_time = Column(DateTime, comment='出发时间')
    estimated_arrival = Column(DateTime, comment='预计到达时间')
    actual_arrival = Column(DateTime, comment='实际到达时间')
    status = Column(String(20), default='pending', comment='状态：pending-待出发，in_transit-运输中，arrived-已到达，completed-已完成')
    total_weight = Column(Float, comment='总重量')
    total_volume = Column(Float, comment='总体积')
    alert_sent = Column(Integer, default=0, comment='是否已发送到货预告')
    remark = Column(Text, comment='备注')


class PortTransportArrival(BaseModel, db.Model):
    """到货验收"""
    __tablename__ = 'port_transport_arrivals'
    task_id = Column(Integer, ForeignKey('port_transport_tasks.id'), comment='运输任务ID')
    arrival_time = Column(DateTime, comment='到货时间')
    inspector_id = Column(Integer, ForeignKey('users.id'), comment='验收人')
    damaged_quantity = Column(Integer, default=0, comment='破损数量')
    short_quantity = Column(Integer, default=0, comment='短缺数量')
    normal_quantity = Column(Integer, default=0, comment='正常数量')
    inspection_result = Column(String(20), default='pending', comment='验收结果：pending-待验收，normal-正常，exception-异常')
    exception_desc = Column(Text, comment='异常描述')
    remark = Column(Text, comment='备注')
