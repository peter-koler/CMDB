from app import db
from datetime import datetime


class CustomView(db.Model):
    __tablename__ = "custom_views"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.Text)
    icon = db.Column(db.String(50), default="AppstoreOutlined")
    is_active = db.Column(db.Boolean, default=True)
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"))

    nodes = db.relationship(
        "CustomViewNode",
        backref="view",
        lazy="dynamic",
        cascade="all, delete-orphan",
        order_by="CustomViewNode.sort_order",
    )

    def get_node_count(self):
        return self.nodes.count()

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "code": self.code,
            "description": self.description,
            "icon": self.icon,
            "is_active": self.is_active,
            "sort_order": self.sort_order,
            "node_count": self.get_node_count(),
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None,
            "updated_at": self.updated_at.strftime("%Y-%m-%d %H:%M:%S") if self.updated_at else None,
            "created_by": self.created_by,
        }


class CustomViewNode(db.Model):
    __tablename__ = "custom_view_nodes"

    id = db.Column(db.Integer, primary_key=True)
    view_id = db.Column(db.Integer, db.ForeignKey("custom_views.id", ondelete="CASCADE"), nullable=False, index=True)
    parent_id = db.Column(db.Integer, db.ForeignKey("custom_view_nodes.id", ondelete="CASCADE"), index=True)
    name = db.Column(db.String(100), nullable=False)
    sort_order = db.Column(db.Integer, default=0)
    filter_config = db.Column(db.Text, default="null")
    is_active = db.Column(db.Boolean, default=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        db.Index('ix_view_node_parent', 'view_id', 'parent_id'),
        db.Index('ix_view_node_active', 'view_id', 'is_active'),
    )

    children = db.relationship(
        "CustomViewNode",
        backref=db.backref("parent", remote_side=[id]),
        lazy="dynamic",
        cascade="all, delete-orphan",
        order_by="CustomViewNode.sort_order",
    )

    role_permissions = db.relationship(
        "CustomViewNodePermission",
        backref="node",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    def is_root(self):
        return self.parent_id is None

    def get_all_children(self):
        children = []
        for child in self.children:
            children.append(child)
            children.extend(child.get_all_children())
        return children

    def get_ancestors(self):
        ancestors = []
        current = self.parent
        while current:
            ancestors.append(current)
            current = current.parent
        return ancestors

    def get_filter_config(self):
        if not self.filter_config or self.filter_config == "null":
            return None
        try:
            import json
            return json.loads(self.filter_config)
        except Exception:
            return None

    def set_filter_config(self, config_data):
        import json
        self.filter_config = json.dumps(config_data) if config_data else None

    def get_level(self):
        level = 0
        current = self.parent
        while current:
            level += 1
            current = current.parent
        return level

    def to_dict(self, include_children=True):
        result = {
            "id": self.id,
            "view_id": self.view_id,
            "parent_id": self.parent_id,
            "name": self.name,
            "sort_order": self.sort_order,
            "filter_config": self.get_filter_config(),
            "is_active": self.is_active,
            "is_root": self.is_root(),
            "level": self.get_level(),
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None,
            "updated_at": self.updated_at.strftime("%Y-%m-%d %H:%M:%S") if self.updated_at else None,
        }
        if include_children:
            result["children"] = [child.to_dict() for child in self.children.all()]
        return result


class CustomViewNodePermission(db.Model):
    __tablename__ = "custom_view_node_permissions"

    id = db.Column(db.Integer, primary_key=True)
    node_id = db.Column(db.Integer, db.ForeignKey("custom_view_nodes.id", ondelete="CASCADE"), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey("roles.id", ondelete="CASCADE"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

    __table_args__ = (
        db.UniqueConstraint("node_id", "role_id", name="uq_node_role"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "node_id": self.node_id,
            "role_id": self.role_id,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None,
        }
