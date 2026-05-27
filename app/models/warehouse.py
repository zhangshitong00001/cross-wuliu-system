"""
云仓集货管理 - 收货、库存、批次模型
"""
from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, Text, Date, DECIMAL
from app.models.base import BaseModel, db


class WarehouseReceipt(BaseModel, db.Model):
    """收货登记"""
    __tablename__ = 'warehouse_receipts'
    receipt_no = Column(String(50), unique=True, nullable=False, comment='收货单号')
    batch_no = Column(String(50), comment='批次号')
    sku = Column(String(100), comment='SKU')
    product_name = Column(String(200), nullable=False, comment='品名')
    quantity = Column(Integer, nullable=False, comment='数量')
    weight = Column(Float, comment='重量(kg)')
    volume = Column(Float, comment='体积(m³)')
    order_no = Column(String(50), comment='所属订单号')
    owner_name = Column(String(100), comment='货主信息')
    expiry_date = Column(Date, comment='保质期')
    status = Column(String(20), default='pending', comment='状态：pending-待确认，confirmed-已确认')
    confirmed_by = Column(Integer, ForeignKey('users.id'), comment='确认人')
    confirmed_at = Column(DateTime, comment='确认时间')


class WarehouseInventory(BaseModel, db.Model):
    """库存管理"""
    __tablename__ = 'warehouse_inventories'
    sku = Column(String(100), comment='SKU')
    product_name = Column(String(200), nullable=False, comment='品名')
    total_quantity = Column(Integer, default=0, comment='总库存数量')
    available_quantity = Column(Integer, default=0, comment='可用数量')
    locked_quantity = Column(Integer, default=0, comment='锁定数量')
    min_threshold = Column(Integer, default=0, comment='最低库存预警')
    max_threshold = Column(Integer, default=999999, comment='最高库存预警')
    warehouse_location = Column(String(100), comment='仓库位置')
    status = Column(String(20), default='normal', comment='状态：normal-正常，low-缺货预警，over-溢货预警')


class WarehouseBatch(BaseModel, db.Model):
    """批次管理"""
    __tablename__ = 'warehouse_batches'
    batch_no = Column(String(50), unique=True, nullable=False, comment='批次号')
    product_name = Column(String(200), comment='品名')
    sku = Column(String(100), comment='SKU')
    quantity = Column(Integer, comment='数量')
    weight = Column(Float, comment='重量(kg)')
    volume = Column(Float, comment='体积(m³)')
    production_date = Column(Date, comment='生产日期')
    expiry_date = Column(Date, comment='保质期')
    status = Column(String(20), default='stored', comment='状态：stored-在库，out-出库')
    remark = Column(Text, comment='备注')


class WarehouseRecord(BaseModel, db.Model):
    """库存变动记录"""
    __tablename__ = 'warehouse_records'
    record_no = Column(String(50), comment='记录编号')
    batch_no = Column(String(50), comment='批次号')
    sku = Column(String(100), comment='SKU')
    product_name = Column(String(200), comment='品名')
    change_type = Column(String(20), comment='变动类型：in-入库，out-出库，adjust-调整')
    quantity_before = Column(Integer, comment='变动前数量')
    quantity_change = Column(Integer, comment='变动数量')
    quantity_after = Column(Integer, comment='变动后数量')
    operator_id = Column(Integer, ForeignKey('users.id'), comment='操作人')
    operation_time = Column(DateTime, comment='操作时间')
    remark = Column(Text, comment='备注')
