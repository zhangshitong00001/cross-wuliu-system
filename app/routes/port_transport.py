"""
口岸至阿拉木图仓库运输管理
"""
from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.models import PortTransportTask, PortTransportArrival, OperationLog
from app import db

port_transport_bp = Blueprint('port_transport', __name__)


@port_transport_bp.route('/tasks', methods=['GET'])
@login_required
def list_tasks():
    """口岸运输任务列表"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    query = PortTransportTask.query.filter_by(is_deleted=0)
    
    status = request.args.get('status')
    if status:
        query = query.filter_by(status=status)
    
    pagination = query.order_by(PortTransportTask.created_at.desc()).paginate(
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


@port_transport_bp.route('/tasks', methods=['POST'])
@login_required
def create_task():
    """创建口岸运输任务"""
    data = request.get_json()
    task = PortTransportTask(
        task_no=data['task_no'],
        batch_no=data.get('batch_no'),
        vehicle_id=data.get('vehicle_id'),
        driver_id=data.get('driver_id'),
        departure_time=datetime.strptime(data['departure_time'], '%Y-%m-%d %H:%M') if data.get('departure_time') else None,
        estimated_arrival=datetime.strptime(data['estimated_arrival'], '%Y-%m-%d %H:%M') if data.get('estimated_arrival') else None,
        total_weight=data.get('total_weight'),
        total_volume=data.get('total_volume')
    )
    task.save()
    return jsonify({'code': 200, 'message': '运输任务创建成功', 'data': task.to_dict()})


@port_transport_bp.route('/tasks/<int:task_id>/send-alert', methods=['POST'])
@login_required
def send_arrival_alert(task_id):
    """发送到货预告"""
    task = PortTransportTask.query.get_or_404(task_id)
    task.alert_sent = 1
    db.session.commit()
    return jsonify({'code': 200, 'message': '到货预告已发送'})


@port_transport_bp.route('/arrivals', methods=['POST'])
@login_required
def create_arrival():
    """到货验收"""
    data = request.get_json()
    arrival = PortTransportArrival(
        task_id=data['task_id'],
        arrival_time=datetime.now(),
        inspector_id=current_user.id,
        damaged_quantity=data.get('damaged_quantity', 0),
        short_quantity=data.get('short_quantity', 0),
        normal_quantity=data.get('normal_quantity', 0),
        inspection_result=data.get('inspection_result', 'normal'),
        exception_desc=data.get('exception_desc')
    )
    arrival.save()
    
    # 更新任务状态
    task = PortTransportTask.query.get(data['task_id'])
    if task:
        task.status = 'arrived'
        task.actual_arrival = datetime.now()
        db.session.commit()
    
    return jsonify({'code': 200, 'message': '验收完成', 'data': arrival.to_dict()})
