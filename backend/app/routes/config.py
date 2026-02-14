from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from app.models.config import SystemConfig
from app.models.user import User
from app.utils.decorators import log_operation

config_bp = Blueprint('config', __name__, url_prefix='/api/v1/configs')

CONFIG_DESCRIPTIONS = {
    'access_token_expire': 'Access Token有效期（分钟）',
    'refresh_token_expire': 'Refresh Token有效期（分钟）',
    'password_min_length': '密码最小长度',
    'password_force_change_days': '强制修改密码周期（天）',
    'password_history_count': '密码历史检查次数',
    'max_login_failures': '最大登录失败次数',
    'lock_duration_hours': '账户锁定时长（小时）',
    'log_retention_days': '日志保留天数',
    'require_uppercase': '密码需要大写字母',
    'require_lowercase': '密码需要小写字母',
    'require_digit': '密码需要数字',
    'require_special': '密码需要特殊字符'
}

def require_admin():
    claims = get_jwt()
    return claims.get('role') == 'admin'

@config_bp.route('', methods=['GET'])
@jwt_required()
def get_configs():
    configs = SystemConfig.query.all()
    data = {}
    for config in configs:
        desc = CONFIG_DESCRIPTIONS.get(config.config_key, '')
        data[config.config_key] = {
            'value': config.config_value,
            'description': desc
        }
    return jsonify({
        'code': 200,
        'data': data
    })

@config_bp.route('', methods=['PUT'])
@jwt_required()
def update_configs():
    if not require_admin():
        return jsonify({'code': 403, 'message': '无权限修改配置'}), 403
    
    identity = get_jwt_identity()
    claims = get_jwt()
    data = request.get_json()
    
    for key, value in data.items():
        if key in CONFIG_DESCRIPTIONS:
            SystemConfig.set_value(key, str(value), int(identity))
    
    log_operation(int(identity), claims.get('username'), 'UPDATE', 'config', None, '更新系统配置')
    
    return jsonify({
        'code': 200,
        'message': '配置更新成功'
    })
