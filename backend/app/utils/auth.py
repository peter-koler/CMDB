from functools import wraps
from flask import request, jsonify
import jwt
from app.models.user import User
from config import Config

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(" ")[1]
            except IndexError:
                return jsonify({'code': 401, 'message': 'Token format invalid'}), 401
        
        if not token:
            return jsonify({'code': 401, 'message': 'Token is missing'}), 401
        
        try:
            data = jwt.decode(token, Config.JWT_SECRET_KEY, algorithms=["HS256"])
            user_id = data.get('sub') or data.get('user_id')
            if not user_id:
                return jsonify({'code': 401, 'message': 'Invalid token'}), 401
            current_user = User.query.get(int(user_id))
            if not current_user:
                return jsonify({'code': 401, 'message': 'User not found'}), 401
            request.current_user = current_user
        except jwt.ExpiredSignatureError:
            return jsonify({'code': 401, 'message': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'code': 401, 'message': 'Token is invalid'}), 401
        
        return f(*args, **kwargs)
    
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not hasattr(request, 'current_user'):
            return jsonify({'code': 401, 'message': 'Authentication required'}), 401
        
        if not request.current_user.is_admin:
            return jsonify({'code': 403, 'message': 'Admin permission required'}), 403
        
        return f(*args, **kwargs)
    
    return decorated
