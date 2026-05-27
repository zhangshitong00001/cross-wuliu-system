"""
对账管理
"""
from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.models import ReconciliationRecord, ReconciliationDetail, OperationLog
from app import db

reconciliation_bp = Blueprint('reconciliation', __name__)


@reconciliation_bp.route('/records', methods=['GET'])
@login_required
def list_records():
    """对账记录列表"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    query = ReconciliationRecord.query.filter_by(is_deleted=0)
    
    status = request.args.get('status')
    if status:
        query = query.filter_by(status=status)
    
    recon_type = request.args.get('recon_type')
    if recon_type:
        query = query.filter_by(recon_type=recon_type)
    
    pagination = query.order_by(ReconciliationRecord.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        'code': 200,
        'data': {
            'items': [r.to_dict() for r in pagination.items],
            'total': pagination.total,
            'page': page,
            'pages': pagination.pages
        }
    })


@reconciliation_bp.route('/records', methods=['POST'])
@login_required
def create_reconciliation():
    """创建对账"""
    data = request.get_json()
    record = ReconciliationRecord(
        recon_no=data['recon_no'],
        batch_no=data.get('batch_no'),
        recon_type=data.get('recon_type', 'monthly'),
        recon_period_start=datetime.strptime(data['period_start'], '%Y-%m-%d') if data.get('period_start') else None,
        recon_period_end=datetime.strptime(data['period_end'], '%Y-%m-%d') if data.get('period_end') else None,
        total_amount=data.get('total_amount')
    )
    record.save()
    return jsonify({'code': 200, 'message': '对账创建成功', 'data': record.to_dict()})


@reconciliation_bp.route('/records/<int:recon_id>/confirm', methods=['POST'])
@login_required
def confirm_reconciliation(recon_id):
    """确认对账"""
    record = ReconciliationRecord.query.get_or_404(recon_id)
    record.status = 'completed'
    record.confirmed_by = current_user.id
    record.confirmed_at = datetime.now()
    db.session.commit()
    return jsonify({'code': 200, 'message': '对账已完成'})


@reconciliation_bp.route('/details', methods=['GET'])
@login_required
def list_details():
    """对账明细列表"""
    recon_id = request.args.get('recon_id', type=int)
    query = ReconciliationDetail.query.filter_by(is_deleted=0)
    if recon_id:
        query = query.filter_by(recon_id=recon_id)
    details = query.all()
    return jsonify({'code': 200, 'data': [d.to_dict() for d in details]})


@reconciliation_bp.route('/details/<int:detail_id>/resolve', methods=['PUT'])
@login_required
def resolve_detail(detail_id):
    """处理对账差异"""
    detail = ReconciliationDetail.query.get_or_404(detail_id)
    data = request.get_json()
    detail.solution = data.get('solution')
    detail.status = data.get('status', 'resolved')
    detail.handler_id = current_user.id
    db.session.commit()
    return jsonify({'code': 200, 'message': '差异已处理'})
