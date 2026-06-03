"""
跨境物流管理系统 - 应用工厂
"""
from flask import Flask
from flask_login import LoginManager
from flask_cors import CORS
from config.config import config
from app.models.base import db

login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = '请先登录系统'


def create_app(config_name='default'):
    import os
    app = Flask(__name__,
                static_folder=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'static'),
                static_url_path='/static')
    app.config.from_object(config.get(config_name, config['default']))
    config[config_name].init_app(app)

    # 初始化扩展
    db.init_app(app)
    login_manager.init_app(app)
    CORS(app, expose_headers=['Content-Disposition', 'Content-Type'])

    # 设置 user_loader
    from app.models import User
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # 添加before_request钩子，支持Token认证
    from app.utils.redis_client import get_session_user
    from flask_login import login_user

    @app.before_request
    def load_user_from_token():
        """如果请求携带token，自动登录"""
        from flask import request
        # 跳过静态文件和健康检查
        if request.path in ['/health', '/'] or request.path.startswith('/static/'):
            return

        # 尝试从请求中获取token
        token = None
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]
        if not token:
            token = request.args.get('token')
        if not token and request.is_json:
            try:
                data = request.get_json(silent=True)
                if data:
                    token = data.get('token')
            except:
                pass

        if token:
            user_id = get_session_user(token)
            if user_id:
                user = User.query.get(user_id)
                if user and user.status == 1:
                    # 刷新过期时间（10分钟无操作过期）
                    from app.utils.redis_client import refresh_session
                    from config.config import Config
                    refresh_session(token, Config.SESSION_TIMEOUT)
                    login_user(user)

    # 注册蓝图
    from app.routes.auth import auth_bp
    from app.routes.warehouse import warehouse_bp
    from app.routes.sorting import sorting_bp
    from app.routes.document import document_bp
    from app.routes.transport import transport_bp
    from app.routes.customs import customs_bp
    from app.routes.clearance import clearance_bp
    from app.routes.port_transport import port_transport_bp
    from app.routes.distribution import distribution_bp
    from app.routes.sign import sign_bp
    from app.routes.reconciliation import reconciliation_bp
    from app.routes.settlement import settlement_bp
    from app.routes.payment import payment_bp
    from app.routes.tracking import tracking_bp
    from app.routes.permission import permission_bp
    from app.routes.statistics import statistics_bp
    from app.routes.alert import alert_bp
    from app.routes.charging import charging_bp
    from app.routes.main import main_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(warehouse_bp, url_prefix='/api/warehouse')
    app.register_blueprint(sorting_bp, url_prefix='/api/sorting')
    app.register_blueprint(document_bp, url_prefix='/api/document')
    app.register_blueprint(transport_bp, url_prefix='/api/transport')
    app.register_blueprint(customs_bp, url_prefix='/api/customs')
    app.register_blueprint(clearance_bp, url_prefix='/api/clearance')
    app.register_blueprint(port_transport_bp, url_prefix='/api/port-transport')
    app.register_blueprint(distribution_bp, url_prefix='/api/distribution')
    app.register_blueprint(sign_bp, url_prefix='/api/sign')
    app.register_blueprint(reconciliation_bp, url_prefix='/api/reconciliation')
    app.register_blueprint(settlement_bp, url_prefix='/api/settlement')
    app.register_blueprint(payment_bp, url_prefix='/api/payment')
    app.register_blueprint(tracking_bp, url_prefix='/api/tracking')
    app.register_blueprint(permission_bp, url_prefix='/api/permission')
    app.register_blueprint(statistics_bp, url_prefix='/api/statistics')
    app.register_blueprint(alert_bp, url_prefix='/api/alert')
    app.register_blueprint(charging_bp, url_prefix='/api/charging')

    # 注册一个 before_request 钩子：首次请求时初始化数据库
    _init_db_on_first_request(app)

    return app


def _init_db_on_first_request(app):
    """在首次请求时初始化数据库表（避免启动时因数据库不可用而崩溃）"""
    initialized = [False]

    @app.before_request
    def init_db_once():
        if initialized[0]:
            return
        try:
            with app.app_context():
                from app.models import (User, Role, Permission,
                                        WarehouseReceipt, WarehouseInventory, WarehouseBatch,
                                        CollectionPoint, SortingTask, SortingRecord,
                                        Document, DocumentVersion,
                                        Vehicle, TransportTask, TransportNode,
                                        CustomsDeclaration, ClearanceRecord,
                                        DistributionTask, DistributionRecord,
                                        SignRecord, SignCertificate,
                                        ReconciliationRecord, ReconciliationDetail,
                                        SettlementOrder, SettlementFlow,
                                        PaymentRecord, InvoiceRecord,
                                        TrackingRecord, AlertRecord,
                                        ChargingRule, OperationLog)
                db.create_all()
                _init_roles_and_permissions()
            initialized[0] = True
        except Exception as e:
            app.logger.warning(f'数据库初始化失败（将在下次请求时重试）: {e}')


def _init_roles_and_permissions():
    """初始化默认角色和权限"""
    from app.models import Role, Permission

    roles = {
        'super_admin': '甲方超级管理员',
        'admin': '运营管理员',
        'finance': '财务人员',
        'warehouse_op': '仓库操作员',
        'transport': '运输人员',
        'customs_broker': '报关专员',
        'sorting_op': '分装人员',
        'point_admin': '收件点管理员',
        'customer': '客户'
    }

    for code, name in roles.items():
        if not Role.query.filter_by(code=code).first():
            Role(code=code, name=name).save()

    # 初始化权限
    permissions_data = [
        # 仓储管理
        {'code': 'warehouse_receipt_create', 'name': '创建收货登记', 'module': 'warehouse'},
        {'code': 'warehouse_receipt_view', 'name': '查看收货登记', 'module': 'warehouse'},
        {'code': 'warehouse_receipt_update', 'name': '修改收货登记', 'module': 'warehouse'},
        {'code': 'warehouse_receipt_delete', 'name': '删除收货登记', 'module': 'warehouse'},
        {'code': 'warehouse_receipt_confirm', 'name': '确认收货', 'module': 'warehouse'},
        {'code': 'warehouse_inventory_view', 'name': '查看库存', 'module': 'warehouse'},
        {'code': 'warehouse_inventory_update', 'name': '调整库存', 'module': 'warehouse'},
        {'code': 'warehouse_batch_create', 'name': '创建批次', 'module': 'warehouse'},
        {'code': 'warehouse_batch_view', 'name': '查看批次', 'module': 'warehouse'},
        # 分装管理
        {'code': 'sorting_point_create', 'name': '创建收件点', 'module': 'sorting'},
        {'code': 'sorting_point_view', 'name': '查看收件点', 'module': 'sorting'},
        {'code': 'sorting_point_update', 'name': '修改收件点', 'module': 'sorting'},
        {'code': 'sorting_point_delete', 'name': '删除收件点', 'module': 'sorting'},
        {'code': 'sorting_task_create', 'name': '创建分装任务', 'module': 'sorting'},
        {'code': 'sorting_task_view', 'name': '查看分装任务', 'module': 'sorting'},
        {'code': 'sorting_task_complete', 'name': '完成分装', 'module': 'sorting'},
        # 文件管理
        {'code': 'document_create', 'name': '创建文件', 'module': 'document'},
        {'code': 'document_view', 'name': '查看文件', 'module': 'document'},
        {'code': 'document_update', 'name': '修改文件', 'module': 'document'},
        {'code': 'document_delete', 'name': '删除文件', 'module': 'document'},
        {'code': 'document_export', 'name': '导出文件', 'module': 'document'},
        # 运输管理
        {'code': 'transport_task_create', 'name': '创建运输任务', 'module': 'transport'},
        {'code': 'transport_task_view', 'name': '查看运输任务', 'module': 'transport'},
        {'code': 'transport_task_update', 'name': '修改运输任务', 'module': 'transport'},
        {'code': 'transport_task_start', 'name': '开始运输', 'module': 'transport'},
        {'code': 'transport_vehicle_create', 'name': '创建车辆', 'module': 'transport'},
        {'code': 'transport_vehicle_view', 'name': '查看车辆', 'module': 'transport'},
        {'code': 'transport_driver_create', 'name': '创建司机', 'module': 'transport'},
        {'code': 'transport_driver_view', 'name': '查看司机', 'module': 'transport'},
        # 报关清关
        {'code': 'customs_create', 'name': '创建报关单', 'module': 'customs'},
        {'code': 'customs_view', 'name': '查看报关单', 'module': 'customs'},
        {'code': 'customs_review', 'name': '审核报关单', 'module': 'customs'},
        {'code': 'clearance_create', 'name': '创建清关记录', 'module': 'clearance'},
        {'code': 'clearance_view', 'name': '查看清关记录', 'module': 'clearance'},
        {'code': 'clearance_clear', 'name': '完成清关', 'module': 'clearance'},
        # 配送管理
        {'code': 'distribution_task_create', 'name': '创建配送任务', 'module': 'distribution'},
        {'code': 'distribution_task_view', 'name': '查看配送任务', 'module': 'distribution'},
        {'code': 'distribution_task_start', 'name': '开始配送', 'module': 'distribution'},
        # 签收管理
        {'code': 'sign_create', 'name': '创建签收记录', 'module': 'sign'},
        {'code': 'sign_view', 'name': '查看签收记录', 'module': 'sign'},
        {'code': 'sign_store', 'name': '签收入库', 'module': 'sign'},
        # 财务
        {'code': 'reconciliation_create', 'name': '创建对账', 'module': 'finance'},
        {'code': 'reconciliation_view', 'name': '查看对账', 'module': 'finance'},
        {'code': 'reconciliation_confirm', 'name': '确认对账', 'module': 'finance'},
        {'code': 'settlement_create', 'name': '创建结算单', 'module': 'finance'},
        {'code': 'settlement_view', 'name': '查看结算单', 'module': 'finance'},
        {'code': 'settlement_audit', 'name': '审核结算单', 'module': 'finance'},
        {'code': 'payment_create', 'name': '创建支付', 'module': 'finance'},
        {'code': 'payment_view', 'name': '查看支付', 'module': 'finance'},
        # 系统管理
        {'code': 'user_create', 'name': '创建用户', 'module': 'system'},
        {'code': 'user_view', 'name': '查看用户', 'module': 'system'},
        {'code': 'user_update', 'name': '修改用户', 'module': 'system'},
        {'code': 'user_delete', 'name': '删除用户', 'module': 'system'},
        {'code': 'role_manage', 'name': '管理角色', 'module': 'system'},
        {'code': 'log_view', 'name': '查看日志', 'module': 'system'},
        {'code': 'statistics_view', 'name': '查看统计', 'module': 'system'},
        {'code': 'alert_view', 'name': '查看预警', 'module': 'system'},
        {'code': 'alert_resolve', 'name': '处理预警', 'module': 'system'},
        {'code': 'charging_manage', 'name': '管理计费规则', 'module': 'system'},
        {'code': 'tracking_view', 'name': '查看物流跟踪', 'module': 'system'},
    ]

    for p_data in permissions_data:
        if not Permission.query.filter_by(code=p_data['code']).first():
            Permission(**p_data).save()
