from functools import wraps
from flask import request, jsonify
from flask_jwt_extended import get_jwt_identity
from app.models.operation_log import OperationLog
from app.models import User


def admin_required(f):
    """要求管理员权限的装饰器"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = get_jwt_identity()
        user = User.query.get(int(user_id))

        if not user or not user.is_admin:
            return jsonify({"code": 403, "message": "需要管理员权限"}), 403

        return f(*args, **kwargs)

    return decorated_function


def log_operation(operation_type, operation_object):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            response = f(*args, **kwargs)

            try:
                if hasattr(request, "current_user"):
                    log = OperationLog(
                        user_id=request.current_user.id,
                        username=request.current_user.username,
                        operation_type=operation_type,
                        operation_object=operation_object,
                        operation_desc=f"{operation_type} {operation_object}",
                        ip_address=request.remote_addr,
                        status="success",
                    )
                    log.save()
            except Exception as e:
                print(f"Log operation failed: {e}")

            return response

        return decorated_function

    return decorator
