"""
对账管理
"""
from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.models import ReconciliationRecord, ReconciliationDetail, OperationLog
from app import db
from app.utils.excel_import import (
    ExcelImporter, FieldValidator, build_import_response,
    allowed_file, get_import_template, safe_str, safe_float, safe_date
)

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


@reconciliation_bp.route('/records/<int:recon_id>', methods=['PUT'])
@login_required
def update_reconciliation(recon_id):
    """更新对账记录"""
    record = ReconciliationRecord.query.get_or_404(recon_id)
    data = request.get_json()
    for field in ['recon_no', 'batch_no', 'recon_type', 'total_amount', 'status']:
        if field in data:
            setattr(record, field, data[field])
    if data.get('period_start'):
        record.recon_period_start = datetime.strptime(data['period_start'], '%Y-%m-%d')
    if data.get('period_end'):
        record.recon_period_end = datetime.strptime(data['period_end'], '%Y-%m-%d')
    db.session.commit()
    return jsonify({'code': 200, 'message': '对账记录更新成功', 'data': record.to_dict()})


@reconciliation_bp.route('/records/<int:recon_id>', methods=['DELETE'])
@login_required
def delete_reconciliation(recon_id):
    """删除对账记录"""
    record = ReconciliationRecord.query.get_or_404(recon_id)
    record.is_deleted = 1
    db.session.commit()
    return jsonify({'code': 200, 'message': '删除成功'})


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


# ===== Excel批量导入 =====

@reconciliation_bp.route('/records/import/template', methods=['GET'])
@login_required
def download_recon_template():
    """下载对账记录导入模板"""
    fields = [
        {'name': 'recon_no', 'display_name': '对账编号', 'required': True, 'example': 'RECON20260601001'},
        {'name': 'batch_no', 'display_name': '批次号', 'example': 'BATCH20260601'},
        {'name': 'recon_type', 'display_name': '对账频率', 'example': 'monthly'},
        {'name': 'period_start', 'display_name': '对账开始日期', 'example': '2026-06-01'},
        {'name': 'period_end', 'display_name': '对账结束日期', 'example': '2026-06-30'},
        {'name': 'total_amount', 'display_name': '总金额', 'example': '50000.00'},
        {'name': 'remark', 'display_name': '备注', 'example': ''},
    ]
    output = get_import_template(fields, sheet_name='对账记录导入')
    from flask import send_file
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='对账-记录导入模板.xlsx'
    )


@reconciliation_bp.route('/records/import', methods=['POST'])
@login_required
def import_recon_records():
    """批量导入对账记录"""
    if 'file' not in request.files:
        return jsonify({'code': 400, 'message': '请上传文件'})

    file = request.files['file']
    if file.filename == '' or not allowed_file(file.filename):
        return jsonify({'code': 400, 'message': '请上传有效的Excel文件（.xlsx或.xls）'})

    validators = [
        FieldValidator('recon_no', '对账编号', required=True,
                       unique_check=lambda v: ReconciliationRecord.query.filter_by(recon_no=v, is_deleted=0).first() is not None),
        FieldValidator('batch_no', '批次号'),
        FieldValidator('recon_type', '对账频率'),
        FieldValidator('period_start', '对账开始日期', field_type='date'),
        FieldValidator('period_end', '对账结束日期', field_type='date'),
        FieldValidator('total_amount', '总金额', field_type='float', min_value=0),
        FieldValidator('remark', '备注'),
    ]

    def process_func(row, row_index):
        record = ReconciliationRecord(
            recon_no=safe_str(row.get('recon_no')),
            batch_no=safe_str(row.get('batch_no')),
            recon_type=safe_str(row.get('recon_type')) or 'monthly',
            recon_period_start=safe_date(row.get('period_start')),
            recon_period_end=safe_date(row.get('period_end')),
            total_amount=safe_float(row.get('total_amount')),
            remark=safe_str(row.get('remark')),
            status='pending'
        )
        record.save()
        return True, None

    importer = ExcelImporter(file, validators=validators)
    result = importer.run(process_func)

    OperationLog(
        user_id=current_user.id, username=current_user.username,
        action='import', module='reconciliation',
        target_desc=f'批量导入对账记录: 成功{result["success"]}条, 失败{result["fail"]}条',
        ip_address=request.remote_addr
    ).save()

    return jsonify(build_import_response(result))
