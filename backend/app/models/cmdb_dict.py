from datetime import datetime

from app import db


class CmdbDictType(db.Model):
    __tablename__ = 'cmdb_dict_types'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(100), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(500))
    enabled = db.Column(db.Boolean, default=True, nullable=False)
    sort_order = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))

    items = db.relationship(
        'CmdbDictItem',
        backref='dict_type',
        lazy='dynamic',
        cascade='all, delete-orphan',
        foreign_keys='CmdbDictItem.type_id'
    )

    def to_dict(self):
        return {
            'id': self.id,
            'code': self.code,
            'name': self.name,
            'description': self.description,
            'enabled': self.enabled,
            'sort_order': self.sort_order,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'created_by': self.created_by
        }

    def save(self):
        db.session.add(self)
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()


class CmdbDictItem(db.Model):
    __tablename__ = 'cmdb_dict_items'

    id = db.Column(db.Integer, primary_key=True)
    type_id = db.Column(db.Integer, db.ForeignKey('cmdb_dict_types.id'), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('cmdb_dict_items.id'))
    code = db.Column(db.String(100), nullable=False)
    label = db.Column(db.String(100), nullable=False)
    enabled = db.Column(db.Boolean, default=True, nullable=False)
    sort_order = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))

    children = db.relationship(
        'CmdbDictItem',
        backref=db.backref('parent', remote_side=[id]),
        lazy='select',
        cascade='all, delete-orphan'
    )

    def to_dict(self):
        return {
            'id': self.id,
            'type_id': self.type_id,
            'parent_id': self.parent_id,
            'code': self.code,
            'label': self.label,
            'enabled': self.enabled,
            'sort_order': self.sort_order,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'created_by': self.created_by
        }

    def save(self):
        db.session.add(self)
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()
