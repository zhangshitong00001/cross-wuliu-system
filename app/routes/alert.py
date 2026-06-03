"""
异常预警管理
"""
from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import AlertRecord, OperationLog
from sqlalchemy import func
from app.utils.excel_import import (
    allowed_file, get_import_template, ExcelImporter, FieldValidator,
    safe_str, safe_int, build_import_response
)

alert_bp = Blueprint('alert', __name__)


@alert_bp.route('/list', methods=['GET'])
@login_required
def list_alerts():
    """预警列表"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    query = AlertRecord.query.filter_by(is_deleted=0)
    
    status = request.args.get('status')
    if status:
        query = query.filter_by(status=status)
    
    alert_type = request.args.get('alert_type')
    if alert_type:
        query = query.filter_by(alert_type=alert_type)
    
    alert_level = request.args.get('alert_level')
    if alert_level:
        query = query.filter_by(alert_level=alert_level)
    
    pagination = query.order_by(AlertRecord.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        'code': 200,
        'data': {
            'items': [a.to_dict() for a in pagination.items],
            'total': pagination.total,
            'page': page,
            'pages': pagination.pages
        }
    })


@alert_bp.route('/create', methods=['POST'])
@login_required
def create_alert():
    """创建预警"""
    data = request.get_json()
    alert = AlertRecord(
        alert_no=data['alert_no'],
        alert_type=data['alert_type'],
        alert_level=data.get('alert_level', 'medium'),
        related_business=data.get('related_business'),
        related_id=data.get('related_id'),
        description=data.get('description'),
        notified_via=data.get('notified_via', 'system')
    )
    alert.save()
    return jsonify({'code': 200, 'message': '预警已创建', 'data': alert.to_dict()})


@alert_bp.route('/<int:alert_id>/handle', methods=['PUT'])
@login_required
def handle_alert(alert_id):
    """处理预警"""
    alert = AlertRecord.query.get_or_404(alert_id)
    data = request.get_json()
    alert.status = data.get('status', 'processing')
    alert.handler_id = current_user.id
    alert.handled_at = datetime.now() if data.get('status') == 'resolved' else None
    alert.solution = data.get('solution')
    alert.result = data.get('result')
    db.session.commit()
    return jsonify({'code': 200, 'message': '预警已处理'})


@alert_bp.route('/<int:alert_id>', methods=['PUT'])
@login_required
def update_alert(alert_id):
    """更新预警"""
    alert = AlertRecord.query.get_or_404(alert_id)
    data = request.get_json()
    for field in ['alert_no', 'alert_type', 'alert_level', 'related_business', 'related_id', 'description', 'status']:
        if field in data:
            setattr(alert, field, data[field])
    db.session.commit()
    return jsonify({'code': 200, 'message': '预警更新成功', 'data': alert.to_dict()})


@alert_bp.route('/<int:alert_id>', methods=['DELETE'])
@login_required
def delete_alert(alert_id):
    """删除预警"""
    alert = AlertRecord.query.get_or_404(alert_id)
    alert.is_deleted = 1
    db.session.commit()
    return jsonify({'code': 200, 'message': '删除成功'})


@alert_bp.route('/stats', methods=['GET'])
@login_required
def alert_stats():
    """预警统计"""
    total = AlertRecord.query.filter_by(is_deleted=0).count()
    pending = AlertRecord.query.filter_by(is_deleted=0, status='pending').count()
    processing = AlertRecord.query.filter_by(is_deleted=0, status='processing').count()
    resolved = AlertRecord.query.filter_by(is_deleted=0, status='resolved').count()
    
    # 按类型统计
    type_stats = db.session.query(
        AlertRecord.alert_type,
        func.count(AlertRecord.id).label('count')
    ).filter_by(is_deleted=0).group_by(AlertRecord.alert_type).all()
    
    return jsonify({
        'code': 200,
        'data': {
            'total': total,
            'pending': pending,
            'processing': processing,
            'resolved': resolved,
            'by_type': [{'type': t[0], 'count': t[1]} for t in type_stats]
        }
    })


# ===== Excel批量导入 =====

@alert_bp.route('/list/import/template', methods=['GET'])
@login_required
def download_alert_template():
    """下载预警导入模板"""
    fields = [
        {'name': 'alert_no', 'display_name': '预警编号', 'required': True, 'example': 'AL20260603001'},
        {'name': 'alert_type', 'display_name': '预警类型', 'required': True, 'example': 'overdue_stay'},
        {'name': 'alert_level', 'display_name': '预警级别', 'example': 'medium'},
        {'name': 'description', 'display_name': '描述', 'example': '货物滞留超期'},
        {'name': 'related_business', 'display_name': '关联业务类型', 'example': 'transport'},
        {'name': 'related_id', 'display_name': '关联业务ID', 'example': '1'},
        {'name': 'notified_via', 'display_name': '通知方式', 'example': 'system'},
        {'name': 'status', 'display_name': '状态', 'example': 'pending'},
    ]
    output = get_import_template(fields, sheet_name='预警导入')
    from flask import send_file
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='预警导入模板.xlsx'
    )


@alert_bp.route('/list/import', methods=['POST'])
@login_required
def import_alerts():
    """批量导入预警"""
    if 'file' not in request.files:
        return jsonify({'code': 400, 'message': '请上传文件'})

    file = request.files['file']
    if file.filename == '' or not allowed_file(file.filename):
        return jsonify({'code': 400, 'message': '请上传有效的Excel文件（.xlsx或.xls）'})

    validators = [
        FieldValidator('alert_no', '预警编号', required=True,
                       unique_check=lambda v: AlertRecord.query.filter_by(alert_no=v, is_deleted=0).first() is not None),
        FieldValidator('alert_type', '预警类型', required=True,
                       options=['overdue_stay', 'material_miss', 'route_deviation',
                                'package_damage', 'sign_exception', 'recon_diff',
                                'settlement_overdue', 'invoice_fail']),
        FieldValidator('alert_level', '预警级别', options=['low', 'medium', 'high']),
        FieldValidator('description', '描述'),
        FieldValidator('related_business', '关联业务类型'),
        FieldValidator('related_id', '关联业务ID', field_type='int'),
        FieldValidator('notified_via', '通知方式'),
        FieldValidator('status', '状态', options=['pending', 'processing', 'resolved']),
    ]

    def process_func(row, row_index):
        alert = AlertRecord(
            alert_no=safe_str(row.get('alert_no')),
            alert_type=safe_str(row.get('alert_type')),
            alert_level=safe_str(row.get('alert_level'), 'medium'),
            description=safe_str(row.get('description')),
            related_business=safe_str(row.get('related_business')),
            related_id=safe_int(row.get('related_id')),
            notified_via=safe_str(row.get('notified_via'), 'system'),
            status=safe_str(row.get('status'), 'pending')
        )
        alert.save()
        return True, None

    importer = ExcelImporter(file, validators=validators)
    result = importer.run(process_func)

    OperationLog(
        user_id=current_user.id, username=current_user.username,
        action='import', module='alert',
        target_desc=f'批量导入预警: 成功{result["success"]}条, 失败{result["fail"]}条',
        ip_address=request.remote_addr
    ).save()

    return jsonify(build_import_response(result))
