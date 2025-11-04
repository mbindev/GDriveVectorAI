from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, HttpUrl
from typing import Optional, List
from app.services import notification_service
from app.main import get_db_connection
import psycopg2.extras

router = APIRouter()

class WebhookCreate(BaseModel):
    name: str
    url: HttpUrl
    events: List[str]  # e.g., ["job_completed", "job_failed", "document_processed"]
    secret_key: Optional[str] = None

class WebhookUpdate(BaseModel):
    name: Optional[str] = None
    url: Optional[HttpUrl] = None
    events: Optional[List[str]] = None
    is_active: Optional[bool] = None
    secret_key: Optional[str] = None

@router.get("/")
async def get_notifications(
    is_read: Optional[bool] = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """Get notifications."""
    try:
        notifications = notification_service.get_notifications(
            user_id=None,  # TODO: Get from current user
            is_read=is_read,
            limit=limit,
            offset=offset
        )
        unread_count = notification_service.get_unread_count()

        return {
            "notifications": notifications,
            "unread_count": unread_count,
            "total": len(notifications)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch notifications: {str(e)}")

@router.put("/{notification_id}/read")
async def mark_as_read(notification_id: int):
    """Mark a notification as read."""
    try:
        notification_service.mark_notification_read(notification_id)
        return {"message": "Notification marked as read"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to mark notification as read: {str(e)}")

@router.put("/mark-all-read")
async def mark_all_read():
    """Mark all notifications as read."""
    try:
        notification_service.mark_all_notifications_read()
        return {"message": "All notifications marked as read"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to mark all as read: {str(e)}")

@router.get("/unread-count")
async def get_unread_count():
    """Get count of unread notifications."""
    try:
        count = notification_service.get_unread_count()
        return {"unread_count": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get unread count: {str(e)}")

# Webhook management
@router.get("/webhooks")
async def list_webhooks():
    """List all webhook configurations."""
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT id, name, url, events, is_active, created_at, updated_at
                    FROM webhook_configs
                    ORDER BY created_at DESC
                """)
                webhooks = [dict(row) for row in cursor.fetchall()]
                return {"webhooks": webhooks}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch webhooks: {str(e)}")

@router.post("/webhooks")
async def create_webhook(webhook: WebhookCreate):
    """Create a new webhook configuration."""
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute("""
                    INSERT INTO webhook_configs (name, url, events, secret_key, is_active)
                    VALUES (%s, %s, %s, %s, true)
                    RETURNING id, name, url, events, is_active, created_at
                """, (webhook.name, str(webhook.url), webhook.events, webhook.secret_key))
                result = dict(cursor.fetchone())
                conn.commit()
                return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create webhook: {str(e)}")

@router.put("/webhooks/{webhook_id}")
async def update_webhook(webhook_id: int, webhook: WebhookUpdate):
    """Update a webhook configuration."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                updates = []
                params = []

                if webhook.name is not None:
                    updates.append("name = %s")
                    params.append(webhook.name)

                if webhook.url is not None:
                    updates.append("url = %s")
                    params.append(str(webhook.url))

                if webhook.events is not None:
                    updates.append("events = %s")
                    params.append(webhook.events)

                if webhook.is_active is not None:
                    updates.append("is_active = %s")
                    params.append(webhook.is_active)

                if webhook.secret_key is not None:
                    updates.append("secret_key = %s")
                    params.append(webhook.secret_key)

                if not updates:
                    raise HTTPException(status_code=400, detail="No fields to update")

                params.append(webhook_id)
                query = f"UPDATE webhook_configs SET {', '.join(updates)} WHERE id = %s"
                cursor.execute(query, params)
                conn.commit()

                return {"message": "Webhook updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update webhook: {str(e)}")

@router.delete("/webhooks/{webhook_id}")
async def delete_webhook(webhook_id: int):
    """Delete a webhook configuration."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM webhook_configs WHERE id = %s", (webhook_id,))
                conn.commit()
                return {"message": "Webhook deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete webhook: {str(e)}")

@router.post("/webhooks/{webhook_id}/test")
async def test_webhook(webhook_id: int):
    """Test a webhook by sending a test payload."""
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT url, secret_key FROM webhook_configs WHERE id = %s
                """, (webhook_id,))
                webhook = cursor.fetchone()

                if not webhook:
                    raise HTTPException(status_code=404, detail="Webhook not found")

                test_payload = {
                    "event": "test",
                    "message": "This is a test webhook from DriveVectorAI",
                    "timestamp": "2024-01-01T00:00:00Z"
                }

                success = await notification_service.send_webhook_notification(
                    url=webhook['url'],
                    payload=test_payload,
                    secret_key=webhook.get('secret_key')
                )

                if success:
                    return {"message": "Test webhook sent successfully"}
                else:
                    raise HTTPException(status_code=500, detail="Failed to send test webhook")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to test webhook: {str(e)}")
