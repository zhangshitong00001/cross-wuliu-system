"""
计费规则可配置模型
"""
from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, Text, DECIMAL
from app.models.base import BaseModel, db


class ChargingRule(BaseModel, db.Model):
    """计费规则"""
    __tablename__ = 'charging_rules'
    rule_name = Column(String(100), nullable=False, comment='规则名称')
    rule_type = Column(String(30), comment='费用类型：transport-运输费，storage-仓储费，packaging-包装费，fuel_surcharge-燃油附加费，remote_surcharge-偏远地区附加费')
    calc_method = Column(String(30), comment='计算方式：fixed-固定费用，by_weight-按重量，by_volume-按体积，by_quantity-按数量，ladder-阶梯定价，max_vol_weight-体积重量取大')
    priority = Column(Integer, default=0, comment='优先级')
    rule_config = Column(Text, comment='规则配置(JSON格式)')
    effective_date = Column(DateTime, comment='生效日期')
    expire_date = Column(DateTime, comment='失效日期')
    status = Column(String(20), default='active', comment='状态：active-启用，inactive-停用')
