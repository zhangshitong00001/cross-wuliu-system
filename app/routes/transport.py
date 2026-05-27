"""
装车运输管理
"""
from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.models import TransportTask, TransportNode, TransportException, Vehicle, Driver, OperationLog
from app import db

transport_bp = Blueprint('transport', __name__)


@transport_bp.route('/tasks', methods=['GET'])
@login_required
def list_tasks():
    """运输任务列表"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    query = TransportTask.query.filter_by(is_deleted=0)
    
    status = request.args.get('status')
    if status:
        query = query.filter_by(status=status)
    
    pagination = query.order_by(TransportTask.created_at.desc()).paginate(
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


@transport_bp.route('/tasks', methods=['POST'])
@login_required
def create_task():
    """创建运输任务"""
    data = request.get_json()
    task = TransportTask(
        task_no=data['task_no'],
        batch_no=data.get('batch_no'),
        vehicle_id=data.get('vehicle_id'),
        driver_id=data.get('driver_id'),
        route_from=data.get('route_from'),
        route_to=data.get('route_to'),
        planned_departure=datetime.strptime(data['planned_departure'], '%Y-%m-%d %H:%M') if data.get('planned_departure') else None,
        planned_arrival=datetime.strptime(data['planned_arrival'], '%Y-%m-%d %H:%M') if data.get('planned_arrival') else None,
        total_weight=data.get('total_weight'),
        total_volume=data.get('total_volume'),
        created_by=current_user.id
    )
    task.save()
    return jsonify({'code': 200, 'message': '运输任务创建成功', 'data': task.to_dict()})


@transport_bp.route('/tasks/<int:task_id>/start', methods=['POST'])
@login_required
def start_transport(task_id):
    """开始运输"""
    task = TransportTask.query.get_or_404(task_id)
    task.status = 'in_transit'
    task.actual_departure = datetime.now()
    db.session.commit()
    
    TransportNode(
        task_id=task.id,
        node_name='出发',
        node_type='departure',
        record_time=datetime.now(),
        description=f'从{task.route_from}出发'
    ).save()
    
    return jsonify({'code': 200, 'message': '运输已开始'})


@transport_bp.route('/tasks/<int:task_id>/arrive', methods=['POST'])
@login_required
def arrive_transport(task_id):
    """到达目的地"""
    task = TransportTask.query.get_or_404(task_id)
    task.status = 'arrived'
    task.actual_arrival = datetime.now()
    db.session.commit()
    
    TransportNode(
        task_id=task.id,
        node_name='到达',
        node_type='arrival',
        record_time=datetime.now(),
        description=f'到达{task.route_to}'
    ).save()
    
    return jsonify({'code': 200, 'message': '已到达目的地'})


@transport_bp.route('/tasks/<int:task_id>/complete', methods=['POST'])
@login_required
def complete_transport(task_id):
    """完成运输"""
    task = TransportTask.query.get_or_404(task_id)
    task.status = 'completed'
    db.session.commit()
    return jsonify({'code': 200, 'message': '运输已完成'})


@transport_bp.route('/nodes', methods=['GET'])
@login_required
def list_nodes():
    """运输节点列表"""
    task_id = request.args.get('task_id', type=int)
    query = TransportNode.query.filter_by(is_deleted=0)
    if task_id:
        query = query.filter_by(task_id=task_id)
    nodes = query.order_by(TransportNode.record_time.asc()).all()
    return jsonify({'code': 200, 'data': [n.to_dict() for n in nodes]})


@transport_bp.route('/exceptions', methods=['GET'])
@login_required
def list_exceptions():
    """运输异常列表"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    query = TransportException.query.filter_by(is_deleted=0)
    
    task_id = request.args.get('task_id', type=int)
    if task_id:
        query = query.filter_by(task_id=task_id)
    
    pagination = query.order_by(TransportException.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        'code': 200,
        'data': {
            'items': [e.to_dict() for e in pagination.items],
            'total': pagination.total,
            'page': page,
            'pages': pagination.pages
        }
    })


@transport_bp.route('/exceptions', methods=['POST'])
@login_required
def report_exception():
    """报告运输异常"""
    data = request.get_json()
    exc = TransportException(
        task_id=data['task_id'],
        exception_type=data['exception_type'],
        description=data.get('description'),
        severity=data.get('severity', 'medium'),
        handler_id=current_user.id
    )
    exc.save()
    return jsonify({'code': 200, 'message': '异常已报告', 'data': exc.to_dict()})


@transport_bp.route('/exceptions/<int:exc_id>/handle', methods=['PUT'])
@login_required
def handle_exception(exc_id):
    """处理异常"""
    exc = TransportException.query.get_or_404(exc_id)
    data = request.get_json()
    exc.solution = data.get('solution')
    exc.progress = data.get('progress', 'processing')
    exc.result = data.get('result')
    db.session.commit()
    return jsonify({'code': 200, 'message': '异常处理已更新'})


# ===== 车辆管理 =====

@transport_bp.route('/vehicles', methods=['GET'])
@login_required
def list_vehicles():
    """车辆列表"""
    vehicles = Vehicle.query.filter_by(is_deleted=0).all()
    return jsonify({'code': 200, 'data': [v.to_dict() for v in vehicles]})


@transport_bp.route('/vehicles', methods=['POST'])
@login_required
def create_vehicle():
    """创建车辆"""
    data = request.get_json()
    vehicle = Vehicle(
        plate_no=data['plate_no'],
        vehicle_type=data.get('vehicle_type'),
        brand=data.get('brand'),
        model=data.get('model'),
        load_weight=data.get('load_weight'),
        load_volume=data.get('load_volume'),
        driver_id=data.get('driver_id'),
        driving_license=data.get('driving_license')
    )
    vehicle.save()
    return jsonify({'code': 200, 'message': '车辆创建成功', 'data': vehicle.to_dict()})


@transport_bp.route('/drivers', methods=['GET'])
@login_required
def list_drivers():
    """司机列表"""
    drivers = Driver.query.filter_by(is_deleted=0).all()
    return jsonify({'code': 200, 'data': [d.to_dict() for d in drivers]})


@transport_bp.route('/drivers', methods=['POST'])
@login_required
def create_driver():
    """创建司机"""
    data = request.get_json()
    driver = Driver(
        name=data['name'],
        phone=data.get('phone'),
        license_no=data.get('license_no'),
        id_card=data.get('id_card')
    )
    driver.save()
    return jsonify({'code': 200, 'message': '司机创建成功', 'data': driver.to_dict()})
