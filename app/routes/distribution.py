"""
收件点配送管理
"""
from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.models import DistributionTask, DistributionRecord, DistributionPersonnel, OperationLog
from app import db
from app.utils.excel_import import (
    ExcelImporter, FieldValidator, build_import_response,
    allowed_file, get_import_template, safe_str, safe_int, safe_float, safe_datetime
)

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


@distribution_bp.route('/tasks/<int:task_id>', methods=['PUT'])
@login_required
def update_distribution_task(task_id):
    """更新配送任务"""
    task = DistributionTask.query.get_or_404(task_id)
    data = request.get_json()
    for field in ['task_no', 'batch_no', 'point_id', 'vehicle_id', 'driver_id',
                  'package_count', 'total_weight', 'status', 'route_json']:
        if field in data:
            setattr(task, field, data[field])
    if data.get('planned_time'):
        task.planned_time = datetime.strptime(data['planned_time'], '%Y-%m-%d %H:%M')
    db.session.commit()
    return jsonify({'code': 200, 'message': '配送任务更新成功', 'data': task.to_dict()})


@distribution_bp.route('/tasks/<int:task_id>', methods=['DELETE'])
@login_required
def delete_distribution_task(task_id):
    """删除配送任务"""
    task = DistributionTask.query.get_or_404(task_id)
    task.is_deleted = 1
    db.session.commit()
    return jsonify({'code': 200, 'message': '删除成功'})


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


# ===== Excel批量导入 =====

@distribution_bp.route('/tasks/import/template', methods=['GET'])
@login_required
def download_task_template():
    """下载配送任务导入模板"""
    fields = [
        {'name': 'task_no', 'display_name': '任务编号', 'required': True, 'example': 'DT20260601001'},
        {'name': 'batch_no', 'display_name': '批次号', 'example': 'BATCH20260601'},
        {'name': 'point_id', 'display_name': '收件点ID', 'required': True, 'example': '1'},
        {'name': 'vehicle_id', 'display_name': '车辆ID', 'example': '1'},
        {'name': 'driver_id', 'display_name': '司机ID', 'example': '1'},
        {'name': 'package_count', 'display_name': '包裹数', 'example': '30'},
        {'name': 'total_weight', 'display_name': '总重量(kg)', 'example': '200.5'},
        {'name': 'planned_time', 'display_name': '计划配送时间', 'example': '2026-06-02 14:00'},
        {'name': 'remark', 'display_name': '备注', 'example': ''},
    ]
    output = get_import_template(fields, sheet_name='配送任务导入')
    from flask import send_file
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='配送任务导入模板.xlsx'
    )


@distribution_bp.route('/tasks/import', methods=['POST'])
@login_required
def import_tasks():
    """批量导入配送任务"""
    if 'file' not in request.files:
        return jsonify({'code': 400, 'message': '请上传文件'})

    file = request.files['file']
    if file.filename == '' or not allowed_file(file.filename):
        return jsonify({'code': 400, 'message': '请上传有效的Excel文件（.xlsx或.xls）'})

    validators = [
        FieldValidator('task_no', '任务编号', required=True,
                       unique_check=lambda v: DistributionTask.query.filter_by(task_no=v, is_deleted=0).first() is not None),
        FieldValidator('batch_no', '批次号'),
        FieldValidator('point_id', '收件点ID', required=True, field_type='int'),
        FieldValidator('vehicle_id', '车辆ID', field_type='int'),
        FieldValidator('driver_id', '司机ID', field_type='int'),
        FieldValidator('package_count', '包裹数', field_type='int', min_value=0),
        FieldValidator('total_weight', '总重量(kg)', field_type='float', min_value=0),
        FieldValidator('planned_time', '计划配送时间', field_type='datetime'),
        FieldValidator('remark', '备注'),
    ]

    def process_func(row, row_index):
        task = DistributionTask(
            task_no=safe_str(row.get('task_no')),
            batch_no=safe_str(row.get('batch_no')),
            point_id=safe_int(row.get('point_id')),
            vehicle_id=safe_int(row.get('vehicle_id')),
            driver_id=safe_int(row.get('driver_id')),
            package_count=safe_int(row.get('package_count'), 0),
            total_weight=safe_float(row.get('total_weight')),
            planned_time=safe_datetime(row.get('planned_time')),
            remark=safe_str(row.get('remark')),
            status='pending'
        )
        task.save()
        return True, None

    importer = ExcelImporter(file, validators=validators)
    result = importer.run(process_func)

    OperationLog(
        user_id=current_user.id, username=current_user.username,
        action='import', module='distribution_task',
        target_desc=f'批量导入配送任务: 成功{result["success"]}条, 失败{result["fail"]}条',
        ip_address=request.remote_addr
    ).save()

    return jsonify(build_import_response(result))
