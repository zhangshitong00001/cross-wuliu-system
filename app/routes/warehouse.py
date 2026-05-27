"""
云仓集货管理 - 收货登记、库存管理、批次管理
"""
from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.models import WarehouseReceipt, WarehouseInventory, WarehouseBatch, WarehouseRecord, OperationLog
from app import db

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
