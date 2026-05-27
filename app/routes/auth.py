"""
认证管理 - 登录、登出、用户管理
"""
from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from app.models import User, Role, OperationLog
from app import db

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['POST'])
def login():
    """用户登录"""
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'code': 400, 'message': '请输入用户名和密码'})
    
    user = User.query.filter_by(username=username, is_deleted=0).first()
    if not user or not user.check_password(password):
        return jsonify({'code': 401, 'message': '用户名或密码错误'})
    
    if user.status == 0:
        return jsonify({'code': 403, 'message': '账号已被禁用'})
    
    login_user(user, remember=data.get('remember', False))
    user.last_login_at = datetime.now()
    user.last_login_ip = request.remote_addr
    db.session.commit()
    
    # 记录日志
    OperationLog(
        user_id=user.id, username=user.username,
        action='login', module='auth',
        ip_address=request.remote_addr
    ).save()
    
    return jsonify({
        'code': 200,
        'message': '登录成功',
        'data': user.to_dict()
    })


@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    """用户登出"""
    OperationLog(
        user_id=current_user.id, username=current_user.username,
        action='logout', module='auth',
        ip_address=request.remote_addr
    ).save()
    logout_user()
    return jsonify({'code': 200, 'message': '已退出登录'})


@auth_bp.route('/profile', methods=['GET'])
@login_required
def profile():
    """获取当前用户信息"""
    return jsonify({'code': 200, 'data': current_user.to_dict()})


@auth_bp.route('/users', methods=['GET'])
@login_required
def list_users():
    """用户列表"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    query = User.query.filter_by(is_deleted=0)
    
    role_id = request.args.get('role_id', type=int)
    if role_id:
        query = query.filter_by(role_id=role_id)
    
    keyword = request.args.get('keyword')
    if keyword:
        query = query.filter(
            (User.username.like(f'%{keyword}%')) |
            (User.real_name.like(f'%{keyword}%')) |
            (User.phone.like(f'%{keyword}%'))
        )
    
    pagination = query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        'code': 200,
        'data': {
            'items': [u.to_dict() for u in pagination.items],
            'total': pagination.total,
            'page': page,
            'pages': pagination.pages
        }
    })


@auth_bp.route('/users', methods=['POST'])
@login_required
def create_user():
    """创建用户"""
    data = request.get_json()
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'code': 400, 'message': '用户名已存在'})
    
    user = User(
        username=data['username'],
        real_name=data.get('real_name'),
        email=data.get('email'),
        phone=data.get('phone'),
        role_id=data.get('role_id')
    )
    user.set_password(data.get('password', '123456'))
    user.save()
    
    OperationLog(
        user_id=current_user.id, username=current_user.username,
        action='create', module='user', target_id=user.id,
        target_desc=f'创建用户: {user.username}',
        ip_address=request.remote_addr
    ).save()
    
    return jsonify({'code': 200, 'message': '创建成功', 'data': user.to_dict()})


@auth_bp.route('/users/<int:user_id>', methods=['PUT'])
@login_required
def update_user(user_id):
    """更新用户"""
    user = User.query.get_or_404(user_id)
    data = request.get_json()
    
    for field in ['real_name', 'email', 'phone', 'role_id', 'status']:
        if field in data:
            setattr(user, field, data[field])
    
    if 'password' in data and data['password']:
        user.set_password(data['password'])
    
    db.session.commit()
    return jsonify({'code': 200, 'message': '更新成功', 'data': user.to_dict()})


@auth_bp.route('/roles', methods=['GET'])
@login_required
def list_roles():
    """角色列表"""
    roles = Role.query.filter_by(is_deleted=0).all()
    return jsonify({'code': 200, 'data': [r.to_dict() for r in roles]})
