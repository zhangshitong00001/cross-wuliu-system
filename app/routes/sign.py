"""
签收入库管理
"""
from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.models import SignRecord, SignCertificate, OperationLog
from app import db
from app.utils.excel_import import (
    ExcelImporter, FieldValidator, build_import_response,
    allowed_file, get_import_template, safe_str, safe_int
)

sign_bp = Blueprint('sign', __name__)


@sign_bp.route('/records', methods=['GET'])
@login_required
def list_records():
    """签收记录列表"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    query = SignRecord.query.filter_by(is_deleted=0)
    
    point_id = request.args.get('point_id', type=int)
    if point_id:
        query = query.filter_by(point_id=point_id)
    
    package_no = request.args.get('package_no')
    if package_no:
        query = query.filter_by(package_no=package_no)

    keyword = request.args.get('keyword')
    if keyword:
        query = query.filter(
            (SignRecord.sign_no.ilike(f'%{keyword}%')) |
            (SignRecord.package_no.ilike(f'%{keyword}%')) |
            (SignRecord.signer.ilike(f'%{keyword}%'))
        )

    pagination = query.order_by(SignRecord.sign_time.desc()).paginate(
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


@sign_bp.route('/records', methods=['POST'])
@login_required
def create_sign():
    """创建签收记录"""
    data = request.get_json()
    record = SignRecord(
        sign_no=data['sign_no'],
        package_no=data.get('package_no'),
        point_id=data.get('point_id'),
        sign_type=data.get('sign_type', 'manual'),
        signer=data.get('signer'),
        package_status=data.get('package_status', 'normal'),
        damage_desc=data.get('damage_desc'),
        operator_id=current_user.id
    )
    record.save()
    return jsonify({'code': 200, 'message': '签收成功', 'data': record.to_dict()})


@sign_bp.route('/records/<int:record_id>/store', methods=['POST'])
@login_required
def store_record(record_id):
    """入库登记"""
    record = SignRecord.query.get_or_404(record_id)
    record.status = 'stored'
    db.session.commit()
    return jsonify({'code': 200, 'message': '入库成功'})


@sign_bp.route('/records/<int:record_id>', methods=['PUT'])
@login_required
def update_sign_record(record_id):
    """更新签收记录"""
    record = SignRecord.query.get_or_404(record_id)
    data = request.get_json()
    for field in ['sign_no', 'package_no', 'point_id', 'sign_type', 'signer', 'package_status', 'damage_desc', 'status']:
        if field in data:
            setattr(record, field, data[field])
    db.session.commit()
    return jsonify({'code': 200, 'message': '签收记录更新成功', 'data': record.to_dict()})


@sign_bp.route('/records/<int:record_id>', methods=['DELETE'])
@login_required
def delete_sign_record(record_id):
    """删除签收记录"""
    record = SignRecord.query.get_or_404(record_id)
    record.is_deleted = 1
    db.session.commit()
    return jsonify({'code': 200, 'message': '删除成功'})


@sign_bp.route('/certificates', methods=['POST'])
@login_required
def upload_certificate():
    """上传签收凭证"""
    data = request.get_json()
    cert = SignCertificate(
        sign_id=data['sign_id'],
        cert_type=data.get('cert_type'),
        file_path=data.get('file_path'),
        file_name=data.get('file_name')
    )
    cert.save()
    return jsonify({'code': 200, 'message': '凭证上传成功', 'data': cert.to_dict()})


# ===== Excel批量导入 =====

@sign_bp.route('/records/import/template', methods=['GET'])
@login_required
def download_sign_template():
    """下载签收记录导入模板"""
    fields = [
        {'name': 'sign_no', 'display_name': '签收编号', 'required': True, 'example': 'SN20260601001'},
        {'name': 'package_no', 'display_name': '包裹编号', 'required': True, 'example': 'PKG20260601001'},
        {'name': 'point_id', 'display_name': '收件点ID', 'required': True, 'example': '1'},
        {'name': 'sign_type', 'display_name': '签收方式', 'example': 'manual'},
        {'name': 'signer', 'display_name': '签收人', 'required': True, 'example': '李四'},
        {'name': 'package_status', 'display_name': '包裹状态', 'example': 'normal'},
        {'name': 'damage_desc', 'display_name': '破损描述', 'example': ''},
        {'name': 'remark', 'display_name': '备注', 'example': ''},
    ]
    output = get_import_template(fields, sheet_name='签收记录导入')
    from flask import send_file
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='签收-记录导入模板.xlsx'
    )


@sign_bp.route('/records/import', methods=['POST'])
@login_required
def import_sign_records():
    """批量导入签收记录"""
    if 'file' not in request.files:
        return jsonify({'code': 400, 'message': '请上传文件'})

    file = request.files['file']
    if file.filename == '' or not allowed_file(file.filename):
        return jsonify({'code': 400, 'message': '请上传有效的Excel文件（.xlsx或.xls）'})

    validators = [
        FieldValidator('sign_no', '签收编号', required=True,
                       unique_check=lambda v: SignRecord.query.filter_by(sign_no=v, is_deleted=0).first() is not None),
        FieldValidator('package_no', '包裹编号', required=True),
        FieldValidator('point_id', '收件点ID', required=True, field_type='int'),
        FieldValidator('sign_type', '签收方式'),
        FieldValidator('signer', '签收人', required=True),
        FieldValidator('package_status', '包裹状态'),
        FieldValidator('damage_desc', '破损描述'),
        FieldValidator('remark', '备注'),
    ]

    def process_func(row, row_index):
        record = SignRecord(
            sign_no=safe_str(row.get('sign_no')),
            package_no=safe_str(row.get('package_no')),
            point_id=safe_int(row.get('point_id')),
            sign_type=safe_str(row.get('sign_type')) or 'manual',
            signer=safe_str(row.get('signer')),
            package_status=safe_str(row.get('package_status')) or 'normal',
            damage_desc=safe_str(row.get('damage_desc')),
            remark=safe_str(row.get('remark')),
            status='signed',
            operator_id=current_user.id,
            sign_time=datetime.now()
        )
        record.save()
        return True, None

    importer = ExcelImporter(file, validators=validators)
    result = importer.run(process_func)

    OperationLog(
        user_id=current_user.id, username=current_user.username,
        action='import', module='sign_record',
        target_desc=f'批量导入签收记录: 成功{result["success"]}条, 失败{result["fail"]}条',
        ip_address=request.remote_addr
    ).save()

    return jsonify(build_import_response(result))
