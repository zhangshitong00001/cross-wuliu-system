"""
哈国口岸进口清关管理
"""
from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.models import ClearanceRecord, ClearanceFee, OperationLog
from app import db

clearance_bp = Blueprint('clearance', __name__)


@clearance_bp.route('/records', methods=['GET'])
@login_required
def list_records():
    """清关记录列表"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    query = ClearanceRecord.query.filter_by(is_deleted=0)
    
    status = request.args.get('status')
    if status:
        query = query.filter_by(status=status)
    
    batch_no = request.args.get('batch_no')
    if batch_no:
        query = query.filter_by(batch_no=batch_no)
    
    pagination = query.order_by(ClearanceRecord.created_at.desc()).paginate(
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


@clearance_bp.route('/records', methods=['POST'])
@login_required
def create_clearance():
    """提交清关"""
    data = request.get_json()
    record = ClearanceRecord(
        clearance_no=data['clearance_no'],
        batch_no=data.get('batch_no'),
        declaration_no=data.get('declaration_no'),
        handler_id=current_user.id,
        submitted_at=datetime.now()
    )
    record.save()
    return jsonify({'code': 200, 'message': '清关提交成功', 'data': record.to_dict()})


@clearance_bp.route('/records/<int:record_id>/clear', methods=['POST'])
@login_required
def clear_clearance(record_id):
    """确认清关完成"""
    record = ClearanceRecord.query.get_or_404(record_id)
    record.status = 'cleared'
    record.cleared_at = datetime.now()
    db.session.commit()
    return jsonify({'code': 200, 'message': '清关已完成'})


@clearance_bp.route('/fees', methods=['GET'])
@login_required
def list_fees():
    """清关费用列表"""
    clearance_id = request.args.get('clearance_id', type=int)
    query = ClearanceFee.query.filter_by(is_deleted=0)
    if clearance_id:
        query = query.filter_by(clearance_id=clearance_id)
    fees = query.all()
    return jsonify({'code': 200, 'data': [f.to_dict() for f in fees]})


@clearance_bp.route('/fees', methods=['POST'])
@login_required
def add_fee():
    """添加清关费用"""
    data = request.get_json()
    fee = ClearanceFee(
        clearance_id=data['clearance_id'],
        batch_no=data.get('batch_no'),
        fee_type=data['fee_type'],
        amount=data['amount'],
        currency=data.get('currency', 'KZT'),
        remark=data.get('remark')
    )
    fee.save()
    return jsonify({'code': 200, 'message': '费用添加成功', 'data': fee.to_dict()})
