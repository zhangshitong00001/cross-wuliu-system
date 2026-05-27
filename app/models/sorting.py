"""
阿拉木图收件点分装管理 - 收件点、分装任务模型
"""
from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, Text
from app.models.base import BaseModel, db


class CollectionPoint(BaseModel, db.Model):
    """收件点"""
    __tablename__ = 'collection_points'
    point_code = Column(String(50), unique=True, nullable=False, comment='收件点编码')
    name = Column(String(200), nullable=False, comment='收件点名称')
    address = Column(String(500), comment='地址')
    contact_person = Column(String(50), comment='联系人')
    contact_phone = Column(String(30), comment='联系方式')
    latitude = Column(Float, comment='纬度')
    longitude = Column(Float, comment='经度')
    status = Column(String(20), default='active', comment='状态：active-启用，inactive-停用')
    region = Column(String(100), comment='所在区域')


class SortingTask(BaseModel, db.Model):
    """分装任务"""
    __tablename__ = 'sorting_tasks'
    task_no = Column(String(50), unique=True, nullable=False, comment='任务编号')
    batch_no = Column(String(50), comment='批次号')
    point_id = Column(Integer, ForeignKey('collection_points.id'), comment='收件点ID')
    total_packages = Column(Integer, default=0, comment='总包裹数')
    total_weight = Column(Float, comment='总重量(kg)')
    total_volume = Column(Float, comment='总体积(m³)')
    assigned_to = Column(Integer, ForeignKey('users.id'), comment='分配人员')
    status = Column(String(20), default='pending', comment='状态：pending-待分装，sorting-分装中，completed-已完成，exception-异常')
    completed_at = Column(DateTime, comment='完成时间')


class SortingRecord(BaseModel, db.Model):
    """分装记录"""
    __tablename__ = 'sorting_records'
    task_id = Column(Integer, ForeignKey('sorting_tasks.id'), comment='任务ID')
    package_no = Column(String(50), comment='包裹编号')
    product_name = Column(String(200), comment='品名')
    quantity = Column(Integer, comment='数量')
    weight = Column(Float, comment='重量(kg)')
    operator_id = Column(Integer, ForeignKey('users.id'), comment='操作人')
    status = Column(String(20), default='pending', comment='状态：pending-待分装，sorted-已分装，exception-异常')
    exception_type = Column(String(50), comment='异常类型：miss-漏装，wrong-错装')
    exception_desc = Column(Text, comment='异常描述')
    exception_solution = Column(Text, comment='处理方案')
    exception_result = Column(Text, comment='处理结果')
    sorted_at = Column(DateTime, comment='分装时间')


class SortingPersonnel(BaseModel, db.Model):
    """分装人员"""
    __tablename__ = 'sorting_personnel'
    user_id = Column(Integer, ForeignKey('users.id'), comment='用户ID')
    shift_date = Column(DateTime, comment='排班日期')
    shift_type = Column(String(20), comment='班次：morning-早班，afternoon-午班，night-晚班')
    task_count = Column(Integer, default=0, comment='完成任务数')
    status = Column(String(20), default='idle', comment='状态：idle-空闲，working-工作中，off-休息')
