"""
签收入库管理
"""
from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.models import SignRecord, SignCertificate, OperationLog
from app import db

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
