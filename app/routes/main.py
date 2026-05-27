"""
主路由 - 提供前端页面
"""
import os
from flask import Blueprint, send_file, jsonify

main_bp = Blueprint('main', __name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@main_bp.route('/')
def index():
    return send_file(os.path.join(BASE_DIR, 'static', 'index.html'))


@main_bp.route('/health')
def health():
    return jsonify({'status': 'ok', 'message': '跨境物流管理系统运行正常'})
