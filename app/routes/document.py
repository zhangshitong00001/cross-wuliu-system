"""
文件生成管理
"""
from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.models import Document, DocumentVersion, OperationLog
from app import db
import json

document_bp = Blueprint('document', __name__)


def generate_doc_no(doc_type):
    prefix = {'loading': 'LD', 'customs': 'CD', 'invoice': 'INV', 'packing_list': 'PL', 'coo': 'COO'}
    p = prefix.get(doc_type, 'DOC')
    seq = Document.query.count() + 1
    return f'{p}{datetime.now().strftime("%Y%m%d")}{seq:04d}'


@document_bp.route('/list', methods=['GET'])
@login_required
def list_documents():
    """文件列表"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    query = Document.query.filter_by(is_deleted=0)
    
    doc_type = request.args.get('doc_type')
    if doc_type:
        query = query.filter_by(doc_type=doc_type)
    
    batch_no = request.args.get('batch_no')
    if batch_no:
        query = query.filter_by(batch_no=batch_no)
    
    pagination = query.order_by(Document.created_at.desc()).paginate(
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


@document_bp.route('/create', methods=['POST'])
@login_required
def create_document():
    """创建文件"""
    data = request.get_json()
    doc = Document(
        doc_no=generate_doc_no(data['doc_type']),
        doc_type=data['doc_type'],
        title=data.get('title'),
        batch_no=data.get('batch_no'),
        content_json=json.dumps(data.get('content', {}), ensure_ascii=False),
        created_by=current_user.id
    )
    doc.save()
    
    # 创建初始版本
    DocumentVersion(
        doc_id=doc.id,
        version_no=1,
        content_json=doc.content_json,
        operator_id=current_user.id,
        change_summary='初始版本'
    ).save()
    
    return jsonify({'code': 200, 'message': '文件创建成功', 'data': doc.to_dict()})


@document_bp.route('/<int:doc_id>', methods=['GET'])
@login_required
def get_document(doc_id):
    """获取文件详情"""
    doc = Document.query.get_or_404(doc_id)
    versions = DocumentVersion.query.filter_by(doc_id=doc_id, is_deleted=0).order_by(
        DocumentVersion.version_no.desc()).all()
    result = doc.to_dict()
    result['versions'] = [v.to_dict() for v in versions]
    return jsonify({'code': 200, 'data': result})


@document_bp.route('/<int:doc_id>/update', methods=['PUT'])
@login_required
def update_document(doc_id):
    """更新文件（创建新版本）"""
    doc = Document.query.get_or_404(doc_id)
    data = request.get_json()
    
    doc.version += 1
    doc.content_json = json.dumps(data.get('content', {}), ensure_ascii=False)
    db.session.commit()
    
    DocumentVersion(
        doc_id=doc.id,
        version_no=doc.version,
        content_json=doc.content_json,
        operator_id=current_user.id,
        change_summary=data.get('change_summary', '更新版本')
    ).save()
    
    return jsonify({'code': 200, 'message': '文件更新成功', 'data': doc.to_dict()})


@document_bp.route('/<int:doc_id>/versions', methods=['GET'])
@login_required
def list_versions(doc_id):
    """文件版本列表"""
    versions = DocumentVersion.query.filter_by(doc_id=doc_id, is_deleted=0).order_by(
        DocumentVersion.version_no.desc()).all()
    return jsonify({'code': 200, 'data': [v.to_dict() for v in versions]})


@document_bp.route('/<int:doc_id>/switch-version/<int:version_id>', methods=['POST'])
@login_required
def switch_version(doc_id, version_id):
    """切换文件版本"""
    doc = Document.query.get_or_404(doc_id)
    version = DocumentVersion.query.get_or_404(version_id)
    
    doc.content_json = version.content_json
    db.session.commit()
    
    return jsonify({'code': 200, 'message': '版本切换成功'})
