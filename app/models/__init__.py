"""
数据模型定义
"""
from app.models.base import BaseModel, db
from app.models.user import User, Role, Permission
from app.models.warehouse import WarehouseReceipt, WarehouseInventory, WarehouseBatch, WarehouseRecord
from app.models.sorting import CollectionPoint, SortingTask, SortingRecord, SortingPersonnel
from app.models.document import Document, DocumentVersion
from app.models.vehicle import Vehicle, Driver
from app.models.transport import TransportTask, TransportNode, TransportException
from app.models.customs import CustomsDeclaration, CustomsMaterial
from app.models.clearance import ClearanceRecord, ClearanceFee
from app.models.port_transport import PortTransportTask, PortTransportArrival
from app.models.distribution import DistributionTask, DistributionRecord, DistributionPersonnel
from app.models.sign import SignRecord, SignCertificate
from app.models.reconciliation import ReconciliationRecord, ReconciliationDetail
from app.models.settlement import SettlementOrder, SettlementFlow
from app.models.payment import PaymentRecord, InvoiceRecord
from app.models.tracking import TrackingRecord
from app.models.alert import AlertRecord
from app.models.charging import ChargingRule
from app.models.log import OperationLog

__all__ = [
    'BaseModel', 'db',
    'User', 'Role', 'Permission',
    'WarehouseReceipt', 'WarehouseInventory', 'WarehouseBatch', 'WarehouseRecord',
    'CollectionPoint', 'SortingTask', 'SortingRecord', 'SortingPersonnel',
    'Document', 'DocumentVersion',
    'Vehicle', 'Driver',
    'TransportTask', 'TransportNode', 'TransportException',
    'CustomsDeclaration', 'CustomsMaterial',
    'ClearanceRecord', 'ClearanceFee',
    'PortTransportTask', 'PortTransportArrival',
    'DistributionTask', 'DistributionRecord', 'DistributionPersonnel',
    'SignRecord', 'SignCertificate',
    'ReconciliationRecord', 'ReconciliationDetail',
    'SettlementOrder', 'SettlementFlow',
    'PaymentRecord', 'InvoiceRecord',
    'TrackingRecord',
    'AlertRecord',
    'ChargingRule',
    'OperationLog',
]
