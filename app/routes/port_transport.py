"""
口岸至阿拉木图仓库运输管理
"""
from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.models import PortTransportTask, PortTransportArrival, OperationLog
from app import db
from app.utils.excel_import import (
    ExcelImporter, FieldValidator, build_import_response,
    allowed_file, get_import_template, safe_str, safe_int, safe_float, safe_datetime
)

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


@port_transport_bp.route('/tasks/<int:task_id>', methods=['PUT'])
@login_required
def update_port_transport_task(task_id):
    """更新口岸运输任务"""
    task = PortTransportTask.query.get_or_404(task_id)
    data = request.get_json()
    for field in ['task_no', 'batch_no', 'vehicle_id', 'driver_id', 'total_weight', 'total_volume', 'status']:
        if field in data:
            setattr(task, field, data[field])
    if data.get('departure_time'):
        task.departure_time = datetime.strptime(data['departure_time'], '%Y-%m-%d %H:%M')
    if data.get('estimated_arrival'):
        task.estimated_arrival = datetime.strptime(data['estimated_arrival'], '%Y-%m-%d %H:%M')
    db.session.commit()
    return jsonify({'code': 200, 'message': '运输任务更新成功', 'data': task.to_dict()})


@port_transport_bp.route('/tasks/<int:task_id>', methods=['DELETE'])
@login_required
def delete_port_transport_task(task_id):
    """删除口岸运输任务"""
    task = PortTransportTask.query.get_or_404(task_id)
    task.is_deleted = 1
    db.session.commit()
    return jsonify({'code': 200, 'message': '删除成功'})


# ===== Excel批量导入 =====

@port_transport_bp.route('/tasks/import/template', methods=['GET'])
@login_required
def download_task_template():
    """下载口岸运输任务导入模板"""
    fields = [
        {'name': 'task_no', 'display_name': '任务编号', 'required': True, 'example': 'PT20260601001'},
        {'name': 'batch_no', 'display_name': '批次号', 'example': 'BATCH20260601'},
        {'name': 'vehicle_id', 'display_name': '车辆ID', 'example': '1'},
        {'name': 'driver_id', 'display_name': '司机ID', 'example': '1'},
        {'name': 'departure_time', 'display_name': '出发时间', 'example': '2026-06-02 10:00'},
        {'name': 'estimated_arrival', 'display_name': '预计到达', 'example': '2026-06-02 16:00'},
        {'name': 'total_weight', 'display_name': '总重量(kg)', 'example': '3000'},
        {'name': 'total_volume', 'display_name': '总体积(m³)', 'example': '15'},
        {'name': 'remark', 'display_name': '备注', 'example': ''},
    ]
    output = get_import_template(fields, sheet_name='口岸运输任务导入')
    from flask import send_file
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='口岸运输-任务导入模板.xlsx'
    )


@port_transport_bp.route('/tasks/import', methods=['POST'])
@login_required
def import_tasks():
    """批量导入口岸运输任务"""
    if 'file' not in request.files:
        return jsonify({'code': 400, 'message': '请上传文件'})

    file = request.files['file']
    if file.filename == '' or not allowed_file(file.filename):
        return jsonify({'code': 400, 'message': '请上传有效的Excel文件（.xlsx或.xls）'})

    validators = [
        FieldValidator('task_no', '任务编号', required=True,
                       unique_check=lambda v: PortTransportTask.query.filter_by(task_no=v, is_deleted=0).first() is not None),
        FieldValidator('batch_no', '批次号'),
        FieldValidator('vehicle_id', '车辆ID', field_type='int'),
        FieldValidator('driver_id', '司机ID', field_type='int'),
        FieldValidator('departure_time', '出发时间', field_type='datetime'),
        FieldValidator('estimated_arrival', '预计到达', field_type='datetime'),
        FieldValidator('total_weight', '总重量(kg)', field_type='float', min_value=0),
        FieldValidator('total_volume', '总体积(m³)', field_type='float', min_value=0),
        FieldValidator('remark', '备注'),
    ]

    def process_func(row, row_index):
        task = PortTransportTask(
            task_no=safe_str(row.get('task_no')),
            batch_no=safe_str(row.get('batch_no')),
            vehicle_id=safe_int(row.get('vehicle_id')),
            driver_id=safe_int(row.get('driver_id')),
            departure_time=safe_datetime(row.get('departure_time')),
            estimated_arrival=safe_datetime(row.get('estimated_arrival')),
            total_weight=safe_float(row.get('total_weight')),
            total_volume=safe_float(row.get('total_volume')),
            remark=safe_str(row.get('remark')),
            status='pending'
        )
        task.save()
        return True, None

    importer = ExcelImporter(file, validators=validators)
    result = importer.run(process_func)

    OperationLog(
        user_id=current_user.id, username=current_user.username,
        action='import', module='port_transport_task',
        target_desc=f'批量导入口岸运输任务: 成功{result["success"]}条, 失败{result["fail"]}条',
        ip_address=request.remote_addr
    ).save()

    return jsonify(build_import_response(result))
