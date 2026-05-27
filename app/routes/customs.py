"""
霍尔果斯口岸出口报关管理
"""
from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.models import CustomsDeclaration, CustomsMaterial, OperationLog
from app import db

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
