"""
物流状态实时跟踪
"""
from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.models import TrackingRecord, OperationLog
from app import db
from app.utils.excel_import import (
    allowed_file, get_import_template, ExcelImporter, FieldValidator,
    safe_str, safe_datetime, build_import_response
)

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

    keyword = request.args.get('keyword')
    if keyword:
        query = query.filter(
            (TrackingRecord.tracking_no.ilike(f'%{keyword}%')) |
            (TrackingRecord.order_no.ilike(f'%{keyword}%'))
        )

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


@tracking_bp.route('/create', methods=['POST'])
@login_required
def create_tracking():
    """创建物流跟踪记录"""
    data = request.get_json()
    record = TrackingRecord(
        tracking_no=data.get('tracking_no'),
        order_no=data.get('order_no'),
        waybill_no=data.get('waybill_no'),
        batch_no=data.get('batch_no'),
        current_stage=data.get('current_stage'),
        stage_detail=data.get('stage_detail'),
        operator=data.get('operator'),
        certificate=data.get('certificate')
    )
    record.save()
    return jsonify({'code': 200, 'message': '跟踪记录创建成功', 'data': record.to_dict()})


@tracking_bp.route('/<int:tracking_id>', methods=['PUT'])
@login_required
def update_tracking(tracking_id):
    """更新跟踪记录"""
    record = TrackingRecord.query.get_or_404(tracking_id)
    data = request.get_json()
    for field in ['tracking_no', 'order_no', 'waybill_no', 'batch_no', 'current_stage', 'stage_detail', 'operator']:
        if field in data:
            setattr(record, field, data[field])
    db.session.commit()
    return jsonify({'code': 200, 'message': '跟踪记录更新成功', 'data': record.to_dict()})


@tracking_bp.route('/<int:tracking_id>', methods=['DELETE'])
@login_required
def delete_tracking(tracking_id):
    """删除跟踪记录"""
    record = TrackingRecord.query.get_or_404(tracking_id)
    record.is_deleted = 1
    db.session.commit()
    return jsonify({'code': 200, 'message': '删除成功'})


# ===== Excel批量导入 =====

@tracking_bp.route('/list/import/template', methods=['GET'])
@login_required
def download_tracking_template():
    """下载物流跟踪导入模板"""
    fields = [
        {'name': 'tracking_no', 'display_name': '跟踪编号', 'required': True, 'example': 'TRK20260603001'},
        {'name': 'order_no', 'display_name': '订单号', 'example': 'ORD20260603001'},
        {'name': 'waybill_no', 'display_name': '运单号', 'example': 'WB20260603001'},
        {'name': 'batch_no', 'display_name': '批次号', 'example': 'B20260601'},
        {'name': 'current_stage', 'display_name': '当前环节', 'required': True, 'example': 'transporting'},
        {'name': 'stage_detail', 'display_name': '环节详情', 'example': '货物已从云仓发出'},
        {'name': 'operator', 'display_name': '操作人', 'example': 'admin'},
        {'name': 'operation_time', 'display_name': '操作时间', 'example': '2026-06-03 10:00:00'},
        {'name': 'certificate', 'display_name': '凭证信息', 'example': ''},
        {'name': 'remark', 'display_name': '备注', 'example': ''},
    ]
    output = get_import_template(fields, sheet_name='物流跟踪导入')
    from flask import send_file
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='物流跟踪-记录导入模板.xlsx'
    )


@tracking_bp.route('/list/import', methods=['POST'])
@login_required
def import_tracking():
    """批量导入物流跟踪记录"""
    if 'file' not in request.files:
        return jsonify({'code': 400, 'message': '请上传文件'})

    file = request.files['file']
    if file.filename == '' or not allowed_file(file.filename):
        return jsonify({'code': 400, 'message': '请上传有效的Excel文件（.xlsx或.xls）'})

    stage_options = ['collecting', 'sorted', 'transporting', 'customs', 'cleared', 'distributing', 'signed']

    validators = [
        FieldValidator('tracking_no', '跟踪编号', required=True,
                       unique_check=lambda v: TrackingRecord.query.filter_by(tracking_no=v, is_deleted=0).first() is not None),
        FieldValidator('order_no', '订单号'),
        FieldValidator('waybill_no', '运单号'),
        FieldValidator('batch_no', '批次号'),
        FieldValidator('current_stage', '当前环节', required=True, options=stage_options),
        FieldValidator('stage_detail', '环节详情'),
        FieldValidator('operator', '操作人'),
        FieldValidator('operation_time', '操作时间', field_type='datetime'),
        FieldValidator('certificate', '凭证信息'),
        FieldValidator('remark', '备注'),
    ]

    def process_func(row, row_index):
        record = TrackingRecord(
            tracking_no=safe_str(row.get('tracking_no')),
            order_no=safe_str(row.get('order_no')),
            waybill_no=safe_str(row.get('waybill_no')),
            batch_no=safe_str(row.get('batch_no')),
            current_stage=safe_str(row.get('current_stage')),
            stage_detail=safe_str(row.get('stage_detail')),
            operator=safe_str(row.get('operator')),
            operation_time=safe_datetime(row.get('operation_time')),
            certificate=safe_str(row.get('certificate')),
            remark=safe_str(row.get('remark')),
        )
        record.save()
        return True, None

    importer = ExcelImporter(file, validators=validators)
    result = importer.run(process_func)

    OperationLog(
        user_id=current_user.id, username=current_user.username,
        action='import', module='tracking',
        target_desc=f'批量导入物流跟踪: 成功{result["success"]}条, 失败{result["fail"]}条',
        ip_address=request.remote_addr
    ).save()

    return jsonify(build_import_response(result))
