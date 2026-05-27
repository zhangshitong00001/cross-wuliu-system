"""
车辆与司机管理模型
"""
from sqlalchemy import Column, Integer, String, Float, ForeignKey, Text, Date
from app.models.base import BaseModel, db


class Vehicle(BaseModel, db.Model):
    """车辆"""
    __tablename__ = 'vehicles'
    plate_no = Column(String(20), unique=True, nullable=False, comment='车牌号')
    vehicle_type = Column(String(50), comment='车辆类型')
    brand = Column(String(50), comment='品牌')
    model = Column(String(50), comment='型号')
    load_weight = Column(Float, comment='载重(kg)')
    load_volume = Column(Float, comment='载货体积(m³)')
    driver_id = Column(Integer, ForeignKey('drivers.id'), comment='关联司机ID')
    driving_license = Column(String(200), comment='行驶证信息')
    status = Column(String(20), default='idle', comment='状态：idle-空闲，in_transit-运输中，maintenance-维修中')


class Driver(BaseModel, db.Model):
    """司机"""
    __tablename__ = 'drivers'
    name = Column(String(50), nullable=False, comment='姓名')
    phone = Column(String(20), comment='联系方式')
    license_no = Column(String(50), comment='驾驶证号')
    id_card = Column(String(30), comment='身份证号')
    status = Column(String(20), default='idle', comment='状态：idle-空闲，driving-驾驶中，rest-休息')
