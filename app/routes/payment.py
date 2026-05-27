"""
支付开票系统
"""
from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.models import PaymentRecord, InvoiceRecord, OperationLog
from app import db

payment_bp = Blueprint('payment', __name__)


@payment_bp.route('/records', methods=['GET'])
@login_required
def list_payments():
    """支付记录列表"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    query = PaymentRecord.query.filter_by(is_deleted=0)
    
    status = request.args.get('status')
    if status:
        query = query.filter_by(status=status)
    
    pagination = query.order_by(PaymentRecord.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        'code': 200,
        'data': {
            'items': [p.to_dict() for p in pagination.items],
            'total': pagination.total,
            'page': page,
            'pages': pagination.pages
        }
    })


@payment_bp.route('/records', methods=['POST'])
@login_required
def create_payment():
    """发起支付"""
    data = request.get_json()
    payment = PaymentRecord(
        payment_no=data['payment_no'],
        settlement_id=data.get('settlement_id'),
        amount=data['amount'],
        payment_method=data.get('payment_method', 'bank'),
        remark=data.get('remark')
    )
    payment.save()
    return jsonify({'code': 200, 'message': '支付发起成功', 'data': payment.to_dict()})


@payment_bp.route('/records/<int:payment_id>/status', methods=['PUT'])
@login_required
def update_payment_status(payment_id):
    """更新支付状态"""
    payment = PaymentRecord.query.get_or_404(payment_id)
    data = request.get_json()
    payment.status = data['status']
    if data['status'] == 'success':
        payment.paid_at = datetime.now()
    db.session.commit()
    return jsonify({'code': 200, 'message': '状态已更新'})


# ===== 发票管理 =====

@payment_bp.route('/invoices', methods=['GET'])
@login_required
def list_invoices():
    """发票列表"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    query = InvoiceRecord.query.filter_by(is_deleted=0)
    
    invoice_status = request.args.get('invoice_status')
    if invoice_status:
        query = query.filter_by(invoice_status=invoice_status)
    
    pagination = query.order_by(InvoiceRecord.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        'code': 200,
        'data': {
            'items': [i.to_dict() for i in pagination.items],
            'total': pagination.total,
            'page': page,
            'pages': pagination.pages
        }
    })


@payment_bp.route('/invoices', methods=['POST'])
@login_required
def create_invoice():
    """开具发票"""
    data = request.get_json()
    invoice = InvoiceRecord(
        invoice_no=data['invoice_no'],
        settlement_id=data.get('settlement_id'),
        invoice_type=data.get('invoice_type', 'special'),
        amount=data['amount'],
        buyer_info=data.get('buyer_info'),
        seller_info=data.get('seller_info')
    )
    invoice.save()
    return jsonify({'code': 200, 'message': '发票开具成功', 'data': invoice.to_dict()})


@payment_bp.route('/invoices/<int:invoice_id>/cancel', methods=['POST'])
@login_required
def cancel_invoice(invoice_id):
    """作废发票"""
    invoice = InvoiceRecord.query.get_or_404(invoice_id)
    invoice.invoice_status = 'cancelled'
    db.session.commit()
    return jsonify({'code': 200, 'message': '发票已作废'})


@payment_bp.route('/invoices/<int:invoice_id>/red-flush', methods=['POST'])
@login_required
def red_flush_invoice(invoice_id):
    """红冲发票"""
    invoice = InvoiceRecord.query.get_or_404(invoice_id)
    invoice.invoice_status = 'red_flush'
    db.session.commit()
    return jsonify({'code': 200, 'message': '发票已红冲'})
