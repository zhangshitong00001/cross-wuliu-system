"""
霍尔果斯口岸出口报关管理
"""
from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.models import CustomsDeclaration, CustomsMaterial, OperationLog
from app import db
from app.utils.excel_import import (
    ExcelImporter, FieldValidator, build_import_response,
    allowed_file, get_import_template, safe_str, safe_int
)

customs_bp = Blueprint('customs', __name__)


@customs_bp.route('/declarations', methods=['GET'])
@login_required
def list_declarations():
    """报关单列表"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    query = CustomsDeclaration.query.filter_by(is_deleted=0)
    
    status = request.args.get('status')
    if status:
        query = query.filter_by(status=status)
    
    batch_no = request.args.get('batch_no')
    if batch_no:
        query = query.filter_by(batch_no=batch_no)
    
    pagination = query.order_by(CustomsDeclaration.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        'code': 200,
        'data': {
            'items': [d.to_dict() for d in pagination.items],
            'total': pagination.total,
            'page': page,
            'pages': pagination.pages
        }
    })


@customs_bp.route('/declarations', methods=['POST'])
@login_required
def create_declaration():
    """提交报关"""
    data = request.get_json()
    declaration = CustomsDeclaration(
        declaration_no=data['declaration_no'],
        batch_no=data.get('batch_no'),
        transport_task_id=data.get('transport_task_id'),
        submitted_by=current_user.id,
        submitted_at=datetime.now()
    )
    declaration.save()
    
    OperationLog(
        user_id=current_user.id, username=current_user.username,
        action='create', module='customs_declaration',
        target_id=declaration.id,
        target_desc=f'提交报关: {declaration.declaration_no}',
        ip_address=request.remote_addr
    ).save()
    
    return jsonify({'code': 200, 'message': '报关提交成功', 'data': declaration.to_dict()})


@customs_bp.route('/declarations/<int:decl_id>/review', methods=['POST'])
@login_required
def review_declaration(decl_id):
    """审核报关"""
    declaration = CustomsDeclaration.query.get_or_404(decl_id)
    data = request.get_json()
    
    declaration.status = data.get('status', 'approved')
    declaration.reviewed_at = datetime.now()
    declaration.reviewer_opinion = data.get('opinion')
    if data.get('status') == 'rejected':
        declaration.reject_reason = data.get('reject_reason')
    
    db.session.commit()
    return jsonify({'code': 200, 'message': '审核完成', 'data': declaration.to_dict()})


@customs_bp.route('/declarations/<int:decl_id>/confirm', methods=['POST'])
@login_required
def confirm_declaration(decl_id):
    """确认归档报关"""
    declaration = CustomsDeclaration.query.get_or_404(decl_id)
    declaration.status = 'confirmed'
    declaration.confirmed_by = current_user.id
    declaration.confirmed_at = datetime.now()
    db.session.commit()
    return jsonify({'code': 200, 'message': '报关已归档'})


@customs_bp.route('/declarations/<int:decl_id>', methods=['PUT'])
@login_required
def update_declaration(decl_id):
    """更新报关单"""
    declaration = CustomsDeclaration.query.get_or_404(decl_id)
    data = request.get_json()
    for field in ['declaration_no', 'batch_no', 'transport_task_id', 'status']:
        if field in data:
            setattr(declaration, field, data[field])
    db.session.commit()
    return jsonify({'code': 200, 'message': '报关单更新成功', 'data': declaration.to_dict()})


@customs_bp.route('/declarations/<int:decl_id>', methods=['DELETE'])
@login_required
def delete_declaration(decl_id):
    """删除报关单"""
    declaration = CustomsDeclaration.query.get_or_404(decl_id)
    declaration.is_deleted = 1
    db.session.commit()
    return jsonify({'code': 200, 'message': '删除成功'})


@customs_bp.route('/materials', methods=['POST'])
@login_required
def upload_material():
    """上传补充材料"""
    data = request.get_json()
    material = CustomsMaterial(
        declaration_id=data['declaration_id'],
        material_type=data.get('material_type'),
        file_path=data.get('file_path'),
        file_name=data.get('file_name'),
        uploaded_by=current_user.id
    )
    material.save()
    return jsonify({'code': 200, 'message': '材料上传成功', 'data': material.to_dict()})


@customs_bp.route('/materials', methods=['GET'])
@login_required
def list_materials():
    """补充材料列表"""
    decl_id = request.args.get('declaration_id', type=int)
    query = CustomsMaterial.query.filter_by(is_deleted=0)
    if decl_id:
        query = query.filter_by(declaration_id=decl_id)
    materials = query.order_by(CustomsMaterial.uploaded_at.desc()).all()
    return jsonify({'code': 200, 'data': [m.to_dict() for m in materials]})


# ===== Excel批量导入 =====

@customs_bp.route('/declarations/import/template', methods=['GET'])
@login_required
def download_declaration_template():
    """下载报关单导入模板"""
    fields = [
        {'name': 'declaration_no', 'display_name': '报关单号', 'required': True, 'example': 'CD20260601001'},
        {'name': 'batch_no', 'display_name': '批次号', 'example': 'BATCH20260601'},
        {'name': 'transport_task_id', 'display_name': '运输任务ID', 'example': '1'},
        {'name': 'remark', 'display_name': '备注', 'example': ''},
    ]
    output = get_import_template(fields, sheet_name='报关单导入')
    from flask import send_file
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='报关单导入模板.xlsx'
    )


@customs_bp.route('/declarations/import', methods=['POST'])
@login_required
def import_declarations():
    """批量导入报关单"""
    if 'file' not in request.files:
        return jsonify({'code': 400, 'message': '请上传文件'})

    file = request.files['file']
    if file.filename == '' or not allowed_file(file.filename):
        return jsonify({'code': 400, 'message': '请上传有效的Excel文件（.xlsx或.xls）'})

    validators = [
        FieldValidator('declaration_no', '报关单号', required=True,
                       unique_check=lambda v: CustomsDeclaration.query.filter_by(declaration_no=v, is_deleted=0).first() is not None),
        FieldValidator('batch_no', '批次号'),
        FieldValidator('transport_task_id', '运输任务ID', field_type='int'),
        FieldValidator('remark', '备注'),
    ]

    def process_func(row, row_index):
        declaration = CustomsDeclaration(
            declaration_no=safe_str(row.get('declaration_no')),
            batch_no=safe_str(row.get('batch_no')),
            transport_task_id=safe_int(row.get('transport_task_id')),
            remark=safe_str(row.get('remark')),
            status='pending',
            submitted_by=current_user.id,
            submitted_at=datetime.now()
        )
        declaration.save()
        return True, None

    importer = ExcelImporter(file, validators=validators)
    result = importer.run(process_func)

    OperationLog(
        user_id=current_user.id, username=current_user.username,
        action='import', module='customs_declaration',
        target_desc=f'批量导入报关单: 成功{result["success"]}条, 失败{result["fail"]}条',
        ip_address=request.remote_addr
    ).save()

    return jsonify(build_import_response(result))
