"""
云仓集货管理 - 收货登记、库存管理、批次管理
"""
from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.models import WarehouseReceipt, WarehouseInventory, WarehouseBatch, WarehouseRecord, OperationLog
from app import db
from app.utils.excel_import import (
    ExcelImporter, FieldValidator, build_import_response,
    allowed_file, get_import_template, safe_str, safe_int, safe_float, safe_date
)

warehouse_bp = Blueprint('warehouse', __name__)


def generate_receipt_no():
    """生成收货单号"""
    from datetime import datetime
    prefix = 'REC' + datetime.now().strftime('%Y%m%d')
    last = WarehouseReceipt.query.filter(
        WarehouseReceipt.receipt_no.like(f'{prefix}%')
    ).order_by(WarehouseReceipt.id.desc()).first()
    if last:
        seq = int(last.receipt_no[-4:]) + 1
    else:
        seq = 1
    return f'{prefix}{seq:04d}'


@warehouse_bp.route('/receipts', methods=['GET'])
@login_required
def list_receipts():
    """收货登记列表"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    query = WarehouseReceipt.query.filter_by(is_deleted=0)
    
    status = request.args.get('status')
    if status:
        query = query.filter_by(status=status)
    
    batch_no = request.args.get('batch_no')
    if batch_no:
        query = query.filter_by(batch_no=batch_no)
    
    keyword = request.args.get('keyword')
    if keyword:
        query = query.filter(
            (WarehouseReceipt.product_name.like(f'%{keyword}%')) |
            (WarehouseReceipt.sku.like(f'%{keyword}%')) |
            (WarehouseReceipt.receipt_no.like(f'%{keyword}%'))
        )
    
    pagination = query.order_by(WarehouseReceipt.created_at.desc()).paginate(
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


@warehouse_bp.route('/receipts', methods=['POST'])
@login_required
def create_receipt():
    """创建收货登记"""
    data = request.get_json()
    receipt = WarehouseReceipt(
        receipt_no=generate_receipt_no(),
        batch_no=data.get('batch_no'),
        sku=data.get('sku'),
        product_name=data['product_name'],
        quantity=data['quantity'],
        weight=data.get('weight'),
        volume=data.get('volume'),
        order_no=data.get('order_no'),
        owner_name=data.get('owner_name'),
        expiry_date=datetime.strptime(data['expiry_date'], '%Y-%m-%d') if data.get('expiry_date') else None
    )
    receipt.save()
    
    # 更新库存
    inventory = WarehouseInventory.query.filter_by(sku=data.get('sku'), is_deleted=0).first()
    if inventory:
        inventory.total_quantity += data['quantity']
        inventory.available_quantity += data['quantity']
    else:
        inventory = WarehouseInventory(
            sku=data.get('sku'),
            product_name=data['product_name'],
            total_quantity=data['quantity'],
            available_quantity=data['quantity']
        )
        inventory.save()
    
    # 记录库存变动
    WarehouseRecord(
        record_no=f'IN{receipt.receipt_no}',
        batch_no=data.get('batch_no'),
        sku=data.get('sku'),
        product_name=data['product_name'],
        change_type='in',
        quantity_before=inventory.total_quantity - data['quantity'],
        quantity_change=data['quantity'],
        quantity_after=inventory.total_quantity,
        operator_id=current_user.id
    ).save()
    
    OperationLog(
        user_id=current_user.id, username=current_user.username,
        action='create', module='warehouse_receipt',
        target_id=receipt.id,
        target_desc=f'收货登记: {receipt.receipt_no}',
        ip_address=request.remote_addr
    ).save()
    
    return jsonify({'code': 200, 'message': '收货登记成功', 'data': receipt.to_dict()})


@warehouse_bp.route('/receipts/<int:receipt_id>', methods=['GET'])
@login_required
def get_receipt(receipt_id):
    """获取收货详情"""
    receipt = WarehouseReceipt.query.get_or_404(receipt_id)
    return jsonify({'code': 200, 'data': receipt.to_dict()})


@warehouse_bp.route('/receipts/<int:receipt_id>', methods=['PUT'])
@login_required
def update_receipt(receipt_id):
    """更新收货登记"""
    receipt = WarehouseReceipt.query.get_or_404(receipt_id)
    data = request.get_json()

    for field in ['batch_no', 'sku', 'product_name', 'quantity', 'weight', 'volume', 'order_no', 'owner_name']:
        if field in data:
            setattr(receipt, field, data[field])

    if data.get('expiry_date'):
        receipt.expiry_date = datetime.strptime(data['expiry_date'], '%Y-%m-%d')

    db.session.commit()

    OperationLog(
        user_id=current_user.id, username=current_user.username,
        action='update', module='warehouse_receipt',
        target_id=receipt.id, target_desc=f'更新收货: {receipt.receipt_no}',
        ip_address=request.remote_addr
    ).save()

    return jsonify({'code': 200, 'message': '更新成功', 'data': receipt.to_dict()})


@warehouse_bp.route('/receipts/<int:receipt_id>', methods=['DELETE'])
@login_required
def delete_receipt(receipt_id):
    """删除收货记录"""
    receipt = WarehouseReceipt.query.get_or_404(receipt_id)
    receipt.is_deleted = 1
    db.session.commit()
    OperationLog(
        user_id=current_user.id, username=current_user.username,
        action='delete', module='warehouse_receipt',
        target_id=receipt.id, target_desc=f'删除收货: {receipt.receipt_no}',
        ip_address=request.remote_addr
    ).save()
    return jsonify({'code': 200, 'message': '删除成功'})


@warehouse_bp.route('/receipts/<int:receipt_id>/confirm', methods=['POST'])
@login_required
def confirm_receipt(receipt_id):
    """确认收货"""
    receipt = WarehouseReceipt.query.get_or_404(receipt_id)
    receipt.status = 'confirmed'
    receipt.confirmed_by = current_user.id
    receipt.confirmed_at = datetime.now()
    db.session.commit()
    
    OperationLog(
        user_id=current_user.id, username=current_user.username,
        action='update', module='warehouse_receipt',
        target_id=receipt.id,
        target_desc=f'确认收货: {receipt.receipt_no}',
        ip_address=request.remote_addr
    ).save()
    
    return jsonify({'code': 200, 'message': '确认成功', 'data': receipt.to_dict()})


@warehouse_bp.route('/inventory', methods=['GET'])
@login_required
def list_inventory():
    """库存列表"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    query = WarehouseInventory.query.filter_by(is_deleted=0)
    
    status = request.args.get('status')
    if status:
        query = query.filter_by(status=status)
    
    keyword = request.args.get('keyword')
    if keyword:
        query = query.filter(
            (WarehouseInventory.product_name.like(f'%{keyword}%')) |
            (WarehouseInventory.sku.like(f'%{keyword}%'))
        )
    
    pagination = query.order_by(WarehouseInventory.updated_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        'code': 200,
        'data': {
            'items': [i.to_dict() for i in pagination.items],
            'total': pagination.total,
            'page': page,
            'pages': pagination.pages
        }
    })


@warehouse_bp.route('/batches', methods=['GET'])
@login_required
def list_batches():
    """批次列表"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    query = WarehouseBatch.query.filter_by(is_deleted=0)
    
    batch_no = request.args.get('batch_no')
    if batch_no:
        query = query.filter_by(batch_no=batch_no)
    
    pagination = query.order_by(WarehouseBatch.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        'code': 200,
        'data': {
            'items': [b.to_dict() for b in pagination.items],
            'total': pagination.total,
            'page': page,
            'pages': pagination.pages
        }
    })


@warehouse_bp.route('/batches', methods=['POST'])
@login_required
def create_batch():
    """创建批次"""
    data = request.get_json()
    batch = WarehouseBatch(
        batch_no=data['batch_no'],
        product_name=data.get('product_name'),
        sku=data.get('sku'),
        quantity=data.get('quantity'),
        weight=data.get('weight'),
        volume=data.get('volume')
    )
    batch.save()
    return jsonify({'code': 200, 'message': '批次创建成功', 'data': batch.to_dict()})


@warehouse_bp.route('/batches/<int:batch_id>', methods=['PUT'])
@login_required
def update_batch(batch_id):
    """更新批次"""
    batch = WarehouseBatch.query.get_or_404(batch_id)
    data = request.get_json()
    for field in ['batch_no', 'product_name', 'sku', 'quantity', 'weight', 'volume', 'status']:
        if field in data:
            setattr(batch, field, data[field])
    db.session.commit()
    return jsonify({'code': 200, 'message': '批次更新成功', 'data': batch.to_dict()})


@warehouse_bp.route('/batches/<int:batch_id>', methods=['DELETE'])
@login_required
def delete_batch(batch_id):
    """删除批次"""
    batch = WarehouseBatch.query.get_or_404(batch_id)
    batch.is_deleted = 1
    db.session.commit()
    return jsonify({'code': 200, 'message': '删除成功'})


@warehouse_bp.route('/inventory/<int:inventory_id>', methods=['PUT'])
@login_required
def update_inventory(inventory_id):
    """更新库存"""
    inventory = WarehouseInventory.query.get_or_404(inventory_id)
    data = request.get_json()
    for field in ['sku', 'product_name', 'total_quantity', 'available_quantity', 'locked_quantity', 'min_threshold', 'max_threshold', 'warehouse_location']:
        if field in data:
            setattr(inventory, field, data[field])
    db.session.commit()
    return jsonify({'code': 200, 'message': '库存更新成功', 'data': inventory.to_dict()})


@warehouse_bp.route('/records', methods=['GET'])
@login_required
def list_records():
    """库存变动记录"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    query = WarehouseRecord.query.filter_by(is_deleted=0)
    
    batch_no = request.args.get('batch_no')
    if batch_no:
        query = query.filter_by(batch_no=batch_no)
    
    change_type = request.args.get('change_type')
    if change_type:
        query = query.filter_by(change_type=change_type)
    
    pagination = query.order_by(WarehouseRecord.operation_time.desc()).paginate(
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


# ===== Excel批量导入 =====

@warehouse_bp.route('/receipts/import/template', methods=['GET'])
@login_required
def download_receipt_template():
    """下载收货登记导入模板"""
    fields = [
        {'name': 'batch_no', 'display_name': '批次号', 'example': 'BATCH20260601'},
        {'name': 'sku', 'display_name': 'SKU', 'required': True, 'example': 'SKU-001'},
        {'name': 'product_name', 'display_name': '品名', 'required': True, 'example': '电子产品'},
        {'name': 'quantity', 'display_name': '数量', 'required': True, 'example': '100'},
        {'name': 'weight', 'display_name': '重量(kg)', 'example': '25.5'},
        {'name': 'volume', 'display_name': '体积(m³)', 'example': '0.5'},
        {'name': 'order_no', 'display_name': '订单号', 'example': 'ORD20260601001'},
        {'name': 'owner_name', 'display_name': '货主', 'example': '张三'},
        {'name': 'expiry_date', 'display_name': '保质期', 'example': '2026-12-31'},
        {'name': 'remark', 'display_name': '备注', 'example': '易碎品，轻拿轻放'},
    ]
    output = get_import_template(fields, sheet_name='收货登记导入')
    from flask import send_file
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='收货登记导入模板.xlsx'
    )


@warehouse_bp.route('/receipts/import', methods=['POST'])
@login_required
def import_receipts():
    """批量导入收货登记"""
    if 'file' not in request.files:
        return jsonify({'code': 400, 'message': '请上传文件'})

    file = request.files['file']
    if file.filename == '' or not allowed_file(file.filename):
        return jsonify({'code': 400, 'message': '请上传有效的Excel文件（.xlsx或.xls）'})

    validators = [
        FieldValidator('batch_no', '批次号'),
        FieldValidator('sku', 'SKU', required=True),
        FieldValidator('product_name', '品名', required=True),
        FieldValidator('quantity', '数量', required=True, field_type='int', min_value=1),
        FieldValidator('weight', '重量(kg)', field_type='float', min_value=0),
        FieldValidator('volume', '体积(m³)', field_type='float', min_value=0),
        FieldValidator('order_no', '订单号'),
        FieldValidator('owner_name', '货主'),
        FieldValidator('expiry_date', '保质期', field_type='date'),
        FieldValidator('remark', '备注'),
    ]

    def process_func(row, row_index):
        """处理单行数据"""
        receipt = WarehouseReceipt(
            receipt_no=_generate_receipt_no(),
            batch_no=safe_str(row.get('batch_no')),
            sku=safe_str(row.get('sku')),
            product_name=safe_str(row.get('product_name')),
            quantity=safe_int(row.get('quantity'), 0),
            weight=safe_float(row.get('weight')),
            volume=safe_float(row.get('volume')),
            order_no=safe_str(row.get('order_no')),
            owner_name=safe_str(row.get('owner_name')),
            expiry_date=safe_date(row.get('expiry_date')),
            remark=safe_str(row.get('remark')),
            status='pending'
        )
        receipt.save()

        # 更新库存
        sku = safe_str(row.get('sku'))
        if sku:
            inventory = WarehouseInventory.query.filter_by(sku=sku, is_deleted=0).first()
            qty = safe_int(row.get('quantity'), 0)
            if inventory:
                inventory.total_quantity += qty
                inventory.available_quantity += qty
            else:
                inventory = WarehouseInventory(
                    sku=sku,
                    product_name=safe_str(row.get('product_name')),
                    total_quantity=qty,
                    available_quantity=qty
                )
                inventory.save()

            # 记录库存变动
            WarehouseRecord(
                record_no=f'IN{receipt.receipt_no}',
                batch_no=safe_str(row.get('batch_no')),
                sku=sku,
                product_name=safe_str(row.get('product_name')),
                change_type='in',
                quantity_before=(inventory.total_quantity - qty) if hasattr(inventory, 'total_quantity') else 0,
                quantity_change=qty,
                quantity_after=inventory.total_quantity,
                operator_id=current_user.id
            ).save()

        return True, None

    importer = ExcelImporter(file, validators=validators)
    result = importer.run(process_func)

    # 记录操作日志
    OperationLog(
        user_id=current_user.id, username=current_user.username,
        action='import', module='warehouse_receipt',
        target_desc=f'批量导入收货登记: 成功{result["success"]}条, 失败{result["fail"]}条',
        ip_address=request.remote_addr
    ).save()

    return jsonify(build_import_response(result))


@warehouse_bp.route('/batches/import/template', methods=['GET'])
@login_required
def download_batch_template():
    """下载批次导入模板"""
    fields = [
        {'name': 'batch_no', 'display_name': '批次号', 'required': True, 'example': 'BATCH20260601'},
        {'name': 'product_name', 'display_name': '品名', 'example': '电子产品'},
        {'name': 'sku', 'display_name': 'SKU', 'example': 'SKU-001'},
        {'name': 'quantity', 'display_name': '数量', 'example': '200'},
        {'name': 'weight', 'display_name': '重量(kg)', 'example': '50.0'},
        {'name': 'volume', 'display_name': '体积(m³)', 'example': '1.0'},
        {'name': 'production_date', 'display_name': '生产日期', 'example': '2026-06-01'},
        {'name': 'expiry_date', 'display_name': '保质期', 'example': '2027-06-01'},
        {'name': 'remark', 'display_name': '备注', 'example': ''},
    ]
    output = get_import_template(fields, sheet_name='批次导入')
    from flask import send_file
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='批次导入模板.xlsx'
    )


@warehouse_bp.route('/batches/import', methods=['POST'])
@login_required
def import_batches():
    """批量导入批次"""
    if 'file' not in request.files:
        return jsonify({'code': 400, 'message': '请上传文件'})

    file = request.files['file']
    if file.filename == '' or not allowed_file(file.filename):
        return jsonify({'code': 400, 'message': '请上传有效的Excel文件（.xlsx或.xls）'})

    validators = [
        FieldValidator('batch_no', '批次号', required=True,
                       unique_check=lambda v: WarehouseBatch.query.filter_by(batch_no=v, is_deleted=0).first() is not None),
        FieldValidator('product_name', '品名'),
        FieldValidator('sku', 'SKU'),
        FieldValidator('quantity', '数量', field_type='int', min_value=0),
        FieldValidator('weight', '重量(kg)', field_type='float', min_value=0),
        FieldValidator('volume', '体积(m³)', field_type='float', min_value=0),
        FieldValidator('production_date', '生产日期', field_type='date'),
        FieldValidator('expiry_date', '保质期', field_type='date'),
        FieldValidator('remark', '备注'),
    ]

    def process_func(row, row_index):
        batch = WarehouseBatch(
            batch_no=safe_str(row.get('batch_no')),
            product_name=safe_str(row.get('product_name')),
            sku=safe_str(row.get('sku')),
            quantity=safe_int(row.get('quantity')),
            weight=safe_float(row.get('weight')),
            volume=safe_float(row.get('volume')),
            production_date=safe_date(row.get('production_date')),
            expiry_date=safe_date(row.get('expiry_date')),
            remark=safe_str(row.get('remark')),
            status='stored'
        )
        batch.save()
        return True, None

    importer = ExcelImporter(file, validators=validators)
    result = importer.run(process_func)

    OperationLog(
        user_id=current_user.id, username=current_user.username,
        action='import', module='warehouse_batch',
        target_desc=f'批量导入批次: 成功{result["success"]}条, 失败{result["fail"]}条',
        ip_address=request.remote_addr
    ).save()

    return jsonify(build_import_response(result))


def _generate_receipt_no():
    """生成收货单号（内部函数，避免与已有函数名冲突）"""
    from datetime import datetime
    prefix = 'REC' + datetime.now().strftime('%Y%m%d')
    last = WarehouseReceipt.query.filter(
        WarehouseReceipt.receipt_no.like(f'{prefix}%')
    ).order_by(WarehouseReceipt.id.desc()).first()
    if last:
        seq = int(last.receipt_no[-4:]) + 1
    else:
        seq = 1
    return f'{prefix}{seq:04d}'
