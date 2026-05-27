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
    app = Flask(__name__)
    app.config.from_object(config.get(config_name, config['default']))
    config[config_name].init_app(app)

    # 初始化扩展
    db.init_app(app)
    login_manager.init_app(app)
    CORS(app)

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
                    # 刷新过期时间
                    from app.utils.redis_client import save_session_token
                    from config.config import Config
                    save_session_token(user_id, token, Config.SESSION_TIMEOUT)
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
    
    # 创建表
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
        
        # 初始化角色和权限
        _init_roles_and_permissions()
    
    return app


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
