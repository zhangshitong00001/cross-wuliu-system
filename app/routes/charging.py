"""
计费规则可配置管理
"""
from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.models import ChargingRule, OperationLog
from app import db
from app.utils.excel_import import (
    ExcelImporter, FieldValidator, build_import_response,
    allowed_file, get_import_template, safe_str, safe_int
)

charging_bp = Blueprint('charging', __name__)


@charging_bp.route('/rules', methods=['GET'])
@login_required
def list_rules():
    """计费规则列表"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    query = ChargingRule.query.filter_by(is_deleted=0)
    
    rule_type = request.args.get('rule_type')
    if rule_type:
        query = query.filter_by(rule_type=rule_type)
    
    status = request.args.get('status')
    if status:
        query = query.filter_by(status=status)
    
    pagination = query.order_by(ChargingRule.priority.asc()).paginate(
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


@charging_bp.route('/rules', methods=['POST'])
@login_required
def create_rule():
    """创建计费规则"""
    data = request.get_json()
    rule = ChargingRule(
        rule_name=data['rule_name'],
        rule_type=data.get('rule_type'),
        calc_method=data.get('calc_method'),
        priority=data.get('priority', 0),
        rule_config=data.get('rule_config'),
        effective_date=datetime.strptime(data['effective_date'], '%Y-%m-%d') if data.get('effective_date') else None,
        expire_date=datetime.strptime(data['expire_date'], '%Y-%m-%d') if data.get('expire_date') else None
    )
    rule.save()
    return jsonify({'code': 200, 'message': '规则创建成功', 'data': rule.to_dict()})


@charging_bp.route('/rules/<int:rule_id>', methods=['PUT'])
@login_required
def update_rule(rule_id):
    """更新计费规则"""
    rule = ChargingRule.query.get_or_404(rule_id)
    data = request.get_json()
    
    for field in ['rule_name', 'rule_type', 'calc_method', 'priority', 'rule_config', 'status']:
        if field in data:
            setattr(rule, field, data[field])
    
    if data.get('effective_date'):
        rule.effective_date = datetime.strptime(data['effective_date'], '%Y-%m-%d')
    if data.get('expire_date'):
        rule.expire_date = datetime.strptime(data['expire_date'], '%Y-%m-%d')
    
    db.session.commit()
    return jsonify({'code': 200, 'message': '规则更新成功', 'data': rule.to_dict()})


@charging_bp.route('/rules/<int:rule_id>/toggle', methods=['POST'])
@login_required
def toggle_rule(rule_id):
    """启用/停用规则"""
    rule = ChargingRule.query.get_or_404(rule_id)
    rule.status = 'inactive' if rule.status == 'active' else 'active'
    db.session.commit()
    return jsonify({'code': 200, 'message': f'规则已{"启用" if rule.status == "active" else "停用"}'})


@charging_bp.route('/rules/<int:rule_id>', methods=['DELETE'])
@login_required
def delete_rule(rule_id):
    """删除计费规则"""
    rule = ChargingRule.query.get_or_404(rule_id)
    rule.is_deleted = 1
    db.session.commit()
    return jsonify({'code': 200, 'message': '规则删除成功'})


@charging_bp.route('/calculate', methods=['POST'])
@login_required
def calculate_fee():
    """试算费用"""
    data = request.get_json()
    weight = data.get('weight', 0)
    volume = data.get('volume', 0)
    quantity = data.get('quantity', 0)
    
    # 获取启用的规则
    rules = ChargingRule.query.filter_by(is_deleted=0, status='active').order_by(
        ChargingRule.priority.asc()).all()
    
    result = []
    total = 0
    
    for rule in rules:
        fee = 0
        if rule.calc_method == 'fixed':
            import json
            config = json.loads(rule.rule_config) if rule.rule_config else {}
            fee = config.get('amount', 0)
        elif rule.calc_method == 'by_weight':
            import json
            config = json.loads(rule.rule_config) if rule.rule_config else {}
            fee = weight * config.get('unit_price', 0)
        elif rule.calc_method == 'by_volume':
            import json
            config = json.loads(rule.rule_config) if rule.rule_config else {}
            fee = volume * config.get('unit_price', 0)
        elif rule.calc_method == 'by_quantity':
            import json
            config = json.loads(rule.rule_config) if rule.rule_config else {}
            fee = quantity * config.get('unit_price', 0)
        elif rule.calc_method == 'max_vol_weight':
            import json
            config = json.loads(rule.rule_config) if rule.rule_config else {}
            vol_weight = volume * config.get('vol_factor', 167)
            charged_weight = max(weight, vol_weight)
            fee = charged_weight * config.get('unit_price', 0)
        
        result.append({
            'rule_name': rule.rule_name,
            'rule_type': rule.rule_type,
            'calc_method': rule.calc_method,
            'fee': round(fee, 2)
        })
        total += fee

    return jsonify({
        'code': 200,
        'data': {
            'details': result,
            'total': round(total, 2)
        }
    })


# ===== Excel批量导入 =====

@charging_bp.route('/rules/import/template', methods=['GET'])
@login_required
def download_rule_template():
    """下载计费规则导入模板"""
    fields = [
        {'name': 'rule_name', 'display_name': '规则名称', 'required': True, 'example': '仓储费-标准'},
        {'name': 'rule_type', 'display_name': '费用类型', 'example': 'storage'},
        {'name': 'calc_method', 'display_name': '计算方式', 'example': 'by_weight'},
        {'name': 'priority', 'display_name': '优先级', 'example': '10'},
        {'name': 'rule_config', 'display_name': '规则配置(JSON)', 'example': '{"unit_price": 2.5}'},
        {'name': 'effective_date', 'display_name': '生效日期', 'example': '2026-06-01'},
        {'name': 'expire_date', 'display_name': '失效日期', 'example': '2027-06-01'},
        {'name': 'remark', 'display_name': '备注', 'example': ''},
    ]
    output = get_import_template(fields, sheet_name='计费规则导入')
    from flask import send_file
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='计费-规则导入模板.xlsx'
    )


@charging_bp.route('/rules/import', methods=['POST'])
@login_required
def import_rules():
    """批量导入计费规则"""
    if 'file' not in request.files:
        return jsonify({'code': 400, 'message': '请上传文件'})

    file = request.files['file']
    if file.filename == '' or not allowed_file(file.filename):
        return jsonify({'code': 400, 'message': '请上传有效的Excel文件（.xlsx或.xls）'})

    validators = [
        FieldValidator('rule_name', '规则名称', required=True),
        FieldValidator('rule_type', '费用类型'),
        FieldValidator('calc_method', '计算方式'),
        FieldValidator('priority', '优先级', field_type='int', min_value=0),
        FieldValidator('rule_config', '规则配置(JSON)'),
        FieldValidator('effective_date', '生效日期', field_type='date'),
        FieldValidator('expire_date', '失效日期', field_type='date'),
        FieldValidator('remark', '备注'),
    ]

    def process_func(row, row_index):
        rule = ChargingRule(
            rule_name=safe_str(row.get('rule_name')),
            rule_type=safe_str(row.get('rule_type')),
            calc_method=safe_str(row.get('calc_method')),
            priority=safe_int(row.get('priority'), 0),
            rule_config=safe_str(row.get('rule_config')),
            effective_date=safe_str(row.get('effective_date')),
            expire_date=safe_str(row.get('expire_date')),
            remark=safe_str(row.get('remark')),
            status='active'
        )
        rule.save()
        return True, None

    importer = ExcelImporter(file, validators=validators)
    result = importer.run(process_func)

    OperationLog(
        user_id=current_user.id, username=current_user.username,
        action='import', module='charging_rule',
        target_desc=f'批量导入计费规则: 成功{result["success"]}条, 失败{result["fail"]}条',
        ip_address=request.remote_addr
    ).save()

    return jsonify(build_import_response(result))
