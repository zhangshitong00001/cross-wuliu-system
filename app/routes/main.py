"""
主路由 - 提供前端页面
"""
import os
import csv
import io
from datetime import datetime
from flask import Blueprint, send_file, jsonify, request, make_response, Response
from flask_login import login_required

main_bp = Blueprint('main', __name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@main_bp.route('/')
def index():
    response = send_file(os.path.join(BASE_DIR, 'static', 'index.html'))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


@main_bp.route('/health')
def health():
    return jsonify({'status': 'ok', 'message': '跨境物流管理系统运行正常'})


@main_bp.route('/api/lang', methods=['GET', 'POST'])
def language():
    """
    国际化语言设置接口
    GET: 获取当前语言设置
    POST: 设置语言 (zh/en)
    """
    if request.method == 'GET':
        lang = request.cookies.get('lang', 'zh')
        return jsonify({'code': 200, 'data': {'lang': lang}})

    data = request.get_json(silent=True) or {}
    lang = data.get('lang', 'zh')
    if lang not in ('zh', 'en'):
        lang = 'zh'

    resp = make_response(jsonify({'code': 200, 'data': {'lang': lang}}))
    resp.set_cookie('lang', lang, max_age=365*24*3600)  # 保存1年
    return resp


# ===== 服务端导出：API路径 → 模型映射 =====
EXPORT_MODEL_MAP = None


def _get_export_model_map():
    """延迟加载模型映射，避免循环导入"""
    global EXPORT_MODEL_MAP
    if EXPORT_MODEL_MAP is not None:
        return EXPORT_MODEL_MAP
    from app.models import (
        WarehouseReceipt, WarehouseInventory, WarehouseBatch, WarehouseRecord,
        CollectionPoint, SortingTask, SortingRecord,
        Document,
        Vehicle, Driver, TransportTask, TransportNode,
        CustomsDeclaration,
        ClearanceRecord,
        PortTransportTask,
        DistributionTask,
        SignRecord,
        ReconciliationRecord,
        SettlementOrder,
        PaymentRecord,
        TrackingRecord,
        AlertRecord,
        ChargingRule,
        User, OperationLog
    )
    EXPORT_MODEL_MAP = {
        '/api/warehouse/receipts': WarehouseReceipt,
        '/api/warehouse/inventory': WarehouseInventory,
        '/api/warehouse/batches': WarehouseBatch,
        '/api/sorting/points': CollectionPoint,
        '/api/sorting/tasks': SortingTask,
        '/api/document/list': Document,
        '/api/transport/tasks': TransportTask,
        '/api/transport/vehicles': Vehicle,
        '/api/transport/drivers': Driver,
        '/api/customs/declarations': CustomsDeclaration,
        '/api/clearance/records': ClearanceRecord,
        '/api/port-transport/tasks': PortTransportTask,
        '/api/distribution/tasks': DistributionTask,
        '/api/sign/records': SignRecord,
        '/api/reconciliation/records': ReconciliationRecord,
        '/api/settlement/orders': SettlementOrder,
        '/api/payment/records': PaymentRecord,
        '/api/tracking/list': TrackingRecord,
        '/api/alert/list': AlertRecord,
        '/api/charging/rules': ChargingRule,
        '/api/auth/users': User,
        '/api/permission/logs': OperationLog,
    }
    return EXPORT_MODEL_MAP


# 内部字段，导出时自动排除
EXPORT_EXCLUDE_FIELDS = {
    'id', 'is_deleted', 'password_hash', '_sa_instance_state',
    'created_by', 'updated_by', 'handler_id', 'confirmed_by',
    'resolved_by', 'audited_by', 'reviewed_by', 'assigned_to',
    'creator_id', 'operator_id', 'driver_id', 'vehicle_id',
}


def _apply_filters(query, model, params):
    """根据前端传入的参数对查询应用过滤条件"""
    # 通用关键字搜索（对常见文本列做 ilike）
    keyword = params.get('keyword', '').strip()
    if keyword:
        from sqlalchemy import or_
        text_columns = []
        for col in model.__table__.columns:
            col_type = str(col.type).upper()
            if 'VARCHAR' in col_type or 'TEXT' in col_type:
                text_columns.append(col.ilike(f'%{keyword}%'))
        if text_columns:
            query = query.filter(or_(*text_columns))

    # status 过滤
    status = params.get('status', '').strip()
    if status:
        if hasattr(model, 'status'):
            query = query.filter(model.status == status)

    # 各模块特有过滤条件
    for key, value in params.items():
        if key in ('keyword', 'status', 'page', 'per_page', 'format') or not value:
            continue
        if hasattr(model, key):
            query = query.filter(getattr(model, key) == value)

    return query


def _model_to_export_rows(query, model):
    """将查询结果转为导出用的字典列表，自动排除内部字段"""
    rows = []
    records = query.filter(model.is_deleted == 0).all()
    for rec in records:
        row = {}
        try:
            d = rec.to_dict() if hasattr(rec, 'to_dict') else {}
        except Exception:
            d = {}
        for k, v in d.items():
            if k in EXPORT_EXCLUDE_FIELDS:
                continue
            # 处理值
            if v is None:
                row[k] = ''
            elif isinstance(v, (dict, list)):
                import json
                row[k] = json.dumps(v, ensure_ascii=False, default=str)
            else:
                row[k] = v
        rows.append(row)
    return rows


@main_bp.route('/api/export', methods=['POST'])
@login_required
def export_data():
    """
    通用数据导出接口（服务端查询）
    请求体: {
        "source_api": "/api/warehouse/receipts",   # 数据源API路径
        "params": {"keyword": "...", "status": "..."},  # 查询过滤参数
        "format": "csv|json"                        # 导出格式
    }
    也兼容旧版格式: { "data": [...], "filename": "...", "format": "..." }
    """
    req_data = request.get_json(silent=True) or {}

    # 兼容旧版：前端直接传 data 数组
    if 'data' in req_data and isinstance(req_data['data'], list):
        rows = req_data['data']
        filename = req_data.get('filename', 'export')
        export_format = req_data.get('format', 'csv')

        if not rows:
            return jsonify({'code': 400, 'message': '没有可导出的数据'})

        if export_format == 'json':
            from app.services import export_to_json
            content, fname = export_to_json(rows, filename)
            return Response(
                content,
                mimetype='application/json',
                headers={'Content-Disposition': f'attachment; filename={fname}'}
            )
        else:
            from app.services import export_to_csv
            content, fname = export_to_csv(rows, filename)
            return Response(
                content,
                mimetype='text/csv',
                headers={'Content-Disposition': f'attachment; filename={fname}'}
            )

    # 新版：服务端查询导出
    source_api = req_data.get('source_api', '').strip()
    params = req_data.get('params') or {}
    export_format = req_data.get('format', 'csv')

    if not source_api:
        return jsonify({'code': 400, 'message': '请指定导出数据源 (source_api)'})

    model_map = _get_export_model_map()
    model = model_map.get(source_api)
    if not model:
        return jsonify({'code': 400, 'message': f'不支持的数据源: {source_api}'})

    try:
        query = model.query
        query = _apply_filters(query, model, params)
        rows = _model_to_export_rows(query, model)

        if not rows:
            return jsonify({'code': 400, 'message': '没有符合条件的数据可导出'})

        # 生成文件名
        filename = source_api.strip('/').replace('/', '-')
        if export_format == 'json':
            from app.services import export_to_json
            content, fname = export_to_json(rows, filename)
            return Response(
                content,
                mimetype='application/json',
                headers={'Content-Disposition': f'attachment; filename={fname}'}
            )
        else:
            from app.services import export_to_csv
            content, fname = export_to_csv(rows, filename)
            return Response(
                content,
                mimetype='text/csv',
                headers={'Content-Disposition': f'attachment; filename={fname}'}
            )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'code': 500, 'message': f'导出失败: {str(e)}'})
