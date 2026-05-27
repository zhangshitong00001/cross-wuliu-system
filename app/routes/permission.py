"""
权限管理
"""
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.models import Role, Permission, OperationLog
from app import db

permission_bp = Blueprint('permission', __name__)


@permission_bp.route('/roles', methods=['GET'])
@login_required
def list_roles():
    """角色列表"""
    roles = Role.query.filter_by(is_deleted=0).all()
    result = []
    for r in roles:
        d = r.to_dict()
        d['permissions'] = [p.to_dict() for p in r.permissions] if r.permissions else []
        result.append(d)
    return jsonify({'code': 200, 'data': result})


@permission_bp.route('/roles', methods=['POST'])
@login_required
def create_role():
    """创建角色"""
    data = request.get_json()
    role = Role(code=data['code'], name=data['name'], description=data.get('description'))
    role.save()
    return jsonify({'code': 200, 'message': '角色创建成功', 'data': role.to_dict()})


@permission_bp.route('/roles/<int:role_id>/permissions', methods=['PUT'])
@login_required
def assign_permissions(role_id):
    """分配权限"""
    role = Role.query.get_or_404(role_id)
    data = request.get_json()
    permission_ids = data.get('permission_ids', [])
    
    permissions = Permission.query.filter(Permission.id.in_(permission_ids)).all()
    role.permissions = permissions
    db.session.commit()
    
    OperationLog(
        user_id=current_user.id, username=current_user.username,
        action='update', module='permission',
        target_id=role_id, target_desc=f'更新角色权限: {role.name}',
        ip_address=request.remote_addr
    ).save()
    
    return jsonify({'code': 200, 'message': '权限分配成功'})


@permission_bp.route('/permissions', methods=['GET'])
@login_required
def list_permissions():
    """权限列表"""
    permissions = Permission.query.filter_by(is_deleted=0).all()
    return jsonify({'code': 200, 'data': [p.to_dict() for p in permissions]})


@permission_bp.route('/logs', methods=['GET'])
@login_required
def list_logs():
    """操作日志"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    query = OperationLog.query.filter_by(is_deleted=0)
    
    module = request.args.get('module')
    if module:
        query = query.filter_by(module=module)
    
    action = request.args.get('action')
    if action:
        query = query.filter_by(action=action)
    
    pagination = query.order_by(OperationLog.operation_time.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        'code': 200,
        'data': {
            'items': [l.to_dict() for l in pagination.items],
            'total': pagination.total,
            'page': page,
            'pages': pagination.pages
        }
    })
