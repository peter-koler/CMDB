from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt
from app import db
from app.models.operation_log import OperationLog
from app.models.config import SystemConfig
from datetime import datetime, timedelta

log_bp = Blueprint('log', __name__, url_prefix='/api/v1/logs')

def require_admin():
    claims = get_jwt()
    return claims.get('role') == 'admin'

@log_bp.route('', methods=['GET'])
@jwt_required()
def get_logs():
    if not require_admin():
        return jsonify({'code': 403, 'message': '无权限查看日志'}), 403
    
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    user_id = request.args.get('user_id', type=int)
    operation_type = request.args.get('operation_type')
    status = request.args.get('status')
    
    query = OperationLog.query
    
    if date_from:
        query = query.filter(OperationLog.created_at >= datetime.fromisoformat(date_from))
    if date_to:
        query = query.filter(OperationLog.created_at <= datetime.fromisoformat(date_to))
    if user_id:
        query = query.filter(OperationLog.user_id == user_id)
    if operation_type:
        query = query.filter(OperationLog.operation_type == operation_type)
    if status:
        query = query.filter(OperationLog.status == status)
    
    query = query.order_by(OperationLog.created_at.desc())
    
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'code': 200,
        'data': {
            'items': [log.to_dict() for log in pagination.items],
            'total': pagination.total,
            'page': page,
            'per_page': per_page,
            'total_pages': pagination.pages
        }
    })

@log_bp.route('/export', methods=['GET'])
@jwt_required()
def export_logs():
    if not require_admin():
        return jsonify({'code': 403, 'message': '无权限导出日志'}), 403
    
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    operation_type = request.args.get('operation_type')
    status = request.args.get('status')
    
    query = OperationLog.query
    
    if date_from:
        query = query.filter(OperationLog.created_at >= datetime.fromisoformat(date_from))
    if date_to:
        query = query.filter(OperationLog.created_at <= datetime.fromisoformat(date_to))
    if operation_type:
        query = query.filter(OperationLog.operation_type == operation_type)
    if status:
        query = query.filter(OperationLog.status == status)
    
    logs = query.order_by(OperationLog.created_at.desc()).all()
    
    csv_data = 'ID,用户名,操作类型,操作对象,操作描述,IP地址,状态,时间\n'
    for log in logs:
        csv_data += f'{log.id},{log.username},{log.operation_type},{log.operation_object},"{log.operation_desc}",{log.ip_address},{log.status},{log.created_at}\n'
    
    return jsonify({
        'code': 200,
        'message': '导出成功',
        'data': {
            'csv': csv_data
        }
    })

@log_bp.route('/clean', methods=['POST'])
@jwt_required()
def clean_logs():
    if not require_admin():
        return jsonify({'code': 403, 'message': '无权限清理日志'}), 403
    
    retention_days = int(SystemConfig.get_value('log_retention_days', '30'))
    cutoff_date = datetime.now() - timedelta(days=retention_days)
    
    deleted = OperationLog.query.filter(OperationLog.created_at < cutoff_date).delete()
    db.session.commit()
    
    return jsonify({
        'code': 200,
        'message': f'已清理 {deleted} 条日志'
    })
