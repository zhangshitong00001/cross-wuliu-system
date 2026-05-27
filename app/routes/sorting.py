"""
阿拉木图收件点分装管理
"""
from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.models import CollectionPoint, SortingTask, SortingRecord, SortingPersonnel, OperationLog
from app import db

sorting_bp = Blueprint('sorting', __name__)


# ===== 收件点管理 =====

@sorting_bp.route('/points', methods=['GET'])
@login_required
def list_points():
    """收件点列表"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    query = CollectionPoint.query.filter_by(is_deleted=0)
    
    keyword = request.args.get('keyword')
    if keyword:
        query = query.filter(
            (CollectionPoint.name.like(f'%{keyword}%')) |
            (CollectionPoint.point_code.like(f'%{keyword}%')) |
            (CollectionPoint.address.like(f'%{keyword}%'))
        )
    
    status = request.args.get('status')
    if status:
        query = query.filter_by(status=status)
    
    pagination = query.order_by(CollectionPoint.point_code.asc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        'code': 200,
        'data': {
            'items': [p.to_dict() for p in pagination.items],
            'total': pagination.total,
            'page': page,
            'pages': pagination.pages
        }
    })


@sorting_bp.route('/points', methods=['POST'])
@login_required
def create_point():
    """创建收件点"""
    data = request.get_json()
    point = CollectionPoint(
        point_code=data['point_code'],
        name=data['name'],
        address=data.get('address'),
        contact_person=data.get('contact_person'),
        contact_phone=data.get('contact_phone'),
        latitude=data.get('latitude'),
        longitude=data.get('longitude'),
        region=data.get('region')
    )
    point.save()
    return jsonify({'code': 200, 'message': '收件点创建成功', 'data': point.to_dict()})


@sorting_bp.route('/points/<int:point_id>', methods=['PUT'])
@login_required
def update_point(point_id):
    """更新收件点"""
    point = CollectionPoint.query.get_or_404(point_id)
    data = request.get_json()
    for field in ['name', 'address', 'contact_person', 'contact_phone', 'latitude', 'longitude', 'status', 'region']:
        if field in data:
            setattr(point, field, data[field])
    db.session.commit()
    return jsonify({'code': 200, 'message': '更新成功', 'data': point.to_dict()})


# ===== 分装任务管理 =====

@sorting_bp.route('/tasks', methods=['GET'])
@login_required
def list_tasks():
    """分装任务列表"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    query = SortingTask.query.filter_by(is_deleted=0)
    
    status = request.args.get('status')
    if status:
        query = query.filter_by(status=status)
    
    point_id = request.args.get('point_id', type=int)
    if point_id:
        query = query.filter_by(point_id=point_id)
    
    pagination = query.order_by(SortingTask.created_at.desc()).paginate(
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


@sorting_bp.route('/tasks', methods=['POST'])
@login_required
def create_task():
    """创建分装任务"""
    data = request.get_json()
    task = SortingTask(
        task_no=data['task_no'],
        batch_no=data.get('batch_no'),
        point_id=data.get('point_id'),
        total_packages=data.get('total_packages', 0),
        total_weight=data.get('total_weight'),
        total_volume=data.get('total_volume'),
        assigned_to=data.get('assigned_to')
    )
    task.save()
    return jsonify({'code': 200, 'message': '分装任务创建成功', 'data': task.to_dict()})


@sorting_bp.route('/tasks/<int:task_id>/complete', methods=['POST'])
@login_required
def complete_task(task_id):
    """完成分装任务"""
    task = SortingTask.query.get_or_404(task_id)
    task.status = 'completed'
    task.completed_at = datetime.now()
    db.session.commit()
    return jsonify({'code': 200, 'message': '分装任务已完成'})


# ===== 分装记录 =====

@sorting_bp.route('/records', methods=['GET'])
@login_required
def list_records():
    """分装记录列表"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    query = SortingRecord.query.filter_by(is_deleted=0)
    
    task_id = request.args.get('task_id', type=int)
    if task_id:
        query = query.filter_by(task_id=task_id)
    
    pagination = query.order_by(SortingRecord.created_at.desc()).paginate(
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


@sorting_bp.route('/records', methods=['POST'])
@login_required
def create_record():
    """创建分装记录"""
    data = request.get_json()
    record = SortingRecord(
        task_id=data['task_id'],
        package_no=data.get('package_no'),
        product_name=data.get('product_name'),
        quantity=data.get('quantity'),
        weight=data.get('weight'),
        operator_id=current_user.id
    )
    record.save()
    return jsonify({'code': 200, 'message': '分装记录创建成功', 'data': record.to_dict()})


# ===== 分装人员管理 =====

@sorting_bp.route('/personnel', methods=['GET'])
@login_required
def list_personnel():
    """分装人员列表"""
    personnel = SortingPersonnel.query.filter_by(is_deleted=0).all()
    return jsonify({'code': 200, 'data': [p.to_dict() for p in personnel]})


@sorting_bp.route('/personnel/schedule', methods=['POST'])
@login_required
def schedule_personnel():
    """人员排班"""
    data = request.get_json()
    personnel = SortingPersonnel(
        user_id=data['user_id'],
        shift_date=datetime.strptime(data['shift_date'], '%Y-%m-%d'),
        shift_type=data.get('shift_type')
    )
    personnel.save()
    return jsonify({'code': 200, 'message': '排班成功'})
