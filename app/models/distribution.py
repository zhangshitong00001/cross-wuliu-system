"""
收件点配送管理模型
"""
from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, Text
from app.models.base import BaseModel, db


class DistributionTask(BaseModel, db.Model):
    """配送任务"""
    __tablename__ = 'distribution_tasks'
    task_no = Column(String(50), unique=True, nullable=False, comment='任务编号')
    batch_no = Column(String(50), comment='批次号')
    point_id = Column(Integer, ForeignKey('collection_points.id'), comment='收件点ID')
    vehicle_id = Column(Integer, ForeignKey('vehicles.id'), comment='配送车辆ID')
    driver_id = Column(Integer, ForeignKey('drivers.id'), comment='配送人员ID')
    package_count = Column(Integer, default=0, comment='包裹数量')
    total_weight = Column(Float, comment='总重量')
    status = Column(String(20), default='pending', comment='状态：pending-待配送，dispatching-配送中，completed-已完成，exception-异常')
    planned_time = Column(DateTime, comment='计划配送时间')
    actual_departure = Column(DateTime, comment='实际出发时间')
    actual_arrival = Column(DateTime, comment='实际到达时间')
    route_json = Column(Text, comment='配送路线(JSON)')
    remark = Column(Text, comment='备注')


class DistributionRecord(BaseModel, db.Model):
    """配送记录"""
    __tablename__ = 'distribution_records'
    task_id = Column(Integer, ForeignKey('distribution_tasks.id'), comment='任务ID')
    package_no = Column(String(50), comment='包裹编号')
    status = Column(String(20), default='pending', comment='状态：pending-待配送，delivered-已送达，failed-配送失败')
    exception_type = Column(String(50), comment='异常类型：delay-延误，reject-拒收，lost-丢失')
    exception_desc = Column(Text, comment='异常描述')
    exception_solution = Column(Text, comment='处理方案')
    exception_result = Column(Text, comment='处理结果')
    delivered_at = Column(DateTime, comment='送达时间')
    signer = Column(String(50), comment='签收人')


class DistributionPersonnel(BaseModel, db.Model):
    """配送人员"""
    __tablename__ = 'distribution_personnel'
    user_id = Column(Integer, ForeignKey('users.id'), comment='用户ID')
    check_in_time = Column(DateTime, comment='签到时间')
    check_out_time = Column(DateTime, comment='签退时间')
    status = Column(String(20), default='offline', comment='状态：offline-离线，online-在线，working-配送中')
    current_location = Column(String(200), comment='当前位置')
