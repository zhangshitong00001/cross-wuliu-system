"""
装车运输管理模型
"""
from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, Text
from app.models.base import BaseModel, db


class TransportTask(BaseModel, db.Model):
    """运输任务"""
    __tablename__ = 'transport_tasks'
    task_no = Column(String(50), unique=True, nullable=False, comment='任务编号')
    batch_no = Column(String(50), comment='批次号')
    vehicle_id = Column(Integer, ForeignKey('vehicles.id'), comment='车辆ID')
    driver_id = Column(Integer, ForeignKey('drivers.id'), comment='司机ID')
    route_from = Column(String(200), comment='出发地')
    route_to = Column(String(200), comment='目的地')
    planned_departure = Column(DateTime, comment='计划出发时间')
    planned_arrival = Column(DateTime, comment='计划到达时间')
    actual_departure = Column(DateTime, comment='实际出发时间')
    actual_arrival = Column(DateTime, comment='实际到达时间')
    status = Column(String(20), default='pending', comment='状态：pending-待出发，in_transit-运输中，arrived-已到达，completed-已完成，exception-异常')
    total_weight = Column(Float, comment='总重量(kg)')
    total_volume = Column(Float, comment='总体积(m³)')
    priority = Column(Integer, default=0, comment='优先级')
    created_by = Column(Integer, ForeignKey('users.id'), comment='创建人')


class TransportNode(BaseModel, db.Model):
    """运输节点"""
    __tablename__ = 'transport_nodes'
    task_id = Column(Integer, ForeignKey('transport_tasks.id'), comment='任务ID')
    node_name = Column(String(100), comment='节点名称')
    node_type = Column(String(30), comment='节点类型：departure-出发，waypoint-途经，arrival-到达')
    latitude = Column(Float, comment='纬度')
    longitude = Column(Float, comment='经度')
    record_time = Column(DateTime, comment='记录时间')
    description = Column(Text, comment='描述')


class TransportException(BaseModel, db.Model):
    """运输异常"""
    __tablename__ = 'transport_exceptions'
    task_id = Column(Integer, ForeignKey('transport_tasks.id'), comment='任务ID')
    exception_type = Column(String(50), comment='异常类型：delay-延误，route_deviation-偏离路线，damage-货物破损')
    description = Column(Text, comment='异常描述')
    severity = Column(String(20), default='medium', comment='严重程度：low-低，medium-中，high-高')
    solution = Column(Text, comment='处理方案')
    progress = Column(String(20), default='pending', comment='处理进度：pending-待处理，processing-处理中，resolved-已解决')
    result = Column(Text, comment='处理结果')
    handler_id = Column(Integer, ForeignKey('users.id'), comment='处理人')
