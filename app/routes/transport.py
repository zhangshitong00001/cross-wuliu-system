"""
装车运输管理
"""
from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.models import TransportTask, TransportNode, TransportException, Vehicle, Driver, OperationLog
from app import db
from app.utils.excel_import import (
    ExcelImporter, FieldValidator, build_import_response,
    allowed_file, get_import_template, safe_str, safe_int, safe_float, safe_datetime
)

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


@transport_bp.route('/tasks/<int:task_id>', methods=['PUT'])
@login_required
def update_transport_task(task_id):
    """更新运输任务"""
    task = TransportTask.query.get_or_404(task_id)
    data = request.get_json()
    for field in ['task_no', 'batch_no', 'vehicle_id', 'driver_id', 'route_from', 'route_to',
                  'total_weight', 'total_volume', 'status', 'priority']:
        if field in data:
            setattr(task, field, data[field])
    if data.get('planned_departure'):
        task.planned_departure = datetime.strptime(data['planned_departure'], '%Y-%m-%d %H:%M')
    if data.get('planned_arrival'):
        task.planned_arrival = datetime.strptime(data['planned_arrival'], '%Y-%m-%d %H:%M')
    db.session.commit()
    return jsonify({'code': 200, 'message': '运输任务更新成功', 'data': task.to_dict()})


@transport_bp.route('/tasks/<int:task_id>', methods=['DELETE'])
@login_required
def delete_transport_task(task_id):
    """删除运输任务"""
    task = TransportTask.query.get_or_404(task_id)
    task.is_deleted = 1
    db.session.commit()
    return jsonify({'code': 200, 'message': '删除成功'})


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


@transport_bp.route('/vehicles/<int:vehicle_id>', methods=['PUT'])
@login_required
def update_vehicle(vehicle_id):
    """更新车辆"""
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    data = request.get_json()
    for field in ['plate_no', 'vehicle_type', 'brand', 'model', 'load_weight', 'load_volume', 'driver_id', 'driving_license', 'status']:
        if field in data:
            setattr(vehicle, field, data[field])
    db.session.commit()
    return jsonify({'code': 200, 'message': '车辆更新成功', 'data': vehicle.to_dict()})


@transport_bp.route('/vehicles/<int:vehicle_id>', methods=['DELETE'])
@login_required
def delete_vehicle(vehicle_id):
    """删除车辆"""
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    vehicle.is_deleted = 1
    db.session.commit()
    return jsonify({'code': 200, 'message': '删除成功'})


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


@transport_bp.route('/drivers/<int:driver_id>', methods=['PUT'])
@login_required
def update_driver(driver_id):
    """更新司机"""
    driver = Driver.query.get_or_404(driver_id)
    data = request.get_json()
    for field in ['name', 'phone', 'license_no', 'id_card', 'status']:
        if field in data:
            setattr(driver, field, data[field])
    db.session.commit()
    return jsonify({'code': 200, 'message': '司机更新成功', 'data': driver.to_dict()})


@transport_bp.route('/drivers/<int:driver_id>', methods=['DELETE'])
@login_required
def delete_driver(driver_id):
    """删除司机"""
    driver = Driver.query.get_or_404(driver_id)
    driver.is_deleted = 1
    db.session.commit()
    return jsonify({'code': 200, 'message': '删除成功'})


# ===== Excel批量导入 =====

@transport_bp.route('/tasks/import/template', methods=['GET'])
@login_required
def download_task_template():
    """下载运输任务导入模板"""
    fields = [
        {'name': 'task_no', 'display_name': '任务编号', 'required': True, 'example': 'TT20260601001'},
        {'name': 'batch_no', 'display_name': '批次号', 'example': 'BATCH20260601'},
        {'name': 'route_from', 'display_name': '出发地', 'required': True, 'example': '阿拉木图'},
        {'name': 'route_to', 'display_name': '目的地', 'required': True, 'example': '霍尔果斯口岸'},
        {'name': 'vehicle_id', 'display_name': '车辆ID', 'example': '1'},
        {'name': 'driver_id', 'display_name': '司机ID', 'example': '1'},
        {'name': 'planned_departure', 'display_name': '计划出发时间', 'example': '2026-06-02 08:00'},
        {'name': 'planned_arrival', 'display_name': '计划到达时间', 'example': '2026-06-03 18:00'},
        {'name': 'total_weight', 'display_name': '总重量(kg)', 'example': '5000'},
        {'name': 'total_volume', 'display_name': '总体积(m³)', 'example': '20'},
        {'name': 'remark', 'display_name': '备注', 'example': ''},
    ]
    output = get_import_template(fields, sheet_name='运输任务导入')
    from flask import send_file
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='运输任务导入模板.xlsx'
    )


@transport_bp.route('/tasks/import', methods=['POST'])
@login_required
def import_tasks():
    """批量导入运输任务"""
    if 'file' not in request.files:
        return jsonify({'code': 400, 'message': '请上传文件'})

    file = request.files['file']
    if file.filename == '' or not allowed_file(file.filename):
        return jsonify({'code': 400, 'message': '请上传有效的Excel文件（.xlsx或.xls）'})

    validators = [
        FieldValidator('task_no', '任务编号', required=True,
                       unique_check=lambda v: TransportTask.query.filter_by(task_no=v, is_deleted=0).first() is not None),
        FieldValidator('batch_no', '批次号'),
        FieldValidator('route_from', '出发地', required=True),
        FieldValidator('route_to', '目的地', required=True),
        FieldValidator('vehicle_id', '车辆ID', field_type='int'),
        FieldValidator('driver_id', '司机ID', field_type='int'),
        FieldValidator('planned_departure', '计划出发时间', field_type='datetime'),
        FieldValidator('planned_arrival', '计划到达时间', field_type='datetime'),
        FieldValidator('total_weight', '总重量(kg)', field_type='float', min_value=0),
        FieldValidator('total_volume', '总体积(m³)', field_type='float', min_value=0),
        FieldValidator('remark', '备注'),
    ]

    def process_func(row, row_index):
        task = TransportTask(
            task_no=safe_str(row.get('task_no')),
            batch_no=safe_str(row.get('batch_no')),
            vehicle_id=safe_int(row.get('vehicle_id')),
            driver_id=safe_int(row.get('driver_id')),
            route_from=safe_str(row.get('route_from')),
            route_to=safe_str(row.get('route_to')),
            planned_departure=safe_datetime(row.get('planned_departure')),
            planned_arrival=safe_datetime(row.get('planned_arrival')),
            total_weight=safe_float(row.get('total_weight')),
            total_volume=safe_float(row.get('total_volume')),
            remark=safe_str(row.get('remark')),
            status='pending',
            created_by=current_user.id
        )
        task.save()
        return True, None

    importer = ExcelImporter(file, validators=validators)
    result = importer.run(process_func)

    OperationLog(
        user_id=current_user.id, username=current_user.username,
        action='import', module='transport_task',
        target_desc=f'批量导入运输任务: 成功{result["success"]}条, 失败{result["fail"]}条',
        ip_address=request.remote_addr
    ).save()

    return jsonify(build_import_response(result))


@transport_bp.route('/vehicles/import/template', methods=['GET'])
@login_required
def download_vehicle_template():
    """下载车辆导入模板"""
    fields = [
        {'name': 'plate_no', 'display_name': '车牌号', 'required': True, 'example': '京A·88888'},
        {'name': 'vehicle_type', 'display_name': '车辆类型', 'example': '厢式货车'},
        {'name': 'brand', 'display_name': '品牌', 'example': '解放'},
        {'name': 'model', 'display_name': '型号', 'example': 'J6'},
        {'name': 'load_weight', 'display_name': '载重(kg)', 'example': '10000'},
        {'name': 'load_volume', 'display_name': '容积(m³)', 'example': '40'},
        {'name': 'driver_id', 'display_name': '司机ID', 'example': '1'},
        {'name': 'driving_license', 'display_name': '行驶证号', 'example': '粤A123456'},
        {'name': 'remark', 'display_name': '备注', 'example': ''},
    ]
    output = get_import_template(fields, sheet_name='车辆导入')
    from flask import send_file
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='车辆导入模板.xlsx'
    )


@transport_bp.route('/vehicles/import', methods=['POST'])
@login_required
def import_vehicles():
    """批量导入车辆"""
    if 'file' not in request.files:
        return jsonify({'code': 400, 'message': '请上传文件'})

    file = request.files['file']
    if file.filename == '' or not allowed_file(file.filename):
        return jsonify({'code': 400, 'message': '请上传有效的Excel文件（.xlsx或.xls）'})

    validators = [
        FieldValidator('plate_no', '车牌号', required=True,
                       unique_check=lambda v: Vehicle.query.filter_by(plate_no=v, is_deleted=0).first() is not None),
        FieldValidator('vehicle_type', '车辆类型'),
        FieldValidator('brand', '品牌'),
        FieldValidator('model', '型号'),
        FieldValidator('load_weight', '载重(kg)', field_type='float', min_value=0),
        FieldValidator('load_volume', '容积(m³)', field_type='float', min_value=0),
        FieldValidator('driver_id', '司机ID', field_type='int'),
        FieldValidator('driving_license', '行驶证号'),
        FieldValidator('remark', '备注'),
    ]

    def process_func(row, row_index):
        vehicle = Vehicle(
            plate_no=safe_str(row.get('plate_no')),
            vehicle_type=safe_str(row.get('vehicle_type')),
            brand=safe_str(row.get('brand')),
            model=safe_str(row.get('model')),
            load_weight=safe_float(row.get('load_weight')),
            load_volume=safe_float(row.get('load_volume')),
            driver_id=safe_int(row.get('driver_id')),
            driving_license=safe_str(row.get('driving_license')),
            remark=safe_str(row.get('remark')),
            status='idle'
        )
        vehicle.save()
        return True, None

    importer = ExcelImporter(file, validators=validators)
    result = importer.run(process_func)

    OperationLog(
        user_id=current_user.id, username=current_user.username,
        action='import', module='transport_vehicle',
        target_desc=f'批量导入车辆: 成功{result["success"]}条, 失败{result["fail"]}条',
        ip_address=request.remote_addr
    ).save()

    return jsonify(build_import_response(result))


@transport_bp.route('/drivers/import/template', methods=['GET'])
@login_required
def download_driver_template():
    """下载司机导入模板"""
    fields = [
        {'name': 'name', 'display_name': '姓名', 'required': True, 'example': '张三'},
        {'name': 'phone', 'display_name': '手机号', 'example': '13800138000'},
        {'name': 'license_no', 'display_name': '驾驶证号', 'example': '110101199001011234'},
        {'name': 'id_card', 'display_name': '身份证号', 'example': '110101199001011234'},
        {'name': 'remark', 'display_name': '备注', 'example': ''},
    ]
    output = get_import_template(fields, sheet_name='司机导入')
    from flask import send_file
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='司机导入模板.xlsx'
    )


@transport_bp.route('/drivers/import', methods=['POST'])
@login_required
def import_drivers():
    """批量导入司机"""
    if 'file' not in request.files:
        return jsonify({'code': 400, 'message': '请上传文件'})

    file = request.files['file']
    if file.filename == '' or not allowed_file(file.filename):
        return jsonify({'code': 400, 'message': '请上传有效的Excel文件（.xlsx或.xls）'})

    validators = [
        FieldValidator('name', '姓名', required=True),
        FieldValidator('phone', '手机号'),
        FieldValidator('license_no', '驾驶证号',
                       unique_check=lambda v: Driver.query.filter_by(license_no=v, is_deleted=0).first() is not None),
        FieldValidator('id_card', '身份证号'),
        FieldValidator('remark', '备注'),
    ]

    def process_func(row, row_index):
        driver = Driver(
            name=safe_str(row.get('name')),
            phone=safe_str(row.get('phone')),
            license_no=safe_str(row.get('license_no')),
            id_card=safe_str(row.get('id_card')),
            remark=safe_str(row.get('remark')),
            status='idle'
        )
        driver.save()
        return True, None

    importer = ExcelImporter(file, validators=validators)
    result = importer.run(process_func)

    OperationLog(
        user_id=current_user.id, username=current_user.username,
        action='import', module='transport_driver',
        target_desc=f'批量导入司机: 成功{result["success"]}条, 失败{result["fail"]}条',
        ip_address=request.remote_addr
    ).save()

    return jsonify(build_import_response(result))
