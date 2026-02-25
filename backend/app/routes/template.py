from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app.services.template_service import template_service

template_bp = Blueprint("template", __name__, url_prefix="/api/v1/monitoring/templates")


@template_bp.route("", methods=["GET"])
@jwt_required()
def get_templates():
    category = request.args.get("category")
    if category:
        templates = template_service.get_templates_by_category(category)
    else:
        templates = template_service.get_all_templates()
    return jsonify({"code": 200, "data": templates})


@template_bp.route("/<string:app>", methods=["GET"])
@jwt_required()
def get_template(app):
    template = template_service.get_template(app)
    if template:
        return jsonify({"code": 200, "data": template})
    return jsonify({"code": 404, "message": "Template not found"}), 404


@template_bp.route("", methods=["POST"])
@jwt_required()
def create_template():
    data = request.get_json()
    app = data.get("app")
    name = data.get("name")
    category = data.get("category")
    content = data.get("content")
    
    if not all([app, name, category, content]):
        return jsonify({"code": 400, "message": "Missing required fields"}), 400
    
    template = template_service.save_template(app, name, category, content)
    return jsonify({"code": 200, "data": template})


@template_bp.route("/<string:app>", methods=["PUT"])
@jwt_required()
def update_template(app):
    data = request.get_json()
    name = data.get("name")
    category = data.get("category")
    content = data.get("content")
    
    if not all([name, category, content]):
        return jsonify({"code": 400, "message": "Missing required fields"}), 400
    
    template = template_service.save_template(app, name, category, content)
    return jsonify({"code": 200, "data": template})


@template_bp.route("/<string:app>", methods=["DELETE"])
@jwt_required()
def delete_template(app):
    success = template_service.delete_template(app)
    if success:
        return jsonify({"code": 200, "message": "Template deleted"})
    return jsonify({"code": 404, "message": "Template not found"}), 404


@template_bp.route("/categories", methods=["GET"])
@jwt_required()
def get_categories():
    categories = template_service.get_all_categories()
    return jsonify({"code": 200, "data": categories})


@template_bp.route("/categories", methods=["POST"])
@jwt_required()
def create_category():
    data = request.get_json()
    name = data.get("name")
    code = data.get("code")
    icon = data.get("icon")
    parent_id = data.get("parent_id")
    
    if not all([name, code]):
        return jsonify({"code": 400, "message": "Missing required fields"}), 400
    
    category = template_service.save_category(name, code, icon, parent_id)
    return jsonify({"code": 200, "data": category})


@template_bp.route("/categories/<string:code>", methods=["PUT"])
@jwt_required()
def update_category(code):
    data = request.get_json()
    name = data.get("name")
    icon = data.get("icon")
    
    if not name:
        return jsonify({"code": 400, "message": "Missing required fields"}), 400
    
    category = template_service.update_category(code, name, icon)
    if category:
        return jsonify({"code": 200, "data": category})
    return jsonify({"code": 404, "message": "Category not found"}), 404


@template_bp.route("/categories/<string:code>", methods=["DELETE"])
@jwt_required()
def delete_category(code):
    success = template_service.delete_category(code)
    if success:
        return jsonify({"code": 200, "message": "Category deleted"})
    return jsonify({"code": 404, "message": "Category not found"}), 404


@template_bp.route("/hierarchy", methods=["GET"])
@jwt_required()
def get_hierarchy():
    lang = request.args.get("lang", "zh-CN")
    hierarchy = template_service.get_template_hierarchy(lang)
    return jsonify({"code": 200, "data": hierarchy})
