"""添加通知模块数据库索引

Revision ID: 004
Revises: 003
Create Date: 2026-02-19

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade():
    # 添加通知表索引
    op.create_index(
        'ix_notifications_sender_id',
        'notifications',
        ['sender_id']
    )
    op.create_index(
        'ix_notifications_type_id',
        'notifications',
        ['type_id']
    )
    op.create_index(
        'ix_notifications_created_at',
        'notifications',
        ['created_at']
    )
    op.create_index(
        'ix_notifications_expires_at',
        'notifications',
        ['expires_at']
    )
    op.create_index(
        'ix_notifications_is_archived',
        'notifications',
        ['is_archived']
    )
    
    # 添加通知接收者表索引
    op.create_index(
        'ix_notification_recipients_user_id',
        'notification_recipients',
        ['user_id']
    )
    op.create_index(
        'ix_notification_recipients_notification_id',
        'notification_recipients',
        ['notification_id']
    )
    op.create_index(
        'ix_notification_recipients_is_read',
        'notification_recipients',
        ['is_read']
    )
    op.create_index(
        'ix_notification_recipients_user_read',
        'notification_recipients',
        ['user_id', 'is_read']
    )
    op.create_index(
        'ix_notification_recipients_delivery_status',
        'notification_recipients',
        ['delivery_status']
    )
    op.create_index(
        'ix_notification_recipients_created_at',
        'notification_recipients',
        ['created_at']
    )


def downgrade():
    # 删除通知表索引
    op.drop_index('ix_notifications_sender_id', table_name='notifications')
    op.drop_index('ix_notifications_type_id', table_name='notifications')
    op.drop_index('ix_notifications_created_at', table_name='notifications')
    op.drop_index('ix_notifications_expires_at', table_name='notifications')
    op.drop_index('ix_notifications_is_archived', table_name='notifications')
    
    # 删除通知接收者表索引
    op.drop_index('ix_notification_recipients_user_id', table_name='notification_recipients')
    op.drop_index('ix_notification_recipients_notification_id', table_name='notification_recipients')
    op.drop_index('ix_notification_recipients_is_read', table_name='notification_recipients')
    op.drop_index('ix_notification_recipients_user_read', table_name='notification_recipients')
    op.drop_index('ix_notification_recipients_delivery_status', table_name='notification_recipients')
    op.drop_index('ix_notification_recipients_created_at', table_name='notification_recipients')
