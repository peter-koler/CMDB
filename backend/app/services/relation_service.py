import json
from typing import Any

from sqlalchemy.exc import IntegrityError

from app import db
from app.models.ci_instance import CiInstance
from app.models.cmdb_relation import CmdbRelation, RelationType


class RelationServiceError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _parse_json_array(value: Any) -> list[int]:
    if not value:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            data = json.loads(value)
            return data if isinstance(data, list) else []
        except Exception:
            return []
    return []


def parse_relation_style(value: Any) -> dict:
    if not value:
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            data = json.loads(value)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}
    return {}


def validate_relation_constraints(
    source_ci: CiInstance,
    target_ci: CiInstance,
    relation_type: RelationType,
    exclude_relation_id: int | None = None,
):
    # 1. 唯一性检查
    duplicate_query = CmdbRelation.query.filter_by(
        source_ci_id=source_ci.id,
        target_ci_id=target_ci.id,
        relation_type_id=relation_type.id,
    )
    if exclude_relation_id:
        duplicate_query = duplicate_query.filter(CmdbRelation.id != exclude_relation_id)
    if duplicate_query.first():
        raise RelationServiceError("该关系已存在", 400)

    # 双向关系禁止同类型反向重复
    if relation_type.direction == "bidirectional":
        reverse_query = CmdbRelation.query.filter_by(
            source_ci_id=target_ci.id,
            target_ci_id=source_ci.id,
            relation_type_id=relation_type.id,
        )
        if exclude_relation_id:
            reverse_query = reverse_query.filter(CmdbRelation.id != exclude_relation_id)
        if reverse_query.first():
            raise RelationServiceError("双向关系已存在（反向重复）", 400)

    # 2. 自环检查
    if not relation_type.allow_self_loop and source_ci.id == target_ci.id:
        raise RelationServiceError("不允许创建自环关系", 400)

    # 3. 模型白名单检查
    source_model_ids = _parse_json_array(relation_type.source_model_ids)
    target_model_ids = _parse_json_array(relation_type.target_model_ids)

    if source_model_ids and source_ci.model_id not in source_model_ids:
        raise RelationServiceError("该关系类型不允许此源模型", 400)

    if target_model_ids and target_ci.model_id not in target_model_ids:
        raise RelationServiceError("该关系类型不允许此目标模型", 400)

    # 4. 基数限制检查
    if relation_type.cardinality == "one_one":
        source_query = CmdbRelation.query.filter_by(
            source_ci_id=source_ci.id, relation_type_id=relation_type.id
        )
        target_query = CmdbRelation.query.filter_by(
            target_ci_id=target_ci.id, relation_type_id=relation_type.id
        )
        if exclude_relation_id:
            source_query = source_query.filter(CmdbRelation.id != exclude_relation_id)
            target_query = target_query.filter(CmdbRelation.id != exclude_relation_id)

        if source_query.count() > 0:
            raise RelationServiceError("源端已有此类型关系（1:1限制）", 400)
        if target_query.count() > 0:
            raise RelationServiceError("目标端已有此类型关系（1:1限制）", 400)

    if relation_type.cardinality == "one_many":
        target_query = CmdbRelation.query.filter_by(
            target_ci_id=target_ci.id, relation_type_id=relation_type.id
        )
        if exclude_relation_id:
            target_query = target_query.filter(CmdbRelation.id != exclude_relation_id)
        if target_query.count() > 0:
            raise RelationServiceError("目标端已有此类型关系（1:N限制）", 400)


def create_relation_with_validation(
    source_ci_id: int,
    target_ci_id: int,
    relation_type_id: int,
    source_type: str = "manual",
) -> CmdbRelation:
    source_ci = CiInstance.query.get(source_ci_id)
    target_ci = CiInstance.query.get(target_ci_id)
    relation_type = RelationType.query.get(relation_type_id)

    if not source_ci or not target_ci or not relation_type:
        raise RelationServiceError("资源不存在", 404)

    validate_relation_constraints(source_ci, target_ci, relation_type)

    relation = CmdbRelation(
        source_ci_id=source_ci_id,
        target_ci_id=target_ci_id,
        relation_type_id=relation_type_id,
        source_type=source_type,
    )
    db.session.add(relation)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise RelationServiceError("该关系已存在", 400)

    return relation
