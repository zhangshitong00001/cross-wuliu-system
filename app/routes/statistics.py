"""
数据统计与分析
"""
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify
from flask_login import login_required

from app.models import WarehouseReceipt, SortingTask, TransportTask, CustomsDeclaration, \
    ClearanceRecord, DistributionTask, SignRecord, ReconciliationRecord, SettlementOrder, InvoiceRecord
from sqlalchemy import func

statistics_bp = Blueprint('statistics', __name__)


@statistics_bp.route('/dashboard', methods=['GET'])
@login_required
def dashboard():
    """仪表盘数据"""
    today = datetime.now().date()
    start_of_month = today.replace(day=1)
    
    # 集货统计
    total_receipts = WarehouseReceipt.query.filter_by(is_deleted=0).count()
    month_receipts = WarehouseReceipt.query.filter(
        WarehouseReceipt.is_deleted == 0,
        func.date(WarehouseReceipt.created_at) >= start_of_month
    ).count()
    
    # 分装统计
    total_sorting = SortingTask.query.filter_by(is_deleted=0).count()
    completed_sorting = SortingTask.query.filter_by(is_deleted=0, status='completed').count()
    sorting_rate = round(completed_sorting / total_sorting * 100, 1) if total_sorting > 0 else 0
    
    # 运输统计
    total_transport = TransportTask.query.filter_by(is_deleted=0).count()
    in_transit = TransportTask.query.filter_by(is_deleted=0, status='in_transit').count()
    
    # 报关统计
    total_customs = CustomsDeclaration.query.filter_by(is_deleted=0).count()
    approved_customs = CustomsDeclaration.query.filter_by(is_deleted=0, status='approved').count()
    customs_rate = round(approved_customs / total_customs * 100, 1) if total_customs > 0 else 0
    
    # 清关统计
    total_clearance = ClearanceRecord.query.filter_by(is_deleted=0).count()
    cleared = ClearanceRecord.query.filter_by(is_deleted=0, status='cleared').count()
    
    # 配送统计
    total_distribution = DistributionTask.query.filter_by(is_deleted=0).count()
    completed_distribution = DistributionTask.query.filter_by(is_deleted=0, status='completed').count()
    distribution_rate = round(completed_distribution / total_distribution * 100, 1) if total_distribution > 0 else 0
    
    # 签收统计
    total_sign = SignRecord.query.filter_by(is_deleted=0).count()
    
    # 对账结算统计
    total_recon = ReconciliationRecord.query.filter_by(is_deleted=0).count()
    total_settlement = SettlementOrder.query.filter_by(is_deleted=0).count()
    
    # 发票统计
    total_invoice = InvoiceRecord.query.filter_by(is_deleted=0).count()
    
    return jsonify({
        'code': 200,
        'data': {
            'warehouse': {'total': total_receipts, 'month': month_receipts},
            'sorting': {'total': total_sorting, 'completed': completed_sorting, 'rate': sorting_rate},
            'transport': {'total': total_transport, 'in_transit': in_transit},
            'customs': {'total': total_customs, 'approved': approved_customs, 'rate': customs_rate},
            'clearance': {'total': total_clearance, 'cleared': cleared},
            'distribution': {'total': total_distribution, 'completed': completed_distribution, 'rate': distribution_rate},
            'sign': {'total': total_sign},
            'finance': {'reconciliation': total_recon, 'settlement': total_settlement, 'invoice': total_invoice}
        }
    })


@statistics_bp.route('/trends', methods=['GET'])
@login_required
def trends():
    """趋势数据（近7天/30天）"""
    days = request.args.get('days', 7, type=int)
    start_date = datetime.now() - timedelta(days=days)
    
    # 每日集货量
    daily_receipts = db.session.query(
        func.date(WarehouseReceipt.created_at).label('date'),
        func.count(WarehouseReceipt.id).label('count'),
        func.sum(WarehouseReceipt.quantity).label('quantity')
    ).filter(
        WarehouseReceipt.is_deleted == 0,
        WarehouseReceipt.created_at >= start_date
    ).group_by(func.date(WarehouseReceipt.created_at)).all()
    
    # 每日运输任务
    daily_transport = db.session.query(
        func.date(TransportTask.created_at).label('date'),
        func.count(TransportTask.id).label('count')
    ).filter(
        TransportTask.is_deleted == 0,
        TransportTask.created_at >= start_date
    ).group_by(func.date(TransportTask.created_at)).all()
    
    return jsonify({
        'code': 200,
        'data': {
            'daily_receipts': [{'date': str(r.date), 'count': r.count, 'quantity': int(r.quantity or 0)} for r in daily_receipts],
            'daily_transport': [{'date': str(r.date), 'count': r.count} for r in daily_transport]
        }
    })



