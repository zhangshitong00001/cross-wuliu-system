"""
资金结算管理
"""
from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.models import SettlementOrder, SettlementFlow, OperationLog
from app import db
from app.utils.excel_import import (
    ExcelImporter, FieldValidator, build_import_response,
    allowed_file, get_import_template, safe_str, safe_float, safe_int
)

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
    
    keyword = request.args.get('keyword')
    if keyword:
        query = query.filter(
            (SettlementOrder.settlementorder_no.ilike(f'%{keyword}%'))
        )

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


@settlement_bp.route('/orders/<int:order_id>', methods=['PUT'])
@login_required
def update_settlement_order(order_id):
    """更新结算单"""
    order = SettlementOrder.query.get_or_404(order_id)
    data = request.get_json()
    for field in ['settlement_no', 'recon_id', 'total_amount', 'settlement_cycle', 'settlement_method', 'status']:
        if field in data:
            setattr(order, field, data[field])
    db.session.commit()
    return jsonify({'code': 200, 'message': '结算单更新成功', 'data': order.to_dict()})


@settlement_bp.route('/orders/<int:order_id>', methods=['DELETE'])
@login_required
def delete_settlement_order(order_id):
    """删除结算单"""
    order = SettlementOrder.query.get_or_404(order_id)
    order.is_deleted = 1
    db.session.commit()
    return jsonify({'code': 200, 'message': '删除成功'})


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


# ===== Excel批量导入 =====

@settlement_bp.route('/orders/import/template', methods=['GET'])
@login_required
def download_settlement_template():
    """下载结算单导入模板"""
    fields = [
        {'name': 'settlement_no', 'display_name': '结算编号', 'required': True, 'example': 'SET20260601001'},
        {'name': 'recon_id', 'display_name': '对账记录ID', 'example': '1'},
        {'name': 'total_amount', 'display_name': '总金额', 'required': True, 'example': '50000.00'},
        {'name': 'settlement_cycle', 'display_name': '结算周期', 'example': '2026-06'},
        {'name': 'settlement_method', 'display_name': '结算方式', 'example': 'bank_transfer'},
        {'name': 'remark', 'display_name': '备注', 'example': ''},
    ]
    output = get_import_template(fields, sheet_name='结算单导入')
    from flask import send_file
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='结算-结算单导入模板.xlsx'
    )


@settlement_bp.route('/orders/import', methods=['POST'])
@login_required
def import_settlement_orders():
    """批量导入结算单"""
    if 'file' not in request.files:
        return jsonify({'code': 400, 'message': '请上传文件'})

    file = request.files['file']
    if file.filename == '' or not allowed_file(file.filename):
        return jsonify({'code': 400, 'message': '请上传有效的Excel文件（.xlsx或.xls）'})

    validators = [
        FieldValidator('settlement_no', '结算编号', required=True,
                       unique_check=lambda v: SettlementOrder.query.filter_by(settlement_no=v, is_deleted=0).first() is not None),
        FieldValidator('recon_id', '对账记录ID', field_type='int'),
        FieldValidator('total_amount', '总金额', required=True, field_type='float', min_value=0),
        FieldValidator('settlement_cycle', '结算周期'),
        FieldValidator('settlement_method', '结算方式'),
        FieldValidator('remark', '备注'),
    ]

    def process_func(row, row_index):
        order = SettlementOrder(
            settlement_no=safe_str(row.get('settlement_no')),
            recon_id=safe_int(row.get('recon_id')),
            total_amount=safe_float(row.get('total_amount'), 0),
            settlement_cycle=safe_str(row.get('settlement_cycle')),
            settlement_method=safe_str(row.get('settlement_method')) or 'bank_transfer',
            remark=safe_str(row.get('remark')),
            status='pending_audit'
        )
        order.save()
        return True, None

    importer = ExcelImporter(file, validators=validators)
    result = importer.run(process_func)

    OperationLog(
        user_id=current_user.id, username=current_user.username,
        action='import', module='settlement',
        target_desc=f'批量导入结算单: 成功{result["success"]}条, 失败{result["fail"]}条',
        ip_address=request.remote_addr
    ).save()

    return jsonify(build_import_response(result))
