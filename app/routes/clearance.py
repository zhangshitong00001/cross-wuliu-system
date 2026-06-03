"""
哈国口岸进口清关管理
"""
from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.models import ClearanceRecord, ClearanceFee, OperationLog
from app import db
from app.utils.excel_import import (
    ExcelImporter, FieldValidator, build_import_response,
    allowed_file, get_import_template, safe_str
)

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


@clearance_bp.route('/records/<int:record_id>', methods=['PUT'])
@login_required
def update_clearance(record_id):
    """更新清关记录"""
    record = ClearanceRecord.query.get_or_404(record_id)
    data = request.get_json()
    for field in ['clearance_no', 'batch_no', 'declaration_no', 'status']:
        if field in data:
            setattr(record, field, data[field])
    db.session.commit()
    return jsonify({'code': 200, 'message': '清关记录更新成功', 'data': record.to_dict()})


@clearance_bp.route('/records/<int:record_id>', methods=['DELETE'])
@login_required
def delete_clearance(record_id):
    """删除清关记录"""
    record = ClearanceRecord.query.get_or_404(record_id)
    record.is_deleted = 1
    db.session.commit()
    return jsonify({'code': 200, 'message': '删除成功'})


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


# ===== Excel批量导入 =====

@clearance_bp.route('/records/import/template', methods=['GET'])
@login_required
def download_clearance_template():
    """下载清关记录导入模板"""
    fields = [
        {'name': 'clearance_no', 'display_name': '清关编号', 'required': True, 'example': 'CL20260601001'},
        {'name': 'batch_no', 'display_name': '批次号', 'example': 'BATCH20260601'},
        {'name': 'declaration_no', 'display_name': '报关单号', 'example': 'CD20260601001'},
        {'name': 'remark', 'display_name': '备注', 'example': ''},
    ]
    output = get_import_template(fields, sheet_name='清关记录导入')
    from flask import send_file
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='清关记录导入模板.xlsx'
    )


@clearance_bp.route('/records/import', methods=['POST'])
@login_required
def import_clearance_records():
    """批量导入清关记录"""
    if 'file' not in request.files:
        return jsonify({'code': 400, 'message': '请上传文件'})

    file = request.files['file']
    if file.filename == '' or not allowed_file(file.filename):
        return jsonify({'code': 400, 'message': '请上传有效的Excel文件（.xlsx或.xls）'})

    validators = [
        FieldValidator('clearance_no', '清关编号', required=True,
                       unique_check=lambda v: ClearanceRecord.query.filter_by(clearance_no=v, is_deleted=0).first() is not None),
        FieldValidator('batch_no', '批次号'),
        FieldValidator('declaration_no', '报关单号'),
        FieldValidator('remark', '备注'),
    ]

    def process_func(row, row_index):
        record = ClearanceRecord(
            clearance_no=safe_str(row.get('clearance_no')),
            batch_no=safe_str(row.get('batch_no')),
            declaration_no=safe_str(row.get('declaration_no')),
            remark=safe_str(row.get('remark')),
            status='pending',
            handler_id=current_user.id,
            submitted_at=datetime.now()
        )
        record.save()
        return True, None

    importer = ExcelImporter(file, validators=validators)
    result = importer.run(process_func)

    OperationLog(
        user_id=current_user.id, username=current_user.username,
        action='import', module='clearance_record',
        target_desc=f'批量导入清关记录: 成功{result["success"]}条, 失败{result["fail"]}条',
        ip_address=request.remote_addr
    ).save()

    return jsonify(build_import_response(result))
