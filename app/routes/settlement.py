"""
资金结算管理
"""
from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.models import SettlementOrder, SettlementFlow, OperationLog
from app import db

settlement_bp = Blueprint('settlement', __name__)


@settlement_bp.route('/orders', methods=['GET'])
@login_required
def list_orders():
    """结算单列表"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    query = SettlementOrder.query.filter_by(is_deleted=0)
    
    status = request.args.get('status')
    if status:
        query = query.filter_by(status=status)
    
    pagination = query.order_by(SettlementOrder.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        'code': 200,
        'data': {
            'items': [o.to_dict() for o in pagination.items],
            'total': pagination.total,
            'page': page,
            'pages': pagination.pages
        }
    })


@settlement_bp.route('/orders', methods=['POST'])
@login_required
def create_order():
    """创建结算单"""
    data = request.get_json()
    order = SettlementOrder(
        settlement_no=data['settlement_no'],
        recon_id=data.get('recon_id'),
        total_amount=data['total_amount'],
        settlement_cycle=data.get('settlement_cycle'),
        settlement_method=data.get('settlement_method', 'bank_transfer')
    )
    order.save()
    return jsonify({'code': 200, 'message': '结算单创建成功', 'data': order.to_dict()})


@settlement_bp.route('/orders/<int:order_id>/audit', methods=['POST'])
@login_required
def audit_order(order_id):
    """审核结算单"""
    order = SettlementOrder.query.get_or_404(order_id)
    data = request.get_json()
    order.status = data.get('status', 'pending_payment')
    order.audit_by = current_user.id
    order.audit_at = datetime.now()
    order.audit_opinion = data.get('opinion')
    db.session.commit()
    return jsonify({'code': 200, 'message': '审核完成'})


@settlement_bp.route('/orders/<int:order_id>/pay', methods=['POST'])
@login_required
def pay_order(order_id):
    """确认支付"""
    order = SettlementOrder.query.get_or_404(order_id)
    order.status = 'paid'
    db.session.commit()
    return jsonify({'code': 200, 'message': '支付完成'})


@settlement_bp.route('/flows', methods=['GET'])
@login_required
def list_flows():
    """资金流水列表"""
    settlement_id = request.args.get('settlement_id', type=int)
    query = SettlementFlow.query.filter_by(is_deleted=0)
    if settlement_id:
        query = query.filter_by(settlement_id=settlement_id)
    flows = query.order_by(SettlementFlow.flow_time.desc()).all()
    return jsonify({'code': 200, 'data': [f.to_dict() for f in flows]})
