"""
认证管理 - 登录、登出、用户管理（支持Redis Session + 图片验证码）
"""
import uuid
import io
import base64
from datetime import datetime
from flask import Blueprint, request, jsonify, session
from flask_login import login_user, logout_user, login_required, current_user
from captcha.image import ImageCaptcha
from app.models import User, Role, OperationLog
from app import db
from app.utils.redis_client import (
    save_captcha, verify_captcha,
    save_session_token, get_session_user, delete_session,
    incr_login_fail, get_login_fail_count, reset_login_fail
)
from config.config import Config

auth_bp = Blueprint('auth', __name__)


def _get_user_detail(user):
    """获取用户详细信息（含角色名）"""
    data = user.to_dict()
    if user.role:
        data['role_name'] = user.role.name
        data['role_code'] = user.role.code
    else:
        data['role_name'] = '无角色'
        data['role_code'] = ''
    return data


@auth_bp.route('/captcha', methods=['GET'])
def get_captcha():
    """获取图片验证码"""
    code_id = str(uuid.uuid4()).replace('-', '')[:16]

    # 生成4位数字验证码
    import random
    code = ''.join([str(random.randint(0, 9)) for _ in range(4)])

    # 保存到Redis
    save_captcha(code_id, code, Config.CAPTCHA_EXPIRE)

    # 生成图片
    image = ImageCaptcha(width=130, height=44, font_sizes=(36,))
    data = image.generate(code)
    img_base64 = base64.b64encode(data.getvalue()).decode('utf-8')

    return jsonify({
        'code': 200,
        'data': {
            'code_id': code_id,
            'image': f'data:image/png;base64,{img_base64}'
        }
    })


@auth_bp.route('/login', methods=['POST'])
def login():
    """用户登录（支持验证码）"""
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '')
    code_id = data.get('code_id', '')
    captcha_code = data.get('captcha_code', '')
    remember = data.get('remember', False)

    if not username or not password:
        return jsonify({'code': 400, 'message': '请输入用户名和密码'})

    ip = request.remote_addr or 'unknown'
    fail_count = get_login_fail_count(ip)

    # 失败超过限制，必须验证验证码
    if fail_count >= Config.LOGIN_FAIL_LIMIT:
        if not code_id or not captcha_code:
            return jsonify({
                'code': 402,
                'message': f'登录失败次数过多，请输入验证码',
                'need_captcha': True,
                'fail_count': fail_count
            })
        if not verify_captcha(code_id, captcha_code):
            return jsonify({
                'code': 402,
                'message': '验证码错误',
                'need_captcha': True,
                'fail_count': fail_count
            })

    user = User.query.filter_by(username=username, is_deleted=0).first()
    if not user or not user.check_password(password):
        fail_count = incr_login_fail(ip)
        msg = '用户名或密码错误'
        need_captcha = fail_count >= Config.LOGIN_FAIL_LIMIT
        return jsonify({
            'code': 401,
            'message': msg,
            'need_captcha': need_captcha,
            'fail_count': fail_count
        })

    if user.status == 0:
        return jsonify({'code': 403, 'message': '账号已被禁用'})

    # 登录成功，重置失败计数
    reset_login_fail(ip)

    # 生成token并保存到Redis
    token = str(uuid.uuid4()).replace('-', '')
    timeout = Config.SESSION_TIMEOUT
    save_session_token(user.id, token, timeout)

    # 更新用户登录信息
    user.last_login_at = datetime.now()
    user.last_login_ip = ip
    db.session.commit()

    # 记录日志
    OperationLog(
        user_id=user.id, username=user.username,
        action='login', module='auth',
        ip_address=ip
    ).save()

    return jsonify({
        'code': 200,
        'message': '登录成功',
        'data': {
            **user.to_dict(),
            'token': token,
            'role_name': user.role.name if user.role else '管理员',
            'role_code': user.role.code if user.role else '',
        }
    })


@auth_bp.route('/logout', methods=['POST'])
def logout():
    """用户登出"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '') or \
            request.get_json(silent=True) or {}
    if isinstance(token, dict):
        token = token.get('token', '')

    if token:
        user_id = get_session_user(token)
        if user_id:
            user = User.query.get(user_id)
            if user:
                OperationLog(
                    user_id=user.id, username=user.username,
                    action='logout', module='auth',
                    ip_address=request.remote_addr
                ).save()
        delete_session(token)

    return jsonify({'code': 200, 'message': '已退出登录'})


@auth_bp.route('/profile', methods=['GET'])
def profile():
    """获取当前用户信息（通过token）"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '') or \
            request.args.get('token', '')

    if not token:
        return jsonify({'code': 401, 'message': '未登录'})

    user_id = get_session_user(token)
    if not user_id:
        return jsonify({'code': 401, 'message': '登录已过期，请重新登录'})

    user = User.query.get(user_id)
    if not user or user.status == 0:
        return jsonify({'code': 401, 'message': '用户不存在或已被禁用'})

    return jsonify({'code': 200, 'data': _get_user_detail(user)})


@auth_bp.route('/check', methods=['GET'])
def check_login():
    """检查登录状态"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '') or \
            request.args.get('token', '')

    if not token:
        return jsonify({'code': 401, 'message': '未登录', 'logged_in': False})

    user_id = get_session_user(token)
    if not user_id:
        return jsonify({'code': 401, 'message': '登录已过期', 'logged_in': False})

    # 刷新过期时间
    save_session_token(user_id, token, Config.SESSION_TIMEOUT)

    user = User.query.get(user_id)
    if not user or user.status == 0:
        return jsonify({'code': 401, 'message': '用户异常', 'logged_in': False})

    return jsonify({
        'code': 200,
        'message': '已登录',
        'logged_in': True,
        'data': _get_user_detail(user)
    })


# ===== 用户管理 =====

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
            (User.username.ilike(f'%{keyword}%')) |
            (User.real_name.ilike(f'%{keyword}%')) |
            (User.phone.ilike(f'%{keyword}%'))
        )

    pagination = query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return jsonify({
        'code': 200,
        'data': {
            'items': [_get_user_detail(u) for u in pagination.items],
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

    if not data.get('username'):
        return jsonify({'code': 400, 'message': '用户名不能为空'})

    if User.query.filter_by(username=data['username']).first():
        return jsonify({'code': 400, 'message': '用户名已存在'})

    user = User(
        username=data['username'],
        real_name=data.get('real_name', ''),
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

    return jsonify({'code': 200, 'message': '创建成功', 'data': _get_user_detail(user)})


@auth_bp.route('/users/<int:user_id>', methods=['GET'])
@login_required
def get_user(user_id):
    """获取用户详情"""
    user = User.query.get_or_404(user_id)
    return jsonify({'code': 200, 'data': _get_user_detail(user)})


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

    OperationLog(
        user_id=current_user.id, username=current_user.username,
        action='update', module='user', target_id=user.id,
        target_desc=f'更新用户: {user.username}',
        ip_address=request.remote_addr
    ).save()

    return jsonify({'code': 200, 'message': '更新成功', 'data': _get_user_detail(user)})


@auth_bp.route('/users/<int:user_id>', methods=['DELETE'])
@login_required
def delete_user(user_id):
    """删除用户"""
    user = User.query.get_or_404(user_id)
    username = user.username
    user.is_deleted = 1
    db.session.commit()

    OperationLog(
        user_id=current_user.id, username=current_user.username,
        action='delete', module='user', target_id=user.id,
        target_desc=f'删除用户: {username}',
        ip_address=request.remote_addr
    ).save()

    return jsonify({'code': 200, 'message': '删除成功'})


@auth_bp.route('/roles', methods=['GET'])
@login_required
def list_roles():
    """角色列表"""
    roles = Role.query.filter_by(is_deleted=0).all()
    return jsonify({'code': 200, 'data': [r.to_dict() for r in roles]})

