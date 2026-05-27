"""
收件点配送管理
"""
from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.models import DistributionTask, DistributionRecord, DistributionPersonnel, OperationLog
from app import db

distribution_bp = Blueprint('distribution', __name__)


@distribution_bp.route('/tasks', methods=['GET'])
@login_required
def list_tasks():
    """配送任务列表"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    query = DistributionTask.query.filter_by(is_deleted=0)
    
    status = request.args.get('status')
    if status:
        query = query.filter_by(status=status)
    
    point_id = request.args.get('point_id', type=int)
    if point_id:
        query = query.filter_by(point_id=point_id)
    
    pagination = query.order_by(DistributionTask.created_at.desc()).paginate(
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


@distribution_bp.route('/tasks', methods=['POST'])
@login_required
def create_task():
    """创建配送任务"""
    data = request.get_json()
    task = DistributionTask(
        task_no=data['task_no'],
        batch_no=data.get('batch_no'),
        point_id=data.get('point_id'),
        vehicle_id=data.get('vehicle_id'),
        driver_id=data.get('driver_id'),
        package_count=data.get('package_count', 0),
        total_weight=data.get('total_weight'),
        planned_time=datetime.strptime(data['planned_time'], '%Y-%m-%d %H:%M') if data.get('planned_time') else None,
        route_json=data.get('route_json')
    )
    task.save()
    return jsonify({'code': 200, 'message': '配送任务创建成功', 'data': task.to_dict()})


@distribution_bp.route('/tasks/<int:task_id>/start', methods=['POST'])
@login_required
def start_distribution(task_id):
    """开始配送"""
    task = DistributionTask.query.get_or_404(task_id)
    task.status = 'dispatching'
    task.actual_departure = datetime.now()
    db.session.commit()
    return jsonify({'code': 200, 'message': '配送已开始'})


@distribution_bp.route('/tasks/<int:task_id>/complete', methods=['POST'])
@login_required
def complete_distribution(task_id):
    """完成配送"""
    task = DistributionTask.query.get_or_404(task_id)
    task.status = 'completed'
    task.actual_arrival = datetime.now()
    db.session.commit()
    return jsonify({'code': 200, 'message': '配送已完成'})


@distribution_bp.route('/records', methods=['GET'])
@login_required
def list_records():
    """配送记录列表"""
    task_id = request.args.get('task_id', type=int)
    query = DistributionRecord.query.filter_by(is_deleted=0)
    if task_id:
        query = query.filter_by(task_id=task_id)
    records = query.order_by(DistributionRecord.created_at.desc()).all()
    return jsonify({'code': 200, 'data': [r.to_dict() for r in records]})


@distribution_bp.route('/personnel/checkin', methods=['POST'])
@login_required
def check_in():
    """配送人员签到"""
    personnel = DistributionPersonnel.query.filter_by(
        user_id=current_user.id, is_deleted=0).first()
    if not personnel:
        personnel = DistributionPersonnel(user_id=current_user.id)
    personnel.check_in_time = datetime.now()
    personnel.status = 'online'
    personnel.save()
    return jsonify({'code': 200, 'message': '签到成功'})


@distribution_bp.route('/personnel/checkout', methods=['POST'])
@login_required
def check_out():
    """配送人员签退"""
    personnel = DistributionPersonnel.query.filter_by(
        user_id=current_user.id, is_deleted=0).first()
    if personnel:
        personnel.check_out_time = datetime.now()
        personnel.status = 'offline'
        db.session.commit()
    return jsonify({'code': 200, 'message': '签退成功'})
