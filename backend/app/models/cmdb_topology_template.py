from __future__ import annotations

import json
import uuid
from datetime import datetime

from app import db


class CmdbTopologyTemplate(db.Model):
    __tablename__ = "cmdb_topology_templates"

    id = db.Column(db.String(64), primary_key=True, default=lambda: f"tpl-{uuid.uuid4().hex[:16]}")
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=False, default="")

    seed_models = db.Column(db.Text, nullable=False, default="[]")
    traverse_direction = db.Column(db.String(16), nullable=False, default="both")
    allowed_relation_types = db.Column(db.Text, nullable=False, default="[]")
    visible_model_keys = db.Column(db.Text, nullable=False, default="[]")
    layers = db.Column(db.Text, nullable=False, default="[]")

    layout_direction = db.Column(db.String(16), nullable=False, default="horizontal")
    group_by = db.Column(db.String(32), nullable=False, default="idc")
    aggregate_enabled = db.Column(db.Boolean, nullable=False, default=True)
    aggregate_threshold = db.Column(db.Integer, nullable=False, default=4)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    updated_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    creator = db.relationship("User", foreign_keys=[created_by], lazy="joined")
    updater = db.relationship("User", foreign_keys=[updated_by], lazy="joined")

    @staticmethod
    def _safe_load_json_list(raw: str, fallback=None):
        if fallback is None:
            fallback = []
        if not raw:
            return fallback
        try:
            data = json.loads(raw)
            return data if isinstance(data, list) else fallback
        except Exception:
            return fallback

    @staticmethod
    def _dump_json(value):
        return json.dumps(value if value is not None else [], ensure_ascii=False)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description or "",
            "seedModels": self._safe_load_json_list(self.seed_models),
            "traverseDirection": self.traverse_direction,
            "allowedRelationTypes": self._safe_load_json_list(self.allowed_relation_types),
            "visibleModelKeys": self._safe_load_json_list(self.visible_model_keys),
            "layers": self._safe_load_json_list(self.layers),
            "layoutDirection": self.layout_direction,
            "groupBy": self.group_by,
            "aggregateEnabled": bool(self.aggregate_enabled),
            "aggregateThreshold": int(self.aggregate_threshold or 0),
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "updatedAt": self.updated_at.isoformat() if self.updated_at else None,
            "createdBy": self.created_by,
            "updatedBy": self.updated_by,
        }

    def apply_payload(self, payload: dict, operator_id: int | None = None):
        self.name = str(payload.get("name") or self.name or "").strip()
        self.description = str(payload.get("description") or "").strip()

        self.seed_models = self._dump_json(payload.get("seedModels") or [])
        self.traverse_direction = str(payload.get("traverseDirection") or "both").strip() or "both"
        self.allowed_relation_types = self._dump_json(payload.get("allowedRelationTypes") or [])
        self.visible_model_keys = self._dump_json(payload.get("visibleModelKeys") or [])
        self.layers = self._dump_json(payload.get("layers") or [])

        self.layout_direction = str(payload.get("layoutDirection") or "horizontal").strip() or "horizontal"
        self.group_by = str(payload.get("groupBy") or "idc").strip() or "idc"
        self.aggregate_enabled = bool(payload.get("aggregateEnabled", True))
        self.aggregate_threshold = max(2, int(payload.get("aggregateThreshold") or 2))

        if operator_id:
            if not self.created_by:
                self.created_by = operator_id
            self.updated_by = operator_id
