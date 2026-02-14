from app.routes.auth import auth_bp
from app.routes.user import user_bp
from app.routes.config import config_bp
from app.routes.log import log_bp
from app.routes.cmdb import cmdb_bp
from app.routes.department import dept_bp
from app.routes.role import role_bp
from app.routes.ci_instance import ci_bp
from app.routes.cmdb_relation import cmdb_relation_bp

def register_routes(app):
    app.register_blueprint(auth_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(config_bp)
    app.register_blueprint(log_bp)
    app.register_blueprint(cmdb_bp)
    app.register_blueprint(dept_bp)
    app.register_blueprint(role_bp)
    app.register_blueprint(ci_bp)
    app.register_blueprint(cmdb_relation_bp)
