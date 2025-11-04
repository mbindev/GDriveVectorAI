import os
import json
import httpx
from typing import Optional, Dict, List
from datetime import datetime
from app.main import get_db_connection
import psycopg2.extras
import logging

logger = logging.getLogger(__name__)

# Email configuration
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", "noreply@drivevectorai.local")

async def send_email_notification(to_email: str, subject: str, body: str):
    """Send email notification using aiosmtplib."""
    if not SMTP_USER or not SMTP_PASSWORD:
        logger.warning("SMTP not configured, skipping email notification")
        return False

    try:
        import aiosmtplib
        from email.message import EmailMessage

        message = EmailMessage()
        message["From"] = SMTP_FROM
        message["To"] = to_email
        message["Subject"] = subject
        message.set_content(body)

        await aiosmtplib.send(
            message,
            hostname=SMTP_HOST,
            port=SMTP_PORT,
            username=SMTP_USER,
            password=SMTP_PASSWORD,
            start_tls=True,
        )
        logger.info(f"Email sent to {to_email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email: {str(e)}")
        return False

async def send_webhook_notification(url: str, payload: Dict, secret_key: Optional[str] = None):
    """Send webhook notification."""
    try:
        import hmac
        import hashlib

        headers = {"Content-Type": "application/json"}

        # Add signature if secret key is provided
        if secret_key:
            payload_str = json.dumps(payload)
            signature = hmac.new(
                secret_key.encode(),
                payload_str.encode(),
                hashlib.sha256
            ).hexdigest()
            headers["X-Webhook-Signature"] = signature

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                json=payload,
                headers=headers,
                timeout=10.0
            )
            response.raise_for_status()
            logger.info(f"Webhook sent to {url}")
            return True
    except Exception as e:
        logger.error(f"Failed to send webhook: {str(e)}")
        return False

def create_notification(
    user_id: Optional[int],
    notification_type: str,
    category: str,
    title: str,
    message: str,
    metadata: Optional[Dict] = None
):
    """Create a notification in the database."""
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO notifications (user_id, type, category, title, message, metadata)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (user_id, notification_type, category, title, message, json.dumps(metadata) if metadata else None))
            notification_id = cursor.fetchone()[0]
            conn.commit()
            return notification_id

async def notify_job_completed(job_id: str, total_files: int, failed_files: int):
    """Send notifications when a job completes."""
    try:
        from app.services.vector_db_service import get_job_status

        job = get_job_status(job_id)
        if not job:
            return

        title = "Ingestion Job Completed"
        message = f"Job {job_id[:8]} completed: {total_files - failed_files}/{total_files} files processed successfully"

        if failed_files > 0:
            message += f" ({failed_files} failed)"

        # Create in-app notification
        create_notification(
            user_id=None,  # System notification
            notification_type="in_app",
            category="job_completed",
            title=title,
            message=message,
            metadata={"job_id": job_id, "total_files": total_files, "failed_files": failed_files}
        )

        # Send webhooks
        await send_webhooks_for_event("job_completed", {
            "event": "job_completed",
            "job_id": job_id,
            "total_files": total_files,
            "processed_files": total_files,
            "failed_files": failed_files,
            "timestamp": datetime.utcnow().isoformat()
        })

        logger.info(f"Notifications sent for job {job_id}")
    except Exception as e:
        logger.error(f"Failed to send job completion notifications: {str(e)}")

async def notify_job_failed(job_id: str, error_message: str):
    """Send notifications when a job fails."""
    try:
        title = "Ingestion Job Failed"
        message = f"Job {job_id[:8]} failed: {error_message}"

        # Create in-app notification
        create_notification(
            user_id=None,
            notification_type="in_app",
            category="job_failed",
            title=title,
            message=message,
            metadata={"job_id": job_id, "error": error_message}
        )

        # Send webhooks
        await send_webhooks_for_event("job_failed", {
            "event": "job_failed",
            "job_id": job_id,
            "error_message": error_message,
            "timestamp": datetime.utcnow().isoformat()
        })

        logger.info(f"Failure notifications sent for job {job_id}")
    except Exception as e:
        logger.error(f"Failed to send job failure notifications: {str(e)}")

async def send_webhooks_for_event(event_type: str, payload: Dict):
    """Send webhooks for a specific event type."""
    try:
        webhooks = get_active_webhooks_for_event(event_type)
        for webhook in webhooks:
            await send_webhook_notification(
                url=webhook['url'],
                payload=payload,
                secret_key=webhook.get('secret_key')
            )
    except Exception as e:
        logger.error(f"Failed to send webhooks for event {event_type}: {str(e)}")

def get_active_webhooks_for_event(event_type: str) -> List[Dict]:
    """Get active webhooks configured for a specific event."""
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute("""
                SELECT id, name, url, events, secret_key
                FROM webhook_configs
                WHERE is_active = true AND %s = ANY(events)
            """, (event_type,))
            return [dict(row) for row in cursor.fetchall()]

def get_notifications(
    user_id: Optional[int] = None,
    is_read: Optional[bool] = None,
    limit: int = 50,
    offset: int = 0
) -> List[Dict]:
    """Get notifications with filtering."""
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            query = "SELECT * FROM notifications WHERE 1=1"
            params = []

            if user_id is not None:
                query += " AND (user_id = %s OR user_id IS NULL)"
                params.append(user_id)

            if is_read is not None:
                query += " AND is_read = %s"
                params.append(is_read)

            query += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
            params.extend([limit, offset])

            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

def mark_notification_read(notification_id: int):
    """Mark a notification as read."""
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                UPDATE notifications SET is_read = true WHERE id = %s
            """, (notification_id,))
            conn.commit()

def mark_all_notifications_read(user_id: Optional[int] = None):
    """Mark all notifications as read for a user."""
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            if user_id:
                cursor.execute("""
                    UPDATE notifications SET is_read = true
                    WHERE user_id = %s OR user_id IS NULL
                """, (user_id,))
            else:
                cursor.execute("UPDATE notifications SET is_read = true")
            conn.commit()

def get_unread_count(user_id: Optional[int] = None) -> int:
    """Get count of unread notifications."""
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            if user_id:
                cursor.execute("""
                    SELECT COUNT(*) FROM notifications
                    WHERE is_read = false AND (user_id = %s OR user_id IS NULL)
                """, (user_id,))
            else:
                cursor.execute("""
                    SELECT COUNT(*) FROM notifications WHERE is_read = false
                """)
            return cursor.fetchone()[0]
