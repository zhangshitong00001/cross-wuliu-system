"""
异常预警管理
"""
from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import AlertRecord
from sqlalchemy import func

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



