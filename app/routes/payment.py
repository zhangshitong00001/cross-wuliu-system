"""
支付开票系统
"""
from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.models import PaymentRecord, InvoiceRecord, OperationLog
from app import db
from app.utils.excel_import import (
    ExcelImporter, FieldValidator, build_import_response,
    allowed_file, get_import_template, safe_str, safe_float, safe_int
)

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

    keyword = request.args.get('keyword')
    if keyword:
        query = query.filter(
            (PaymentRecord.payment_no.ilike(f'%{keyword}%'))
        )

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


@payment_bp.route('/records/<int:payment_id>', methods=['PUT'])
@login_required
def update_payment(payment_id):
    """更新支付记录"""
    payment = PaymentRecord.query.get_or_404(payment_id)
    data = request.get_json()
    for field in ['payment_no', 'settlement_id', 'amount', 'payment_method', 'status']:
        if field in data:
            setattr(payment, field, data[field])
    db.session.commit()
    return jsonify({'code': 200, 'message': '支付记录更新成功', 'data': payment.to_dict()})


@payment_bp.route('/records/<int:payment_id>', methods=['DELETE'])
@login_required
def delete_payment(payment_id):
    """删除支付记录"""
    payment = PaymentRecord.query.get_or_404(payment_id)
    payment.is_deleted = 1
    db.session.commit()
    return jsonify({'code': 200, 'message': '删除成功'})


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

    keyword = request.args.get('keyword')
    if keyword:
        query = query.filter(
            (InvoiceRecord.invoice_no.ilike(f'%{keyword}%'))
        )

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


# ===== Excel批量导入 =====

@payment_bp.route('/records/import/template', methods=['GET'])
@login_required
def download_payment_template():
    """下载支付记录导入模板"""
    fields = [
        {'name': 'payment_no', 'display_name': '支付编号', 'required': True, 'example': 'PAY20260601001'},
        {'name': 'settlement_id', 'display_name': '结算单ID', 'example': '1'},
        {'name': 'amount', 'display_name': '金额', 'required': True, 'example': '50000.00'},
        {'name': 'payment_method', 'display_name': '支付方式', 'example': 'bank'},
        {'name': 'remark', 'display_name': '备注', 'example': ''},
    ]
    output = get_import_template(fields, sheet_name='支付记录导入')
    from flask import send_file
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='支付-记录导入模板.xlsx'
    )


@payment_bp.route('/records/import', methods=['POST'])
@login_required
def import_payments():
    """批量导入支付记录"""
    if 'file' not in request.files:
        return jsonify({'code': 400, 'message': '请上传文件'})

    file = request.files['file']
    if file.filename == '' or not allowed_file(file.filename):
        return jsonify({'code': 400, 'message': '请上传有效的Excel文件（.xlsx或.xls）'})

    validators = [
        FieldValidator('payment_no', '支付编号', required=True,
                       unique_check=lambda v: PaymentRecord.query.filter_by(payment_no=v, is_deleted=0).first() is not None),
        FieldValidator('settlement_id', '结算单ID', field_type='int'),
        FieldValidator('amount', '金额', required=True, field_type='float', min_value=0),
        FieldValidator('payment_method', '支付方式'),
        FieldValidator('remark', '备注'),
    ]

    def process_func(row, row_index):
        payment = PaymentRecord(
            payment_no=safe_str(row.get('payment_no')),
            settlement_id=safe_int(row.get('settlement_id')),
            amount=safe_float(row.get('amount'), 0),
            payment_method=safe_str(row.get('payment_method')) or 'bank',
            remark=safe_str(row.get('remark')),
            status='pending'
        )
        payment.save()
        return True, None

    importer = ExcelImporter(file, validators=validators)
    result = importer.run(process_func)

    OperationLog(
        user_id=current_user.id, username=current_user.username,
        action='import', module='payment',
        target_desc=f'批量导入支付记录: 成功{result["success"]}条, 失败{result["fail"]}条',
        ip_address=request.remote_addr
    ).save()

    return jsonify(build_import_response(result))


@payment_bp.route('/invoices/import/template', methods=['GET'])
@login_required
def download_invoice_template():
    """下载发票导入模板"""
    fields = [
        {'name': 'invoice_no', 'display_name': '发票编号', 'required': True, 'example': 'INV20260601001'},
        {'name': 'settlement_id', 'display_name': '结算单ID', 'example': '1'},
        {'name': 'invoice_type', 'display_name': '发票类型', 'example': 'special'},
        {'name': 'amount', 'display_name': '金额', 'required': True, 'example': '50000.00'},
        {'name': 'buyer_info', 'display_name': '购买方信息', 'example': 'XX公司'},
        {'name': 'seller_info', 'display_name': '销售方信息', 'example': 'YY公司'},
        {'name': 'remark', 'display_name': '备注', 'example': ''},
    ]
    output = get_import_template(fields, sheet_name='发票导入')
    from flask import send_file
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='支付-发票导入模板.xlsx'
    )


@payment_bp.route('/invoices/import', methods=['POST'])
@login_required
def import_invoices():
    """批量导入发票"""
    if 'file' not in request.files:
        return jsonify({'code': 400, 'message': '请上传文件'})

    file = request.files['file']
    if file.filename == '' or not allowed_file(file.filename):
        return jsonify({'code': 400, 'message': '请上传有效的Excel文件（.xlsx或.xls）'})

    validators = [
        FieldValidator('invoice_no', '发票编号', required=True,
                       unique_check=lambda v: InvoiceRecord.query.filter_by(invoice_no=v, is_deleted=0).first() is not None),
        FieldValidator('settlement_id', '结算单ID', field_type='int'),
        FieldValidator('invoice_type', '发票类型'),
        FieldValidator('amount', '金额', required=True, field_type='float', min_value=0),
        FieldValidator('buyer_info', '购买方信息'),
        FieldValidator('seller_info', '销售方信息'),
        FieldValidator('remark', '备注'),
    ]

    def process_func(row, row_index):
        invoice = InvoiceRecord(
            invoice_no=safe_str(row.get('invoice_no')),
            settlement_id=safe_int(row.get('settlement_id')),
            invoice_type=safe_str(row.get('invoice_type')) or 'special',
            amount=safe_float(row.get('amount'), 0),
            buyer_info=safe_str(row.get('buyer_info')),
            seller_info=safe_str(row.get('seller_info')),
            remark=safe_str(row.get('remark')),
            invoice_status='pending'
        )
        invoice.save()
        return True, None

    importer = ExcelImporter(file, validators=validators)
    result = importer.run(process_func)

    OperationLog(
        user_id=current_user.id, username=current_user.username,
        action='import', module='invoice',
        target_desc=f'批量导入发票: 成功{result["success"]}条, 失败{result["fail"]}条',
        ip_address=request.remote_addr
    ).save()

    return jsonify(build_import_response(result))
