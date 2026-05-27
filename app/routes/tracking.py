"""
物流状态实时跟踪
"""
from flask import Blueprint, request, jsonify
from flask_login import login_required
from app.models import TrackingRecord
from app import db

tracking_bp = Blueprint('tracking', __name__)


@tracking_bp.route('/query', methods=['GET'])
def query_tracking():
    """物流状态查询（公开接口，无需登录）"""
    order_no = request.args.get('order_no')
    waybill_no = request.args.get('waybill_no')
    batch_no = request.args.get('batch_no')
    
    query = TrackingRecord.query.filter_by(is_deleted=0)
    
    if order_no:
        query = query.filter_by(order_no=order_no)
    elif waybill_no:
        query = query.filter_by(waybill_no=waybill_no)
    elif batch_no:
        query = query.filter_by(batch_no=batch_no)
    else:
        return jsonify({'code': 400, 'message': '请提供查询条件'})
    
    records = query.order_by(TrackingRecord.operation_time.desc()).all()
    
    # 整理为按环节分组的轨迹
    stages = []
    for r in records:
        stages.append({
            'stage': r.current_stage,
            'detail': r.stage_detail,
            'operator': r.operator,
            'time': r.operation_time.strftime('%Y-%m-%d %H:%M:%S') if r.operation_time else None,
            'certificate': r.certificate
        })
    
    return jsonify({
        'code': 200,
        'data': {
            'tracking_no': records[0].tracking_no if records else None,
            'order_no': order_no or records[0].order_no if records else None,
            'current_stage': records[0].current_stage if records else None,
            'stages': stages
        }
    })


@tracking_bp.route('/list', methods=['GET'])
@login_required
def list_tracking():
    """跟踪记录列表"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    query = TrackingRecord.query.filter_by(is_deleted=0)
    
    order_no = request.args.get('order_no')
    if order_no:
        query = query.filter_by(order_no=order_no)
    
    batch_no = request.args.get('batch_no')
    if batch_no:
        query = query.filter_by(batch_no=batch_no)
    
    pagination = query.order_by(TrackingRecord.operation_time.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        'code': 200,
        'data': {
            'items': [t.to_dict() for t in pagination.items],
            'total': pagination.total,
            'page': page,
            'pages': pagination.pages
        }
    })
