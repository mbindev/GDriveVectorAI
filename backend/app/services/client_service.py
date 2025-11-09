"""
Client Management Service
Basic CRUD operations for clients.
"""
import psycopg2
from typing import List, Dict, Optional, Any
import logging

logger = logging.getLogger(__name__)


def get_db_connection():
    """Get database connection using existing credentials."""
    from app.services.vector_db_service import get_db_connection as get_conn
    return get_conn()


def create_client(name: str, brand_id: Optional[int] = None, contact_email: Optional[str] = None,
                 contact_phone: Optional[str] = None, company: Optional[str] = None,
                 notes: Optional[str] = None, created_by: Optional[int] = None) -> Dict[str, Any]:
    """Create a new client."""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO clients (name, brand_id, contact_email, contact_phone, company, notes, created_by, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, name, brand_id, contact_email, contact_phone, company, notes, is_active, created_at
        """, (name, brand_id, contact_email, contact_phone, company, notes, created_by, True))
        row = cur.fetchone()
        conn.commit()
        return {"id": row[0], "name": row[1], "brand_id": row[2], "contact_email": row[3],
                "contact_phone": row[4], "company": row[5], "notes": row[6], "is_active": row[7],
                "created_at": row[8].isoformat() if row[8] else None}
    finally:
        cur.close()
        conn.close()


def list_clients(brand_id: Optional[int] = None, is_active: Optional[bool] = None,
                limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
    """List clients with optional filtering."""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        query = "SELECT id, name, brand_id, contact_email, contact_phone, company, is_active, created_at FROM clients WHERE 1=1"
        params = []
        if brand_id is not None:
            query += " AND brand_id = %s"
            params.append(brand_id)
        if is_active is not None:
            query += " AND is_active = %s"
            params.append(is_active)
        query += " ORDER BY name ASC LIMIT %s OFFSET %s"
        params.extend([limit, offset])
        cur.execute(query, params)
        return [{"id": r[0], "name": r[1], "brand_id": r[2], "contact_email": r[3], 
                 "contact_phone": r[4], "company": r[5], "is_active": r[6],
                 "created_at": r[7].isoformat() if r[7] else None} for r in cur.fetchall()]
    finally:
        cur.close()
        conn.close()


def get_client(client_id: int) -> Optional[Dict[str, Any]]:
    """Get a client by ID."""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id, name, brand_id, contact_email, contact_phone, company, notes, is_active, created_at FROM clients WHERE id = %s", (client_id,))
        row = cur.fetchone()
        if not row:
            return None
        return {"id": row[0], "name": row[1], "brand_id": row[2], "contact_email": row[3],
                "contact_phone": row[4], "company": row[5], "notes": row[6], "is_active": row[7],
                "created_at": row[8].isoformat() if row[8] else None}
    finally:
        cur.close()
        conn.close()


def update_client(client_id: int, **kwargs) -> Optional[Dict[str, Any]]:
    """Update client information."""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        updates, params = [], []
        for key in ['name', 'brand_id', 'contact_email', 'contact_phone', 'company', 'notes', 'is_active']:
            if key in kwargs and kwargs[key] is not None:
                updates.append(f"{key} = %s")
                params.append(kwargs[key])
        if not updates:
            return get_client(client_id)
        params.append(client_id)
        cur.execute(f"UPDATE clients SET {', '.join(updates)} WHERE id = %s RETURNING id", params)
        if cur.fetchone():
            conn.commit()
            return get_client(client_id)
        return None
    finally:
        cur.close()
        conn.close()


def delete_client(client_id: int) -> bool:
    """Delete a client."""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM clients WHERE id = %s", (client_id,))
        deleted = cur.rowcount > 0
        conn.commit()
        return deleted
    finally:
        cur.close()
        conn.close()
