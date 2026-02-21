"""通知模块后台定时任务"""

from datetime import timedelta

from flask import current_app
from sqlalchemy import func

from app import db
from app.notifications.models import Notification, NotificationRecipient, get_local_now
from app.notifications.websocket import emit_to_user


def cleanup_expired_notifications():
    """清理过期通知
    
    每天运行一次，删除已过期的通知记录
    """
    try:
        current_app.logger.info("开始清理过期通知...")
        
        now = get_local_now()
        
        expired_notifications = Notification.query.filter(
            Notification.expires_at < now
        ).all()
        
        deleted_count = 0
        for notification in expired_notifications:
            # 删除关联的接收者记录
            NotificationRecipient.query.filter_by(
                notification_id=notification.id
            ).delete()
            
            # 删除通知
            db.session.delete(notification)
            deleted_count += 1
        
        db.session.commit()
        
        current_app.logger.info(f"清理完成，删除了 {deleted_count} 条过期通知")
        return deleted_count
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"清理过期通知失败: {e}")
        return 0


def retry_failed_deliveries():
    """重试失败的推送
    
    每小时运行一次，重试之前推送失败的通知
    """
    try:
        current_app.logger.info("开始重试失败的推送...")
        
        one_day_ago = get_local_now() - timedelta(hours=24)
        
        failed_recipients = NotificationRecipient.query.filter(
            NotificationRecipient.delivery_status == 'failed',
            NotificationRecipient.created_at > one_day_ago
        ).all()
        
        retry_count = 0
        for recipient in failed_recipients:
            try:
                # 重新推送
                notification = Notification.query.get(recipient.notification_id)
                if notification:
                    notification_data = notification.to_dict()
                    notification_data["recipient_id"] = recipient.id
                    emit_to_user(recipient.user_id, "notification:new", notification_data)
                    
                    # 更新状态
                    recipient.delivery_status = 'delivered'
                    retry_count += 1
                    
            except Exception as e:
                current_app.logger.warning(
                    f"重试推送通知 {recipient.notification_id} 到用户 {recipient.user_id} 失败: {e}"
                )
        
        db.session.commit()
        
        current_app.logger.info(f"重试完成，成功重试 {retry_count} 条通知")
        return retry_count
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"重试失败推送失败: {e}")
        return 0


def generate_notification_stats():
    """生成通知统计报告
    
    每天运行一次，生成前一天的统计报告
    """
    try:
        current_app.logger.info("开始生成通知统计报告...")
        
        yesterday = get_local_now() - timedelta(days=1)
        start_of_day = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        # 统计发送的通知数量
        sent_count = Notification.query.filter(
            Notification.created_at >= start_of_day,
            Notification.created_at <= end_of_day
        ).count()
        
        # 统计接收者数量
        recipient_count = NotificationRecipient.query.filter(
            NotificationRecipient.created_at >= start_of_day,
            NotificationRecipient.created_at <= end_of_day
        ).count()
        
        # 统计已读数量
        read_count = NotificationRecipient.query.filter(
            NotificationRecipient.created_at >= start_of_day,
            NotificationRecipient.created_at <= end_of_day,
            NotificationRecipient.is_read.is_(True)
        ).count()
        
        # 统计各类型通知数量
        type_stats = db.session.query(
            Notification.type_id,
            func.count(Notification.id).label('count')
        ).filter(
            Notification.created_at >= start_of_day,
            Notification.created_at <= end_of_day
        ).group_by(Notification.type_id).all()
        
        # 记录统计结果
        stats = {
            'date': yesterday.strftime('%Y-%m-%d'),
            'sent_count': sent_count,
            'recipient_count': recipient_count,
            'read_count': read_count,
            'read_rate': round(read_count / recipient_count * 100, 2) if recipient_count > 0 else 0,
            'type_stats': [{'type_id': t[0], 'count': t[1]} for t in type_stats]
        }
        
        current_app.logger.info(f"通知统计报告: {stats}")
        
        # TODO: 可以将统计结果保存到数据库或发送到监控系统
        
        return stats
        
    except Exception as e:
        current_app.logger.error(f"生成通知统计报告失败: {e}")
        return None


def archive_old_notifications():
    """归档旧通知
    
    每周运行一次，将90天前的通知归档（软删除）
    """
    try:
        current_app.logger.info("开始归档旧通知...")
        
        archive_date = get_local_now() - timedelta(days=90)
        
        old_notifications = Notification.query.filter(
            Notification.created_at < archive_date,
            Notification.is_archived.is_(False)
        ).all()
        
        archived_count = 0
        for notification in old_notifications:
            notification.is_archived = True
            archived_count += 1
        
        db.session.commit()
        
        current_app.logger.info(f"归档完成，归档了 {archived_count} 条旧通知")
        return archived_count
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"归档旧通知失败: {e}")
        return 0


# 任务调度配置
SCHEDULED_TASKS = [
    {
        'id': 'cleanup_expired_notifications',
        'func': cleanup_expired_notifications,
        'trigger': 'cron',
        'hour': 2,  # 每天凌晨2点运行
        'minute': 0
    },
    {
        'id': 'retry_failed_deliveries',
        'func': retry_failed_deliveries,
        'trigger': 'interval',
        'hours': 1  # 每小时运行一次
    },
    {
        'id': 'generate_notification_stats',
        'func': generate_notification_stats,
        'trigger': 'cron',
        'hour': 1,  # 每天凌晨1点运行
        'minute': 0
    },
    {
        'id': 'archive_old_notifications',
        'func': archive_old_notifications,
        'trigger': 'cron',
        'day_of_week': 'sun',  # 每周日凌晨运行
        'hour': 3,
        'minute': 0
    }
]
