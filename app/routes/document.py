"""
文件生成管理
"""
from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.models import Document, DocumentVersion, OperationLog
from app import db
from app.utils.excel_import import (
    ExcelImporter, FieldValidator, build_import_response,
    allowed_file, get_import_template, safe_str
)
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


@document_bp.route('/<int:doc_id>', methods=['DELETE'])
@login_required
def delete_document(doc_id):
    """删除文件"""
    doc = Document.query.get_or_404(doc_id)
    doc.is_deleted = 1
    db.session.commit()
    return jsonify({'code': 200, 'message': '删除成功'})


# ===== Excel批量导入 =====

@document_bp.route('/list/import/template', methods=['GET'])
@login_required
def download_document_template():
    """下载文件导入模板"""
    fields = [
        {'name': 'doc_type', 'display_name': '文件类型', 'required': True, 'example': 'loading'},
        {'name': 'title', 'display_name': '标题', 'example': '装车文件-20260601'},
        {'name': 'batch_no', 'display_name': '批次号', 'example': 'BATCH20260601'},
        {'name': 'remark', 'display_name': '备注', 'example': ''},
    ]
    output = get_import_template(fields, sheet_name='文件导入')
    from flask import send_file
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='文件导入模板.xlsx'
    )


@document_bp.route('/list/import', methods=['POST'])
@login_required
def import_documents():
    """批量导入文件"""
    if 'file' not in request.files:
        return jsonify({'code': 400, 'message': '请上传文件'})

    file = request.files['file']
    if file.filename == '' or not allowed_file(file.filename):
        return jsonify({'code': 400, 'message': '请上传有效的Excel文件（.xlsx或.xls）'})

    validators = [
        FieldValidator('doc_type', '文件类型', required=True),
        FieldValidator('title', '标题'),
        FieldValidator('batch_no', '批次号'),
        FieldValidator('remark', '备注'),
    ]

    def process_func(row, row_index):
        doc_type = safe_str(row.get('doc_type'))
        prefix_map = {'loading': 'LD', 'customs': 'CD', 'invoice': 'INV', 'packing_list': 'PL', 'coo': 'COO'}
        prefix = prefix_map.get(doc_type, 'DOC')
        seq = Document.query.count() + 1 + row_index  # 避免重复
        doc_no = f'{prefix}{datetime.now().strftime("%Y%m%d")}{seq:04d}'

        doc = Document(
            doc_no=doc_no,
            doc_type=doc_type,
            title=safe_str(row.get('title')),
            batch_no=safe_str(row.get('batch_no')),
            remark=safe_str(row.get('remark')),
            content_json='{}',
            created_by=current_user.id
        )
        doc.save()

        # 创建初始版本
        DocumentVersion(
            doc_id=doc.id,
            version_no=1,
            content_json='{}',
            operator_id=current_user.id,
            change_summary='批量导入'
        ).save()
        return True, None

    importer = ExcelImporter(file, validators=validators)
    result = importer.run(process_func)

    OperationLog(
        user_id=current_user.id, username=current_user.username,
        action='import', module='document',
        target_desc=f'批量导入文件: 成功{result["success"]}条, 失败{result["fail"]}条',
        ip_address=request.remote_addr
    ).save()

    return jsonify(build_import_response(result))
