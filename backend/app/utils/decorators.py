from functools import wraps
from flask import request
from app.models.operation_log import OperationLog

def log_operation(operation_type, operation_object):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            response = f(*args, **kwargs)
            
            try:
                if hasattr(request, 'current_user'):
                    log = OperationLog(
                        user_id=request.current_user.id,
                        username=request.current_user.username,
                        operation_type=operation_type,
                        operation_object=operation_object,
                        operation_desc=f'{operation_type} {operation_object}',
                        ip_address=request.remote_addr,
                        status='success'
                    )
                    log.save()
            except Exception as e:
                print(f"Log operation failed: {e}")
            
            return response
        return decorated_function
    return decorator
