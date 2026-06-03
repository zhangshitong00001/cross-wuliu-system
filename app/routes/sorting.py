"""
阿拉木图收件点分装管理
"""
from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.models import CollectionPoint, SortingTask, SortingRecord, SortingPersonnel, OperationLog
from app import db
from app.utils.excel_import import (
    ExcelImporter, FieldValidator, build_import_response,
    allowed_file, get_import_template, safe_str, safe_int, safe_float
)

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


@sorting_bp.route('/points/<int:point_id>', methods=['DELETE'])
@login_required
def delete_point(point_id):
    """删除收件点"""
    point = CollectionPoint.query.get_or_404(point_id)
    point.is_deleted = 1
    db.session.commit()
    return jsonify({'code': 200, 'message': '删除成功'})


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


@sorting_bp.route('/tasks/<int:task_id>', methods=['PUT'])
@login_required
def update_task(task_id):
    """更新分装任务"""
    task = SortingTask.query.get_or_404(task_id)
    data = request.get_json()
    for field in ['task_no', 'batch_no', 'point_id', 'total_packages', 'total_weight', 'total_volume', 'assigned_to', 'status']:
        if field in data:
            setattr(task, field, data[field])
    db.session.commit()
    return jsonify({'code': 200, 'message': '分装任务更新成功', 'data': task.to_dict()})


@sorting_bp.route('/tasks/<int:task_id>', methods=['DELETE'])
@login_required
def delete_task(task_id):
    """删除分装任务"""
    task = SortingTask.query.get_or_404(task_id)
    task.is_deleted = 1
    db.session.commit()
    return jsonify({'code': 200, 'message': '删除成功'})


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


# ===== Excel批量导入 =====

@sorting_bp.route('/points/import/template', methods=['GET'])
@login_required
def download_point_template():
    """下载收件点导入模板"""
    fields = [
        {'name': 'point_code', 'display_name': '编码', 'required': True, 'example': 'PT001'},
        {'name': 'name', 'display_name': '名称', 'required': True, 'example': '阿拉木图1号收件点'},
        {'name': 'address', 'display_name': '地址', 'example': '阿拉木图市阿拜大街100号'},
        {'name': 'contact_person', 'display_name': '联系人', 'example': '王五'},
        {'name': 'contact_phone', 'display_name': '联系方式', 'example': '+7-777-1234567'},
        {'name': 'region', 'display_name': '区域', 'example': '阿拉木图市'},
        {'name': 'latitude', 'display_name': '纬度', 'example': '43.2567'},
        {'name': 'longitude', 'display_name': '经度', 'example': '76.9286'},
        {'name': 'remark', 'display_name': '备注', 'example': ''},
    ]
    output = get_import_template(fields, sheet_name='收件点导入')
    from flask import send_file
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='收件点导入模板.xlsx'
    )


@sorting_bp.route('/points/import', methods=['POST'])
@login_required
def import_points():
    """批量导入收件点"""
    if 'file' not in request.files:
        return jsonify({'code': 400, 'message': '请上传文件'})

    file = request.files['file']
    if file.filename == '' or not allowed_file(file.filename):
        return jsonify({'code': 400, 'message': '请上传有效的Excel文件（.xlsx或.xls）'})

    validators = [
        FieldValidator('point_code', '编码', required=True,
                       unique_check=lambda v: CollectionPoint.query.filter_by(point_code=v, is_deleted=0).first() is not None),
        FieldValidator('name', '名称', required=True),
        FieldValidator('address', '地址'),
        FieldValidator('contact_person', '联系人'),
        FieldValidator('contact_phone', '联系方式'),
        FieldValidator('region', '区域'),
        FieldValidator('latitude', '纬度', field_type='float'),
        FieldValidator('longitude', '经度', field_type='float'),
        FieldValidator('remark', '备注'),
    ]

    def process_func(row, row_index):
        point = CollectionPoint(
            point_code=safe_str(row.get('point_code')),
            name=safe_str(row.get('name')),
            address=safe_str(row.get('address')),
            contact_person=safe_str(row.get('contact_person')),
            contact_phone=safe_str(row.get('contact_phone')),
            region=safe_str(row.get('region')),
            latitude=safe_float(row.get('latitude')),
            longitude=safe_float(row.get('longitude')),
            remark=safe_str(row.get('remark')),
            status='active'
        )
        point.save()
        return True, None

    importer = ExcelImporter(file, validators=validators)
    result = importer.run(process_func)

    OperationLog(
        user_id=current_user.id, username=current_user.username,
        action='import', module='sorting_point',
        target_desc=f'批量导入收件点: 成功{result["success"]}条, 失败{result["fail"]}条',
        ip_address=request.remote_addr
    ).save()

    return jsonify(build_import_response(result))


@sorting_bp.route('/tasks/import/template', methods=['GET'])
@login_required
def download_task_template():
    """下载分装任务导入模板"""
    fields = [
        {'name': 'task_no', 'display_name': '任务编号', 'required': True, 'example': 'ST20260601001'},
        {'name': 'batch_no', 'display_name': '批次号', 'example': 'BATCH20260601'},
        {'name': 'point_id', 'display_name': '收件点ID', 'required': True, 'example': '1'},
        {'name': 'total_packages', 'display_name': '包裹数', 'example': '50'},
        {'name': 'total_weight', 'display_name': '总重量(kg)', 'example': '100.5'},
        {'name': 'total_volume', 'display_name': '总体积(m³)', 'example': '2.0'},
        {'name': 'assigned_to', 'display_name': '负责人', 'example': '张三'},
        {'name': 'remark', 'display_name': '备注', 'example': ''},
    ]
    output = get_import_template(fields, sheet_name='分装任务导入')
    from flask import send_file
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='分装任务导入模板.xlsx'
    )


@sorting_bp.route('/tasks/import', methods=['POST'])
@login_required
def import_tasks():
    """批量导入分装任务"""
    if 'file' not in request.files:
        return jsonify({'code': 400, 'message': '请上传文件'})

    file = request.files['file']
    if file.filename == '' or not allowed_file(file.filename):
        return jsonify({'code': 400, 'message': '请上传有效的Excel文件（.xlsx或.xls）'})

    validators = [
        FieldValidator('task_no', '任务编号', required=True,
                       unique_check=lambda v: SortingTask.query.filter_by(task_no=v, is_deleted=0).first() is not None),
        FieldValidator('batch_no', '批次号'),
        FieldValidator('point_id', '收件点ID', required=True, field_type='int'),
        FieldValidator('total_packages', '包裹数', field_type='int', min_value=0),
        FieldValidator('total_weight', '总重量(kg)', field_type='float', min_value=0),
        FieldValidator('total_volume', '总体积(m³)', field_type='float', min_value=0),
        FieldValidator('assigned_to', '负责人'),
        FieldValidator('remark', '备注'),
    ]

    def process_func(row, row_index):
        task = SortingTask(
            task_no=safe_str(row.get('task_no')),
            batch_no=safe_str(row.get('batch_no')),
            point_id=safe_int(row.get('point_id')),
            total_packages=safe_int(row.get('total_packages'), 0),
            total_weight=safe_float(row.get('total_weight')),
            total_volume=safe_float(row.get('total_volume')),
            assigned_to=safe_str(row.get('assigned_to')),
            remark=safe_str(row.get('remark')),
            status='pending'
        )
        task.save()
        return True, None

    importer = ExcelImporter(file, validators=validators)
    result = importer.run(process_func)

    OperationLog(
        user_id=current_user.id, username=current_user.username,
        action='import', module='sorting_task',
        target_desc=f'批量导入分装任务: 成功{result["success"]}条, 失败{result["fail"]}条',
        ip_address=request.remote_addr
    ).save()

    return jsonify(build_import_response(result))
